"""
RegimeSeal Phase 1 完整测试套件。
跑法: python tests/test_all.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from src.data.synthetic import generate_synthetic_panel
from src.regime.cluster import regime_summary, build_regime_features
from src.dsl.operators import OPERATORS, list_operators
from src.evaluator.sealed import SplitConfig, SealedEvaluator, per_regime_ic
from src.memory.tree import DiscoveryTree, ExperimentNode
from src.controller.planner import BudgetState, decide_action, check_fuel


PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


# ========== 1. DSL 算子因果性 ==========
print("\n[1/7] DSL 算子因果性")
def make_series(seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=100)
    return pd.Series(rng.normal(0, 1, 100), index=idx)

for op in ["lag","delta","rolling_mean","rolling_std","rolling_max",
           "rolling_min","rolling_rank"]:
    s1 = make_series(0)
    s2 = s1.copy(); s2.iloc[50:] += 100
    fn = OPERATORS[op]
    out1 = fn(s1, 5); out2 = fn(s2, 5)
    diff = (out1.iloc[:40] - out2.iloc[:40]).abs().max()
    check(f"causal:{op}", diff < 1e-10, f"diff={diff}")

check("operator_list_len", len(list_operators()) == 15, f"got {len(list_operators())}")


# ========== 2. 数据生成 ==========
print("\n[2/7] 合成数据")
panel = generate_synthetic_panel(n_symbols=30, n_days=500)
check("panel_shape", len(panel) == 30*500, f"got {len(panel)}")
check("panel_columns", set(["open","high","low","close","volume","ret"]).issubset(panel.columns))
check("no_nan_close", not panel["close"].isna().any())
check("ret_variance", panel["ret"].var() > 0)


# ========== 3. Regime 聚类 ==========
print("\n[3/7] Regime 聚类")
all_dates = panel.index.get_level_values(0).unique()
cfg = SplitConfig(train_end="2022-06-30", embargo_end="2022-12-31", test_start="2023-01-01")
train_dates = all_dates[all_dates <= cfg.train_end]
train_mask = pd.Series(True, index=train_dates)
regime_labels, scaler, km = regime_summary(panel, train_mask, n_regimes=4)
check("regime_labels_len", len(regime_labels) > 100, f"got {len(regime_labels)}")
check("regime_4_classes", set(regime_labels.unique()) <= {0,1,2,3}, f"got {set(regime_labels.unique())}")
check("regime_balanced", regime_labels.value_counts().min() > 20, f"min={regime_labels.value_counts().min()}")


# ========== 4. 密封评估器 ==========
print("\n[4/7] 密封评估器")
panel_sorted = panel.sort_index()
fwd_ret = panel_sorted.groupby(level="symbol")["close"].pct_change(5).shift(-5)

# 动态切分：按日期位置 60% / 80%
all_d = panel.index.get_level_values(0).unique().sort_values()
n = len(all_d)
train_end = all_d[int(n*0.6)]
embargo_end = all_d[int(n*0.7)]
test_start = all_d[int(n*0.8)]
cfg = SplitConfig(train_end=str(train_end.date()), embargo_end=str(embargo_end.date()), test_start=str(test_start.date()))
# 重新生成 regime labels 用正确的 train_mask
train_dates2 = all_d[all_d <= train_end]
train_mask2 = pd.Series(True, index=train_dates2)
regime_labels, scaler, km = regime_summary(panel, train_mask2, n_regimes=4)

vol = panel_sorted["volume"]
factor = OPERATORS["cs_rank"](OPERATORS["div"](vol, OPERATORS["rolling_mean"](vol, 10)))

ev = SealedEvaluator(cfg, regime_labels, fwd_ret)
res_val = ev.validate(factor, "test_f1", "cs_rank(volume/rolling_mean(volume,10))")
check("validate_regime_ic", len(res_val.regime_ic) >= 1, f"got {len(res_val.regime_ic)}")
check("validate_mean_abs", res_val.mean_abs_ic >= 0)
check("validate_split", res_val.split == "validation")

res_test = ev.finalize(factor, "test_f1", "cs_rank(volume/rolling_mean(volume,10))")
check("test_split", res_test.split == "test")
check("test_regime_ic", len(res_test.regime_ic) >= 1, f"got {len(res_test.regime_ic)}")

# 重复 finalize 必须报错
try:
    ev.finalize(factor, "test_f1", "dup")
    check("double_finalize_blocked", False, "应该 raise")
except RuntimeError:
    check("double_finalize_blocked", True)


# ========== 5. 发现树 ==========
print("\n[5/7] 发现树")
import tempfile
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
    tree_path = Path(f.name)
tree = DiscoveryTree(tree_path)

for i in range(25):
    node = ExperimentNode(
        experiment_id=f"exp_{i}",
        timestamp="2026-09-28",
        regime_at_time=i % 4,
        hypothesis=f"test {i}",
        expression=f"op_{i}",
        val_regime_ic={i%4: 0.01*i},
        status="accepted" if i % 2 == 0 else "rejected",
    )
    tree.add(node)

check("tree_len", len(tree.nodes) == 25)
regime0 = tree.get_nodes_by_regime(0)
check("regime0_nodes", len(regime0) == 7, f"got {len(regime0)}")
fuel = tree.fuel_status(0, min_nodes=5)
check("fuel_ok", fuel["fuel_ok"] == True)
fuel_low = tree.fuel_status(5, min_nodes=5)
check("fuel_low", fuel_low["fuel_ok"] == False, f"regime 5 should have 0 nodes")


# ========== 6. Controller ==========
print("\n[6/7] 预算 controller")
b = BudgetState(total=10)
check("action_pivot", decide_action(b) == "pivot")
b.used = 5
check("action_mid", decide_action(b) == "improve_combine")
b.used = 8
check("action_stop", decide_action(b) == "stop")


# ========== 7. 端到端冒烟 ==========
print("\n[7/7] 端到端冒烟")
panel2 = generate_synthetic_panel(n_symbols=20, n_days=300)
all_d2 = panel2.index.get_level_values(0).unique().sort_values()
n2 = len(all_d2)
cfg2 = SplitConfig(
    train_end=str(all_d2[int(n2*0.6)].date()),
    embargo_end=str(all_d2[int(n2*0.7)].date()),
    test_start=str(all_d2[int(n2*0.8)].date()),
)
tr2 = all_d2[all_d2 <= pd.Timestamp(cfg2.train_end)]
mask2 = pd.Series(True, index=tr2)
rl2, _, _ = regime_summary(panel2, mask2, n_regimes=3)
fr2 = panel2.sort_index().groupby(level="symbol")["close"].pct_change(3).shift(-3)
ev2 = SealedEvaluator(cfg2, rl2, fr2)

for i in range(5):
    f = OPERATORS["cs_rank"](OPERATORS["rolling_mean"](panel2["close"], 5+i))
    r1 = ev2.validate(f, f"smoke_{i}", f"roll_{i}")
    r2 = ev2.finalize(f, f"smoke_{i}", f"roll_{i}")
check("e2e_5factors", True, "5 factors evaluated without error")


# ========== 结果 ==========
print("\n" + "="*50)
print(f"PASS: {PASS}   FAIL: {FAIL}")
print("="*50)
sys.exit(0 if FAIL == 0 else 1)
