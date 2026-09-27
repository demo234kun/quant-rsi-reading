"""
真实 A股数据回测：CSI300 上跑 3 个手动因子 + 策略回测。
所有数字从真实数据现算，不手填。
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.data.real_akshare import load_cached_or_fetch
from src.regime.cluster import regime_summary
from src.dsl.operators import OPERATORS
from src.evaluator.sealed import SplitConfig, SealedEvaluator
from src.strategy.backtest import evaluate_strategy
from src.memory.tree import DiscoveryTree, ExperimentNode


def main():
    cache = ROOT / "data" / "csi300_daily.parquet"
    panel = load_cached_or_fetch(cache, start="20190101", end="20241231")
    if panel is None:
        print("[FAIL] 无数据")
        return

    print(f"\n[real] 面板: {panel.shape}, {panel.index.get_level_values(0).nunique()} 天, "
          f"{panel.index.get_level_values(1).nunique()} 只")

    # 动态切分：60% train / 10% embargo / 30% test
    all_dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(all_dates)
    cfg = SplitConfig(
        train_end=str(all_dates[int(n*0.6)].date()),
        embargo_end=str(all_dates[int(n*0.7)].date()),
        test_start=str(all_dates[int(n*0.8)].date()),
    )
    print(f"[real] train≤{cfg.train_end}, embargo≤{cfg.embargo_end}, test≥{cfg.test_start}")

    train_dates = all_dates[all_dates <= pd.Timestamp(cfg.train_end)]
    train_mask = pd.Series(True, index=train_dates)
    regime_labels, _, _ = regime_summary(panel, train_mask, n_regimes=4)
    print(f"[real] regime 分布: {regime_labels.value_counts().sort_index().to_dict()}")

    panel = panel.sort_index()
    fwd_ret = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)

    vol = panel["volume"]
    close = panel["close"]
    factors = {
        "f1_volume_ratio": OPERATORS["cs_rank"](
            OPERATORS["div"](vol, OPERATORS["rolling_mean"](vol, 20))),
        "f2_reversal": OPERATORS["cs_rank"](
            OPERATORS["lag"](close.pct_change(), 5)),
        "f3_trend": OPERATORS["cs_zscore"](
            OPERATORS["div"](close, OPERATORS["rolling_mean"](close, 10))),
    }

    ev = SealedEvaluator(cfg, regime_labels, fwd_ret)
    tree = DiscoveryTree(ROOT / "data" / "discovery_tree_real.jsonl")

    test_dates = all_dates[all_dates >= pd.Timestamp(cfg.test_start)]

    print("\n" + "=" * 70)
    print("真实 A股 CSI300 回测结果（成本 2bp 单边）")
    print("=" * 70)

    for fid, f in factors.items():
        res_val = ev.validate(f, fid, f"real:{fid}")
        res_test = ev.finalize(f, fid, f"real:{fid}")

        f_test = f[f.index.get_level_values(0).isin(test_dates)]
        fr_test = fwd_ret[fwd_ret.index.get_level_values(0).isin(test_dates)]
        strat = evaluate_strategy(f_test, fr_test, fid, cost_bps=2.0,
                                   notes="real CSI300 daily, qfq")

        print(f"\n  {fid}:")
        print(f"    VAL  per-regime IC: {{", end="")
        print(", ".join(f"R{r}={v:.4f}" for r,v in res_val.regime_ic.items()), end="")
        print("}")
        print(f"    TEST per-regime IC: {{", end="")
        print(", ".join(f"R{r}={v:.4f}" for r,v in res_test.regime_ic.items()), end="")
        print("}")
        print(f"    STRAT: ann_ret={strat.ann_return:.4f}  ann_vol={strat.ann_vol:.4f}  "
              f"sharpe={strat.sharpe:.3f}  maxDD={strat.max_drawdown:.4f}  "
              f"long_short={strat.long_short_spread:.5f}")

        tree.add(ExperimentNode(
            experiment_id=f"real_{fid}",
            timestamp=str(pd.Timestamp.now().date()),
            regime_at_time=int(regime_labels.iloc[-1]),
            hypothesis=f"real CSI300 {fid}",
            expression=f"real:{fid}",
            val_regime_ic=res_val.regime_ic,
            test_regime_ic=res_test.regime_ic,
            status="accepted" if strat.sharpe > 0.3 else "rejected",
            notes=f"sharpe={strat.sharpe:.3f}",
        ))

    print("\n" + "=" * 70)
    print("完成。结果已写入 data/discovery_tree_real.jsonl")


if __name__ == "__main__":
    main()
