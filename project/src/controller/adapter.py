"""
A_t: 策略演化器。

根据上一轮的失败模式分布，更新下一轮的提案策略 π_{t+1}。
这是 RSI 递归闭环的"适应"环节。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set
import numpy as np

from src.learn.failure_modes import (
    FailureReport, REGIME_REVERSE, REGIME_SPECIFIC,
    NOISE, COST_EATEN, DEGENERATE, ACCEPTED, DIRECTION_REVERSED
)


@dataclass
class PolicyState:
    """
    提案策略 π_t。

    - op_weights: 每个算子被选中的先验概率
    - depth: 表达式深度偏好
    - negative_set: 黑名单表达式模式（避开）
    - regime_bias: 每个 regime 下优先尝试的算子类别
    - round: 当前轮次
    """
    op_weights: Dict[str, float] = field(default_factory=dict)
    depth: int = 3
    negative_set: Set[str] = field(default_factory=set)
    regime_bias: Dict[int, List[str]] = field(default_factory=dict)
    round: int = 0

    def sample_operator(self, rng: np.random.Generator) -> str:
        """按 op_weights 采样一个算子。"""
        if not self.op_weights:
            return "cs_rank"
        ops = list(self.op_weights.keys())
        weights = np.array([self.op_weights[o] for o in ops])
        weights = weights / weights.sum()
        return rng.choice(ops, p=weights)

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "depth": self.depth,
            "op_weights": self.op_weights,
            "negative_set": list(self.negative_set),
            "regime_bias": {str(k): v for k, v in self.regime_bias.items()},
        }


def cold_start_policy(operators: List[str]) -> PolicyState:
    """Round 0: 均匀权重 + 先验知识。"""
    w = {op: 1.0 for op in operators}
    # 先验：常用算子权重稍高
    for op in ["cs_rank", "rolling_mean", "lag", "delta"]:
        if op in w:
            w[op] = 1.5
    return PolicyState(
        op_weights=w,
        depth=3,
        negative_set=set(),
        regime_bias={0: [], 1: [], 2: [], 3: []},
        round=0,
    )


def adapt_policy(
    prev: PolicyState,
    reports: List[FailureReport],
    shrink_factor: float = 0.5,
) -> PolicyState:
    """
    根据上一轮的失败模式报告，更新策略。

    规则（对应 PAPER_PROPOSAL §3.3）：
    1. REGIME_REVERSE: 降低相关算子权重
    2. NOISE 占比高: 降低 depth（简单表达式更稳健）
    3. ACCEPTED 占比高: 提升相关算子权重
    4. COST_EATEN: 降低高频调仓算子权重
    """
    new = PolicyState(
        op_weights=dict(prev.op_weights),
        depth=prev.depth,
        negative_set=set(prev.negative_set),
        regime_bias={k: list(v) for k, v in prev.regime_bias.items()},
        round=prev.round + 1,
    )

    n = len(reports)
    if n == 0:
        return new

    counts = {}
    for r in reports:
        for label in r.labels:
            counts[label] = counts.get(label, 0) + 1

    # 规则 1: REGIME_REVERSE 多 → 降低横截面/算术类算子权重
    n_reverse = counts.get(REGIME_REVERSE, 0)
    if n_reverse > 0:
        penalty = 1.0 - shrink_factor * (n_reverse / n)
        for op in ["cs_rank", "div"]:
            if op in new.op_weights:
                new.op_weights[op] *= penalty
        for r in reports:
            if REGIME_REVERSE in r.labels:
                new.negative_set.add(r.expression)

    # 规则 2: NOISE 占比 > 50% → 降低 depth
    n_noise = counts.get(NOISE, 0)
    if n_noise / n > 0.5 and new.depth > 2:
        new.depth -= 1

    # 规则 3: ACCEPTED 多 → 提升反转/趋势类算子权重
    n_accepted = counts.get(ACCEPTED, 0)
    if n_accepted > 0:
        boost = 1.0 + shrink_factor * (n_accepted / n)
        for op in ["lag", "delta", "rolling_mean"]:
            if op in new.op_weights:
                new.op_weights[op] *= boost

    # 规则 4: COST_EATEN 多 → 降低短窗口 rolling 类
    n_cost = counts.get(COST_EATEN, 0)
    if n_cost > 0:
        penalty = 1.0 - shrink_factor * (n_cost / n)
        for op in ["rolling_mean", "rolling_std", "rolling_max"]:
            if op in new.op_weights:
                new.op_weights[op] *= penalty

    # 规则 5: DIRECTION_REVERSED → 不惩罚算子，建议翻转符号
    # （f1 在所有 regime 都是负 IC，翻转符号可能就变正）
    n_dir_rev = counts.get(DIRECTION_REVERSED, 0)
    if n_dir_rev > 0:
        # 记录这些表达式为"可翻转"，不加入 negative_set
        for r in reports:
            if DIRECTION_REVERSED in r.labels:
                new.negative_set.discard(r.expression)  # 不要拉黑

    return new


def compute_quality(reports: List[FailureReport]) -> float:
    """
    计算一轮的提案质量 Q_t。

    Q_t = mean(per-regime |IC|) over all reports in this round.
    递归有效 ⟺ Q_{t+1} > Q_t。
    """
    if not reports:
        return 0.0
    ics = []
    for r in reports:
        if "mean_abs_ic" in r.details:
            ics.append(r.details["mean_abs_ic"])
        elif "max_abs_ic" in r.details:
            ics.append(r.details["max_abs_ic"])
    return float(np.mean(ics)) if ics else 0.0
