"""
TradingGroup（13）复现。

论文核心：多智能体交易系统，自我反思 + 端到端数据合成管线（用交易活动数据反哺后训练）。

本复现聚焦“数据合成 + 反思”：
  - 数据合成基于真实 train 数据，不凭空虚构：
      * block bootstrap：按时间块重采样真实 (特征, 标签)
      * 特征加噪增强：对真实样本特征加 N(0, noise_std)，标签保持真实
  - 自我反思：每轮在 validation 上按 regime 评估，对弱 regime 增加合成采样权重
  - 用真实 + 合成数据训练 Ridge，产出预测信号
论文中的新闻/财报/风格等需 LLM 的智能体未复现（已在 notes 标注）。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.evaluator import cross_section_ic_series
from methods.data_evolution.rd_agent_quant import build_features


class TradingGroup(BaselineMethod):
    def __init__(self, reflection_rounds: int = 3, block: int = 20,
                 synth_multiplier: int = 2, noise_std: float = 0.1,
                 seed: Optional[int] = 0):
        self.name = "trading_group"
        self.category = "data_evolution"
        self.paper_id = "13"
        self.fidelity = "simplified"
        self.notes = ("数据合成（block bootstrap+加噪）与反思机制忠实；"
                      "新闻/财报/风格等需 LLM 的智能体未复现")
        self.rounds = reflection_rounds
        self.block = block
        self.synth_mult = synth_multiplier
        self.noise_std = noise_std
        self.rng = np.random.RandomState(seed)
        self.model = None
        self.scaler = None
        self.feat_cols = None
        self.reflection_log = []

    def _panel(self, ds, dates):
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)]

    def _prepare(self, ds, dates):
        panel = self._panel(ds, dates)
        X = build_features(panel)
        return X

    def _regime_weak(self, pred_s, y, dates):
        # 用日期前半/后半近似两个“regime”（无显式聚类，仅作反思分组）
        d = pd.concat([pred_s.rename("p"), y.rename("y")], axis=1).dropna()
        if len(d) < 10:
            return None
        mid = d.index.get_level_values(0).sort_values().unique()
        cut = mid[len(mid) // 2]
        groups = {"early": d[d.index.get_level_values(0) < cut],
                  "late": d[d.index.get_level_values(0) >= cut]}
        score = {}
        for g, sub in groups.items():
            if len(sub) > 5:
                pic, _ = cross_section_ic_series(sub["p"], sub["y"])
                score[g] = pic.mean() if len(pic) else np.nan
        if not score:
            return None
        return min(score, key=lambda g: score[g] if np.isfinite(score[g]) else 1e9)

    def _synthesize(self, Xtr, ytr, weak_dates=None):
        """block bootstrap + 加噪，生成合成样本（标签来自真实重采样）。"""
        d = pd.concat([Xtr, ytr.rename("y")], axis=1).dropna()
        # 按日期排序，取连续时间块
        u_dates = d.index.get_level_values(0).sort_values().unique()
        blocks = [u_dates[i:i + self.block] for i in range(0, len(u_dates), self.block)]
        if not blocks:
            return None
        # 反思：弱 regime 对应块权重更高
        weights = np.ones(len(blocks))
        if weak_dates is not None:
            weak_set = set(weak_dates)
            for i, b in enumerate(blocks):
                if any(x in weak_set for x in b):
                    weights[i] *= 3.0
        weights /= weights.sum()
        chosen = self.rng.choice(len(blocks), size=len(blocks) * self.synth_mult, p=weights)
        frames = [d[d.index.get_level_values(0).isin(blocks[i])] for i in chosen]
        syn = pd.concat(frames)
        # 加噪增强
        Xs = syn[Xtr.columns].copy()
        for c in Xs.columns:
            sd = Xs[c].std()
            if np.isfinite(sd) and sd > 0:
                Xs[c] = Xs[c] + self.rng.normal(0, self.noise_std * sd, len(Xs))
        return Xs, syn["y"]

    def fit(self, ds: Dataset):
        Xtr = self._prepare(ds, ds.train_dates)
        ytr = ds.fwd_ret_on("train")
        Xv = self._prepare(ds, ds.val_dates)
        yv = ds.fwd_ret_on("validation")
        weak_dates = None

        for r in range(self.rounds):
            from sklearn.linear_model import Ridge
            from sklearn.preprocessing import StandardScaler
            parts_X, parts_y = [Xtr], [ytr]
            syn = self._synthesize(Xtr, ytr, weak_dates)
            if syn is not None:
                parts_X.append(syn[0]); parts_y.append(syn[1])
            Xall = pd.concat(parts_X)
            yall = pd.concat(parts_y)
            dd = pd.concat([Xall, yall.rename("y")], axis=1).dropna()
            scaler = StandardScaler()
            Xs = scaler.fit_transform(dd[list(Xtr.columns)])
            model = Ridge(alpha=1.0).fit(Xs, dd["y"])

            vd = pd.concat([Xv, yv.rename("y")], axis=1).dropna()
            pred = model.predict(scaler.transform(vd[list(Xtr.columns)]))
            pred_s = pd.Series(pred, index=vd.index)
            pic, _ = cross_section_ic_series(pred_s, vd["y"])
            v_ic = pic.mean() if len(pic) else np.nan
            weak = self._regime_weak(pred_s, vd["y"], None)
            # 反思：弱 regime 对应 val 日期，映射到 train 同期块
            if weak == "late":
                u = Xtr.index.get_level_values(0).sort_values().unique()
                weak_dates = u[int(len(u) * 0.66):]
            elif weak == "early":
                u = Xtr.index.get_level_values(0).sort_values().unique()
                weak_dates = u[:int(len(u) * 0.34)]
            self.reflection_log.append({"round": r, "val_ic": float(v_ic) if np.isfinite(v_ic) else None,
                                        "weak_segment": weak})
            self.model, self.scaler, self.feat_cols = model, scaler, list(Xtr.columns)
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        X = self._prepare(ds, ds.dates_through(split))
        valid = X.dropna()
        pred = self.model.predict(self.scaler.transform(valid[self.feat_cols]))
        s = pd.Series(pred, index=valid.index)
        return s[s.index.get_level_values(0).isin(ds._dates_of(split))]
