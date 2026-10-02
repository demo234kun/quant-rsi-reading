"""
Walk-forward 评估：滚动半年窗口，解决单一切分 regime 样本不足。

设计：
  窗口1: train=2019-2021(3年), test=2022H1
  窗口2: train=2019-2022H1,     test=2022H2
  ...
  窗口6: train=2019-2023H2,     test=2024H2

每个窗口：
  1. 在 train 上重新做 regime 聚类
  2. 按波动率均值对齐 regime 标签（R0=低波动 → R3=高波动）
  3. 在 test 上算 per-regime IC
  4. 汇总所有窗口同 regime 的 IC（样本量 ×6）
"""
from __future__ import annotations
import sys, re, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.dsl.operators import OPERATORS
from src.regime.cluster import build_regime_features


# 半年窗口边界
WINDOWS = [
    ("2019-01-01", "2022-01-01", "2022-07-01"),
    ("2019-01-01", "2022-07-01", "2023-01-01"),
    ("2019-01-01", "2023-01-01", "2023-07-01"),
    ("2019-01-01", "2023-07-01", "2024-01-01"),
    ("2019-01-01", "2024-01-01", "2024-07-01"),
    ("2019-01-01", "2024-07-01", "2025-01-01"),
]


def _factors(panel):
    """4 个有经济逻辑的固定因子。"""
    close = panel["close"]
    vol = panel["volume"]
    ret = close.groupby(level="symbol").pct_change()
    return {
        "reversal_5d": OPERATORS["cs_rank"](OPERATORS["lag"](ret, 5)),
        "momentum_20d": OPERATORS["cs_rank"](OPERATORS["lag"](ret, 20)),
        "volume_ratio": OPERATORS["cs_rank"](
            OPERATORS["div"](vol, OPERATORS["rolling_mean"](vol, 20))),
        "volatility_20d": OPERATORS["cs_rank"](OPERATORS["rolling_std"](ret, 20)),
    }


def _cluster_and_align(panel, train_end, n_regimes=4):
    """在 train 上聚类，按波动率均值对齐标签。"""
    feats = build_regime_features(panel)
    dates = feats.index
    train_dates = dates[dates <= pd.Timestamp(train_end)]
    X = feats.loc[train_dates].dropna()

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=n_regimes, n_init=10, random_state=0)
    raw = km.fit_predict(Xs)

    # 对齐：按每个 cluster 的平均波动率（feats 第 2 列通常是波动率）排序
    vol_col = [c for c in feats.columns if "vol" in c.lower()]
    sort_col = vol_col[0] if vol_col else feats.columns[0]

    cluster_vol = {}
    for c in range(n_regimes):
        mask = raw == c
        cluster_vol[c] = feats.loc[X.index[mask], sort_col].mean()

    # 排序：低波动 → 0，高波动 → n-1
    order = sorted(cluster_vol, key=lambda c: cluster_vol[c])
    remap = {old: new for new, old in enumerate(order)}

    labels = pd.Series(raw, index=X.index).map(remap)

    # 分配所有日期（包括 test）
    all_feats = feats.dropna()
    Xall = scaler.transform(all_feats)
    raw_all = km.predict(Xall)
    all_labels = pd.Series(raw_all, index=all_feats.index).map(remap)
    return all_labels


def _daily_ic_by_regime(factor, fwd, labels):
    """算每个 regime 的日度 IC 列表。"""
    df = pd.DataFrame({
        "f": factor.values, "r": fwd.values,
        "reg": labels.reindex(factor.index.get_level_values(0)).values
    }, index=factor.index).dropna()

    out = {}
    for r in sorted(df["reg"].dropna().unique()):
        daily = []
        for d, g in df[df["reg"] == r].groupby(level=0):
            if len(g) >= 5:
                ic = spearmanr(g["f"], g["r"])[0]
                if np.isfinite(ic):
                    daily.append(ic)
        if daily:
            out[int(r)] = daily
    return out


def run():
    print("=" * 70)
    print("Walk-forward: 6 个半年 test 窗口，扩展 train")
    print("=" * 70)

    panel = pd.read_parquet(ROOT / "data" / "csi300_daily.parquet").sort_index()
    fwd = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)

    # 收集每个因子 × 每个 regime 的所有窗口日度 IC
    pooled = {}  # factor -> regime -> [daily IC across all windows]
    window_summary = []

    for wi, (tstart, tend, test_end) in enumerate(WINDOWS):
        labels = _cluster_and_align(panel, tend, n_regimes=4)

        test_dates = panel.index.get_level_values(0).unique()
        test_dates = test_dates[(test_dates >= pd.Timestamp(tend)) &
                                (test_dates < pd.Timestamp(test_end))]
        tmask = panel.index.get_level_values(0).isin(test_dates)

        factors = _factors(panel)
        wrow = {"window": f"{tend[:7]}~{test_end[:7]}"}

        for fname, f in factors.items():
            ics = _daily_ic_by_regime(f[tmask], fwd[tmask], labels)
            pooled.setdefault(fname, {})
            for r, daily in ics.items():
                pooled[fname].setdefault(r, []).extend(daily)
            wrow[fname] = {f"R{r}": round(float(np.mean(v)), 4) for r, v in ics.items()}

        window_summary.append(wrow)
        print(f"\n窗口 {wi+1}: {wrow['window']}  (test {len(test_dates)} 天)")
        for fname in factors:
            print(f"  {fname:15s} {wrow[fname]}")

    # 汇总：pooled IC + 置信区间
    print("\n" + "=" * 70)
    print("Pooled 结果（6 窗口汇总，regime 按波动率对齐）")
    print("=" * 70)
    print(f"\n{'因子':15s} {'Reg':>4s} {'n_days':>7s} {'meanIC':>9s} {'SE':>7s} {'t':>7s} {'95%CI':>18s}")
    print("-" * 80)

    final = {}
    for fname in sorted(pooled):
        final[fname] = {}
        for r in sorted(pooled[fname]):
            arr = np.array(pooled[fname][r])
            m = arr.mean()
            se = arr.std() / np.sqrt(len(arr))
            t = m / se if se > 0 else 0
            ci = (m - 1.96*se, m + 1.96*se)
            sig = "***" if abs(t) > 2.58 else ("**" if abs(t) > 1.96 else ("*" if abs(t) > 1.65 else ""))
            print(f"{fname:15s} R{r:>3d} {len(arr):>7d} {m:>+9.4f} {se:>7.4f} {t:>+7.2f} "
                  f"[{ci[0]:+.4f},{ci[1]:+.4f}] {sig}")
            final[fname][f"R{r}"] = {
                "n": len(arr), "ic": m, "se": se, "t": t,
                "ci": ci,
            }
        print()

    with open(ROOT / "data" / "walkforward.json", "w", encoding="utf-8") as f:
        json.dump({"windows": window_summary, "pooled": {
            k: {r: {kk: (vv if not isinstance(vv, tuple) else list(vv))
                    for kk, vv in d.items()}
                for r, d in v.items()}
            for k, v in final.items()
        }}, f, ensure_ascii=False, indent=2, default=str)
    print("saved: data/walkforward.json")


if __name__ == "__main__":
    run()
