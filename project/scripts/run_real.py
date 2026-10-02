"""
真实 CSI300 回测（方向修正版）。

关键修正：
  多空方向在 validation 窗口估计（estimate_direction），
  test 窗口固定使用该方向，不能重新估计（防泄漏）。

切分: train 50% / embargo 10% / validation 15% / test 25%
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.dsl.operators import OPERATORS
from src.regime.cluster import regime_summary
from src.evaluator.sealed import SplitConfig, SealedEvaluator
from src.strategy.backtest import evaluate_strategy, estimate_direction
from src.memory.tree import DiscoveryTree, ExperimentNode


def build_factors(panel):
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


def main():
    print("=" * 70)
    print("真实 CSI300 回测（方向在 validation 估计，test 固定）")
    print("=" * 70)

    panel = pd.read_parquet(ROOT / "data" / "csi300_daily.parquet").sort_index()
    dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(dates)

    # 切分: 50/10/15/25
    i50, i60, i75 = int(n*0.5), int(n*0.6), int(n*0.75)
    train_end = dates[i50]
    embargo_end = dates[i60]
    val_end = dates[i75]
    print(f"\ntrain≤{train_end.date()}  embargo≤{embargo_end.date()}  "
          f"validation≤{val_end.date()}  test>{val_end.date()}")

    td = dates[dates <= train_end]
    rl, _, _ = regime_summary(panel, pd.Series(True, index=td), n_regimes=4)

    fwd = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)

    val_dates = dates[(dates > embargo_end) & (dates <= val_end)]
    test_dates = dates[dates > val_end]

    factors = build_factors(panel)
    tree = DiscoveryTree(ROOT / "data" / "discovery_tree_real.jsonl")

    print(f"validation {len(val_dates)} 天, test {len(test_dates)} 天\n")

    results = []
    for fid, f in factors.items():
        # validation 数据
        vmask = f.index.get_level_values(0).isin(val_dates)
        f_val = f[vmask]
        fr_val = fwd[fwd.index.get_level_values(0).isin(val_dates)]

        # 在 validation 上估计方向
        direction = estimate_direction(f_val, fr_val)

        # test 数据（用 validation 确定的方向，不再重新估计）
        tmask = f.index.get_level_values(0).isin(test_dates)
        f_test = f[tmask]
        fr_test = fwd[fwd.index.get_level_values(0).isin(test_dates)]

        strat = evaluate_strategy(f_test, fr_test, fid, cost_bps=2.0,
                                   direction=direction,
                                   notes="direction fixed from validation")

        # per-regime IC（test）
        df = pd.DataFrame({"f": f_test.values, "r": fr_test.values,
                           "reg": rl.reindex(f_test.index.get_level_values(0)).values
                           }, index=f_test.index).dropna()
        from scipy.stats import spearmanr
        regime_ic = {}
        for r in sorted(df["reg"].dropna().unique()):
            daily = []
            for d, g in df[df["reg"] == r].groupby(level=0):
                if len(g) >= 5:
                    ic = spearmanr(g["f"], g["r"])[0]
                    if np.isfinite(ic):
                        daily.append(ic)
            if daily:
                regime_ic[int(r)] = float(np.mean(daily))

        print(f"{fid:15s} direction={direction:+d}  "
              f"ann_ret={strat.ann_return:+.4f}  sharpe={strat.sharpe:+.3f}  "
              f"maxDD={strat.max_drawdown:.4f}")
        print(f"{'':15s} test per-regime IC: " +
              ", ".join(f"R{r}={v:+.4f}" for r, v in regime_ic.items()))

        results.append({"id": fid, "dir": direction, "sharpe": strat.sharpe,
                        "ann_ret": strat.ann_return, "regime_ic": regime_ic})

        tree.add(ExperimentNode(
            experiment_id=f"real_{fid}",
            timestamp=str(pd.Timestamp.now().date()),
            regime_at_time=int(rl.iloc[-1]),
            hypothesis=fid, expression=fid,
            test_regime_ic=regime_ic,
            status="accepted" if strat.sharpe > 0.3 else "rejected",
            notes=f"dir={direction}, sharpe={strat.sharpe:.3f}",
        ))

    print("\n" + "=" * 70)
    print("汇总（方向已修正）")
    print("=" * 70)
    for r in results:
        print(f"  {r['id']:15s} dir={r['dir']:+d}  sharpe={r['sharpe']:+.3f}")


if __name__ == "__main__":
    main()
