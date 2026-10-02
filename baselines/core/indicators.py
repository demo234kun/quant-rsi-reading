"""
技术指标模块（标准定义，逐股票计算，无未来函数）。
供策略进化类方法（EvolveTrade / SHARP 等）使用。
所有指标在 t 时刻只依赖 t 及之前数据。
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _per_symbol(series_or_panel, fn):
    """对每只股票（MultiIndex 第二级）应用 fn(Series)->Series。"""
    return series_or_panel.groupby(level=1, group_keys=False).transform(fn)


def rsi(panel: pd.DataFrame, period: int = 14) -> pd.Series:
    def _rsi(s: pd.Series) -> pd.Series:
        delta = s.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - 100 / (1 + rs)
    return _per_symbol(panel["close"], _rsi)


def ema(panel: pd.DataFrame, period: int = 20) -> pd.Series:
    return _per_symbol(panel["close"], lambda s: s.ewm(span=period, adjust=False).mean())


def macd(panel: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    def _macd(s: pd.Series):
        line = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
        sig = line.ewm(span=signal, adjust=False).mean()
        return line - sig
    return _per_symbol(panel["close"], _macd)


def atr(panel: pd.DataFrame, period: int = 14) -> pd.Series:
    parts = []
    for sym, g in panel.groupby(level=1):
        pc = g["close"].shift(1)
        tr = pd.concat([
            g["high"] - g["low"],
            (g["high"] - pc).abs(),
            (g["low"] - pc).abs(),
        ], axis=1).max(axis=1)
        a = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        parts.append(a)
    return pd.concat(parts).sort_index()


def boll_position(panel: pd.DataFrame, period: int = 20, k: float = 2.0) -> pd.Series:
    """收盘价在布林带中的位置（0 下轨，1 上轨）。"""
    def _boll(s: pd.Series):
        m = s.rolling(period).mean()
        sd = s.rolling(period).std()
        return (s - (m - k * sd)) / (2 * k * sd.replace(0, np.nan))
    return _per_symbol(panel["close"], _boll)


def indicator_table(panel: pd.DataFrame) -> pd.DataFrame:
    """统一技术指标表（无泄漏）。"""
    f = pd.DataFrame(index=panel.index)
    f["rsi14"] = rsi(panel, 14)
    f["ema20_gap"] = panel["close"] / ema(panel, 20) - 1.0
    f["macd_hist"] = macd(panel)
    f["atr_pct"] = atr(panel, 14) / panel["close"]
    f["boll_pos"] = boll_position(panel, 20)
    f["mom10"] = panel["close"].groupby(level=1).transform(lambda s: s / s.shift(10) - 1)
    return f
