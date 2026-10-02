"""
P_t: 因子提案器 v2 —— 遗传算法版。

v1 问题：纯随机采样，不利用历史成功经验。
v2 改进：
  - 精英保留：上一轮 ACCEPTED 的表达式作为种子
  - 50% 新探索 + 50% 精英 mutation（改窗口/换算子/翻转符号）
  - 实现 Diversity-Complementarity Reward（避免重复）
"""
from __future__ import annotations
import re
import numpy as np
from typing import List, Tuple

from src.dsl.operators import OPERATORS
from src.controller.adapter import PolicyState


FIELDS = ["close", "volume", "open", "high", "low", "ret"]
WINDOW_OPS = {"rolling_mean", "rolling_std", "rolling_max", "rolling_min", "rolling_rank"}
BINARY_OPS = {"add", "sub", "mul", "div"}
UNARY_TS = {"lag", "delta"}
CS_OPS = {"cs_rank", "cs_zscore"}


def _sample_field(rng: np.random.Generator) -> str:
    return rng.choice(FIELDS)


def _build_random(policy: PolicyState, rng: np.random.Generator, depth: int) -> str:
    """随机构建一个表达式。"""
    if depth <= 0:
        return _sample_field(rng)

    op = policy.sample_operator(rng)

    if op in WINDOW_OPS:
        window = int(rng.integers(3, min(30, 5 + depth * 10)))
        child = _build_random(policy, rng, depth - 1)
        return f"{op}({child}, {window})"

    elif op in BINARY_OPS:
        left = _build_random(policy, rng, depth - 1)
        right = _build_random(policy, rng, depth - 1)
        return f"{op}({left}, {right})"

    elif op in UNARY_TS:
        k = int(rng.integers(1, 10))
        child = _build_random(policy, rng, depth - 1)
        return f"{op}({child}, {k})"

    elif op in CS_OPS:
        child = _build_random(policy, rng, depth - 1)
        return f"{op}({child})"

    return _sample_field(rng)


def _mutate(expr: str, policy: PolicyState, rng: np.random.Generator) -> str:
    """
    对一个成功表达式做 mutation：
    - 改窗口数（±50%）
    - 换一个同类型算子
    - 或翻转符号（乘 -1）
    """
    # 找所有窗口参数
    windows = re.findall(r"(\w+\([^,]+),\s*(\d+)\)", expr)
    if windows and rng.random() < 0.4:
        # 改窗口
        old_op, old_w = windows[rng.integers(0, len(windows))]
        new_w = max(2, int(int(old_w) * rng.uniform(0.5, 1.5)))
        expr = re.sub(rf"({re.escape(old_op)}),\s*{old_w}\)", rf"\1, {new_w})", expr, count=1)

    # 换一个 CS 算子
    cs_matches = re.findall(r"(cs_rank|cs_zscore)\(", expr)
    if cs_matches and rng.random() < 0.3:
        old_cs = cs_matches[rng.integers(0, len(cs_matches))]
        new_cs = "cs_zscore" if old_cs == "cs_rank" else "cs_rank"
        expr = expr.replace(old_cs, new_cs, 1)

    # 翻转符号（外层包一个 mul(-1)）
    if rng.random() < 0.2:
        expr = f"mul(-1, {expr})"

    return expr


def propose_factors(
    policy: PolicyState,
    n: int = 10,
    seed: int = 42,
    hall_of_fame: List[str] = None,
    reverse_set: List[str] = None,
) -> List[str]:
    """
    v2 提案器：精英保留 + 探索利用平衡。

    参数:
        policy: 当前策略 π_t
        n: 要生成的因子数
        seed: 随机种子
        hall_of_fame: 上一轮 ACCEPTED 的表达式（精英）
        reverse_set: 被标为 DIRECTION_REVERSED 的表达式（翻转后重提）

    返回:
        表达式字符串列表
    """
    rng = np.random.default_rng(seed + policy.round * 7)
    hall_of_fame = hall_of_fame or []
    reverse_set = reverse_set or []
    expressions = []
    seen = set()

    # 预算分配：
    # 30% 精英 mutation（从名人堂变体）
    # 20% DIRECTION_REVERSED 翻转后重提
    # 50% 全新探索
    n_mutate = max(1, int(n * 0.3))
    n_reverse = max(1, int(n * 0.2))
    n_explore = n - n_mutate - n_reverse

    # 1. 精英 mutation
    if hall_of_fame:
        for _ in range(n_mutate):
            parent = rng.choice(hall_of_fame)
            child = _mutate(parent, policy, rng)
            if child not in seen and child not in policy.negative_set:
                seen.add(child)
                expressions.append(child)

    # 2. 翻转后重提（DIRECTION_REVERSED）
    if reverse_set:
        for _ in range(n_reverse):
            parent = rng.choice(reverse_set)
            # 翻转符号：mul(-1, expr)
            child = f"mul(-1, {parent})"
            if child not in seen and child not in policy.negative_set:
                seen.add(child)
                expressions.append(child)

    # 3. 全新探索
    attempts = 0
    while len(expressions) < n and attempts < n * 5:
        attempts += 1
        expr = _build_random(policy, rng, policy.depth)
        if "(" not in expr:
            continue
        if expr in policy.negative_set or expr in seen:
            continue
        seen.add(expr)
        expressions.append(expr)

    return expressions[:n]
