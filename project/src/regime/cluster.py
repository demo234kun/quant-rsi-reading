"""
Regime 聚类与标注。

在 train 窗口上用无监督聚类识别 regime，test/embargo 窗口用最近中心分配。
Agent 无权改 regime 标签——这是密封层的一部分。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def build_regime_features(price_panel: pd.DataFrame) -> pd.DataFrame:
    """从价格面板构造 regime 特征（日频）。

    特征：市场日收益、波动、成交变化、短期动量、短期反转。
    输出：按 date 索引的 DataFrame。
    """
    # 横截面平均日收益（市场收益）
    mkt_ret = price_panel["ret"].groupby(level=0).mean()
    mkt_vol = mkt_ret.rolling(20).std()
    mkt_mom = mkt_ret.rolling(20).mean()
    mkt_rev = mkt_ret.rolling(5).mean()  # 短期反转
    volume_chg = price_panel["volume"].groupby(level=0).mean().pct_change(5)

    feat = pd.DataFrame({
        "mkt_ret": mkt_ret,
        "mkt_vol": mkt_vol,
        "mkt_mom": mkt_mom,
        "mkt_rev": mkt_rev,
        "volume_chg": volume_chg,
    }).dropna()
    return feat


def fit_regime(feat_train: pd.DataFrame, n_regimes: int = 4, seed: int = 42):
    """在 train 特征上拟合 KMeans。返回 scaler + kmeans。"""
    scaler = StandardScaler()
    X = scaler.fit_transform(feat_train.values)
    km = KMeans(n_clusters=n_regimes, random_state=seed, n_init=10)
    km.fit(X)
    return scaler, km


def assign_regime(feat: pd.DataFrame, scaler, km) -> pd.Series:
    """给任意日期打 regime 标签。"""
    X = scaler.transform(feat.values)
    labels = km.predict(X)
    return pd.Series(labels, index=feat.index, name="regime")


def regime_summary(price_panel: pd.DataFrame, train_mask: pd.Series, n_regimes: int = 4):
    """端到端：构造特征、在 train 上拟合、给全样本打标签。

    train_mask: 布尔 Series（按 date 索引），True 表示该日属于 train。
    返回：date -> regime 的 Series，以及 scaler/km。
    """
    feat = build_regime_features(price_panel)
    feat_train = feat.loc[train_mask.reindex(feat.index).fillna(False)]
    scaler, km = fit_regime(feat_train, n_regimes=n_regimes)
    labels = assign_regime(feat, scaler, km)
    return labels, scaler, km
