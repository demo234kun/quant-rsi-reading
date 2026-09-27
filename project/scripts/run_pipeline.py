"""
端到端最小可运行管线：
1. 生成合成数据
2. 拟合 regime
3. 手动提几条因子（用 DSL 算子）
4. 密封评估（先 validate，再 finalize）
5. 结果写入发现树
6. 打印 fuel 状态

Phase 1：不接 LLM，纯手动提案，验证沙箱正确性。
"""
from __future__ import annotations
import sys
from pathlib import Path

# 把项目根加进 path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.data.synthetic import generate_synthetic_panel
from src.regime.cluster import regime_summary
from src.dsl.operators import OPERATORS
from src.evaluator.sealed import SplitConfig, SealedEvaluator, save_result
from src.memory.tree import DiscoveryTree, ExperimentNode
from src.controller.planner import BudgetState, decide_action


def main():
    print("=" * 60)
    print("RegimeSeal Phase 1 端到端管线")
    print("=" * 60)

    # 1. 数据
    print("\n[1/6] 生成合成数据...")
    panel = generate_synthetic_panel(n_symbols=50, n_days=1500)
    print(f"  面板形状: {panel.shape}, 日期范围: {panel.index.get_level_values(0).min().date()} ~ {panel.index.get_level_values(0).max().date()}")

    # 2. regime 标注
    print("\n[2/6] 拟合 regime（在 train 段）...")
    all_dates = panel.index.get_level_values(0).unique()
    cfg = SplitConfig(train_end="2022-12-31", embargo_end="2023-06-30", test_start="2023-07-01")
    train_dates = all_dates[all_dates <= cfg.train_end]
    train_mask = pd.Series(True, index=train_dates)
    regime_labels, scaler, km = regime_summary(panel, train_mask, n_regimes=4)
    print(f"  regime 分布: {regime_labels.value_counts().sort_index().to_dict()}")

    # 3. 构造未来收益标签（forward 5 天收益）
    print("\n[3/6] 构造 forward return 标签...")
    panel = panel.sort_index()
    fwd_ret = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)
    fwd_ret.name = "fwd_ret_5d"
    print(f"  fwd_ret 形状: {fwd_ret.shape}")

    # 4. 手动提几条因子（用 DSL 算子）
    print("\n[4/6] 手动构造 3 条因子...")
    volume = panel["volume"]
    close = panel["close"]

    factors = {
        "f1_volume_ratio": OPERATORS["cs_rank"](
            OPERATORS["div"](volume, OPERATORS["rolling_mean"](volume, 20))
        ),
        "f2_reversal": OPERATORS["cs_rank"](
            OPERATORS["lag"](close.pct_change(), 5)
        ),
        "f3_trend": OPERATORS["cs_zscore"](
            OPERATORS["div"](close, OPERATORS["rolling_mean"](close, 10))
        ),
    }
    for fid, f in factors.items():
        print(f"  {fid}: mean={f.mean():.4f}, nan%={f.isna().mean()*100:.1f}%")

    # 5. 密封评估
    print("\n[5/6] 密封评估（先 validate，再 finalize）...")
    evaluator = SealedEvaluator(cfg, regime_labels, fwd_ret)
    tree = DiscoveryTree(ROOT / "data" / "discovery_tree.jsonl")

    budget = BudgetState(total=10)

    for fid, f in factors.items():
        action = decide_action(budget)
        print(f"\n  --- {fid} (预算剩余 {budget.remaining}, action={action}) ---")
        # validation（agent 可看）
        res_val = evaluator.validate(f, fid, f"manual:{fid}")
        print(f"  VALIDATION: per-regime IC = {res_val.regime_ic}, mean|IC|={res_val.mean_abs_ic:.4f}")

        # finalize（只跑一次）
        res_test = evaluator.finalize(f, fid, f"manual:{fid}")
        print(f"  TEST:       per-regime IC = {res_test.regime_ic}, mean|IC|={res_test.mean_abs_ic:.4f}")

        # 写入发现树
        current_regime = int(regime_labels.iloc[-1])
        node = ExperimentNode(
            experiment_id=f"exp_{fid}",
            timestamp=str(pd.Timestamp.now().date()),
            regime_at_time=current_regime,
            hypothesis=f"manual factor {fid}",
            expression=f"manual:{fid}",
            val_regime_ic=res_val.regime_ic,
            test_regime_ic=res_test.regime_ic,
            status="accepted" if res_test.mean_abs_ic > 0.01 else "rejected",
        )
        tree.add(node)
        budget.used += 1

    # 6. fuel 状态
    print("\n[6/6] 当前 regime 燃料状态...")
    fuel = tree.fuel_status(regime=int(regime_labels.iloc[-1]), min_nodes=3)
    print(f"  {fuel['message']}")

    print("\n" + "=" * 60)
    print("Phase 1 管线跑通。发现树已写入 data/discovery_tree.jsonl")
    print("=" * 60)


if __name__ == "__main__":
    main()
