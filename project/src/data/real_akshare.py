"""
真实数据加载器（A股，新浪源）。
注意：所有结果必须从真实数据跑出，不允许手填。
"""
from __future__ import annotations
from pathlib import Path
import time
import pandas as pd


def _to_sina_symbol(code: str) -> str:
    """000001 -> sz000001, 600519 -> sh600519"""
    code = str(code).zfill(6)
    if code.startswith(("6", "9")):
        return f"sh{code}"
    else:
        return f"sz{code}"


def load_csi300_daily(start: str = "20190101", end: str = "20241231") -> pd.DataFrame:
    """加载 CSI300 成分股日线（新浪源）。"""
    try:
        import akshare as ak
    except ImportError:
        print("[WARN] akshare 未安装")
        return None

    try:
        constituents = ak.index_stock_cons_csindex(symbol="000300")
        codes = constituents["成分券代码"].tolist()[:50]
        print(f"[data] CSI300 成分股 {len(codes)} 只，拉日线 {start}~{end}（新浪源）...")

        rows = []
        for idx, code in enumerate(codes):
            sym = _to_sina_symbol(code)
            df = None
            for attempt in range(3):
                try:
                    df = ak.stock_zh_a_daily(symbol=sym, start_date=start, end_date=end, adjust="qfq")
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(1.0)
            if df is None or len(df) == 0:
                continue
            try:
                df = df.rename(columns={
                    "date": "date", "open": "open", "high": "high",
                    "low": "low", "close": "close", "volume": "volume",
                })
                df["symbol"] = code
                df["date"] = pd.to_datetime(df["date"])
                df["ret"] = df["close"].pct_change()
                keep = df[["date", "symbol", "open", "high", "low", "close", "volume", "ret"]].dropna()
                rows.append(keep)
            except Exception as e:
                print(f"  [parse-skip] {code}: {e}")
            if (idx + 1) % 10 == 0:
                print(f"  进度 {idx+1}/{len(codes)}, 成功 {len(rows)}")
            time.sleep(0.2)

        if not rows:
            print("[ERROR] 无数据")
            return None
        panel = pd.concat(rows, ignore_index=True)
        panel = panel.set_index(["date", "symbol"]).sort_index()
        print(f"[data] 面板形状: {panel.shape}, {panel.index.get_level_values(0).nunique()} 天, "
              f"{panel.index.get_level_values(1).nunique()} 只")
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
