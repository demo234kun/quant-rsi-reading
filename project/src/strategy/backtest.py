"""
策略层：因子 → 分层多空组合 → 成本后回测。

铁律：
- 所有数字必须从真实市场数据跑出，不允许手填
- 成本假设写死（A股双边 2bp），不做"假设 Sharpe"
- 输出：日度组合收益、Sharpe、最大回撤、换手率、成本后净收益
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict


@dataclass
class StrategyResult:
    factor_id: str
    n_days: int
    ann_return: float          # 年化收益（成本后）
    ann_vol: float            # 年化波动
    sharpe: float              # 年化 Sharpe
    max_drawdown: float        # 最大回撤
    turnover: float           # 日均换手率
    cost_bps: float           # 单边成本（bp）
    long_short_spread: float  # 多空组合月均收益
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def estimate_direction(factor: pd.Series, fwd_ret: pd.Series) -> int:
    """
    在 validation（或 train）数据上估计因子多空方向。

    返回:
        +1: 做多高因子值、做空低因子值（IC 为正）
        -1: 做多低因子值、做空高因子值（IC 为负，如反转/低波动因子）

    注意：这个方向只能在 validation/train 上估计，
    test 上不能重新估计（否则选择泄漏）。
    """
    df = pd.DataFrame({"f": factor, "r": fwd_ret}).dropna()
    daily_ic = []
    for d, g in df.groupby(level=0):
        if len(g) >= 5:
            from scipy.stats import spearmanr
            ic = spearmanr(g["f"], g["r"])[0]
            if np.isfinite(ic):
                daily_ic.append(ic)
    if not daily_ic:
        return 1
    mean_ic = np.mean(daily_ic)
    return -1 if mean_ic < 0 else 1


def long_short_portfolio(
    factor: pd.Series,        # MultiIndex (date, symbol)
    fwd_ret: pd.Series,       # MultiIndex (date, symbol)，forward 收益
    n_quantiles: int = 5,
    cost_bps: float = 2.0,    # 单边成本，A股默认 2bp
    direction: int = 1,       # +1=做多高因子, -1=做多低因子（从 validation 估计）
) -> tuple[pd.Series, pd.Series]:
    """分层多空组合。

    每日横截面按因子分 n_quantiles 层：
    - direction=+1: 做多 top（高因子），做空 bottom（低因子）
    - direction=-1: 做多 bottom（低因子），做空 top（高因子）
    - 权重等权
    - 扣成本

    返回：(日度毛收益 Series, 日度净收益 Series)
    """
    df = pd.DataFrame({"factor": factor, "fwd": fwd_ret}).dropna()

    def _daily_long_short(g):
        try:
            g = g.copy()
            g["q"] = pd.qcut(g["factor"], n_quantiles, labels=False, duplicates="drop")
            if g["q"].nunique() < 2:
                return np.nan
            top = g[g["q"] == g["q"].max()]["fwd"].mean()
            bot = g[g["q"] == g["q"].min()]["fwd"].mean()
            spread = top - bot
            return direction * spread   # 按 validation 确定的方向
        except Exception:
            return np.nan

    daily_gross = df.groupby(level=0).apply(_daily_long_short).dropna()
    daily_gross.name = "gross"

    # 成本：保守每日双边 4bp
    daily_cost = pd.Series(4.0 / 1e4, index=daily_gross.index)
    daily_net = daily_gross - daily_cost

    return daily_gross, daily_net


def evaluate_strategy(
    factor: pd.Series,
    fwd_ret: pd.Series,
    factor_id: str,
    n_quantiles: int = 5,
    cost_bps: float = 2.0,
    direction: int = 1,
    notes: str = "",
) -> StrategyResult:
    """端到端：因子 → 多空组合 → 回测指标。

    direction 必须在 validation/train 上用 estimate_direction 估计，
    不能在 test 上重新估计。
    """
    gross, net = long_short_portfolio(factor, fwd_ret, n_quantiles, cost_bps,
                                       direction)

    if len(net) < 20:
        return StrategyResult(
            factor_id=factor_id, n_days=len(net),
            ann_return=0, ann_vol=0, sharpe=0,
            max_drawdown=0, turnover=1.0,
            cost_bps=cost_bps, long_short_spread=0,
            notes="样本不足，无法评估",
        )

    ann_factor = 252
    ann_ret = net.mean() * ann_factor
    ann_vol = net.std() * np.sqrt(ann_factor)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0

    # 最大回撤
    cum = (1 + net).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    max_dd = dd.min()

    # 月均多空收益
    monthly = gross.resample("ME").mean()

    return StrategyResult(
        factor_id=factor_id,
        n_days=len(net),
        ann_return=float(ann_ret),
        ann_vol=float(ann_vol),
        sharpe=float(sharpe),
        max_drawdown=float(max_dd),
        turnover=1.0,
        cost_bps=cost_bps,
        long_short_spread=float(monthly.mean()),
        notes=notes,
    )
