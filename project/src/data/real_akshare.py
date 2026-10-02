"""
真实数据加载器（A股）。
依赖: akshare（pip install akshare）
注意：所有结果必须从真实数据跑出，不允许手填。
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd


def load_csi300_daily(start: str = "20190101", end: str = "20241231") -> pd.DataFrame:
    """加载 CSI300 成分股日线（真实数据）。

    返回 MultiIndex (date, symbol) DataFrame: open/high/low/close/volume/ret。
    需要联网 + akshare。如果 akshare 不可用，返回 None 并提示。
    """
    try:
        import akshare as ak
    except ImportError:
        print("[WARN] akshare 未安装: pip install akshare")
        return None

    try:
        # 获取成分股
        constituents = ak.index_stock_cons_csindex(symbol="000300")
        symbols = constituents["成分券代码"].tolist()[:50]  # 先取前 50 只，避免太慢
        print(f"[data] CSI300 成分股 {len(symbols)} 只，拉日线 {start}~{end}...")

        rows = []
        for sym in symbols:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=sym, period="daily",
                    start_date=start, end_date=end, adjust="qfq"
                )
                if df is None or len(df) == 0:
                    continue
                df = df.rename(columns={
                    "日期": "date", "开盘": "open", "最高": "high",
                    "最低": "low", "收盘": "close", "成交量": "volume",
                })
                df["symbol"] = sym
                df["date"] = pd.to_datetime(df["date"])
                df["ret"] = df["close"].pct_change()
                rows.append(df[["date", "symbol", "open", "high", "low", "close", "volume", "ret"]])
            except Exception as e:
                print(f"  [skip] {sym}: {e}")

        panel = pd.concat(rows, ignore_index=True)
        panel = panel.set_index(["date", "symbol"]).sort_index()
        print(f"[data] 面板形状: {panel.shape}")
        return panel

    except Exception as e:
        print(f"[ERROR] 加载失败: {e}")
        return None


def save_panel(panel: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(path)
    print(f"[data] 已缓存到 {path}")


def load_cached_or_fetch(cache_path: Path, **kwargs) -> pd.DataFrame | None:
    if cache_path.exists():
        print(f"[data] 读缓存 {cache_path}")
        return pd.read_parquet(cache_path)
    panel = load_csi300_daily(**kwargs)
    if panel is not None:
        save_panel(panel, cache_path)
    return panel
