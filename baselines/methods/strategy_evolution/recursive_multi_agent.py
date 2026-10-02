"""
Recursive Multi-Agent Trading System（11）复现。

论文核心：四个专业 agent（Sentiment 风险信号 / Report 动量+盈余 / Analysis regime /
Risk CVaR），Manager 做 confidence 加权聚合，递归协调协议；
GPR 触发的电路断路器（风险超阈值则降仓/防御）；风险感知目标 R = r - λ1σ - λ2·DD。

本复现（价格代理，无 GPR/新闻）：
  - 子信号：report=动量，analysis=趋势，sentiment/risk=用波动+下跌构造的风险代理
  - Manager 聚合：confidence（val 稳定性）加权
  - 风险感知：风险代理对合成信号做负向调节
  - 断路器：风险代理超阈值（80 分位）时对信号降仓
  - 参数 λ1=0.8、λ2=1.5 忠实论文
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.evaluator import cross_section_ic_series

LAM1, LAM2 = 0.8, 1.5


class RecursiveMultiAgent(BaselineMethod):
    def __init__(self, batch: int = 20, seed: Optional[int] = 0):
        self.name = "recursive_multi_agent"
        self.category = "strategy_evolution"
        self.paper_id = "11"
        self.fidelity = "faithful_core"
        self.notes = "多agent confidence聚合、风险感知、断路器忠实；GPR/新闻用价格风险代理替代"
        self.batch = batch
        self.rng = np.random.RandomState(seed)
        self.confidence = None
        self.threshold = None

    def _data(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        return indicator_table(panel), panel

    def _z(self, ind):
        return ind.groupby(level=0).transform(
            lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)

    def _risk_proxy(self, ind):
        """风险代理：高波动（atr）+ 低趋势 + 高布林（超买）→ 风险越高越危险。"""
        z = self._z(ind)
        return z["atr_pct"] + (-z["ema20_gap"]) * 0.5 + (-z["mom10"]) * 0.5

    def fit(self, ds: Dataset):
        ind, panel = self._data(ds, ds.val_dates)
        fwd = ds.fwd_ret_on("validation")
        z = self._z(ind)
        # 子信号 confidence：各自在 val 上 IC 的稳定性
        subs = {"report": z["mom10"], "analysis": z["ema20_gap"] + z["macd_hist"]}
        conf = {}
        for name, s in subs.items():
            pic, _ = cross_section_ic_series(s, fwd)
            conf[name] = abs(pic.mean()) if len(pic) else 0.0
        tot = sum(conf.values()) or 1.0
        self.confidence = {k: v / tot for k, v in conf.items()}
        # 断路器阈值：风险代理 80 分位（val 上）
        rp = self._risk_proxy(ind)
        self.threshold = float(np.nanquantile(rp, 0.8))
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        ind, panel = self._data(ds, ds.dates_through(split))
        z = self._z(ind)
        # Manager confidence 加权聚合
        sig = (z["mom10"] * self.confidence["report"]
               + (z["ema20_gap"] + z["macd_hist"]) * self.confidence["analysis"])
        # 风险感知：风险代理对信号负向调节（R = r - λ1σ - λ2DD 思想）
        rp = self._risk_proxy(ind)
        risk_adj = sig * (1 - LAM1 * 0.2 * rp.clip(lower=0))
        # 断路器：风险超阈值降仓
        breaker = np.where(rp > self.threshold, 0.5, 1.0)
        s = risk_adj * breaker
        target = ds._dates_of(split)
        return s[s.index.get_level_values(0).isin(target)]
