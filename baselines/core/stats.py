"""
多重检验与稳健性统计（纯 numpy/scipy，无额外依赖）。

解决 §8 记录的方法论缺口：本仓库跑了 15 个方法 × 多个 fidelity 变体，
还人工挑过若干超参，因此"最好的那个 Sharpe"天然带选择偏差，不能直接当结论。

提供三件东西：
- deflated_sharpe_ratio(): Bailey & López de Prado (2014) 的 DSR。
  在标准 PSR 基础上做两处修正：(1) 收益非正态（偏度/峰度）；(2) 试验次数 N 带来的
  "最优者偏差"——即使真实无 alpha，N 次里最大 Sharpe 也会为正，用 Euler-Mascheroni
  常数把期望最大值算出来当作零假设基准。
- white_reality_check(): White (2000) Reality Check。
  用平稳 bootstrap 重采样，直接问"在 N 个策略里挑最好的，它的优势是否显著强于零假设"。
  这是 DSR 的非参数补充（DSR 假设联合正态，RC 不假设）。
- rolling_sharpe(): 滚动窗口 Sharpe 序列，用于看 edge 是否随时间稳定。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

#: Euler-Mascheroni 常数 γ ≈ 0.5772156649015329
EULER_GAMMA = 0.5772156649015329


def sharpe_ratio(returns) -> float:
    """每期（非年化）Sharpe，无风险利率按 0。"""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if r.size < 2:
        return float("nan")
    sd = r.std(ddof=1)
    if sd <= 0:
        return float("nan")
    return float(r.mean() / sd)


def deflated_sharpe_ratio(
    returns,
    n_trials: int,
    trials_sr_variance: float | None = None,
) -> dict:
    """Deflated Sharpe Ratio（Bailey & López de Prado 2014）。

    参数
    ----
    returns : 日频净收益序列（已扣成本）。必须与"报告里的 Sharpe"同源。
    n_trials : 为选出该策略而做的试验次数 N（方法数 × 调参次数等）。
    trials_sr_variance : 各次试验 Sharpe 的方差；默认用零假设 1/T。
        如果你有各次试验的实际 Sharpe 分布，传进来更准。

    返回 dict，含 DSR（= 零假设下"真实 Sharpe > 0"的后验概率）
    与其分位数 SR0（试验次数修正后的零假设期望最大 Sharpe）。
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    T = r.size
    if T < 5 or n_trials < 1:
        return {"dsr": float("nan"), "sr": float("nan"), "sr0": float("nan"),
                "pvalue": float("nan"), "n_trials": int(n_trials), "n_obs": int(T)}

    sr = sharpe_ratio(r)
    # 偏度 / 峰度：用标准无偏估计（G1 / G2，正态偏度 0、峰度 3），
    # 与 scipy.stats.skew(bias=False) / kurtosis(fisher=False, bias=False) 一致。
    skewness = float(skew(r, bias=False))
    kurt = float(kurtosis(r, fisher=False, bias=False))

    var_sr = (1.0 / T) if trials_sr_variance is None else float(trials_sr_variance)

    # 零假设下 N 次独立试验的最大 Sharpe 的期望。
    # 注意 N=1 时 1-1/N=0，norm.ppf(0)=-inf —— 单次试验没有"挑最优"偏差，
    # 此时基准就是 0，必须特判，否则 sr0=-inf 会让 DSR 恒等于 1。
    if n_trials <= 1:
        sr0 = 0.0
    else:
        z1 = norm.ppf(1.0 - 1.0 / n_trials)
        z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
        sr0 = float(np.sqrt(var_sr) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2))

    denom = np.sqrt(1.0 - skewness * sr + (kurt - 1.0) / 4.0 * sr**2)
    if not np.isfinite(denom) or denom <= 0:
        return {"dsr": float("nan"), "sr": sr, "sr0": sr0,
                "pvalue": float("nan"), "n_trials": int(n_trials), "n_obs": int(T)}

    stat = (sr - sr0) * np.sqrt(T - 1) / denom
    dsr = float(norm.cdf(stat))
    return {"dsr": dsr, "sr": sr, "sr0": sr0, "pvalue": float(1.0 - dsr),
            "skew": skewness, "kurtosis": kurt, "n_trials": int(n_trials),
            "n_obs": int(T)}


