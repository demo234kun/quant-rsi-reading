"""
多轮 RSI 递归循环 v2：P_t → E_t → L_t → A_t → P_{t+1}

v2 改进：
  - 精英保留：上一轮 ACCEPTED 的表达式进入名人堂，下一轮做 mutation
  - DIRECTION_REVERSED 翻转后重提（不是拉黑）
  - Q_t 只算 ACCEPTED 因子的 IC（不是所有因子）
  - Diversity 检查：新因子与名人堂的相关性不能太高

合成数据上验证机制；真实金融结论看 run_real.py。
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import re
import numpy as np
import pandas as pd

from src.data.synthetic import generate_synthetic_panel
from src.regime.cluster import regime_summary
from src.dsl.operators import OPERATORS, list_operators
from src.evaluator.sealed import SplitConfig, SealedEvaluator
from src.strategy.backtest import evaluate_strategy
from src.learn.failure_modes import (
    extract_failure_modes, summarize_round,
    ACCEPTED, DIRECTION_REVERSED, FailureReport,
)
from src.controller.adapter import cold_start_policy, adapt_policy, PolicyState
from src.controller.proposer import propose_factors


def _eval_expr(expr: str, panel: pd.DataFrame) -> pd.Series | None:
    """沙箱版 DSL 求值。"""
    local_dict = {op: OPERATORS[op] for op in OPERATORS}
    local_dict["panel"] = panel
    local_dict["mul"] = OPERATORS["mul"]
    local_dict["sub"] = OPERATORS["sub"]
    local_dict["add"] = OPERATORS["add"]
    local_dict["div"] = OPERATORS["div"]
    local_dict["rolling_mean"] = OPERATORS["rolling_mean"]
    local_dict["rolling_std"] = OPERATORS["rolling_std"]
    local_dict["rolling_max"] = OPERATORS["rolling_max"]
    local_dict["rolling_min"] = OPERATORS["rolling_min"]
    local_dict["rolling_rank"] = OPERATORS["rolling_rank"]
    local_dict["lag"] = OPERATORS["lag"]
    local_dict["delta"] = OPERATORS["delta"]
    local_dict["cs_rank"] = OPERATORS["cs_rank"]
    local_dict["cs_zscore"] = OPERATORS["cs_zscore"]

    for field in ["close", "volume", "open", "high", "low", "ret"]:
        expr = re.sub(rf'\b{field}\b', f"panel['{field}']", expr)

    try:
        result = eval(expr, {"__builtins__": {}}, local_dict)
        return result
    except Exception:
        return None


def run_round(
    policy: PolicyState,
    panel: pd.DataFrame,
    evaluator: SealedEvaluator,
    test_dates,
    fwd_ret: pd.Series,
    hall_of_fame: list[str],
    reverse_set: list[str],
    n_factors: int = 10,
) -> tuple[list[FailureReport], float, list[str], list[str]]:
    """跑一轮，返回 reports、Q_t、新名人堂、新翻转集。"""
    expressions = propose_factors(
        policy, n=n_factors, seed=policy.round * 100,
        hall_of_fame=hall_of_fame, reverse_set=reverse_set,
    )
    reports = []
    new_hof = []
    new_reverse = []

    for expr in expressions:
        factor = _eval_expr(expr, panel)
        if factor is None or len(factor.dropna()) < 100:
            continue

        try:
            res_val = evaluator.validate(factor, f"r{policy.round}_{abs(hash(expr))%10000}", expr)
            res_test = evaluator.finalize(factor, f"r{policy.round}_{abs(hash(expr))%10000}", expr)
        except RuntimeError:
            continue

        f_test = factor[factor.index.get_level_values(0).isin(test_dates)]
        fr_test = fwd_ret[fwd_ret.index.get_level_values(0).isin(test_dates)]
        try:
            strat = evaluate_strategy(f_test, fr_test, "tmp", cost_bps=2.0)
            sharpe = strat.sharpe
            turnover = strat.turnover
        except Exception:
            sharpe = 0.0
            turnover = 1.0

        rep = extract_failure_modes(
            val_regime_ic=res_val.regime_ic,
            test_regime_ic=res_test.regime_ic,
            sharpe=sharpe,
            turnover=turnover,
            cross_sectional_std=float(f_test.std()) if len(f_test) > 0 else 1.0,
        )
        rep.experiment_id = f"r{policy.round}"
        rep.expression = expr
        reports.append(rep)

        # 收集名人堂和翻转集
        if ACCEPTED in rep.labels:
            new_hof.append(expr)
        if DIRECTION_REVERSED in rep.labels:
            new_reverse.append(expr)

    # Q_t: 只算 ACCEPTED 因子的 mean |IC|（v2 重定义）
    accepted_ics = [r.details.get("mean_abs_ic", 0) for r in reports if ACCEPTED in r.labels]
    Q_t = float(np.mean(accepted_ics)) if accepted_ics else 0.0

    return reports, Q_t, new_hof, new_reverse


def main():
    print("=" * 70)
    print("多轮 RSI 递归循环 v2（合成数据，数字无金融意义）")
    print("精英保留 + 翻转重提 + Q_t 只算 ACCEPTED")
    print("=" * 70)

    panel = generate_synthetic_panel(n_symbols=30, n_days=500)
    all_dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(all_dates)

    cfg = SplitConfig(
        train_end=str(all_dates[int(n*0.6)].date()),
        embargo_end=str(all_dates[int(n*0.7)].date()),
        test_start=str(all_dates[int(n*0.8)].date()),
    )
    train_dates = all_dates[all_dates <= pd.Timestamp(cfg.train_end)]
    train_mask = pd.Series(True, index=train_dates)
    regime_labels, _, _ = regime_summary(panel, train_mask, n_regimes=4)

    panel = panel.sort_index()
    fwd_ret = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)
    evaluator = SealedEvaluator(cfg, regime_labels, fwd_ret)
    test_dates = all_dates[all_dates >= pd.Timestamp(cfg.test_start)]

    ops = list_operators()
    policy = cold_start_policy(ops)

    n_rounds = 8
    Q_curve = []
    all_hof = []
    all_reverse = []

    print(f"\n开始 {n_rounds} 轮递归（v2：精英保留 + 翻转重提）...\n")

    for t in range(n_rounds):
        reports, Q_t, new_hof, new_reverse = run_round(
            policy, panel, evaluator, test_dates, fwd_ret,
            hall_of_fame=all_hof[-5:],  # 最近 5 个精英
            reverse_set=all_reverse[-3:],
            n_factors=10,
        )
        summary = summarize_round(reports)
        Q_curve.append(Q_t)
        all_hof.extend(new_hof)
        all_reverse.extend(new_reverse)

        n_accepted = summary.get(ACCEPTED, 0)
        n_reverse = summary.get(DIRECTION_REVERSED, 0)

        print(f"--- Round {t} ---")
        print(f"  提案数: {len(reports)}  ACCEPTED: {n_accepted}  DIRECTION_REV: {n_reverse}")
        print(f"  失败模式: {summary}")
        print(f"  Q_{t} (accepted mean |IC|) = {Q_t:.5f}")
        print(f"  名人堂累计: {len(all_hof)}  翻转集累计: {len(all_reverse)}")

        policy = adapt_policy(policy, reports)

    # Q_t 曲线
    print("\n" + "=" * 70)
    print("Q_t 曲线（v2：只算 ACCEPTED 因子）")
    print("=" * 70)
    for t, q in enumerate(Q_curve):
        bar = "█" * int(q * 2000)
        print(f"  Q_{t} = {q:.5f}  {bar}")

    if len(Q_curve) >= 2:
        delta = Q_curve[-1] - Q_curve[0]
        n_positive = sum(1 for i in range(1, len(Q_curve)) if Q_curve[i] > Q_curve[i-1])
        print(f"\n  Q_0 = {Q_curve[0]:.5f} → Q_{n_rounds-1} = {Q_curve[-1]:.5f}")
        print(f"  ΔQ = {delta:+.5f}  上升轮次: {n_positive}/{len(Q_curve)-1}")
        print(f"  名人堂总数: {len(all_hof)}")


if __name__ == "__main__":
    main()
