"""
AlgoEvolve（10）复现 —— LLM 驱动的算法交易程序元进化（arXiv:2606.26173）。

════════════ 论文核心机制 ════════════
1. **双层进化**：内层让 LLM 当「语义变异算子」，进化**可执行 Python 交易程序**；
   外层进化 **Evolver Prompt 本身**——把 prompt 表示成 4 个可变异基因的 Prompt Genome。
2. **内层适应度** `S = α·R + (1−α)·C`，α=0.7；`R`=累计 PnL（Total Return），
   `C`=跑赢「跨资产中位市场表现」的资产占比（跨 15 只股票的中位数，非跨 fold/时间）。
3. **walk-forward**：生命周期切 K 个时序 epoch，第 k 轮在 `D_train^(k)` 上进化，
   部署到未见过的 `D_test^(k)`；总目标 `Σ_k S(f*_k, D_test^(k))`。
4. **外层**（Algorithm 1）：Prompt Genome 4 基因（θ_mutation / θ_focus / θ_constraints /
   θ_reasoning）+ 精英保留 + **prompt 空间均匀交叉** + Performance Report 驱动的
   **informed meta-mutation（每次只重写一个基因）**；K=6 代。
5. **非法候选**（运行时报错 / 违反程序契约 / 零有效交易）适应度 −∞。

════════════ 本复现怎么做 ════════════
- 数据：真实 CSI300 日线 15 只；`fit()` **只用 train+validation（336 天）**，绝不见 test。
- walk-forward：把 train+val 均分为 K+1=7 段，第 1 段作初始训练，后 6 段依次作各 epoch 的
  `D_test^(k)`；`D_train^(k)` 为到该段为止的扩展窗（论文未给 epoch 边界，此为自定替代）。
- 程序空间：论文允许任意 Python，本复现替换为**受限 DSL**（见 `algo_evolve_dsl.py`），
  用自实现 AST 白名单求值器计算，**绝不运行/eval LLM 生成的任意代码**。LLM 仍按
  `<reasoning> + <code>` 两段式生成候选，上下文 = 上代 **Top-2 Best + Top-2 Worst**（含适应度）。
- Prompt Genome：4 基因结构 + `build_prompt()` 忠实；每个基因的候选目录、`build_prompt()`
  模板、初始种群 P_0、内层代数/种群、`SelectTop` 规则、epoch 边界均为论文未给定项，自定并标注。
- 外层适应度：**严格取内层冠军在该 epoch 的 held-out walk-forward 窗上的 S**（不是内层均值）。
- Meta-LLM：用 `deepseek-chat` 接收 Performance Report 并只重写一个基因；不可用时确定性降级。
- 成本：内层程序 PnL 按论文 **10bps（0.1%）** 计；最终信号仍交统一评估器按 2bp 评估。

════════════ 哪些没复现及原因 ════════════
- **5 分钟 K 线 / 150 步/日 / 10 根 K 线平仓 / NUMIN SDK / 每日 5 个 obfuscated 符号**：
  不可复现（无盘中/obfuscated 数据），改日频 + 自建回测器，隔夜持仓用次日收益近似。
- **LLM 对任意 Python 的「语义 CoT mutation」**：不可安全复现，改为受限 DSL 的程序变异——
  **保留「进化可执行程序」论点，丢失「语义变异」论点**（两者在 notes 中分开陈述）。
- **Gemini Pro / Flash**：用可用后端 `deepseek-chat` 替代（论文用 Gemini 分层）。
- **Regime 检测 / regime-adaptive 切换**：论文从未定义检测器（spec §10），本复现不实现。
- **多重检验校正 / 复杂度惩罚公式 / R-C 归一化细则**：论文未指定，本复现不实现或自定并标注。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.llm import LLMUnavailable, TextLLM

from .algo_evolve_dsl import (
    SEED_PROGRAMS, DSLViolation, ProgramScore, eval_program,
    fallback_mutate_program, score_program, validate_code,
)
from .algo_evolve_genome import (
    PromptGenome, build_report, deterministic_gene_rewrite,
    initial_population, parse_meta_json, uniform_crossover,
)

# ---- 超参：K=6 与 α=0.7 照抄论文；其余为论文未给定项，自定压到 LLM 预算内 ----
K_META = 6          # 论文 meta-generations
OUTER_POP = 3       # 论文未指定 |P|，自定
INNER_GENS = 3      # 论文未指定内层代数 N，自定
INNER_NEW = 1       # 每内层代 LLM 新候选数（控制预算 → 6*3*3*1=54 程序调用）
SEED_KEEP = 4       # 内层保留种群大小（=Top-2 Best + Top-2 Worst）
COST_BPS = 10.0     # 论文 0.1% 交易成本
COLS = ["open", "high", "low", "close", "volume", "ret"]

# 固定 System Prompt（论文：含数据/允许算子/严格 I/O 约束，永不进化）。
PROGRAM_SYSTEM = """你是「交易程序进化系统」中的语义变异算子。你不写 Python，只用受限 DSL 写交易程序。
[数据] 15 只 A 股日频横截面，可用指标（均为无未来函数的序列）：
  rsi14, ema20_gap, macd_hist, atr_pct, boll_pos, mom10
