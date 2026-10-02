"""
静态因子库：不进化的手工因子，作为所有进化方法的公共对照 baseline。
也用于验证表达式引擎与统一评估管线。
"""
from __future__ import annotations
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression
from core.interface import BaselineMethod


class FixedExpressionMethod(BaselineMethod):
    """固定表达式因子，不做任何进化。"""

    def __init__(self, name: str, expression: str, category: str = "handcrafted",
                 paper_id: str = "baseline", notes: str = "静态手工因子（对照）"):
        self.name = name
        self.expression = expression
        self.category = category
        self.paper_id = paper_id
        self.fidelity = "faithful_core"
        self.notes = notes

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        cols = ["open", "high", "low", "close", "volume", "ret"]
        # 用 split 及之前全部历史完成 warmup，最后只保留目标 split
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(ds.dates_through(split))][cols]
        s = eval_expression(self.expression, panel)
        target_dates = ds._dates_of(split)
        return s[s.index.get_level_values(0).isin(target_dates)]


# 常见手工因子（经典量化 baseline）
HANDFACTORS = {
    "momentum_20": "cs_rank(delta($close, 20) / $close)",
    "reversal_5": "cs_rank(-delta($close, 5) / $close)",
    "low_vol_20": "cs_rank(-rolling_std($close, 20))",
    "volume_ratio": "cs_rank(rolling_mean($volume, 5) / rolling_mean($volume, 20))",
}
