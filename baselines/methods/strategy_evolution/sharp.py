"""
SHARP（09）复现 —— Self-Evolving Human-Auditable Rubric Policy（arXiv:2605.06822）。

论文核心机制 -> 本复现怎么做 -> 哪些没复现
================================================

1) 版本化 rubric：策略 = 一组结构化规则 R_k = (id_k, cat_k, cond_k, act_k)，
   cond/act 是自然语言谓词与调整动作（不是形式化 DSL）。本复现原样保留四元组，
   并把每条规则编译出确定性的价格特征/阈值/动作语义，供无 LLM 的信号计算使用。
2) 最差日归因（Attribution）：取训练回测中 K_attr=20 个最差组合日，打包完整上下文
   （持仓、预测收益、置信度、激活规则、真实收益），**一次联合 LLM 调用**分析全部 20 天，
   输出带 freq= 的结构化错误模式，只保留在 >=3 天出现的模式，且每条必须指名具体规则。
3) 原子编辑（Evolution）：给定最高频错误模式，LLM 产出 <=3 个原子编辑，四类算子
   ADD / MODIFY_THRESHOLD / MODIFY_WEIGHT / REMOVE；rubric 达 12 条后新增须删一条，
   硬上限 M_max=18。
4) 验证门：候选在 val 上算 excess return，**有符号**比较 e_j >= e* - 0.005 才接受；
   仅严格改进 e_j > e* 时更新 (R*, e*)；拒绝则回滚到上一版；取全程 val 最优 rubric 冻结。
5) 测试期：冻结 R*，produce_signal 100% 确定性、零 LLM 调用。

论文未复现 / 用价格代理之处（诚实标注）：
  - 论文用新闻文本，本复现无任何文本数据，故 6 条共享规则中 4 条纯新闻规则
    (temporal_earnings_season / news_analyst_rating / news_generic_market / news_count_low)
    **删除**；temporal_priced_in 用「5日累计涨跌幅绝对值 > 3%」代理，
    macro_high_vix 用「20日年化已实现波动率 > 25%」代理。
  - 论文的 LLM analyst f_θ（新闻 -> 预测收益 r̂、置信度 c、激活记录 A）无法复现，
    本复现用固定价格特征横截面 z-score 线性映射替代 r̂，用 ATR 倒数替代 c；因此
    激活记录由确定性引擎给出，而非论文的 self-reported A（属偏差，见 fidelity/notes）。
  - 论文的 e(·) excess return 精确公式未指定（spec §5/§11），本复现取
    「val 期 dollar-neutral 多空组合日净收益（含 5bps 换手成本）的算术累计和」。
  - 论文的 O2O 开盘价口径未提供，本复现用数据集日频 fwd_ret 作已实现收益代理。
  - 论文 A1 消融（去归因）通过构造参数 use_attribution=False 复现：跳过归因与进化，
    等价于 static，作为对照。
"""
from __future__ import annotations

import json
import math
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.llm import TextLLM, LLMUnavailable

from .sharp_rubric import (
    Edit, Rule, ACTIONS, apply_edits, apply_rubric, backtest_details, base_analyst,
    build_features, describe_features, initial_rubric, no_leak_forward_returns,
    parse_json_object, rubric_to_prompt, sanitize_edit,
)

_ATTR_SYSTEM = (
    "你是 SHARP 框架中的归因智能体（Attribution Agent）。输入是当前 rubric 与若干个最差"
    "组合交易日的完整上下文（持仓、预测、置信度、激活规则、真实收益）。你的任务：跨样本做"
    "结构性 credit assignment —— 从市场噪声中识别系统性逻辑缺陷，指出哪些规则调整本可避免"
    "这些回撤，并指名具体规则 id。只输出一个 JSON 对象，不要解释或 markdown。"
)

_EVOLVE_SYSTEM = (
    "你是 SHARP 框架中的进化智能体（Evolution Agent）。你基于归因智能体给出的高频错误模式，"
    "对 rubric 做『原子编辑』—— 每次只改一条规则的单个字段，每条编辑必须显式绑定到一个因果"
    "诊断。禁止全局自由改写。可用算子：ADD（新增规则）、MODIFY_THRESHOLD（改阈值）、"
    "MODIFY_WEIGHT（改信号权重/动作强度）、REMOVE（删除误触发规则）。每轮最多 3 条编辑，"
    "rubric 达 12 条后每次 ADD 必须同时 REMOVE 一条，规则总数硬上限 18。"
    "只输出一个 JSON 对象，不要解释或 markdown。"
)


