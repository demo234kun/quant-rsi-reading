"""
策略组合器：把因子转成可交易的多空策略。

对应 AQuA Part II：因子挖出来之后，还要组合成策略、调权重、算成本后 Sharpe。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class StrategyResult:
    strategy_id: str
    expression: str              # 策略构造表达式
    # per-regime
    regime_sharpe: dict          # {regime: sharpe}
    regime_maxdd: dict           # {regime: max drawdown}
    regime_turnover: dict         # {regime: turnover per period}
    overall_sharpe: float
    overall_maxdd: float
    n_long: int
    n_short: int
    cost_bps: float


def dollar_neutral_long_short(
    factor: pd.Series,
    prices: pd.Series,
    top_pct: float = 0.1,
    cost_bps: float = 2.0,
) -> pd.Series:
    """把因子转成美元中性多空组合的日收益序列。

    参数:
        factor: MultiIndex (date, symbol) 的因子值
        prices: MultiIndex (date, symbol) 的收盘价（用来算持仓收益）
        top_pct: 多空各取前/后 top_pct
        cost_bps: 单边成本（基点）

    返回:
        daily strategy return Series (按 date 索引)
    """
    df = pd.DataFrame({"factor": factor, "price": prices}).dropna()
    df = df.sort_index()

    # 每日横截面排名
    df["rank"] = df.groupby(level=0)["factor"].rank(pct=True)

    # 多空仓位：rank > 1-top_pct 做多，rank < top_pct 做空
    df["long"] = (df["rank"] > 1 - top_pct).astype(float)
    df["short"] = (df["rank"] < top_pct).astype(float)

    # 每日收益
    df["ret"] = df.groupby(level="symbol")["price"].pct_change()

    # 构造组合：每日 long/short 权重归一化
    def _daily_portfolio(g):
        n_long = g["long"].sum()
        n_short = g["short"].sum()
        if n_long == 0 or n_short == 0:
            return pd.Series([0.0], index=[g.index.get_level_values(0)[0]])
        w_long = g["long"] / n_long
        w_short = -g["short"] / n_short
        gross = w_long + w_short  # 美元中性：多空各 1 元
        port_ret = (g["ret"] * gross).sum()
        # 换手成本：|w_t - w_{t-1}| 的变化量 × cost
        return pd.Series([port_ret], index=[g.index.get_level_values(0)[0]])

    daily_ret = df.groupby(level=0).apply(_daily_portfolio)
    daily_ret.index = daily_ret.index.get_level_values(0) if daily_ret.index.nlevels > 1 else daily_ret.index

    # 简化：直接算
    rets = []
    prev_w = None
    for date, g in df.groupby(level=0):
        n_long = g["long"].sum()
        n_short = g["short"].sum()
        if n_long == 0 or n_short == 0:
            rets.append(0.0)
            continue
        w = g["long"] / n_long - g["short"] / n_short
        port_ret = (g["ret"] * w).sum()
        # 换手
        if prev_w is not None:
            common = w.index.intersection(prev_w.index)
            turnover = (w[common] - prev_w[common]).abs().sum()
            port_ret -= turnover * cost_bps / 10000.0
        rets.append(port_ret)
        prev_w = w

    return pd.Series(rets, index=sorted(df.index.get_level_values(0).unique()))


def per_regime_metrics(
    strategy_ret: pd.Series,
    regime_labels: pd.Series,
    periods_per_year: int = 252,
) -> tuple[dict, dict]:
    """计算 per-regime Sharpe 和 max drawdown。

    返回 (regime_sharpe, regime_maxdd)
    """
    df = pd.DataFrame({"ret": strategy_ret}).join(regime_labels.rename("regime"), how="inner")

    sharpe = {}
    maxdd = {}
    for r, g in df.groupby("regime"):
        rets = g["ret"].dropna()
        if len(rets) < 10:
            sharpe[int(r)] = float("nan")
            maxdd[int(r)] = float("nan")
            continue
        ann_ret = rets.mean() * periods_per_year
        ann_vol = rets.std() * np.sqrt(periods_per_year)
        sharpe[int(r)] = float(ann_ret / (ann_vol + 1e-10))
        # max drawdown
        cum = (1 + rets).cumprod()
        dd = (cum / cum.cummax() - 1).min()
        maxdd[int(r)] = float(dd)

    return sharpe, maxdd


def overall_metrics(strategy_ret: pd.Series, periods_per_year: int = 252):
    rets = strategy_ret.dropna()
    if len(rets) < 10:
        return 0.0, 0.0
    ann_ret = rets.mean() * periods_per_year
    ann_vol = rets.std() * np.sqrt(periods_per_year)
    sharpe = ann_ret / (ann_vol + 1e-10)
    cum = (1 + rets).cumprod()
    maxdd = (cum / cum.cummax() - 1).min()
    return float(sharpe), float(maxdd)
