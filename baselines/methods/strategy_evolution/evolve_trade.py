"""
EvolveTrade（08）复现。

论文核心：把 tool-use policy 当作可编辑文本；每个 batch 结束，
Policy Agent 读取决策轨迹与真实反馈，重写 policy（policy self-evolution），
改进工具/指标使用规则；LLM 骨干固定。

本复现（可运行量化近似）：
  - policy = 各技术指标的使用权重（代表“如何使用工具/指标”）
  - 每个 batch 用当前 policy 合成信号，
    再根据真实反馈（各指标在该 batch 的 IC）更新权重：
    有效指标加权、失效指标减权 —— 即“从经验重写 policy”
  - 多个 batch 迭代，最终 policy 产出信号
未做自然语言 policy 文本（无 LLM），用权重 policy 近似，fidelity 标注。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.evaluator import cross_section_ic_series


class EvolveTrade(BaselineMethod):
    def __init__(self, batch: int = 20, lr: float = 0.5, seed: Optional[int] = 0):
        self.name = "evolve_trade"
        self.category = "strategy_evolution"
        self.paper_id = "08"
        self.fidelity = "policy_text_approx"
        self.notes = "policy 按经验逐批更新（指标使用权重）忠实；自然语言 policy 文本用权重近似"
        self.batch = batch
        self.lr = lr
        self.rng = np.random.RandomState(seed)
        self.weights = None
        self.policy_log = []

    def _data(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        ind = indicator_table(panel)
        return ind

    def _z(self, ind):
        return ind.groupby(level=0).transform(
            lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)

    def _signal(self, ind, w):
        z = self._z(ind)
        comp = 0
        for c in list(w.index):
            comp = comp + z[c] * w[c]
        return comp

    def fit(self, ds: Dataset):
        ind = self._data(ds, ds.val_dates)
        fwd = ds.fwd_ret_on("validation")
        cols = list(ind.columns)
        w = pd.Series(1.0 / len(cols), index=cols)

        u_dates = ind.index.get_level_values(0).sort_values().unique()
        batches = [u_dates[i:i + self.batch] for i in range(0, len(u_dates), self.batch)]
        for bi, bd in enumerate(batches):
            z = self._z(ind)
            # 该 batch 各指标 IC
            ics = {}
            for c in cols:
                sub_z = z[c][z[c].index.get_level_values(0).isin(bd)]
                sub_f = fwd[fwd.index.get_level_values(0).isin(bd)]
                d = pd.concat([sub_z.rename("z"), sub_f.rename("r")], axis=1).dropna()
                if len(d) > 10:
                    pic, _ = cross_section_ic_series(d["z"], d["r"])
                    ics[c] = pic.mean() if len(pic) else 0.0
                else:
                    ics[c] = 0.0
            for c in cols:
                w[c] = max(0.0, w[c] + self.lr * ics[c])
            if w.sum() > 0:
                w = w / w.sum()
            self.policy_log.append({"batch": bi, "weights": {k: float(v) for k, v in w.items()}})
        self.weights = w
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        ind = self._data(ds, ds.dates_through(split))
        s = self._signal(ind, self.weights)
        target = ds._dates_of(split)
        return s[s.index.get_level_values(0).isin(target)]
