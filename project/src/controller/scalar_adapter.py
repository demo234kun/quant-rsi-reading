"""
标量 IC 奖励版策略演化（对照组）。

只看 mean IC（标量），不区分失败原因：
- IC 高 → 提升相关算子权重
- IC 低 → 降低相关算子权重
- 不区分 NOISE / REGIME_REVERSE / DIRECTION_REVERSED

这模拟 QuantEvolver 等现有 RSI 系统的奖励方式。
"""
from __future__ import annotations
import numpy as np
from typing import List

from src.controller.adapter import PolicyState, cold_start_policy


def scalar_adapt(
    prev: PolicyState,
    scored: list[dict],
    lr: float = 0.3,
) -> PolicyState:
    """
    标量奖励版策略演化。

    scored: [{"expr": str, "ic": float, "ops_used": [str,...]}]
    """
    new = PolicyState(
        op_weights=dict(prev.op_weights),
        depth=prev.depth,
        negative_set=set(prev.negative_set),
        regime_bias={k: list(v) for k, v in prev.regime_bias.items()},
        round=prev.round + 1,
    )

    if not scored:
        return new

    # 标量奖励：IC > 0 提升，IC < 0 降低
    for item in scored:
        ic = item["ic"]
        # 归一化到 [-1, 1]
        reward = np.tanh(ic * 10)
        for op in item.get("ops_used", []):
            if op in new.op_weights:
                new.op_weights[op] *= (1 + lr * reward)

    # 标量版不改变 depth，不区分失败原因
    return new
