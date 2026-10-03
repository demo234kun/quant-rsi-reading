"""
AlgoEvolve 外层 Prompt Genome（论文 §4 的 4 个基因）——自定目录与模板。

论文只给出 4 个基因的**语义**，未给出候选目录、基数、`build_prompt()` 模板，
也未给出 Performance Report 的 schema。本文件自建：
  - 每个基因一套离散候选指令目录（categorical choices）；
  - PromptGenome.build_prompt() 把 4 个离散选择拼成「连贯的 executive directive」；
  - prompt 空间均匀交叉（每个基因独立从父母之一采样）；
  - Performance Report（学习曲线轨迹 / 失败率 / 冠军解剖）与确定性降级改写。

**禁止**把这些目录当成论文原始目录——它们全部标注为 self-defined。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

GENES: Tuple[str, ...] = ("theta_mutation", "theta_focus", "theta_constraints", "theta_reasoning")

# ---- 自定候选目录（论文 §4 只给语义示例，未给目录/基数） ----
MUTATION_CATALOG: Dict[str, str] = {
    "minor_tweak": "提出一个 MINOR 数值变体：只微调一个系数或阈值，保持整体结构不变。",
    "bold_paradigm": "探索 BOLD 的新范式：把主导指标换成结构上不同的指标或组合。",
    "simplify": "简化：删除一个项以降低复杂度，保留最有效的成分。",
    "combine": "组合：用一个新的交互项（如乘法门控）把两个现有信号组合起来。",
}
FOCUS_CATALOG: Dict[str, str] = {
    "momentum_vol": "聚焦于把动量与波动率结合（例如动量除以波动）。",
    "mean_reversion": "聚焦于布林带 / RSI 极值处的均值回复。",
    "trend_gating": "用趋势确认门控所有入场（例如仅当 EMA 趋势为正时才做多）。",
    "diversity": "提出结构多样的原型；探索非线性指标组合与逆波动率信号。",
}
CONSTRAINTS_CATALOG: Dict[str, str] = {
    "no_lookahead": "不得使用未来函数，只能用当日及之前的指标。",
    "no_overfit": "不得过拟合：最多使用三个项，避免极窄阈值。",
    "no_tiny_dispersion": "横截面离散度极小时不要交易。",
    "no_zero_trade": "不得输出全零信号：必须保证有有效持仓。",
}
REASONING_CATALOG: Dict[str, str] = {
    "learning_curve": "分析学习曲线：若适应度停滞则提高探索强度。",
    "failure_analysis": "分析失败候选的共同错误并规避。",
    "champion_anatomy": "解剖冠军程序的结构，扩展其最强成分。",
    "ablation": "对每一项做心算消融，只保留有增益的项。",
}
GENE_CATALOGS: Dict[str, Dict[str, str]] = {
    "theta_mutation": MUTATION_CATALOG,
    "theta_focus": FOCUS_CATALOG,
    "theta_constraints": CONSTRAINTS_CATALOG,
    "theta_reasoning": REASONING_CATALOG,
}


@dataclass(frozen=True)
class PromptGenome:
    """4 基因 Prompt Genome（每个基因是离散类别选择）。"""

    theta_mutation: str
    theta_focus: str
    theta_constraints: str
    theta_reasoning: str

    def as_dict(self) -> Dict[str, str]:
        return {g: getattr(self, g) for g in GENES}

    def describe(self) -> str:
        return "; ".join(f"{g}={getattr(self, g)}" for g in GENES)

    def build_prompt(self) -> str:
        """把 4 个离散基因拼成一条连贯的 Evolver Prompt（executive directive）。"""
        return (
            "[Editable Evolver Prompt —— 由 4 基因 Prompt Genome 生成]\n"
            f"1. θ_mutation（变异指令）: {MUTATION_CATALOG[self.theta_mutation]}\n"
            f"2. θ_focus（创意焦点）: {FOCUS_CATALOG[self.theta_focus]}\n"
            f"3. θ_constraints（负向搜索约束）: {CONSTRAINTS_CATALOG[self.theta_constraints]}\n"
            f"4. θ_reasoning（分析框架）: {REASONING_CATALOG[self.theta_reasoning]}\n"
            "请严格据此指导候选交易程序的生成与变异。"
        )

    def replace_gene(self, gene: str, choice: str) -> "PromptGenome":
        if gene not in GENE_CATALOGS or choice not in GENE_CATALOGS[gene]:
            raise ValueError(f"非法基因或候选: {gene}={choice}")
        return replace(self, **{gene: choice})


def initial_population(rng: np.random.RandomState, size: int) -> List[PromptGenome]:
    """初始种群 P_0：1 个默认基因组 + (size-1) 个随机基因组（论文未指定构造，自定）。"""
    default = PromptGenome(*(next(iter(GENE_CATALOGS[g])) for g in GENES))
    pop: List[PromptGenome] = [default]
    guard = 0
    while len(pop) < size and guard < 100:
        guard += 1
        g = PromptGenome(*(rng.choice(list(GENE_CATALOGS[f].keys())) for f in GENES))
        if g not in pop:
            pop.append(g)
    return pop[:size]


def uniform_crossover(p1: PromptGenome, p2: PromptGenome, rng: np.random.RandomState) -> PromptGenome:
    """prompt 空间均匀交叉：子代每个基因独立从父母之一采样。"""
    vals = {g: (getattr(p1, g) if rng.rand() < 0.5 else getattr(p2, g)) for g in GENES}
    return PromptGenome(**vals)


def deterministic_gene_rewrite(genome: PromptGenome, rng: np.random.RandomState) -> PromptGenome:
    """LLM 不可用时的确定性降级：随机选一个基因改成另一个候选值。"""
    gene = GENES[int(rng.randint(len(GENES)))]
    cur = getattr(genome, gene)
    choices = [c for c in GENE_CATALOGS[gene] if c != cur]
    return genome.replace_gene(gene, choices[int(rng.randint(len(choices)))])


def parse_meta_json(text: str) -> Optional[Tuple[str, str]]:
    """从 Meta-LLM 输出中解析 {"gene":..., "choice":...}；非法则返回 None。"""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    gene, choice = obj.get("gene"), obj.get("choice")
    if gene in GENE_CATALOGS and choice in GENE_CATALOGS[gene]:
        return gene, choice
    return None


def build_report(logs: Dict, genome: PromptGenome) -> str:
    """生成 Performance Report（论文只描述三项内容，schema 为自定）。"""
    curve = logs.get("curve", []) or []
    curve_s = ", ".join(
        "nan" if (v is None or not np.isfinite(v)) else f"{v:+.4f}" for v in curve)
    n_cand = int(logs.get("n_cand", 0))
    n_inv = int(logs.get("n_invalid", 0))
    fail = (n_inv / n_cand) if n_cand else 0.0
    champ = str(logs.get("champion", ""))
    return "\n".join([
        "Performance Report（三项内容来自论文，字段 schema 自定）:",
        f"- 学习曲线轨迹（每代 D_train 上最优 S）: [{curve_s}]",
        f"- 失败率: {n_inv}/{n_cand} = {fail:.2%}",
        f"- 冠军解剖: code={champ}",
        f"- 冠军 D_train S: {logs.get('champion_train_S')}",
        f"- 冠军 held-out walk-forward D_test S: {logs.get('champion_test_S')}",
        f"- 当前基因组: {genome.describe()}",
    ])