[DSL 语法] 只允许：数字常量、算术 + - * /、一元负号；
  函数 zs(x)(截面 z-score)、rk(x)(截面百分位)、sg(x)(符号)、ab(x)(绝对值)、
  cl(x,lo,hi)(截断)、wt(cond,a,b)(cond 真取 a 否则 b)、mx(a,b)、mn(a,b)；
  比较 > < >= <= == != 只能出现在 wt() 的第一个参数里。
[程序契约] 输出一个横截面 score 表达式；score 越高越看多；禁止未来函数；长度 <= 400 字符。
[输出格式] 先输出 <reasoning>...</reasoning>，紧接 <code>...</code>；
  <code> 内只放一个 DSLL 表达式，不要 markdown，不要 import。"""

PROGRAM_USER_TMPL = """[Evolver Prompt（被进化的搜索启发式）]
{evolver}

[上代候选（含历史适应度 S）]
{context}

请基于以上线索生成 1 个新候选程序。先给出 <reasoning> 分析，再给出 <code> 表达式。"""

META_SYSTEM = """你是「元进化」中的 Meta-LLM，扮演研究科学家。唯一任务：根据 Performance Report，
在 4 基因 Prompt Genome 中【恰好重写一个基因】，以修复报告指出的缺陷。
基因与候选目录（choice 只能从对应 key 中选）：
theta_mutation: minor_tweak | bold_paradigm | simplify | combine
theta_focus: momentum_vol | mean_reversion | trend_gating | diversity
theta_constraints: no_lookahead | no_overfit | no_tiny_dispersion | no_zero_trade
theta_reasoning: learning_curve | failure_analysis | champion_anatomy | ablation
只允许输出严格 JSON：{"gene": "<4 个基因之一>", "choice": "<该基因目录中的 key>"}。"""


class AlgoEvolve(BaselineMethod):
    """AlgoEvolve 双层元进化复现（内层程序进化 + 外层 Prompt Genome 进化）。"""

    def __init__(self, seed: int = 0, temperature: float = 0.9) -> None:
        self.name = "algo_evolve"
        self.category = "strategy_evolution"
        self.paper_id = "10"
        self.fidelity = "simplified"
        self.notes = (
            "外层机制忠实复现：4 基因 Prompt Genome、build_prompt、K=6 元代、精英保留、"
            "prompt 空间均匀交叉、Performance Report 驱动的单基因 informed meta-mutation、"
            "外层适应度=内层冠军在 held-out walk-forward 窗上的 S、非法候选 −∞。"
            "内层替换：论文用 LLM 对任意 Python 程序做语义 CoT 变异，本复现改用自建的受限 DSL "
            "程序空间——保留『进化可执行程序』，丢失『语义变异』。候选目录/build_prompt 模板/"
            "内层代数与种群/外层种群/walk-forward epoch 边界均为论文未给定项，由本复现自定。"
            "未复现：5 分钟 K 线与 NUMIN（改日频）、regime 检测（论文未定义）、多重检验校正。"
        )
        self.seed = seed
        self.temperature = temperature
        self.rng = np.random.RandomState(seed)
        self.llm = TextLLM(tag="algo_evolve", temperature=temperature, max_tokens=1200)
        self.frozen_genome: Optional[PromptGenome] = None
        self.frozen_program: Optional[str] = None
        self.outer_log: List[Dict] = []
        self.meta_log: List[Dict] = []
        self.inner_logs: List[Dict] = []
        self.llm_stats: Dict[str, int] = {}
        self._n_prog_calls = 0
        self._n_meta_calls = 0
        self._fallback_used = False

    # ------------------------------------------------------------------ 数据/切分
    @staticmethod
    def _walk_forward_blocks(dev_dates: pd.DatetimeIndex) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """把 train+val 均分为 K+1 段：第 1 段初始训练，后 K 段依次为 D_test^(k)。"""
        n = len(dev_dates)
        seg = max(1, n // (K_META + 1))
        blocks: List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]] = []
        for k in range(1, K_META + 1):
            blocks.append((dev_dates[: seg * k], dev_dates[seg * k: seg * (k + 1)]))
        return blocks

    @staticmethod
    def _safe(x: float) -> Optional[float]:
        return float(x) if np.isfinite(x) else None

    # ------------------------------------------------------------------ 内层循环
    def _run_inner_loop(
        self, evolver_prompt: str,
        ind_tr: pd.DataFrame, nxt_tr: pd.Series,
        ind_te: pd.DataFrame, nxt_te: pd.Series, purpose: str,
    ) -> Tuple[str, Dict, int, float]:
        """内层：在 D_train^(k) 上进化程序；返回 (冠军, logs, LLM次数, 冠军在 D_test^(k) 的 S)。"""
        # 全历史（含被淘汰/非法候选）作为上代上下文来源：保证每代的 Top-2 Best + Top-2 Worst
        # 随新候选变化，从而让语义变异有真实反馈，而不是重复同一上下文。
        history: List[Tuple[ProgramScore, str, str]] = [
            (score_program(code, ind_tr, nxt_tr, COST_BPS), code, "") for code in SEED_PROGRAMS
        ]
        pop = self._top_programs(history, SEED_KEEP)  # 精英工作种群（Top-4）
        logs: Dict = {"curve": [], "n_cand": 0, "n_invalid": 0,
                      "champion": "", "champion_train_S": None, "champion_test_S": None}
        n_calls = 0
        for gen in range(INNER_GENS):
            base = self._best_valid_code(pop)
            code, reasoning = self._propose_program(
                evolver_prompt, self._format_context(history), base, f"{purpose}_gen{gen + 1}")
            n_calls += 1
            logs["n_cand"] += 1
            sc = score_program(code, ind_tr, nxt_tr, COST_BPS)
            if not sc.valid:  # 非法候选也进历史，用作负例教材；其 S=−∞ 不会进入 Top-4
                logs["n_invalid"] += 1
            history.append((sc, code, reasoning))
            pop = self._top_programs(history, SEED_KEEP)
            logs["curve"].append(self._best_fitness(pop))

        champ_entry = self._best_entry(pop)
        if champ_entry is None:  # 全代均非法：退化为种子程序
            champ = SEED_PROGRAMS[0]
            F = -np.inf
        else:
            train_sc, champ, _ = champ_entry
            # 外层适应度 = 冠军在 held-out walk-forward 窗上的 S（不是内层均值）
            test_sc = score_program(champ, ind_te, nxt_te, COST_BPS)
            F = test_sc.fitness
            logs["champion_train_S"] = float(train_sc.fitness)
            logs["champion_test_S"] = self._safe(test_sc.fitness)
        logs["champion"] = champ
        return champ, logs, n_calls, float(F)

    @staticmethod
    def _top_programs(pop: List[Tuple[ProgramScore, str, str]], k: int):
        return sorted(pop, key=lambda t: t[0].fitness, reverse=True)[:k]

    @staticmethod
    def _best_entry(pop: List[Tuple[ProgramScore, str, str]]):
        valid = [t for t in pop if t[0].valid and np.isfinite(t[0].fitness)]
        return max(valid, key=lambda t: t[0].fitness) if valid else None

    @staticmethod
    def _best_valid_code(pop: List[Tuple[ProgramScore, str, str]]) -> str:
        valid = [t for t in pop if t[0].valid and np.isfinite(t[0].fitness)]
        return max(valid, key=lambda t: t[0].fitness)[1] if valid else SEED_PROGRAMS[0]

    @staticmethod
    def _best_fitness(pop: List[Tuple[ProgramScore, str, str]]) -> Optional[float]:
        vals = [t[0].fitness for t in pop if np.isfinite(t[0].fitness)]
        return float(max(vals)) if vals else None

    @staticmethod
    def _format_context(pop: List[Tuple[ProgramScore, str, str]]) -> str:
        order = sorted(pop, key=lambda t: t[0].fitness, reverse=True)

        def fmt(items: List[Tuple[ProgramScore, str, str]]) -> str:
            lines = []
            for i, (sc, code, _r) in enumerate(items, 1):
                f = "−inf" if not np.isfinite(sc.fitness) else f"{sc.fitness:+.4f}"
                err = f" ({sc.error})" if (not sc.valid and sc.error) else ""
                lines.append(f"  #{i} S={f}: {code}{err}")
            return "\n".join(lines) if lines else "  (无)"
        return ("上代 Top-2 Best:\n" + fmt(order[:2])
                + "\n上代 Top-2 Worst:\n" + fmt(order[-2:]))

    def _propose_program(self, evolver_prompt: str, context: str,
                         base_code: str, purpose: str) -> Tuple[str, str]:
        """用 LLM 生成一个候选（<reasoning>+<code>）；不可用/非法时确定性降级。"""
        if not self.llm.available:
            return fallback_mutate_program(base_code, self.rng), ""
        user = PROGRAM_USER_TMPL.format(evolver=evolver_prompt, context=context)
        try:
            text = self.llm.complete(PROGRAM_SYSTEM, user, temperature=self.temperature,
                                     max_tokens=1200, purpose=purpose)
        except LLMUnavailable:
            self._fallback_used = True
            return fallback_mutate_program(base_code, self.rng), ""
        parsed = self._parse_blocks(text)
        if parsed is None:
            self._fallback_used = True
            return fallback_mutate_program(base_code, self.rng), ""
        code, reasoning = parsed
        try:
            validate_code(code)
        except DSLViolation:
            self._fallback_used = True
            return fallback_mutate_program(base_code, self.rng), reasoning
        return code, reasoning

    @staticmethod
    def _parse_blocks(text: str) -> Optional[Tuple[str, str]]:
        m_c = re.search(r"<code>(.*?)</code>", text, re.S | re.I)
        if not m_c:
            return None
        code = " ".join(m_c.group(1).replace("`", " ").split()).strip()
        if not code:
            return None
        m_r = re.search(r"<reasoning>(.*?)</reasoning>", text, re.S | re.I)
        reasoning = m_r.group(1).strip() if m_r else ""
        return code, reasoning

    # ------------------------------------------------------------------ 外层循环
    @staticmethod
    def _select_top(population: List[PromptGenome], F: Dict[PromptGenome, float]):
        """SelectTop：论文未指定规则，自定按适应度排名取 Top-1 / Top-2。"""
        order = sorted(population, key=lambda G: F[G], reverse=True)
        return order[0], order[1]

    def _meta_mutate(self, child: PromptGenome, report: str, purpose: str) -> PromptGenome:
        """informed meta-mutation：Meta-LLM 依 Performance Report 恰好重写一个基因。"""
        if self.llm.available:
            user = ("[当前 Prompt Genome]\n" + child.describe()
                    + "\n\n[Performance Report]\n" + report
                    + "\n\n请只重写一个基因，输出严格 JSON。")
            try:
                text = self.llm.complete(META_SYSTEM, user, temperature=0.4,
                                         max_tokens=300, purpose=purpose)
                parsed = parse_meta_json(text)
                if parsed is not None:
                    return child.replace_gene(*parsed)
            except LLMUnavailable:
                self._fallback_used = True
        return deterministic_gene_rewrite(child, self.rng)

    # ------------------------------------------------------------------ 主接口
    def fit(self, ds: Dataset) -> "AlgoEvolve":
        # ---- 零泄漏：只用 train + validation，硬断言绝不越过 validation 边界 ----
        dev_dates = ds.train_dates.union(ds.val_dates)
        if len(dev_dates) == 0:
            raise ValueError("train+validation 区为空")
        assert dev_dates.max() == ds.val_dates.max()
        assert dev_dates.max() < ds.test_dates.min(), "fit() 不得接触 test 区"

        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dev_dates)][COLS]
        ind = indicator_table(panel)
        # 次日收益只在 train+val 内部推导：最后一天自然为 NaN，绝不读取 test 价格
        nxt = panel["close"].groupby(level=1).transform(lambda s: s.shift(-1) / s - 1.0)

        blocks = self._walk_forward_blocks(dev_dates)
        population = initial_population(self.rng, OUTER_POP)
        self.outer_log, self.meta_log, self.inner_logs = [], [], []
        n_prog = n_meta = 0
        global_genome: Optional[PromptGenome] = None
        global_champion: Optional[str] = None
        global_F = -np.inf
        last_genome: Optional[PromptGenome] = None
        last_champion: Optional[str] = None

        for k in range(K_META):
            train_dates, test_dates = blocks[k]
            ind_tr = ind[ind.index.get_level_values(0).isin(train_dates)]
            nxt_tr = nxt[nxt.index.get_level_values(0).isin(train_dates)]
            ind_te = ind[ind.index.get_level_values(0).isin(test_dates)]
            nxt_te = nxt[nxt.index.get_level_values(0).isin(test_dates)]

            F: Dict[PromptGenome, float] = {}
            L: Dict[PromptGenome, Dict] = {}
            CH: Dict[PromptGenome, str] = {}
            for gi, G in enumerate(population):
                champ, logs, ncalls, Fk = self._run_inner_loop(
                    G.build_prompt(), ind_tr, nxt_tr, ind_te, nxt_te,
                    purpose=f"algoevolve_program_k{k + 1}_g{gi + 1}")
                F[G], L[G], CH[G] = Fk, logs, champ
                n_prog += ncalls
                self.inner_logs.append({
                    "meta_gen": k + 1, "genome_idx": gi + 1, "champion": champ,
                    "champion_train_S": logs["champion_train_S"],
                    "champion_test_S": logs["champion_test_S"],
                    "n_cand": logs["n_cand"], "n_invalid": logs["n_invalid"],
                    "curve": logs["curve"],
                    "champion_is_seed": champ in SEED_PROGRAMS,
                })
            best_G = max(population, key=lambda G: F[G])
            best_F = F[best_G]
            self.outer_log.append({
                "meta_gen": k + 1,
                "genome_fitness": {f"g{i + 1}": self._safe(F[G]) for i, G in enumerate(population)},
                "best_genome": best_G.as_dict(),
                "best_fitness": self._safe(best_F),
                "D_train_last": str(train_dates.max().date()),
                "D_test_window": [str(test_dates.min().date()), str(test_dates.max().date())],
            })
            if np.isfinite(best_F) and best_F > global_F:
                global_F, global_genome, global_champion = best_F, best_G, CH[best_G]
            if np.isfinite(best_F) or last_genome is None:
                last_genome, last_champion = best_G, CH[best_G]

            # ---- Algorithm 1 第 11-18 行：精英保留 + 均匀交叉 + 报告驱动单基因改写 ----
            P_next: List[PromptGenome] = [best_G]  # Elitism
            while len(P_next) < OUTER_POP:
                p1, p2 = self._select_top(population, F)
                child = uniform_crossover(p1, p2, self.rng)
                report = build_report(L[p1], child)
                child = self._meta_mutate(child, report,
                                          purpose=f"algoevolve_metamut_k{k + 1}_c{len(P_next)}")
                n_meta += 1
                P_next.append(child)
            self.meta_log.append({"meta_gen": k + 1,
                                  "population": [g.as_dict() for g in P_next]})
            population = P_next

        # ---- 冻结 Best Found Prompt Genome G* 及其冠军程序（Algorithm 1 Output） ----
        # 全局按外层适应度 F 取最优；若全程无有限值则退回末代。
        if global_genome is not None:
            self.frozen_genome, self.frozen_program = global_genome, global_champion
        else:
            self.frozen_genome, self.frozen_program = last_genome, last_champion
        if self.frozen_program is None:
            self.frozen_program = SEED_PROGRAMS[0]

        self._n_prog_calls, self._n_meta_calls = n_prog, n_meta
        self.llm_stats = dict(self.llm.stats)
        if not self.llm.available:
            self.fidelity = "llm_replaced_by_rule"
            self.notes += "；LLM 后端不可用，程序生成与 meta-mutation 全程走确定性降级"
        elif self._fallback_used:
            self.notes += "；部分 LLM 输出不可解析时回退到确定性变异"
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        """确定性产出 split 信号：零 LLM 调用，只用冻结的冠军程序 + split 及之前数据。"""
        if self.frozen_program is None:
            raise RuntimeError("AlgoEvolve.fit() 必须先运行")
        dates = ds.dates_through(split)
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][COLS]
        ind = indicator_table(panel)                      # 指标只用 split 及之前数据 warmup
        sig = eval_program(self.frozen_program, ind)      # 受限 DSL 求值，无任何 LLM
        target = ds._dates_of(split)
        out = sig[sig.index.get_level_values(0).isin(target)]
        return out.astype(float)


def _self_test() -> None:
    """契约 §8 自测：打印 LLM api_call 数 / test 日数 / NaN 比例，并断言通过。"""
    from core.data import make_dataset
    ds = make_dataset()
    m = AlgoEvolve().fit(ds)
    s = m.produce_signal(ds, "test")
    n_days = int(s.index.get_level_values(0).nunique())
    nan_ratio = float(s.isna().mean())
    print(f"[AlgoEvolve self-test] llm_api_call={m.llm.stats['api_call']} "
          f"cache_hit={m.llm.stats['cache_hit']} error={m.llm.stats['error']} "
          f"program_calls={m._n_prog_calls} meta_calls={m._n_meta_calls}")
    print(f"[AlgoEvolve self-test] test_days={n_days} n_signal={len(s)} nan_ratio={nan_ratio:.4f}")
    print(f"[AlgoEvolve self-test] fidelity={m.fidelity}")
    print(f"[AlgoEvolve self-test] genome={m.frozen_genome.as_dict() if m.frozen_genome else None}")
    print(f"[AlgoEvolve self-test] champion={m.frozen_program}")
    assert n_days == 84, f"test 日数应为 84，实际 {n_days}"
    assert len(s) > 0
    assert nan_ratio < 0.5, f"NaN 比例过高: {nan_ratio}"
    assert m.frozen_genome is not None and m.frozen_program
    print("[AlgoEvolve self-test] PASS")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    _self_test()
