"""
Regime 敏感性分析：K=2/3/4/5，用 silhouette score 选 K。

回应"regime 数量主观"的质疑。
所有数字从真实数据现算。
"""
from __future__ import annotations
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.regime.cluster import build_regime_features


def run():
    print("=" * 70)
    print("Regime 敏感性分析：K=2..5 + silhouette")
    print("=" * 70)

    panel = pd.read_parquet(ROOT / "data" / "csi300_daily.parquet").sort_index()
    feats = build_regime_features(panel).dropna()
    print(f"\nregime 特征: {feats.columns.tolist()}")
    print(f"样本天数: {len(feats)}")

    X = StandardScaler().fit_transform(feats)

    rows = []
    for k in range(2, 6):
        km = KMeans(n_clusters=k, n_init=20, random_state=0)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)
        counts = pd.Series(labels).value_counts().sort_index()
        inertia = km.inertia_

        rows.append({"k": k, "silhouette": sil, "inertia": inertia,
                     "sizes": counts.tolist()})

        print(f"\nK={k}:  silhouette={sil:.4f}  inertia={inertia:.1f}")
        print(f"  cluster sizes: {counts.tolist()}")
        print(f"  最小簇 {counts.min()} 天，最大簇 {counts.max()} 天")

    # 选 K
    best = max(rows, key=lambda r: r["silhouette"])
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print(f"\n  silhouette 最高: K={best['k']} (sil={best['silhouette']:.4f})")
    print("  解读：silhouette 越接近 1 簇结构越清晰；接近 0 表示簇重叠。")

    # 检查 K=4 的稳健性：如果 K=4 各簇大小都 >50 天，说明可估计
    for r in rows:
        if r["k"] == 4:
            print(f"\n  K=4 簇大小: {r['sizes']}，最小 {min(r['sizes'])} 天")

    with open(ROOT / "data" / "regime_sensitivity.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("\nsaved: data/regime_sensitivity.json")


if __name__ == "__main__":
    run()
