"""
AutoScientist-Quant（06）复现。

论文核心：把量化研究当作预算搜索；单一 controller 根据剩余预算统一调度
“假设 -> 实验 -> （deployable）策略”，共享 memory。

本复现：
  - 固定评估预算（budget），controller 按剩余预算切换策略：
      前期 explore（广泛新假设），后期 exploit（围绕当前最优深挖）
  - 共享 memory：所有候选与结果集中保存
  - 无 LLM 时结构变异用规则替代
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression
from core.interface import BaselineMethod
from core.llm import RuleBasedLLM
from core.evaluator import cross_section_ic_series
from core.evolution import SEED_EXPRESSIONS


class AutoScientist(BaselineMethod):
    def __init__(self, budget: int = 30, explore_frac: float = 0.6,
                 llm=None, seed: Optional[int] = 0):
        self.name = "auto_scientist"
        self.category = "factor_evolution"
        self.paper_id = "06"
        self.fidelity = "llm_replaced_by_rule"
        self.notes = "预算搜索 controller 与共享 memory 忠实；LLM 用规则变异替代"
        self.budget = budget
        self.explore_frac = explore_frac
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.memory = {}
        self.best_expr: Optional[str] = None

    def _panel(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]

    def _ic(self, expr, panel, fwd):
        try:
            sig = eval_expression(expr, panel)
            pic, _ = cross_section_ic_series(sig, fwd)
            return pic.mean() if len(pic) else np.nan
        except Exception:
            return np.nan

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")

        for e in SEED_EXPRESSIONS:
            self.memory[e] = self._ic(e, val_panel, val_fwd)
        used = len(self.memory)

        def current_best():
            return sorted(self.memory.items(),
                          key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)[0]

        while used < self.budget:
            phase_explore = used < self.budget * self.explore_frac
            best_expr, _ = current_best()
            if phase_explore:
                keys = [k for k, v in self.memory.items() if np.isfinite(v)]
                parent = keys[np.random.randint(len(keys))] if keys else SEED_EXPRESSIONS[0]
            else:
                parent = best_expr
            cand = self.llm.mutate(parent, f"val IC={self.memory.get(parent):.3f}")
            if cand not in self.memory:
                self.memory[cand] = self._ic(cand, val_panel, val_fwd)
                used += 1
        self.best_expr = current_best()[0]
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        s = eval_expression(self.best_expr, self._panel(ds, ds.dates_through(split)))
        return s[s.index.get_level_values(0).isin(ds._dates_of(split))]