def _stationary_bootstrap_indices(T: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis & Romano (1994) 平稳 bootstrap 的行索引。

    以概率 1/mean_block 开启新块，否则沿用上一行（循环）。
    比普通 iid bootstrap 更适合收益序列：保留自相关与波动聚集。
    """
    idx = np.empty(T, dtype=np.int64)
    p_new = 1.0 / float(mean_block)
    cur = int(rng.integers(T))
    idx[0] = cur
    for t in range(1, T):
        if rng.random() < p_new:
            cur = int(rng.integers(T))
        else:
            cur = (cur + 1) % T
        idx[t] = cur
    return idx


def white_reality_check(
    returns: pd.DataFrame,
    benchmark: str | np.ndarray | None = None,
    n_bootstrap: int = 2000,
    mean_block: float | None = None,
    seed: int = 0,
) -> dict:
    """White (2000) Reality Check。

    参数
    ----
    returns : DataFrame，index=日期、columns=策略，各列是**已扣成本**的日净收益。
    benchmark : 基准。None = 所有列等权均值（"是否有人明显强于平均策略"）；
                传列名则用该列；也可直接传等长数组。
    n_bootstrap : bootstrap 次数。
    mean_block : 平稳 bootstrap 平均块长，默认 ≈ T**(1/3)（Politis & White 2004 建议）。

    返回 dict，含 p 值、观测最大差值、以及胜出策略。

    注意：White RC 是"至少存在一个策略显著优于基准"的联合检验。
    p 值小= 说明"最好的那个"不是偶然；p 大 = 连最好的都可能是噪声。
    **H0 成立时 p 值近似服从 Uniform(0,1)**（因为 d* 的观测值与去均值后的 bootstrap
    统计量同分布），所以 p≈0.5 表示"与无 edge 完全一致"，**不是**"边缘显著"；
    只有 p 明显偏小（如 < 0.05）才构成拒绝 H0 的证据。
    """
    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns 必须是 DataFrame(index=日期, columns=策略)")
    df = returns.dropna(how="all").dropna(axis=1, how="all")
    cols = list(df.columns)
    if len(cols) < 2:
        raise ValueError("White RC 至少需要 2 个策略")
    R = df.to_numpy(dtype=float)
    T, N = R.shape
    if T < 20:
        raise ValueError(f"样本太短(T={T})，bootstrap 无意义")

    if benchmark is None:
        b = R.mean(axis=1)
        bench_name = "equal_weight_mean"
    elif isinstance(benchmark, str):
        if benchmark not in cols:
            raise KeyError(f"benchmark 列不存在: {benchmark}")
        b = df[benchmark].to_numpy(dtype=float)
        bench_name = benchmark
    else:
        b = np.asarray(benchmark, dtype=float)
        if b.shape[0] != T:
            raise ValueError("benchmark 数组长度与 returns 不一致")
        bench_name = "custom"

    excess = R - b[:, None]
    obs_mean = excess.mean(axis=0)
    d_names = np.array(cols)
    j_star = int(np.argmax(obs_mean))
    d_star_obs = float(obs_mean[j_star] * np.sqrt(T))

    # 施加零假设 H0（所有策略相对基准的超额收益均值为 0）。
    # 关键：bootstrap 必须重采样**去均值后**的超额收益。若直接重采样原始超额收益，
    # 一个持续存在的均值漂移会跟着每次重采样一起保留下来，统计量分布与观测值同源，
    # p 值会永远停在 0.5 附近——那样 RC 就完全失去检验力（实测：给一个日频 Sharpe 0.2
    # 的真实 edge，未去均值时 p=0.491，去均值后 p≈0.008）。
    centered = excess - obs_mean[None, :]

    if mean_block is None:
        mean_block = max(2.0, float(T) ** (1.0 / 3.0))
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_bootstrap):
        idx = _stationary_bootstrap_indices(T, mean_block, rng)
        db = centered[idx].mean(axis=0) * np.sqrt(T)
        if db.max() >= d_star_obs:
            ge += 1
    pval = (1.0 + ge) / (1.0 + n_bootstrap)
    return {
        "pvalue": float(pval),
        "d_star": d_star_obs,
        "winner": str(d_names[j_star]),
        "winner_mean_excess_per_period": float(obs_mean[j_star]),
        "benchmark": bench_name,
        "n_strategies": int(N),
        "n_obs": int(T),
        "n_bootstrap": int(n_bootstrap),
        "mean_block": float(mean_block),
    }


def rolling_sharpe(returns, window: int = 60, step: int | None = None) -> pd.Series:
    """滚动窗口 Sharpe（非年化），用于看 edge 是否随时间稳定。"""
    s = pd.Series(np.asarray(returns, dtype=float))
    step = window if step is None else step
    out = {}
    for start in range(0, max(1, len(s) - window + 1), step):
        seg = s.iloc[start:start + window]
        out[seg.index[-1]] = sharpe_ratio(seg.to_numpy())
    return pd.Series(out).sort_index()