class SHARP(BaselineMethod):
    """SHARP：版本化 rubric + 最差日归因 + 原子编辑 + 有符号验证门。"""

    def __init__(
        self,
        rounds: int = 5,
        k_attr: int = 20,
        epsilon: float = 0.005,
        m_max: int = 18,
        delta_max: int = 3,
        compact_at: int = 12,
        n_long: int = 5,
        n_short: int = 5,
        cost_bps: float = 5.0,
        use_attribution: bool = True,
        seed: Optional[int] = 0,
    ):
        self.name = "sharp"
        self.category = "strategy_evolution"
        self.paper_id = "09"
        self.fidelity = "paper_ablation_added"
        self.notes = (
            "版本化 rubric(id,cat,cond,act)、K_attr=20 最差日联合 LLM 归因(freq>=3)、<=3 原子编辑"
            "(ADD/改阈值/改权重/REMOVE)、有符号验证门 e_j>=e*-0.005 与回滚/best-tracking、冻结最优 "
            "rubric 均忠实实现；A1 去归因消融由 use_attribution 开关复现。论文新闻/VIX/5分钟/美股"
            "用价格代理：temporal_priced_in→|5日涨跌幅|>3%，macro_high_vix→20日年化波动率>25%，"
            "4 条纯新闻规则删除；LLM analyst(新闻→r̂,c)用价格特征确定性映射替代；e(·) 取 val 组合"
            "净收益累计和（论文未定义）。"
        )
        self.rounds = rounds
        self.k_attr = k_attr
        self.epsilon = epsilon
        self.m_max = m_max
        self.delta_max = delta_max
        self.compact_at = compact_at
        self.n_long = n_long
        self.n_short = n_short
        self.cost_bps = cost_bps
        self.use_attribution = use_attribution
        self.rng = np.random.RandomState(seed)
        self.llm = TextLLM(tag="sharp", temperature=0.3, max_tokens=2000)
        self.degraded = not self.llm.available
        # 冻结产物（初始即确定性，无需 fit 也可产出信号，便于接口稳健）
        self.best_rubric: List[Rule] = initial_rubric()
        self.best_score: float = float("nan")
        self.versions: List[Tuple[int, List[Rule], float, str]] = []
        self.history: List[dict] = []
        self._feats: Optional[pd.DataFrame] = None
        self._rh: Optional[pd.Series] = None
        self._cf: Optional[pd.Series] = None
        self._fwd: Optional[pd.Series] = None

    # ------------------------------------------------------------------
    # LLM 智能体
    # ------------------------------------------------------------------
    def _attribute_llm(self, details: Dict, worst: Sequence, rules: Sequence[Rule],
                       round_idx: int) -> List[dict]:
        bundle = [details[d] for d in worst if d in details]
        user = (
            f"当前是第 {round_idx}/{self.rounds} 轮进化。当前 rubric：\n"
            + json.dumps(rubric_to_prompt(rules), ensure_ascii=False, sort_keys=True, indent=1)
            + f"\n\n最差 {len(bundle)} 个组合交易日完整上下文：\n"
            + json.dumps(bundle, ensure_ascii=False, sort_keys=True)
            + "\n\n请输出 JSON："
            + '{"patterns": [{"pattern": "<简短错误模式名>", "freq": <在以上天数中出现的天数,整数>, '
            + '"rule": "<被牵涉的规则 id>", "diagnosis": "<一句话诊断>"}]}。'
            + f"要求：freq 为 1..{len(bundle)} 的整数；rule 必须是上面 rubric 中真实存在的 id。"
        )
        text = self.llm.complete(_ATTR_SYSTEM, user, purpose=f"attribution_round_{round_idx}")
        obj = parse_json_object(text)
        if obj is None:
            return []
        raw = obj.get("patterns", [])
        if not isinstance(raw, list):
            return []
        ids = {r.id for r in rules}
        out = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            try:
                freq = int(p.get("freq", 0))
            except (TypeError, ValueError):
                continue
            rule = str(p.get("rule", "")).strip()
            if freq >= 3 and rule in ids:
                out.append({
                    "pattern": str(p.get("pattern", "unknown"))[:80],
                    "freq": freq, "rule": rule,
                    "diagnosis": str(p.get("diagnosis", ""))[:200],
                })
        return sorted(out, key=lambda x: -x["freq"])

    def _evolve_llm(self, rules: Sequence[Rule], patterns: Sequence[dict],
                    round_idx: int) -> List[Edit]:
        user = (
            f"当前是第 {round_idx}/{self.rounds} 轮进化。当前 rubric：\n"
            + json.dumps(rubric_to_prompt(rules), ensure_ascii=False, sort_keys=True, indent=1)
            + "\n\n归因得到的高频错误模式（已按 freq 降序，freq>=3）：\n"
            + json.dumps(list(patterns), ensure_ascii=False, sort_keys=True, indent=1)
            + "\n\n可用特征（feature -> 合理范围）：\n"
            + json.dumps(describe_features(), ensure_ascii=False, sort_keys=True)
            + f"\n动作类型 action ∈ {list(ACTIONS)}；side ∈ ['all','long','short']。"
            + "\n\n请基于最高频错误模式，输出 JSON（最多 3 条原子编辑，可少于 3）："
            + '\n{"edits": ['
            + '{"op": "MODIFY_THRESHOLD", "id": "<rule id>", "threshold": <float>, '
            + '"cond": "<可选新自然语言条件>", "rationale": "..."}, '
            + '{"op": "MODIFY_WEIGHT", "id": "<rule id>", "action": "scale_rhat|cap_conf", '
            + '"magnitude": <float>, "act": "<可选新动作描述>", "rationale": "..."}, '
            + '{"op": "ADD", "id": "<新 id>", "cat": "<类别>", "cond": "<自然语言条件>", '
            + '"act": "<自然语言动作>", "feature": "<上面特征>", "cmp": ">|<", '
            + '"threshold": <float>, "action": "scale_rhat|cap_conf", "magnitude": <float>, '
            + '"side": "all|long|short", "rationale": "..."}, '
            + '{"op": "REMOVE", "id": "<rule id>", "rationale": "..."}'
            + "]}"
        )
        text = self.llm.complete(_EVOLVE_SYSTEM, user, purpose=f"evolution_round_{round_idx}")
        obj = parse_json_object(text)
        if obj is None:
            return []
        raw = obj.get("edits", [])
        if not isinstance(raw, list):
            return []
        edits: List[Edit] = []
        for item in raw[: self.delta_max]:
            cleaned = sanitize_edit(item, rules)
            if cleaned is not None:
                edits.append(cleaned)
        return edits

    # ------------------------------------------------------------------
    # 确定性降级路径（无 LLM 凭据或调用失败时）
    # ------------------------------------------------------------------
    def _attribute_fallback(self, details: Dict, worst: Sequence,
                            rules: Sequence[Rule]) -> List[dict]:
        counts: Dict[str, int] = {r.id: 0 for r in rules}
        for d in worst:
            det = details.get(d)
            if not det:
                continue
            seen = set()
            for side_ in ("long", "short"):
                for item in det[side_]:
                    seen.update(item["rules"])
            for rid in seen:
                if rid in counts:
                    counts[rid] += 1
        out = [{"pattern": f"{rid}_misfire", "freq": c, "rule": rid,
                "diagnosis": "确定性回退：该规则在最差日中反复激活"}
               for rid, c in counts.items() if c >= 3]
        return sorted(out, key=lambda x: -x["freq"])

    def _evolve_fallback(self, rules: Sequence[Rule], patterns: Sequence[dict],
                         round_idx: int) -> List[Edit]:
        edits: List[Edit] = []
        for p in patterns[: self.delta_max]:
            base = next((r for r in rules if r.id == p["rule"]), None)
            if base is None:
                continue
            if round_idx % 2 == 0:
                factor = 1.1 if base.op == ">" else 0.9
                edits.append(Edit(op="MODIFY_THRESHOLD", rule_id=base.id,
                                  new_threshold=base.threshold * factor,
                                  rationale="确定性回退：收紧触发阈值"))
            else:
                mag = (base.magnitude * 0.85 if base.action == "scale_rhat"
                       else max(0.05, base.magnitude - 0.10))
                edits.append(Edit(op="MODIFY_WEIGHT", rule_id=base.id,
                                  new_magnitude=mag, new_action=base.action,
                                  rationale="确定性回退：降低该规则动作强度"))
        return edits

    def _degrade(self) -> None:
        if not self.degraded:
            self.degraded = True
            self.fidelity = "llm_replaced_by_rule"
            self.notes = ("LLM 后端不可用/调用失败，归因与进化降级为确定性规则；"
                          + self.notes)

    # ------------------------------------------------------------------
    # 验证门与目标
    # ------------------------------------------------------------------
    def _excess_return(self, rules: Sequence[Rule], dates: pd.DatetimeIndex) -> float:
        daily, _ = backtest_details(
            rules, self._feats, self._rh, self._cf, self._fwd, dates,
            self.n_long, self.n_short, self.cost_bps)
        return float(daily.sum()) if len(daily) else float("nan")

    def _gate_accept(self, e_j: float, e_star: float) -> bool:
        """有符号比较（绝不取 abs）：e_j >= e* - ε。"""
        if not math.isfinite(e_j):
            return False
        if not math.isfinite(e_star):
            return True
        return e_j >= e_star - self.epsilon

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def fit(self, ds: Dataset) -> "SHARP":
        tv_dates = ds.train_dates.union(ds.val_dates)
        panel_tv = ds.panel[ds.panel.index.get_level_values(0).isin(tv_dates)]
        self._feats = build_features(panel_tv)
        self._rh, self._cf = base_analyst(self._feats)
        self._fwd = no_leak_forward_returns(panel_tv, ds.horizon)  # 截到 val 末尾，test 永不参与

        rules = initial_rubric()
        e_cur = self._excess_return(rules, ds.val_dates)
        e_star = e_cur
        best = list(rules)
        self.versions = [(0, list(rules), e_cur, "init")]
        self.history = []

        for j in range(1, self.rounds + 1):
            # --- y ← BACKTEST(R, D_train)：训练回测 + 最差日 ---
            _, details = backtest_details(
                rules, self._feats, self._rh, self._cf, self._fwd, ds.train_dates,
                self.n_long, self.n_short, self.cost_bps)
            if not details:
                self.history.append({"round": j, "status": "no_train_days"})
                continue
            daily = pd.Series({d: v["portfolio_ret"] for d, v in details.items()}).sort_index()
            k = min(self.k_attr, len(daily))
            worst = list(daily.nsmallest(k).index)

            # --- E ← ATTRIBUTE(worst days)：1 次联合 LLM 调用 ---
            patterns: List[dict] = []
            if self.use_attribution:
                if self.degraded:
                    patterns = self._attribute_fallback(details, worst, rules)
                else:
                    try:
                        patterns = self._attribute_llm(details, worst, rules, j)
                    except LLMUnavailable:
                        self._degrade()
                        patterns = self._attribute_fallback(details, worst, rules)

            # --- P ← EVOLVE(R, E)：1 次 LLM 调用（<=3 原子编辑）---
            edits: List[Edit] = []
            if patterns:
                if self.degraded:
                    edits = self._evolve_fallback(rules, patterns, j)
                else:
                    try:
                        edits = self._evolve_llm(rules, patterns, j)
                    except LLMUnavailable:
                        self._degrade()
                        edits = self._evolve_fallback(rules, patterns, j)
                    if not edits:
                        edits = self._evolve_fallback(rules, patterns, j)

            # --- R̃ ← APPLY(R, P) ---
            candidate, applied = apply_edits(
                rules, edits, self.m_max, self.delta_max, self.compact_at)
            # --- e_j ← e(BACKTEST(R̃, D_val))，有符号验证门 ---
            e_j = self._excess_return(candidate, ds.val_dates)
            accepted = self._gate_accept(e_j, e_star)
            if accepted:
                rules = candidate
                e_cur = e_j
                if math.isfinite(e_j) and (not math.isfinite(e_star) or e_j > e_star):
                    best, e_star = candidate, e_j  # best-tracking：仅严格改进
            # 否则回滚：rules 与 e_cur 保持不变
            self.versions.append(
                (j, list(rules), e_cur, "accepted" if accepted else "rejected"))
            self.history.append({
                "round": j, "n_worst": k, "patterns": patterns,
                "edits": [e.op for e in applied], "e_j": e_j if math.isfinite(e_j) else None,
                "e_star": e_star if math.isfinite(e_star) else None, "accepted": accepted,
            })

        self.best_rubric = best
        self.best_score = e_star
        return self

    # ------------------------------------------------------------------
    # 测试期：冻结 rubric，零 LLM
    # ------------------------------------------------------------------
    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        dates = ds.dates_through(split)
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)]
        feats = build_features(panel)
        rh, cf = base_analyst(feats)
        sigma, _, _, _ = apply_rubric(self.best_rubric, feats, rh, cf)
        target = ds._dates_of(split)
        return sigma[sigma.index.get_level_values(0).isin(target)]


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from core.data import make_dataset

    _ds = make_dataset()
    _m = SHARP().fit(_ds)
    _s = _m.produce_signal(_ds, "test")
    print("llm_stats:", _m.llm.stats)
    print("backend:", _m.llm.backend_name)
    print("fidelity:", _m.fidelity)
    print("test_days:", int(_s.index.get_level_values(0).nunique()))
    print("n_rows:", int(len(_s)))
    print("nan_ratio:", float(_s.notna().mean()))
