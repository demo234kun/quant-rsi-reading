"""
因果性单测：每个算子必须不依赖未来数据。

方法：把序列后半段改成不同值，看前半段输出是否变化。
如果前半段输出变了 → 算子偷看了未来。
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from src.dsl.operators import OPERATORS


def make_series(seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=100)
    return pd.Series(rng.normal(0, 1, 100), index=idx)


def test_operator_causal(op_name: str, k: int = 5):
    """检查 op_name 算子的前半段输出不被后半段修改影响。"""
    s1 = make_series(0)
    s2 = s1.copy()
    # 修改后半段
    s2.iloc[50:] += 100

    fn = OPERATORS[op_name]
    if op_name in ("rolling_mean", "rolling_std", "rolling_max", "rolling_min",
                   "rolling_rank", "lag", "delta"):
        out1 = fn(s1, k)
        out2 = fn(s2, k)
    elif op_name in ("cs_rank", "cs_zscore", "cs_demean"):
        # 横截面算子，需要 MultiIndex，跳过因果测试（它们在截面内操作）
        return True
    else:
        return True  # 算术算子无需测试

    # 前 40 个值（在修改点之前）应该完全相同
    diff = (out1.iloc[:40] - out2.iloc[:40]).abs().max()
    if diff > 1e-10:
        print(f"  FAIL {op_name}: 前半段被后半段影响! diff={diff}")
        return False
    return True


def test_all():
    print("测试算子因果性...")
    all_ok = True
    for op in OPERATORS:
        ok = test_operator_causal(op)
        if ok:
            print(f"  OK   {op}")
        all_ok = all_ok and ok
    print("\n全部通过!" if all_ok else "\n有失败!")
    return all_ok


if __name__ == "__main__":
    test_all()
