"""EvolveTrade（论文 08）辅助层：自然语言策略 ↔ 可执行配置。

职责单一：定义固定工具集、策略 schema 的确定性编译器（纯文本解析，绝不 eval）、
初始策略 π0 与 Policy Agent 的固定更新指令 I_update。
被 `methods.strategy_evolution.evolve_trade.EvolveTrade` 使用。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# 固定工具集：论文的工具接口全程冻结；本复现以 6 个价格技术指标充当工具。
INDICATORS: List[str] = ["rsi14", "ema20_gap", "macd_hist", "atr_pct", "boll_pos", "mom10"]


@dataclass
class PolicyConfig:
    """由 policy 文本编译出的可执行配置（确定性解释器的输入）。"""

    weights: Dict[str, float]      # 每个指标的有符号权重
    priority: List[str]            # 工具调用优先级（含主证据校验门）
    min_abs_z: float               # 弱证据过滤阈值
    require_confirmations: int     # 至少多少指标同向确认
    max_position: float            # 单标的最大权重（集中度上限）
    vol_cap_pct: float             # 高波动的 atr_pct 阈值，超过则降权
    cash_buffer: float             # 现金缓冲比例，整体缩小暴露

    def normalized_weights(self) -> Dict[str, float]:
        s = sum(abs(v) for v in self.weights.values())
        if s <= 0.0:
            return {c: 0.0 for c in INDICATORS}
        return {c: self.weights.get(c, 0.0) / s for c in INDICATORS}


# 初始 policy π0（源自论文 Appendix G Figure 8 的初始提示要点）。
INITIAL_POLICY = (
    "# EvolveTrade 策略 π0\n"
    "# Role\n"
    "你是工具调用型交易智能体的系统提示策略。你只通过工具获取证据，"
    "并遵循下列流程规则把证据转成仓位；骨干模型与工具接口固定不变。\n"
    "# 分析流程\n"
    "先取价格，再用代码计算量化指标，最后综合成仓位；证据不足时降低暴露、留现金缓冲。\n"
    "# tool_priority\n"
    "priority: ema20_gap > macd_hist > mom10 > boll_pos > rsi14 > atr_pct\n"
    "# signal_weights\n"
    "ema20_gap: 0.40\n"
    "macd_hist: 0.30\n"
    "mom10: 0.20\n"
    "boll_pos: 0.05\n"
    "rsi14: -0.05\n"
    "atr_pct: 0.00\n"
    "# validation_rules\n"
    "min_abs_z: 0.30\n"
    "require_confirmations: 2\n"
    "# risk_rules\n"
    "max_position: 0.35\n"
    "vol_cap_pct: 0.06\n"
    "cash_buffer: 0.05\n"
)

# Policy Agent 的固定更新指令 I_update（system prompt）。
POLICY_SYSTEM = (
    "你是 EvolveTrade 的独立 Policy Agent，不执行任何交易决策。"
    "你的唯一职责：读取交易智能体的当前自然语言策略 π、它在刚结束批次上的决策轨迹，"
    "以及该批次的已实现收益反馈，诊断流程缺陷并完整重写策略文本。\n"
    "硬约束：工具集合固定为 6 个技术指标 "
    "[rsi14, ema20_gap, macd_hist, atr_pct, boll_pos, mom10]，不得增删工具、不得改变输出格式，"
    "只能修改流程规则（工具优先级、信号权重、校验规则、风控规则）；禁止输出代码。\n"
    "输出纯文本，不要 JSON，不要 markdown 代码围栏，格式如下：\n"
    "### reasoning\n<基于轨迹与收益的归因：哪条规则帮助/损害了表现，证据是什么>\n"
    "### policy\n<完整策略文档，严格包含以下小节与字段名>\n"
    "## tool_priority\npriority: <6 个工具名用 > 连接，必须覆盖全部 6 个>\n"
    "## signal_weights\n<每行: 指标名: 权重（-2..2），至少一个非零>\n"
    "## validation_rules\nmin_abs_z: <0..3>\nrequire_confirmations: <整数 1..6>\n"
    "## risk_rules\nmax_position: <0.02..1>\nvol_cap_pct: <0.005..0.5>\ncash_buffer: <0..0.5>\n"
)


def default_config() -> PolicyConfig:
    """π0 编译出的默认可执行配置。"""
    return PolicyConfig(
        weights={"rsi14": -0.05, "ema20_gap": 0.40, "macd_hist": 0.30,
                 "atr_pct": 0.0, "boll_pos": 0.05, "mom10": 0.20},
        priority=["ema20_gap", "macd_hist", "mom10", "boll_pos", "rsi14", "atr_pct"],
        min_abs_z=0.30, require_confirmations=2,
        max_position=0.35, vol_cap_pct=0.06, cash_buffer=0.05,
    )


def _sections(text: str) -> Dict[str, str]:
    """按 `## name` 级别标题切分文本；无法识别的标题归入当前小节。"""
    secs: Dict[str, List[str]] = {}
    cur: str | None = None
    for raw in text.splitlines():
        m = re.match(r"^#{1,3}\s*([A-Za-z_]+)\s*$", raw.strip())
        if m:
            cur = m.group(1).lower()
            secs.setdefault(cur, [])
        elif cur is not None:
            secs[cur].append(raw)
    return {k: "\n".join(v) for k, v in secs.items()}


def _num_in(text: str, key: str, default: float, lo: float, hi: float) -> float:
    """从文本里安全提取 `key: <number>`，缺失/非法/越界时回退 default。"""
    m = re.search(rf"{key}\s*[:=]\s*([-+]?\d*\.?\d+)", text, re.I)
    if not m:
        return default
    try:
        v = float(m.group(1))
    except ValueError:
        return default
    if not np.isfinite(v):
        return default
    return max(lo, min(hi, v))


def compile_policy(text: str, prev: PolicyConfig) -> Tuple[PolicyConfig, List[str]]:
    """把 LLM 生成的策略文本解析为 PolicyConfig；任何字段解析失败都沿用 prev。"""
    warns: List[str] = []
    secs = _sections(text)

    # 1) signal_weights：只认固定工具集里的指标；全部非法/全零则沿用上一版
    weights = dict(prev.weights)
    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*([-+]?\d*\.?\d+)",
                       secs.get("signal_weights", ""))
    parsed = {n.lower(): float(v) for n, v in pairs if n.lower() in INDICATORS}
    if parsed and any(abs(v) > 0.0 for v in parsed.values()):
        for c in INDICATORS:
            weights[c] = max(-2.0, min(2.0, parsed.get(c, 0.0)))
    else:
        warns.append("signal_weights 解析失败/全零，沿用上一版权重")

    # 2) tool_priority：解析 `>`/逗号分隔顺序，补齐缺失项
    pri_raw = secs.get("tool_priority", "")
    m = re.search(r"(?:priority|order)\s*[:=]\s*(.+)", pri_raw, re.I)
    tokens = re.split(r">|,|、|，|\s+", m.group(1) if m else pri_raw)
    priority: List[str] = []
    for t in tokens:
        t = t.strip().lower()
        if t in INDICATORS and t not in priority:
            priority.append(t)
    for c in list(prev.priority) + INDICATORS:
        if c not in priority:
            priority.append(c)

    # 3) validation_rules / risk_rules：数值字段带范围裁剪
    vr, rr = secs.get("validation_rules", ""), secs.get("risk_rules", "")
    cfg = PolicyConfig(
        weights=weights,
        priority=priority,
        min_abs_z=_num_in(vr, "min_abs_z", prev.min_abs_z, 0.0, 3.0),
        require_confirmations=int(_num_in(
            vr, "require_confirmations", float(prev.require_confirmations), 1, len(INDICATORS))),
        max_position=_num_in(rr, "max_position", prev.max_position, 0.02, 1.0),
        vol_cap_pct=_num_in(rr, "vol_cap_pct", prev.vol_cap_pct, 0.005, 0.5),
        cash_buffer=_num_in(rr, "cash_buffer", prev.cash_buffer, 0.0, 0.5),
    )
    return cfg, warns
