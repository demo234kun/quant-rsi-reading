"""
统一数据层：同一批真实数据可被所有方法复用。

- 数据来源：真实市场面板（默认 CSI300 前复权日线，akshare 下载后缓存为 parquet）
- 小样本：通过 n_symbols / n_days 取真实子集（数据本身真实，不虚构）
- 切分：严格按时间 train / validation / test，方法不可改
- 同时提供 fwd_ret（未来 h 日收益，用于 IC）与 next_ret（次日收益，用于组合回测，避免重叠收益高估）
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_PARQUET = Path(__file__).resolve().parents[2] / "project" / "data" / "csi300_daily.parquet"


@dataclass
class Dataset:
    name: str
    panel: pd.DataFrame            # MultiIndex (date, symbol): open/high/low/close/volume/ret
    fwd_ret: pd.Series             # 未来 h 日累计收益，MultiIndex
    next_ret: pd.Series            # 次日收益，MultiIndex
    horizon: int
    train_dates: pd.DatetimeIndex
    val_dates: pd.DatetimeIndex
    test_dates: pd.DatetimeIndex

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.panel.index.get_level_values(0).unique().sort_values()

    @property
    def symbols(self):
        return self.panel.index.get_level_values(1).unique()

    def _slice_dates(self, dates: pd.DatetimeIndex, series: pd.Series) -> pd.Series:
        return series[series.index.get_level_values(0).isin(dates)]

    def train_panel(self) -> pd.DataFrame:
        return self.panel[self.panel.index.get_level_values(0).isin(self.train_dates)]

    def val_signal_input(self) -> pd.DataFrame:
        return self.panel[self.panel.index.get_level_values(0).isin(self.val_dates)]

    def field(self, col: str, dates: pd.DatetimeIndex | None = None) -> pd.Series:
        s = self.panel[col]
        return s if dates is None else self._slice_dates(dates, s)

    def fwd_ret_on(self, split: str) -> pd.Series:
        return self._slice_dates(self._dates_of(split), self.fwd_ret)

    def next_ret_on(self, split: str) -> pd.Series:
        return self._slice_dates(self._dates_of(split), self.next_ret)

    def _dates_of(self, split: str) -> pd.DatetimeIndex:
        return {"train": self.train_dates, "validation": self.val_dates, "test": self.test_dates}[split]

    def dates_through(self, split: str) -> pd.DatetimeIndex:
        """目标 split 及之前的全部日期（用于技术指标 warmup，避免在 split 起点产生 NaN）。"""
        if split == "train":
            return self.train_dates
        if split == "validation":
            return self.train_dates.union(self.val_dates)
        return self.train_dates.union(self.val_dates).union(self.test_dates)


def load_panel(parquet_path: Path | str = DEFAULT_PARQUET) -> pd.DataFrame:
    p = Path(parquet_path)
    if not p.exists():
        raise FileNotFoundError(
            f"未找到真实数据缓存 {p}。请先用 project/src/data/real_akshare.py 下载。"
        )
    panel = pd.read_parquet(p)
    if not isinstance(panel.index, pd.MultiIndex):
        panel = panel.set_index(["date", "symbol"])
    return panel.sort_index()


def _add_returns(panel: pd.DataFrame, horizon: int):
    close = panel["close"]
    # 未来 h 日收益：close[t+h]/close[t]-1，shift(-h) 保证只用未来价格
    fwd = close.groupby(level=1).transform(lambda s: s.shift(-horizon) / s - 1.0)
    # 次日收益：close[t+1]/close[t]-1
    nxt = close.groupby(level=1).transform(lambda s: s.shift(-1) / s - 1.0)
    fwd.name, nxt.name = "fwd_ret", "next_ret"
    return fwd, nxt


def make_dataset(
    name: str = "csi300_small",
    n_symbols: int | None = 15,
    n_days: int | None = 420,
    horizon: int = 5,
    train_frac: float = 0.6,
    val_frac: float = 0.2,
    parquet_path: Path | str = DEFAULT_PARQUET,
) -> Dataset:
    """从真实面板取（小样本）子集并切分。

    n_symbols/n_days 为 None 时使用全量。
    """
    panel = load_panel(parquet_path)

    if n_symbols is not None:
        syms = panel.index.get_level_values(1).unique().sort_values()[:n_symbols]
        panel = panel[panel.index.get_level_values(1).isin(syms)]
    if n_days is not None:
        dates = panel.index.get_level_values(0).unique().sort_values()
        panel = panel[panel.index.get_level_values(0).isin(dates[-n_days:])]

    fwd, nxt = _add_returns(panel, horizon)
    all_dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(all_dates)
    n_tr = int(n * train_frac)
    n_va = int(n * (train_frac + val_frac))
    train_dates = all_dates[:n_tr]
    val_dates = all_dates[n_tr:n_va]
    test_dates = all_dates[n_va:]

    return Dataset(
        name=name, panel=panel, fwd_ret=fwd, next_ret=nxt, horizon=horizon,
        train_dates=train_dates, val_dates=val_dates, test_dates=test_dates,
    )


def window_view(ds: Dataset, name: str, train_dates, val_dates, test_dates) -> Dataset:
    """把已有 Dataset 重新切成另一个时间窗，**复用同一份 panel 与已算好的收益**。

    滚动窗口必须这样做：panel 与 fwd/next_ret 只依赖 horizon，与切分无关，
    每个窗口重新 load parquet + 重新算 shift 是纯浪费。
    """
    return Dataset(
        name=name,
        panel=ds.panel,
        fwd_ret=ds.fwd_ret,
        next_ret=ds.next_ret,
        horizon=ds.horizon,
        train_dates=pd.DatetimeIndex(train_dates),
        val_dates=pd.DatetimeIndex(val_dates),
        test_dates=pd.DatetimeIndex(test_dates),
    )


def rolling_window_splits(
    dates: pd.DatetimeIndex,
    n_windows: int,
    test_size: int,
    val_size: int,
    min_train_size: int,
    expanding: bool = True,
    train_size: int | None = None,
) -> list[tuple[pd.DatetimeIndex, pd.DatetimeIndex, pd.DatetimeIndex]]:
    """生成最近 n_windows 个滚动切分（test 段互不重叠），从旧到新返回。

    每个窗口 test 不重叠、且都以样本末尾收尾，这样能覆盖到最新行情；
    train 默认 expanding（用尽所有历史），也可设 expanding=False + train_size 得到滑窗。
    """
    n = len(dates)
    first_test_start = min_train_size + val_size
    out: list[tuple[pd.DatetimeIndex, pd.DatetimeIndex, pd.DatetimeIndex]] = []
    t1 = n
    while len(out) < n_windows:
        t0 = t1 - test_size
        if t0 < first_test_start:
            break
        v1, v0 = t0, t0 - val_size
        # train 永远紧贴 val 之前结束（v0）。expanding 从样本最早开始；
        # 滑窗则只取 train_size 天。**必须用切片而非 dates[:tr_end]，
        # 后者把 tr_end 当结束下标，train 长度会等于 tr_end 而非 train_size
        # （滑窗会静默退化成 expanding）。
        if expanding:
            tr = dates[:v0]
        else:
            width = train_size if train_size else v0
            tr = dates[max(0, v0 - width):v0]
        out.append((tr, dates[v0:v1], dates[t0:t1]))
        t1 = t0
    out.reverse()
    return out
