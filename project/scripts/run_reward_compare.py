"""
方向 C: 标量 IC 奖励 vs 结构化失败模式奖励。

两组在相同真实 CSI300 数据、相同预算、相同初始策略下对比：
- Scalar 组：只看 mean IC（模拟 QuantEvolver）
- Structured 组：看 6 种失败模式标签（本文方法）

度量：
- ACCEPTED 累计数
- Q_t 曲线
- 样本效率（第几轮出现 ACCEPTED）
"""
from __future__ import annotations
import sys, re, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.dsl.operators import OPERATORS, list_operators
from src.regime.cluster import regime_summary
from src.evaluator.sealed import SplitConfig
from src.controller.adapter import cold_start_policy, adapt_policy, compute_quality
from src.controller.scalar_adapter import scalar_adapt
from src.controller.proposer import propose_factors
from src.learn.failure_modes import extract_failure_modes, ACCEPTED, DIRECTION_REVERSED


def _eval_expr(expr, panel):
    local = {op: OPERATORS[op] for op in OPERATORS}
    local["panel"] = panel
    for f in ["close", "volume", "open", "high", "low", "ret"]:
        expr = re.sub(rf'\b{f}\b', f"panel['{f}']", expr)
    try:
        return eval(expr, {"__builtins__": {}}, local)
    except Exception:
        return None


def _per_regime_ic(factor, fwd, regime_arr):
    df = pd.DataFrame({"f": factor.values, "r": fwd.values, "regime": regime_arr},
                      index=factor.index).dropna()
    out = {}
    for r in sorted(df["regime"].dropna().unique()):
        daily = []
        for d, g in df[df["regime"] == r].groupby(level=0):
            if len(g) >= 5:
                ic = spearmanr(g["f"], g["r"])[0]
                if np.isfinite(ic):
                    daily.append(ic)
        if daily:
            out[int(r)] = float(np.mean(daily))
    return out


def _ops_in_expr(expr):
    """提取表达式中用到的算子。"""
    return list(set(re.findall(r"(rolling_mean|rolling_std|rolling_max|rolling_min|rolling_rank|"
                               r"cs_rank|cs_zscore|lag|delta|add|sub|mul|div)\(", expr)))


def run(n_rounds=8, factors_per_round=10):
    print("=" * 70)
    print("方向 C: Scalar IC Reward vs Structured Failure-Mode Reward")
    print("=" * 70)

    panel = pd.read_parquet(ROOT / "data" / "csi300_daily.parquet").sort_index()
    dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(dates)
    cfg = SplitConfig(
        train_end=str(dates[int(n*0.6)].date()),
        embargo_end=str(dates[int(n*0.7)].date()),
        test_start=str(dates[int(n*0.8)].date()),
    )
    td = dates[dates <= pd.Timestamp(cfg.train_end)]
    rl, _, _ = regime_summary(panel, pd.Series(True, index=td), n_regimes=4)

    fwd = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)
    test_dates = dates[dates >= pd.Timestamp(cfg.test_start)]
    tmask = panel.index.get_level_values(0).isin(test_dates)
    ptest = panel[tmask]
    ftest = fwd[tmask]
    rarr = rl.reindex(ptest.index.get_level_values(0)).values

    ops = list_operators()

    # 两组独立策略
    p_scalar = cold_start_policy(ops)
    p_struct = cold_start_policy(ops)

    scalar_Q, struct_Q = [], []
    scalar_accepted, struct_accepted = 0, 0
    scalar_first_round, struct_first_round = None, None

    for t in range(n_rounds):
        # 两组各自提案（用相同种子保证初始分布一致）
        p_scalar.round = t
        p_struct.round = t
        exprs_s = propose_factors(p_scalar, n=factors_per_round, seed=t * 101)
        exprs_r = propose_factors(p_struct, n=factors_per_round, seed=t * 101)

        # 评估 Scalar 组
        scalar_scored = []
        scalar_reports = []
        for expr in exprs_s:
            f = _eval_expr(expr, panel)
            if f is None:
                continue
            ft = f[tmask]
            if len(ft.dropna()) < 200:
                continue
            fic = _per_regime_ic(ft, ftest, rarr)
            if not fic:
                continue
            mean_ic = float(np.mean(list(fic.values())))
            scalar_scored.append({"expr": expr, "ic": mean_ic, "ops_used": _ops_in_expr(expr)})

            # 也提取标签（仅用于统计 Q_t，不用于更新）
            rep = extract_failure_modes({}, fic, sharpe=mean_ic*5, turnover=1.0)
            rep.expression = expr
            scalar_reports.append(rep)
            if ACCEPTED in rep.labels:
                scalar_accepted += 1
                if scalar_first_round is None:
                    scalar_first_round = t

        # 评估 Structured 组
        struct_reports = []
        for expr in exprs_r:
            f = _eval_expr(expr, panel)
            if f is None:
                continue
            ft = f[tmask]
            if len(ft.dropna()) < 200:
                continue
            fic = _per_regime_ic(ft, ftest, rarr)
            if not fic:
                continue
            mean_ic = float(np.mean(list(fic.values())))
            rep = extract_failure_modes({}, fic, sharpe=mean_ic*5, turnover=1.0)
            rep.expression = expr
            struct_reports.append(rep)
            if ACCEPTED in rep.labels:
                struct_accepted += 1
                if struct_first_round is None:
                    struct_first_round = t

        # Q_t: ACCEPTED 因子的 mean |IC|
        s_q = compute_quality(scalar_reports)
        r_q = compute_quality(struct_reports)
        scalar_Q.append(s_q)
        struct_Q.append(r_q)

        # Scalar 组用标量更新
        p_scalar = scalar_adapt(p_scalar, scalar_scored)
        # Structured 组用失败模式更新
        p_struct = adapt_policy(p_struct, struct_reports)

        print(f"\n--- Round {t} ---")
        print(f"  Scalar:    tested={len(scalar_scored)}, accepted_total={scalar_accepted}, Q={s_q:.5f}")
        print(f"  Structured: tested={len(struct_reports)}, accepted_total={struct_accepted}, Q={r_q:.5f}")

    # 汇总
    print("\n" + "=" * 70)
    print("对比结果")
    print("=" * 70)

    print(f"\n{'指标':25s} {'Scalar':>10s} {'Structured':>10s}")
    print("-" * 50)
    print(f"{'ACCEPTED 累计':25s} {scalar_accepted:>10d} {struct_accepted:>10d}")
    print(f"{'首次 ACCEPTED 轮次':25s} {str(scalar_first_round):>10s} {str(struct_first_round):>10s}")
    print(f"{'Q_t 曲线下面积':25s} {np.sum(scalar_Q):>10.4f} {np.sum(struct_Q):>10.4f}")
    print(f"{'最终 Q_t':25s} {scalar_Q[-1]:>10.4f} {struct_Q[-1]:>10.4f}")

    print("\nQ_t 曲线:")
    for t in range(n_rounds):
        print(f"  R{t}: scalar={scalar_Q[t]:.4f}  struct={struct_Q[t]:.4f}")

    # 保存
    out = {
        "scalar_Q": scalar_Q, "struct_Q": struct_Q,
        "scalar_accepted": scalar_accepted, "struct_accepted": struct_accepted,
        "scalar_first": scalar_first_round, "struct_first": struct_first_round,
    }
    with open(ROOT / "data" / "reward_compare.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nsaved: data/reward_compare.json")


if __name__ == "__main__":
    run()
