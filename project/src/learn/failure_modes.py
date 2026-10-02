"""
L_t: 失败模式提取器。

从 ExperimentNode 的 per-regime IC 和回测结果中，提取结构化失败模式标签。
这是 RSI 递归闭环的"学习"环节——不是把分数喂回 LLM，而是归纳可复用的规则。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


# 失败模式标签
REGIME_REVERSE = "REGIME_REVERSE"     # 同因子在不同 regime 下方向相反
REGIME_SPECIFIC = "REGIME_SPECIFIC"   # 只在单一 regime 下有效
NOISE = "NOISE"                       # 所有 regime 下 |IC| 都很小
COST_EATEN = "COST_EATEN"             # 换手率吃掉收益
DEGENERATE = "DEGENERATE"             # 横截面方差为 0
LOOKAHEAD = "LOOKAHEAD"               # 因果性破坏（密封层拦截）
DIRECTION_REVERSED = "DIRECTION_REVERSED"  # 全 regime 同向但符号错（翻转即可）
ACCEPTED = "ACCEPTED"                 # 稳健有效


@dataclass
class FailureReport:
    """一个节点的失败模式报告。"""
    experiment_id: str
    expression: str
    labels: List[str] = field(default_factory=list)
    details: Dict[str, float] = field(default_factory=dict)

    @property
    def is_accepted(self) -> bool:
        return ACCEPTED in self.labels

    def __str__(self) -> str:
        return f"[{self.experiment_id}] {self.labels}  details={self.details}"


def extract_failure_modes(
    val_regime_ic: Dict[int, float],
    test_regime_ic: Dict[int, float],
    sharpe: float = 0.0,
    turnover: float = 0.0,
    cross_sectional_std: float = 1.0,
    ic_threshold: float = 0.02,
    regime_consistency: int = 2,
) -> FailureReport:
    """
    从 per-regime IC 和回测结果中提取失败模式。

    参数:
        val_regime_ic: validation 窗口上每个 regime 的 IC
        test_regime_ic: test 窗口上每个 regime 的 IC
        sharpe: 净 Sharpe
        turnover: 日均换手率
        cross_sectional_std: 因子横截面标准差（退化检测）
        ic_threshold: |IC| 小于此值视为噪声
        regime_consistency: 需要几个 regime 同号才算稳健

    返回:
        FailureReport，含标签列表
    """
    rep = FailureReport(
        experiment_id="",
        expression="",
    )

    # 合并 val + test 的 IC 向量（用 test 为主，val 为辅）
    all_regimes = set(test_regime_ic.keys()) | set(val_regime_ic.keys())
    if not all_regimes:
        rep.labels.append(NOISE)
        return rep

    # 1. 退化检测
    if cross_sectional_std < 1e-6:
        rep.labels.append(DEGENERATE)
        rep.details["cs_std"] = cross_sectional_std
        return rep

    # 2. 用 test_regime_ic 判断（样本外）
    ic_values = [test_regime_ic.get(r, 0.0) for r in sorted(all_regimes)]
    n_regimes = len(ic_values)

    # 3. NOISE：所有 regime |IC| < threshold
    max_abs_ic = max(abs(v) for v in ic_values)
    rep.details["max_abs_ic"] = max_abs_ic
    rep.details["mean_abs_ic"] = np.mean([abs(v) for v in ic_values])

    if max_abs_ic < ic_threshold:
        rep.labels.append(NOISE)

    # 4. REGIME_REVERSE：同因子在不同 regime 下方向相反
    signs = [1 if v > ic_threshold else (-1 if v < -ic_threshold else 0)
             for v in ic_values]
    nonzero_signs = [s for s in signs if s != 0]
    if len(set(nonzero_signs)) > 1:  # 既有正又有负
        rep.labels.append(REGIME_REVERSE)
        # 找出最反向的 regime
        worst_regime = min(test_regime_ic.items(), key=lambda x: x[1])
        rep.details["worst_regime"] = worst_regime[0]
        rep.details["worst_ic"] = worst_regime[1]

    # 5. REGIME_SPECIFIC：只在 1 个 regime 下显著
    n_significant = sum(1 for v in ic_values if abs(v) > ic_threshold)
    if n_significant == 1 and NOISE not in rep.labels:
        rep.labels.append(REGIME_SPECIFIC)
        best_regime = max(test_regime_ic.items(), key=lambda x: abs(x[1]))
        rep.details["best_regime"] = best_regime[0]
        rep.details["best_ic"] = best_regime[1]

    # 5b. DIRECTION_REVERSED：因子方向反了（全 regime 同向但 Sharpe 为负）
    #     不要求所有 regime 都显著，只要显著 regime 同号且 Sharpe < 0
    significant_vals = [v for v in ic_values if abs(v) > ic_threshold / 2]
    if (max_abs_ic > ic_threshold
            and len(significant_vals) >= 2
            and all(v < 0 for v in significant_vals)
            and sharpe < 0):
        rep.labels.append(DIRECTION_REVERSED)
        rep.details["flip_suggested"] = True
        rep.details["note"] = "翻转符号后可能变正 IC"

    # 6. COST_EATEN：毛 Sharpe 高但净 Sharpe 低（这里用 turnover 近似）
    #    turnover > 1.0 表示每天全换仓，成本敏感
    rep.details["turnover"] = turnover
    if turnover > 1.0 and abs(sharpe) < 0.3:
        rep.labels.append(COST_EATEN)

    # 7. ACCEPTED：通过所有检查（≥2 个 regime 同号显著 + Sharpe > 0.3）
    n_consistent = sum(1 for v in ic_values if v > ic_threshold)
    if (n_consistent >= regime_consistency
            and sharpe > 0.3
            and NOISE not in rep.labels
            and REGIME_REVERSE not in rep.labels):
        rep.labels.append(ACCEPTED)

    # 如果一个标签都没有，至少标 NOISE
    if not rep.labels:
        rep.labels.append(NOISE)

    return rep


def summarize_round(reports: List[FailureReport]) -> Dict[str, int]:
    """汇总一轮的失败模式分布。"""
    from collections import Counter
    c: Counter = Counter()
    for r in reports:
        for label in r.labels:
            c[label] += 1
    return dict(c)
