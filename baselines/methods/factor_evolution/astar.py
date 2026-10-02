"""
Astar（03）复现。

论文核心：一个 8B 专用模型只做一件事——提出 AI 系统下一步演化方向
（工业闭环、pairwise 数据、奖励模型、GRPO）。在 Lazada 广告召回无人值守多轮。

本复现把“方向提案”用于量化因子：
  - 每轮 proposer 从当前系统状态（当前最优 + 证据）出发，
    批量生成多个不同方向的候选（强制不同变异类型：换字段/换窗口/换算子/包裹）
  - 评估并采纳最优方向，迭代（方向提案驱动的递归）
  - 无 LLM 时用规则的多方向提案替代
论文的广告召回/工业 A/B 与 GRPO 权重训练未复现。
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression, _preprocess
from core.interface import BaselineMethod
from core.evaluator import cross_section_ic_series
from core.evolution import SEED_EXPRESSIONS
import ast


class Astar(BaselineMethod):
    def __init__(self, rounds: int = 5, llm=None, seed: Optional[int] = 0):
        self.name = "astar"
        self.category = "factor_evolution"
        self.paper_id = "03"
        self.fidelity = "llm_replaced_by_rule"
        self.notes = "方向提案驱动的递归进化机制忠实；8B 提案模型/GRPO/广告场景未复现"
        self.rounds = rounds
        self.best_expr: Optional[str] = None
        self.rng = np.random.RandomState(seed)

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

    def _direction_proposals(self, current: str) -> List[str]:
        """模拟 proposer 一次性提出多个不同方向。"""
        from core.llm import RuleBasedLLM
        proposers = [RuleBasedLLM(seed=i) for i in range(4)]
        out = []
        for p in proposers:
            c = p.mutate(current, "propose next direction")
            if c not in out:
                out.append(c)
        return out

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")
        scores = {e: self._ic(e, val_panel, val_fwd) for e in SEED_EXPRESSIONS}

        for r in range(self.rounds):
            current = max(scores, key=lambda e: abs(scores[e]) if np.isfinite(scores[e]) else 0)
            for cand in self._direction_proposals(current):
                if cand not in scores:
                    scores[cand] = self._ic(cand, val_panel, val_fwd)
        self.best_expr = max(scores, key=lambda e: abs(scores[e]) if np.isfinite(scores[e]) else 0)
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        s = eval_expression(self.best_expr, self._panel(ds, ds.dates_through(split)))
        return s[s.index.get_level_values(0).isin(ds._dates_of(split))]
