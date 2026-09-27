"""
合成数据生成。
Phase 1 用合成数据跑通管线；真实 A股接口在 data/loader_real.py 留空。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path


def generate_synthetic_panel(
    n_symbols: int = 50,
    n_days: int = 1500,
    seed: int = 42,
) -> pd.DataFrame:
    """生成合成的 OHLCV 面板数据。

    返回 MultiIndex (date, symbol) 的 DataFrame，列：open/high/low/close/volume/ret。
    内含两个 regime 切换点（600 天和 1100 天），模拟风格变化。
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_days)

    rows = []
    for s in range(n_symbols):
        # 每个股票有不同的 beta 和 alpha
        beta = rng.uniform(0.5, 1.5)
        drift = rng.uniform(-0.0002, 0.0005)
        vol = rng.uniform(0.01, 0.03)

        # regime 切换：第 600 天和 1100 天改变市场方向
        mkt = np.zeros(n_days)
        mkt[:600] = rng.normal(0.0005, 0.01, 600)     # 牛市
        mkt[600:1100] = rng.normal(-0.0008, 0.015, 500)  # 熊市
        mkt[1100:] = rng.normal(0.0003, 0.012, n_days - 1100)  # 震荡

        idio = rng.normal(0, vol, n_days)
        ret = drift + beta * mkt + idio

        close = 100 * np.cumprod(1 + ret)
        open_ = close * (1 + rng.normal(0, 0.002, n_days))
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, n_days)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, n_days)))
        volume = rng.uniform(1e6, 1e7, n_days)

        for i, d in enumerate(dates):
            rows.append((d, f"S{s:03d}", open_[i], high[i], low[i], close[i], volume[i], ret[i]))

    df = pd.DataFrame(rows, columns=["date", "symbol", "open", "high", "low", "close", "volume", "ret"])
    df = df.set_index(["date", "symbol"]).sort_index()
    return df


def save_synthetic(data_dir: Path):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_panel()
    df.to_parquet(data_dir / "synthetic_panel.parquet")
    print(f"saved {len(df)} rows to {data_dir / 'synthetic_panel.parquet'}")
    return df


if __name__ == "__main__":
    save_synthetic(Path(__file__).resolve().parents[2] / "data")
