"""
完整端到端：因子 → 密封评估 → 策略回测 → 发现树。

【重要声明】
- 合成数据段：仅验证管线正确性，数字无金融意义，不构成任何结论
- 真实数据段：尝试加载 akshare A股数据；若不可用则明确标注"待跑"
- 所有真实结果必须从真实市场数据跑出，不手填、不虚构
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.data.synthetic import generate_synthetic_panel
from src.regime.cluster import regime_summary
from src.dsl.operators import OPERATORS
from src.evaluator.sealed import SplitConfig, SealedEvaluator
from src.strategy.backtest import evaluate_strategy
from src.memory.tree import DiscoveryTree, ExperimentNode
from src.controller.planner import BudgetState, decide_action


def run_synthetic_pipeline():
    """合成数据：仅验证管线。数字不代表真实金融表现。"""
    print("\n" + "=" * 60)
    print("【A 段】合成数据管线验证（数字无金融意义）")
    print("=" * 60)

    panel = generate_synthetic_panel(n_symbols=50, n_days=1500)
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

    # 手动因子
    vol = panel["volume"]; close = panel["close"]
    factors = {
        "f1_volume_ratio": OPERATORS["cs_rank"](
            OPERATORS["div"](vol, OPERATORS["rolling_mean"](vol, 20))),
        "f2_reversal": OPERATORS["cs_rank"](
            OPERATORS["lag"](close.pct_change(), 5)),
        "f3_trend": OPERATORS["cs_zscore"](
            OPERATORS["div"](close, OPERATORS["rolling_mean"](close, 10))),
    }

    ev = SealedEvaluator(cfg, regime_labels, fwd_ret)
    tree = DiscoveryTree(ROOT / "data" / "discovery_tree.jsonl")
    budget = BudgetState(total=10)

    for fid, f in factors.items():
        action = decide_action(budget)
        res_val = ev.validate(f, fid, f"manual:{fid}")
        res_test = ev.finalize(f, fid, f"manual:{fid}")

        # 策略回测（test 窗口）
        test_dates = all_dates[all_dates >= pd.Timestamp(cfg.test_start)]
        f_test = f[f.index.get_level_values(0).isin(test_dates)]
        fr_test = fwd_ret[fwd_ret.index.get_level_values(0).isin(test_dates)]
        strat = evaluate_strategy(f_test, fr_test, fid, cost_bps=2.0,
                                   notes="合成数据，仅管线验证")

        print(f"\n  {fid} (action={action})")
        print(f"    VAL  per-regime IC: {res_val.regime_ic}")
        print(f"    TEST per-regime IC: {res_test.regime_ic}")
        print(f"    STRAT  ann_ret={strat.ann_return:.4f}  sharpe={strat.sharpe:.3f}  "
              f"maxDD={strat.max_drawdown:.4f}  turnover={strat.turnover:.2f}")

        tree.add(ExperimentNode(
            experiment_id=f"exp_{fid}",
            timestamp=str(pd.Timestamp.now().date()),
            regime_at_time=int(regime_labels.iloc[-1]),
            hypothesis=f"manual {fid} (synthetic, pipeline check)",
            expression=f"manual:{fid}",
            val_regime_ic=res_val.regime_ic,
            test_regime_ic=res_test.regime_ic,
            status="accepted" if res_test.mean_abs_ic > 0.01 else "rejected",
            notes=strat.notes,
        ))
        budget.used += 1


def run_real_data_pipeline():
    """真实 A股数据：尝试加载，不可用则明确标注待跑。"""
    print("\n" + "=" * 60)
    print("【B 段】真实 A股数据（结果必须真实跑出）")
    print("=" * 60)
    try:
        from src.data.real_akshare import load_cached_or_fetch
        cache = ROOT / "data" / "csi300_daily.parquet"
        panel = load_cached_or_fetch(cache, start="20190101", end="20241231")
        if panel is None:
            print("\n[待跑] akshare 未安装或联网失败。")
            print("  运行: pip install akshare")
            print("  然后重跑本脚本，真实结果将写入 data/ 下")
            return
        print(f"\n[真实数据] 面板 {panel.shape}, 日期 {panel.index.get_level_values(0).min().date()} ~ {panel.index.get_level_values(0).max().date()}")
        # TODO: 在真实数据上跑 factors + strategy，结果会写入发现树
        print("[待跑] 真实数据管线接入（Phase 2）")
    except Exception as e:
        print(f"\n[跳过] 真实数据段出错: {e}")


if __name__ == "__main__":
    run_synthetic_pipeline()
    run_real_data_pipeline()
