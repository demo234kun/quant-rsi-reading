"""
统一评估器（同一口径）。

- 因子预测力：每日横截面 Pearson IC / Spearman RankIC，及其 IR（mean/std）
- 多空组合：用 next_ret（信号在 t 日、收益在 t+1 日，避免未来函数），
  等权分层多空，真实计算每日持仓与换手，扣单边交易成本
- 方向：在 validation 上估计 IC 符号，test 固定，防止选择泄漏
"""
from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .data import Dataset
from .interface import BaselineMethod, MethodMetrics


def _daily_cross_section(signal: pd.Series, ret: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"sig": signal, "ret": ret}).dropna()
    return df


def cross_section_ic_series(signal: pd.Series, ret: pd.Series, min_names: int = 5):
    """每日横截面 Pearson IC 与 Spearman RankIC。"""
    df = _daily_cross_section(signal, ret)
    pic, ric = [], []
    for d, g in df.groupby(level=0):
        if g["sig"].nunique() < min_names or len(g) < min_names:
            continue
        p = g["sig"].corr(g["ret"])
        r = spearmanr(g["sig"], g["ret"]).statistic
        if np.isfinite(p):
            pic.append(p)
        if np.isfinite(r):
            ric.append(r)
    return np.array(pic), np.array(ric)


def estimate_direction(val_signal: pd.Series, val_fwd: pd.Series) -> int:
    pic, _ = cross_section_ic_series(val_signal, val_fwd)
    if len(pic) == 0:
        return 1
    return -1 if pic.mean() < 0 else 1


def _build_daily_weights(signal: pd.Series, n_quantiles: int = 5) -> pd.DataFrame:
    """每日等权多头 top 组 / 空头 bottom 组，返回行=date、列=symbol 的权重。"""
    df = pd.DataFrame({"sig": signal}).dropna()
    df["rankp"] = df.groupby(level=0)["sig"].rank(pct=True)
    weights = {}
    for d, g in df.groupby(level=0):
        m = g.index.get_level_values(1)
        w = pd.Series(0.0, index=m)
        n = len(g)
        k = max(1, int(np.ceil(n / n_quantiles)))
        order = g["sig"].sort_values()
        longs = order.index.get_level_values(1)[-k:]
        shorts = order.index.get_level_values(1)[:k]
        w.loc[longs] = 1.0 / k
        w.loc[shorts] = -1.0 / k
        weights[d] = w
    W = pd.DataFrame(weights).T.sort_index()
    W.index.name = "date"
    return W


def long_short_backtest(
    signal: pd.Series, next_ret: pd.Series, direction: int,
    n_quantiles: int = 5, cost_bps: float = 2.0,
):
    """返回 (日净收益 Series, 日均换手, 日权重 DataFrame)。"""
    sig = signal * direction
    W = _build_daily_weights(sig, n_quantiles)
    # 收益矩阵：行 date、列 symbol 的 next_ret
    R = pd.DataFrame({
        "d": next_ret
    }).reset_index()
    ret_mat = next_ret.unstack(level=1).sort_index()
    # 对齐
    common_dates = W.index.intersection(ret_mat.index)
    W = W.loc[common_dates]
    Rm = ret_mat.loc[common_dates].reindex(columns=W.columns).fillna(0.0)
    Wf = W.fillna(0.0)
    gross = (Wf * Rm).sum(axis=1)

    # 换手：相邻日权重差的绝对值和（含多头与空头）
    turnover = Wf.diff().abs().sum(axis=1)
    turnover.iloc[0] = Wf.iloc[0].abs().sum()
    cost = turnover * (cost_bps / 1e4)
    net = gross - cost
    return net, float(turnover.mean()), Wf


def evaluate_signal(method: BaselineMethod, ds: Dataset, test_signal: pd.Series) -> MethodMetrics:
    val_signal = method.produce_signal(ds, split="validation")
    direction = estimate_direction(val_signal, ds.fwd_ret_on("validation"))

    test_fwd = ds.fwd_ret_on("test")
    test_nxt = ds.next_ret_on("test")

    pic, ric = cross_section_ic_series(test_signal, test_fwd)
    mean_ic = float(pic.mean()) if len(pic) else float("nan")
    ic_ir = float(pic.mean() / pic.std()) if len(pic) > 1 and pic.std() > 0 else float("nan")
    mean_ric = float(ric.mean()) if len(ric) else float("nan")
    ric_ir = float(ric.mean() / ric.std()) if len(ric) > 1 and ric.std() > 0 else float("nan")

    net, turnover, _ = long_short_backtest(test_signal, test_nxt, direction)
    if len(net) > 2:
        ann_ret = float(net.mean() * 252)
        ann_vol = float(net.std() * np.sqrt(252))
        sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else float("nan")
        cum = (1 + net).cumprod()
        max_dd = float(((cum - cum.cummax()) / cum.cummax()).min())
    else:
        ann_ret = sharpe = max_dd = float("nan")

    return MethodMetrics(
        method=method.name, category=method.category, paper_id=method.paper_id,
        dataset=ds.name, n_test_days=int(len(net)),
        n_symbols=int(ds.symbols.nunique()), horizon=ds.horizon,
        direction=direction,
        mean_ic=mean_ic, ic_ir=ic_ir, mean_rank_ic=mean_ric, rank_ic_ir=ric_ir,
        long_short_ann_return=ann_ret, long_short_sharpe=sharpe,
        max_drawdown=max_dd, turnover=turnover, cost_bps=2.0,
        fidelity=method.fidelity, notes=method.notes,
    )
