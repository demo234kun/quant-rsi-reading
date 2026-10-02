"""
通用符号因子进化循环：变异 -> 评估 -> 选择，多轮迭代。
是多个“因子/数据进化”论文方法的公共基座；各论文方法在其上定制差异。

仅使用 validation 段做选择（fit 阶段），test 段不参与。
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from .data import Dataset
from .expr import eval_expression
from .interface import BaselineMethod
from .llm import RuleBasedLLM, get_llm
from .evaluator import cross_section_ic_series

SEED_EXPRESSIONS = [
    "cs_rank(delta($close, 5))",
    "cs_rank(rolling_mean($close, 20) / $close)",
    "cs_rank(-rolling_std($close, 20))",
    "cs_rank(rolling_mean($volume, 5) / rolling_mean($volume, 20))",
    "cs_rank(delta($close, 20) / rolling_std($close, 20))",
    "cs_rank(rolling_corr($close, $volume, 10))",
]


class SymbolicEvolutionBase(BaselineMethod):
    """通用种群式符号进化。"""

    def __init__(
        self,
        name: str = "symbolic_evolution",
        category: str = "factor_evolution",
        paper_id: str = "",
        seeds: Optional[List[str]] = None,
        rounds: int = 4,
        pop_size: int = 10,
        n_mutants_per_round: int = 6,
        llm=None,
        seed: Optional[int] = 0,
        fidelity: str = "llm_replaced_by_rule",
        notes: str = "LLM 用规则变异替代（无 API key）；进化循环忠实",
    ):
        self.name = name
        self.category = category
        self.paper_id = paper_id
        self.seeds = seeds or SEED_EXPRESSIONS
        self.rounds = rounds
        self.pop_size = pop_size
        self.n_mutants = n_mutants_per_round
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.fidelity = fidelity
        self.notes = notes
        self.best_expr: Optional[str] = None
        self.history: List[dict] = []

    def _eval_ic(self, expr: str, panel: pd.DataFrame, fwd: pd.Series):
        try:
            sig = eval_expression(expr, panel)
            pic, _ = cross_section_ic_series(sig, fwd)
            if len(pic) == 0:
                return np.nan
            return pic.mean()
        except Exception:
            return np.nan

    def fit(self, ds: Dataset):
        # 用 validation 段做选择
        cols = ["open", "high", "low", "close", "volume", "ret"]
        val_panel = ds.panel[ds.panel.index.get_level_values(0).isin(ds.val_dates)][cols]
        val_fwd = ds.fwd_ret_on("validation")

        pool: dict[str, float] = {}
        for e in self.seeds:
            pool[e] = self._eval_ic(e, val_panel, val_fwd)

        for r in range(self.rounds):
            scored = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            parents = [e for e, _ in scored[: max(1, self.pop_size // 2)]]
            for _ in range(self.n_mutants):
                parent = parents[np.random.randint(len(parents))] if parents else self.seeds[0]
                parent_ic = pool.get(parent, np.nan)
                fb = f"val IC={parent_ic:.4f}"
                cand = self.llm.mutate(parent, fb)
                if cand not in pool:
                    pool[cand] = self._eval_ic(cand, val_panel, val_fwd)
            # 保留 top
            scored = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            keep = dict(scored[: self.pop_size])
            self.history.append({"round": r, "best_ic": scored[0][1], "best_expr": scored[0][0],
                                 "n_evaluated": len(pool)})
            pool = {**keep, **{e: v for e, v in scored[self.pop_size:self.pop_size + 2]}}
        scored = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
        self.best_expr = scored[0][0]
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        dates = {"train": ds.train_dates, "validation": ds.val_dates, "test": ds.test_dates}[split]
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        return eval_expression(self.best_expr, panel)
