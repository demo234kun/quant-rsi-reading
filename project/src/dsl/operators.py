"""
密封 DSL 算子表。

每个算子必须数学上证明：输出只依赖 t 时刻及之前的数据。
不允许任何 lookahead。所有算子经过 tests/test_causality.py 验证。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Callable, Dict


# ---------- 时序算子（只依赖回看窗口） ----------

def lag(x: pd.Series, k: int) -> pd.Series:
    """滞后 k 期。t 时刻输出 x[t-k]。"""
    return x.shift(k)


def delta(x: pd.Series, k: int) -> pd.Series:
    """k 期差分：x[t] - x[t-k]。"""
    return x.diff(k)


def rolling_mean(x: pd.Series, k: int) -> pd.Series:
    """k 期滚动均值（含 t 时刻）。"""
    return x.rolling(k, min_periods=k).mean()


def rolling_std(x: pd.Series, k: int) -> pd.Series:
    return x.rolling(k, min_periods=k).std()


def rolling_max(x: pd.Series, k: int) -> pd.Series:
    return x.rolling(k, min_periods=k).max()


def rolling_min(x: pd.Series, k: int) -> pd.Series:
    return x.rolling(k, min_periods=k).min()


def rolling_rank(x: pd.Series, k: int) -> pd.Series:
    """t 时刻的值在过去 k 期（含 t）中的分位。"""
    def _rank(window):
        return (window[-1] >= window).mean()
    return x.rolling(k, min_periods=k).apply(_rank, raw=True)


def rolling_corr(a: pd.Series, b: pd.Series, k: int) -> pd.Series:
    """a 和 b 在过去 k 期（含 t）的滚动相关系数。"""
    return a.rolling(k, min_periods=k).corr(b)


# ---------- 横截面算子（同一截面内操作） ----------

def cs_rank(x: pd.Series) -> pd.Series:
    """横截面排名：同一时点所有股票的分位。
    输入必须是 MultiIndex (date, symbol) 的 Series。"""
    return x.groupby(level=0).rank(pct=True)


def cs_zscore(x: pd.Series) -> pd.Series:
    """横截面 z-score。"""
    grp = x.groupby(level=0)
    return (x - grp.transform("mean")) / grp.transform("std").replace(0, np.nan)


def cs_demean(x: pd.Series) -> pd.Series:
    return x - x.groupby(level=0).transform("mean")


# ---------- 算术算子 ----------

def add(a, b): return a + b
def sub(a, b): return a - b
def mul(a, b): return a * b
def div(a, b): return a / b.replace(0, np.nan)


# ---------- 算子注册表（密封） ----------

OPERATORS: Dict[str, Callable] = {
    "lag": lag,
    "delta": delta,
    "rolling_mean": rolling_mean,
    "rolling_std": rolling_std,
    "rolling_max": rolling_max,
    "rolling_min": rolling_min,
    "rolling_rank": rolling_rank,
    "rolling_corr": rolling_corr,
    "cs_rank": cs_rank,
    "cs_zscore": cs_zscore,
    "cs_demean": cs_demean,
    "add": add,
    "sub": sub,
    "mul": mul,
    "div": div,
}


def list_operators():
    """返回算子表（agent 只能看到这个列表，不能扩展）。"""
    return sorted(OPERATORS.keys())
