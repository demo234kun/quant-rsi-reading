"""
SHARP（09）复现。

论文核心：Self-Evolving Human-Auditable Rubric Policy
  - rubric = 一组结构化 condition-action 规则（id, category, condition, action）
  - 三智能体闭环：Attribution（把损失归因到具体规则）-> Evolution（原子编辑）
    -> Validation gate（val 超过当前才接受）
  - 原子、可审计，不做全局自由文本重写

本复现用价格/技术条件替代论文中的新闻/FDA 条件（我们无新闻数据），
规则机制与三智能体闭环忠实：
  - 规则：超买(RSI)、波动(ATR)、趋势确认(EMA)、动量过热 -> 对基础信号乘系数
  - Attribution：val 最差 K 天中哪个规则激活最多
  - Evolution：原子编辑该规则阈值/强度
  - Gate：候选 val IC 必须不劣于当前
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.evaluator import cross_section_ic_series


# 初始规则：(指标列, 方向, 阈值, 强度)；方向 high_reduce=高则减, high_boost=高则增
def initial_rules():
    return {
        "overbought_rsi": ["rsi14", "high_reduce", 70.0, 0.5],
        "high_volatility": ["atr_pct", "high_reduce", 0.03, 0.5],
        "trend_confirm": ["ema20_gap", "high_boost", 0.02, 0.3],
        "momentum_overheat": ["mom10", "high_reduce", 0.10, 0.4],
    }


class SHARP(BaselineMethod):
    def __init__(self, rounds: int = 6, k_worst: int = 10, seed: Optional[int] = 0):
        self.name = "sharp"
        self.category = "strategy_evolution"
        self.paper_id = "09"
        self.fidelity = "faithful_core"
        self.notes = ("rubric 规则、归因/原子编辑/验证门机制忠实；"
                      "条件用技术指标替代论文新闻/FDA 条件")
        self.rounds = rounds
        self.k_worst = k_worst
        self.rng = np.random.RandomState(seed)
        self.rules = initial_rules()
        self.audit = []

    def _indicators(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        return indicator_table(panel), panel

    def _base_signal(self, ind: pd.DataFrame) -> pd.Series:
        """初始通用启发式：技术指标横截面 z-score 合成。"""
        z = ind.groupby(level=0).transform(
            lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)
        # 初始：趋势(EMA/MACD) 正向，超买/波动负向
        w = {"rsi14": -0.2, "ema20_gap": 0.4, "macd_hist": 0.4,
             "atr_pct": -0.2, "boll_pos": -0.1, "mom10": 0.3}
        s = 0
        for c in w:
            s = s + z[c] * w[c]
        return s

    def _apply(self, base: pd.Series, ind: pd.DataFrame) -> pd.Series:
        mult = pd.Series(1.0, index=base.index)
        for name, (col, kind, thr, strength) in self.rules.items():
            if col not in ind:
                continue
            if kind == "high_reduce":
                cond = ind[col] > thr
                mult = mult * np.where(cond, 1.0 - strength, 1.0)
            else:
                cond = ind[col] > thr
                mult = mult * np.where(cond, 1.0 + strength, 1.0)
        return base * mult

    def _val_ic(self, rules, ind, panel, fwd) -> float:
        old = self.rules
        self.rules = rules
        try:
            sig = self._apply(self._base_signal(ind), ind)
            pic, _ = cross_section_ic_series(sig, fwd)
            return pic.mean() if len(pic) else np.nan
        finally:
            self.rules = old

    def fit(self, ds: Dataset):
        ind, panel = self._indicators(ds, ds.val_dates)
        fwd = ds.fwd_ret_on("validation")
        base = self._base_signal(ind)

        def score(rules):
            return self._val_ic(rules, ind, panel, fwd)

        current_ic = score(self.rules)
        for r in range(self.rounds):
            # Attribution：用当前信号算每日组合 proxy，找最差 K 天
            sig = self._apply(base, ind)
            d = pd.concat([sig.rename("s"), fwd.rename("r")], axis=1).dropna()
            daily = d.groupby(level=0).apply(
                lambda g: (g["s"].rank(pct=True) * g["r"]).mean())
            if len(daily) < 5:
                break
            worst = daily.nsmallest(min(self.k_worst, len(daily))).index
            # 统计最差天激活的规则
            rule_votes = {}
            for name, (col, kind, thr, strength) in self.rules.items():
                if col not in ind:
                    continue
                sub = ind[ind.index.get_level_values(0).isin(worst)]
                rule_votes[name] = int((sub[col] > thr).sum())
            blamed = max(rule_votes, key=rule_votes.get) if rule_votes else None
            # Evolution：原子编辑（阈值/强度 ±）
            accepted = False
            if blamed:
                col, kind, thr, strength = self.rules[blamed]
                edits = []
                edits.append((blamed, [col, kind, thr, min(0.9, strength + 0.15)]))
                edits.append((blamed, [col, kind, thr * 0.9 if kind == "high_reduce" else thr * 1.1, strength]))
                for bname, newrule in edits:
                    cand = {k: list(v) for k, v in self.rules.items()}
                    cand[bname] = newrule
                    cic = score(cand)
                    if np.isfinite(cic) and (not np.isfinite(current_ic) or abs(cic) > abs(current_ic) - 1e-9):
                        self.rules = cand
                        current_ic = cic
                        accepted = True
                        self.audit.append({"round": r, "blamed": bname, "val_ic": float(cic)})
                        break
            if not accepted:
                self.audit.append({"round": r, "blamed": blamed, "accepted": False})
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        ind, panel = self._indicators(ds, ds.dates_through(split))
        base = self._base_signal(ind)
        s = self._apply(base, ind)
        target = ds._dates_of(split)
        return s[s.index.get_level_values(0).isin(target)]
