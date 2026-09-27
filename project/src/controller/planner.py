"""
预算感知 controller（学 AutoScientist-Quant）。

根据剩余预算决定：
- 预算多 → 允许 pivot（试全新方向）
- 预算中等 → improve/combine
- 预算少 → 停手写报告
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class BudgetState:
    total: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return self.total - self.used

    @property
    def fraction(self) -> float:
        return self.remaining / max(self.total, 1)


def decide_action(budget: BudgetState) -> str:
    """根据剩余预算返回允许的动作。"""
    f = budget.fraction
    if f >= 0.7:
        return "pivot"   # 预算充足，允许全新方向
    elif f >= 0.3:
        return "improve_combine"  # 在当前方向深挖
    else:
        return "stop"    # 停手，写报告，不硬凑


def check_fuel(tree, current_regime: int, min_nodes: int = 20) -> dict:
    """检查当前 regime 经验是否充足。"""
    return tree.fuel_status(current_regime, min_nodes)
