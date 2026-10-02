"""
AQuA（01）复现。

论文核心：密封沙箱 + 双隔离闭环 + 证据库；因子侧多智能体符号挖掘，
组合信号的 IC 强度来自多个有效因子的组合。

本复现落地因子侧：
  - 密封沙箱：智能体只能改因子表达式，不能改数据/切分/评估器（由本框架结构保证）
  - 证据库：append-only，所有候选（含失败）都记录
  - 递归进化：多轮变异-评估-选择（无 LLM 时用规则变异）
  - 因子组合：取 val top-K 因子，按 val IC 方向/大小加权合成（论文强调强度来自组合）
论文的“时序模型开发子系统”完全隔离，未在本方法内复现（见 rd_agent 的 model arm）。
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression
from core.interface import BaselineMethod
from core.llm import RuleBasedLLM
from core.evaluator import cross_section_ic_series
from core.evolution import SEED_EXPRESSIONS


class AQuA(BaselineMethod):
    def __init__(self, rounds: int = 4, pop_size: int = 10, top_k: int = 4,
                 llm=None, seed: Optional[int] = 0):
        self.name = "aqua"
        self.category = "factor_evolution"
        self.paper_id = "01"
        self.fidelity = "llm_replaced_by_rule"
        self.notes = "密封沙箱、append-only 证据库、递归进化、因子组合忠实；LLM 用规则变异替代"
        self.rounds = rounds
        self.pop_size = pop_size
        self.top_k = top_k
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.evidence: List[dict] = []
        self.selected: List[tuple[str, float]] = []   # (expr, val_ic)

    def _panel(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]

    def _ic(self, expr, panel, fwd):
        try:
            sig = eval_expression(expr, panel)
            pic, _ = cross_section_ic_series(sig, fwd)
            return pic.mean() if len(pic) else np.nan
        except Exception as e:
            return np.nan

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")
        pool: dict[str, float] = {}

        def evaluate(expr):
            ic = self._ic(expr, val_panel, val_fwd)
            self.evidence.append({"expr": expr, "val_ic": None if np.isnan(ic) else float(ic)})
            pool[expr] = ic

        for e in SEED_EXPRESSIONS:
            evaluate(e)
        for r in range(self.rounds):
            ranked = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            parents = [e for e, _ in ranked[: self.pop_size // 2]]
            for _ in range(6):
                p = parents[np.random.randint(len(parents))]
                cand = self.llm.mutate(p, f"val IC={pool[p]:.3f}")
                if cand not in pool:
                    evaluate(cand)
            ranked = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            pool = dict(ranked[: self.pop_size])
        ranked = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
        self.selected = [(e, v) for e, v in ranked[: self.top_k]]
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        panel = self._panel(ds, ds.dates_through(split))
        # 因子组合：横截面 z-score，按 val IC 加权（IC 符号即方向）
        comp = None
        total_w = 0.0
        for expr, ic in self.selected:
            sig = eval_expression(expr, panel)
            z = sig.groupby(level=0).transform(
                lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)
            w = abs(ic) if np.isfinite(ic) else 0.0
            sign = 1.0 if (ic if np.isfinite(ic) else 0) >= 0 else -1.0
            comp = z * w * sign if comp is None else comp + z * w * sign
            total_w += w
        s = comp / total_w if total_w else comp
        return s[s.index.get_level_values(0).isin(ds._dates_of(split))]
