"""
AlgoEvolve（10）复现。

论文核心：bi-level meta-evolution
  - Inner Loop：LLM 作为语义变异算子，进化可执行 Python 交易策略（程序），
    walk-forward 评估（fitness = α·Total Return + (1-α)·Consistency）
  - Outer Loop：进化 Evolver Prompt（搜索启发式本身：变异方式 / focus / 强度）
  - Meta-crossover：组合 elite heuristic

本复现：
  - Inner：技术指标加权“交易程序”，按经验逐轮更新（同 EvolveTrade 的 inner）
  - Outer：对多种搜索启发式（focus 先验 + 变异尺度）各跑一次 inner，
    选择表现最好的 heuristic（即进化搜索启发式）
  - 无 LLM，inner 反馈与 outer 选择用真实 val 表现，fidelity 标注
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.evaluator import cross_section_ic_series

HEURISTICS = {
    "trend_focus": {"rsi14": 0.0, "ema20_gap": 0.35, "macd_hist": 0.35,
                    "atr_pct": 0.0, "boll_pos": 0.0, "mom10": 0.3},
    "mean_revert_focus": {"rsi14": 0.3, "ema20_gap": 0.0, "macd_hist": 0.0,
                          "atr_pct": 0.1, "boll_pos": 0.4, "mom10": 0.2},
    "balanced": {"rsi14": 0.15, "ema20_gap": 0.2, "macd_hist": 0.2,
                 "atr_pct": 0.1, "boll_pos": 0.15, "mom10": 0.2},
}


class AlgoEvolve(BaselineMethod):
    def __init__(self, inner_rounds: int = 3, lr: float = 0.5, seed: Optional[int] = 0):
        self.name = "algo_evolve"
        self.category = "strategy_evolution"
        self.paper_id = "10"
        self.fidelity = "meta_evolution_approx"
        self.notes = "双层元进化机制（内层程序进化、外层选择搜索启发式）忠实；LLM 变异用规则/经验替代"
        self.inner_rounds = inner_rounds
        self.lr = lr
        self.rng = np.random.RandomState(seed)
        self.best_weights: Optional[pd.Series] = None
        self.outer_log = []

    def _data(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        return indicator_table(panel)

    def _z(self, ind):
        return ind.groupby(level=0).transform(
            lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)

    def _inner(self, prior, ind, fwd, batches):
        w = pd.Series(prior, dtype=float)
        z = self._z(ind)
        for bd in batches:
            for c in w.index:
                sub_z = z[c][z[c].index.get_level_values(0).isin(bd)]
                sub_f = fwd[fwd.index.get_level_values(0).isin(bd)]
                d = pd.concat([sub_z.rename("z"), sub_f.rename("r")], axis=1).dropna()
                if len(d) > 10:
                    pic, _ = cross_section_ic_series(d["z"], d["r"])
                    ic = pic.mean() if len(pic) else 0.0
                    w[c] = max(0.0, w[c] + self.lr * ic)
            if w.sum() > 0:
                w = w / w.sum()
        # 评估 inner 结果
        sig = 0
        for c in list(w.index):
            sig = sig + z[c] * w[c]
        pic, _ = cross_section_ic_series(sig, fwd)
        return pic.mean() if len(pic) else np.nan, w

    def fit(self, ds: Dataset):
        ind = self._data(ds, ds.val_dates)
        fwd = ds.fwd_ret_on("validation")
        u = ind.index.get_level_values(0).sort_values().unique()
        batches = [u[i:i + 20] for i in range(0, len(u), 20)]
        best_score, best_w = np.nan, None
        for hname, prior in HEURISTICS.items():
            score, w = self._inner(prior, ind, fwd, batches)
            self.outer_log.append({"heuristic": hname, "val_ic": float(score) if np.isfinite(score) else None})
            if np.isfinite(score) and (not np.isfinite(best_score) or abs(score) > abs(best_score)):
                best_score, best_w = score, w
        self.best_weights = best_w
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        ind = self._data(ds, ds.dates_through(split))
        z = self._z(ind)
        comp = 0
        for c in list(self.best_weights.index):
            comp = comp + z[c] * self.best_weights[c]
        target = ds._dates_of(split)
        return comp[comp.index.get_level_values(0).isin(target)]
