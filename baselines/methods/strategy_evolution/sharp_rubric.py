"""
SHARP 辅助模块：rubric 数据模型 (id,cat,cond,act) + 数值执行语义、确定性执行引擎、
5L/5S 组合回测、四类原子编辑算子与 LLM 输出清洗。

cond/act 是论文要求的自然语言结构化规则；feature/op/threshold/action/magnitude 是把规则
落到无新闻价格数据上的确定性执行语义（论文里由 LLM 自行执行，见 spec §10 偏差说明）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from core.indicators import indicator_table

# 执行引擎支持的价格/波动特征（均无未来函数）
FEATURES: Tuple[str, ...] = (
    "rsi14", "ema20_gap", "macd_hist", "atr_pct", "boll_pos",
    "mom10", "mom5", "absmom5", "vol20",
)
# 每个特征的阈值合理区间（防止 LLM 给出量级错误的值）
THRESHOLD_RANGE: Dict[str, Tuple[float, float]] = {
    "rsi14": (5.0, 95.0), "ema20_gap": (-0.20, 0.20), "macd_hist": (-0.50, 0.50),
    "atr_pct": (0.001, 0.200), "boll_pos": (-0.50, 1.50), "mom10": (-0.50, 0.50),
    "mom5": (-0.30, 0.30), "absmom5": (0.0, 0.50), "vol20": (0.02, 1.50),
}
FEATURE_LABEL: Dict[str, str] = {
    "rsi14": "RSI14", "ema20_gap": "价格对EMA20偏离", "macd_hist": "MACD柱",
    "atr_pct": "ATR/收盘价", "boll_pos": "布林带位置", "mom10": "10日动量",
    "mom5": "5日动量", "absmom5": "5日累计涨跌幅绝对值", "vol20": "20日年化已实现波动率",
}
ACTIONS = ("scale_rhat", "cap_conf")
SIDES = ("all", "long", "short")


@dataclass(frozen=True)
class Rule:
    """一条 rubric 规则：自然语言 (id, cat, cond, act) + 数值执行语义。"""
    id: str
    cat: str
    cond: str
    act: str
    feature: str
    op: str                 # ">" | "<"
    threshold: float
    action: str             # "scale_rhat" | "cap_conf"
    magnitude: float
    side: str = "all"       # "all" | "long" | "short"


@dataclass(frozen=True)
class Edit:
    """一个原子编辑，op ∈ ADD/MODIFY_THRESHOLD/MODIFY_WEIGHT/REMOVE。"""
    op: str
    rule_id: str
    rationale: str = ""
    rule: Optional[Rule] = None
    new_threshold: Optional[float] = None
    new_magnitude: Optional[float] = None
    new_action: Optional[str] = None
    new_cond: Optional[str] = None
    new_act: Optional[str] = None


def initial_rubric() -> List[Rule]:
    """初始 rubric：论文 6 条共享规则中可用价格代理的 2 条 + 4 条自定价格规则。

    论文 6 条共享规则（spec §1）：temporal_priced_in→|5日涨跌幅|代理；macro_high_vix→
    20日年化已实现波动率代理；temporal_earnings_season / news_analyst_rating /
    news_generic_market / news_count_low 需要财报/分析师/新闻文本，无数据，**删除**。
    """
    return [
        Rule("temporal_priced_in", "temporal_discount",
             "IF 5日累计涨跌幅绝对值 > 3% THEN 削减信号强度 70%",
             "signal ×0.30（叙事已被价格消化）",
             "absmom5", ">", 0.03, "scale_rhat", 0.30, "all"),
        Rule("macro_high_vix", "macro_interaction",
             "IF 20日年化已实现波动率 > 25% THEN 多头收益下修 30%",
             "bullish r_hat ×0.70", "vol20", ">", 0.25, "scale_rhat", 0.70, "long"),
        Rule("overbought_rsi", "price_momentum",
             "IF RSI14 > 70 THEN 削减信号强度 50%",
             "signal ×0.50", "rsi14", ">", 70.0, "scale_rhat", 0.50, "all"),
        Rule("high_volatility", "volatility_regime",
             "IF ATR% > 3% THEN 削减信号强度 50%",
             "signal ×0.50", "atr_pct", ">", 0.03, "scale_rhat", 0.50, "all"),
        Rule("trend_confirmation", "price_momentum",
             "IF 价格高于EMA20 > 2% THEN 多头信心 ×1.30",
             "bullish r_hat ×1.30", "ema20_gap", ">", 0.02, "scale_rhat", 1.30, "long"),
        Rule("deep_drawdown_rebound", "price_momentum",
             "IF 布林带位置 < 0.10 THEN 多头信心 ×1.20",
             "bullish r_hat ×1.20", "boll_pos", "<", 0.10, "scale_rhat", 1.20, "long"),
    ]


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """指标表 + 5 日动量 + 20 日已实现波动率（无未来函数）。"""
    feats = indicator_table(panel)
    close = panel["close"]
    ret1 = close.groupby(level=1).pct_change()
    feats["mom5"] = close.groupby(level=1).transform(lambda s: s / s.shift(5) - 1.0)
    feats["absmom5"] = feats["mom5"].abs()
    feats["vol20"] = ret1.groupby(level=1).transform(
        lambda s: s.rolling(20).std() * np.sqrt(252.0))
    return feats


# 论文 LLM analyst 的替代：固定价格特征线性映射 -> 预测收益 r_hat
ANALYST_WEIGHTS: Dict[str, float] = {
    "ema20_gap": 0.4, "macd_hist": 0.4, "mom10": 0.3,
    "rsi14": -0.2, "atr_pct": -0.2, "boll_pos": -0.1,
}


def _cs_z(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(level=0).transform(
        lambda s: (s - s.mean()) / s.std() if s.std() else s * 0.0)


def base_analyst(feats: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """确定性价格特征 -> (r_hat, confidence)。"""
    z = _cs_z(feats)
    r_hat: Optional[pd.Series] = None
    for col, w in ANALYST_WEIGHTS.items():
        term = z[col] * w
        r_hat = term if r_hat is None else r_hat + term
    atr = feats["atr_pct"].clip(lower=0.0).fillna(0.0)
    conf = (1.0 / (1.0 + 10.0 * atr)).clip(0.05, 1.0)
    return r_hat.astype(float), conf.astype(float)


def apply_rubric(
    rules: Sequence[Rule], feats: pd.DataFrame, r_hat: pd.Series, conf: pd.Series,
) -> Tuple[pd.Series, pd.Series, pd.Series, Dict[str, pd.Series]]:
    """按顺序把规则作用到 (r_hat, conf)，返回 (sigma, r_hat', conf', 激活记录)。"""
    rh, cf = r_hat.copy(), conf.copy()
    activates: Dict[str, pd.Series] = {}
    for rule in rules:
        if rule.feature not in feats.columns:
            activates[rule.id] = pd.Series(False, index=rh.index)
            continue
        col = feats[rule.feature].reindex(rh.index)
        active = (col > rule.threshold) if rule.op == ">" else (col < rule.threshold)
        if rule.side == "long":
            active = active & (rh > 0)
        elif rule.side == "short":
            active = active & (rh < 0)
        active = active.fillna(False).astype(bool)
        if rule.action == "scale_rhat":
            rh = rh.mask(active, rh * rule.magnitude)
        elif rule.action == "cap_conf":
            cf = cf.mask(active, np.minimum(cf, rule.magnitude))
        activates[rule.id] = active
    return rh * cf, rh, cf, activates


def backtest_details(
    rules: Sequence[Rule], feats: pd.DataFrame, r_hat: pd.Series, conf: pd.Series,
    fwd: pd.Series, dates: pd.DatetimeIndex,
    n_long: int = 5, n_short: int = 5, cost_bps: float = 5.0,
):
    """在 dates 内回测 5L/5S 等权 dollar-neutral，返回 (每日净收益, 每日详情)。"""
    sigma, rh2, cf2, activates = apply_rubric(rules, feats, r_hat, conf)
    dd = pd.DataFrame({"sig": sigma.reindex(fwd.index), "ret": fwd,
                       "rh": rh2.reindex(fwd.index), "cf": cf2.reindex(fwd.index)}
                      ).dropna().reset_index()
    dd.columns = ["date", "symbol", "sig", "ret", "rh", "cf"]
    dd = dd[dd["date"].isin(dates)]
    rule_ids = [r.id for r in rules]
    daily: Dict[pd.Timestamp, float] = {}
    details: Dict[pd.Timestamp, dict] = {}
    prev: Optional[pd.Series] = None
    for d, g in dd.groupby("date"):
        if g["symbol"].nunique() < n_long + n_short:
            continue
        g = g.set_index("symbol")
        order = g["sig"].sort_values()
        longs, shorts = list(order.index[-n_long:]), list(order.index[:n_short])
        w = pd.Series(0.0, index=g.index)
        w.loc[longs], w.loc[shorts] = 1.0 / n_long, -1.0 / n_short
        gross = float(g.loc[longs, "ret"].mean() - g.loc[shorts, "ret"].mean())
        if prev is None:
            turn = float(w.abs().sum())
        else:
            idx = prev.index.union(w.index)
            turn = float((w.reindex(idx, fill_value=0.0)
                          - prev.reindex(idx, fill_value=0.0)).abs().sum())
        daily[d] = gross - turn * cost_bps / 1e4

        def pack(syms: List[str]) -> List[dict]:
            return [{"symbol": str(s_), "ret": round(float(g.loc[s_, "ret"]), 4),
                     "sigma": round(float(g.loc[s_, "sig"]), 4),
                     "conf": round(float(g.loc[s_, "cf"]), 4),
                     "rules": [rid for rid in rule_ids
                               if bool(activates[rid].get((d, s_), False))]}
                    for s_ in syms]

        details[d] = {"date": str(pd.Timestamp(d).date()),
                      "portfolio_ret": round(daily[d], 4), "gross_ret": round(gross, 4),
                      "long": pack(longs), "short": pack(shorts),
                      "context": {"xs_mean_ret": round(float(g["ret"].mean()), 4),
                                  "xs_std_ret": round(float(g["ret"].std(ddof=0)), 4),
                                  "n_names": int(len(g))}}
        prev = w
    return pd.Series(daily).sort_index(), details


def no_leak_forward_returns(panel: pd.DataFrame, horizon: int) -> pd.Series:
    """只用给定 panel（fit 时截到 validation 末尾）算未来 horizon 日收益，尾部为 NaN。"""
    close = panel["close"]
    fwd = close.groupby(level=1).transform(lambda s: s.shift(-horizon) / s - 1.0)
    fwd.name = "fwd_ret_no_leak"
    return fwd


def render_cond(rule: Rule) -> str:
    sign = ">" if rule.op == ">" else "<"
    return f"IF {FEATURE_LABEL.get(rule.feature, rule.feature)} {sign} {round(rule.threshold, 4)} THEN 调整信号"


def render_act(rule: Rule) -> str:
    if rule.action == "cap_conf":
        return f"cap confidence at {round(rule.magnitude, 4)}"
    return f"signal ×{round(rule.magnitude, 4)}"


def rule_to_prompt(rule: Rule) -> dict:
    return {"id": rule.id, "cat": rule.cat, "cond": rule.cond, "act": rule.act,
            "feature": rule.feature, "op": rule.op, "threshold": round(rule.threshold, 4),
            "action": rule.action, "magnitude": round(rule.magnitude, 4), "side": rule.side}


def rubric_to_prompt(rules: Sequence[Rule]) -> List[dict]:
    return [rule_to_prompt(r) for r in rules]


def describe_features() -> dict:
    return {f: {"label": FEATURE_LABEL[f], "range": list(THRESHOLD_RANGE[f])} for f in FEATURES}


def _clamp_threshold(feature: str, value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    lo, hi = THRESHOLD_RANGE.get(feature, (0.0, 1.0))
    return float(min(max(v, lo), hi))


def _clamp_magnitude(action: str, value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    lo, hi = (0.05, 1.0) if action == "cap_conf" else (0.10, 3.0)
    return float(min(max(v, lo), hi))


def sanitize_edit(raw: dict, rules: Sequence[Rule]) -> Optional[Edit]:
    """把 LLM 给出的任意 dict 清洗成合法 Edit；不合法返回 None。"""
    if not isinstance(raw, dict):
        return None
    op = str(raw.get("op", "")).strip().upper()
    rid = str(raw.get("id", raw.get("rule", ""))).strip()
    rationale = str(raw.get("rationale", ""))[:200]
    ids = {r.id for r in rules}
    base = next((r for r in rules if r.id == rid), None)

    if op == "ADD":
        feature = str(raw.get("feature", "")).strip()
        if feature not in FEATURES or not rid or rid in ids:
            return None
        cmp_ = str(raw.get("cmp", raw.get("comparison", ">"))).strip()
        thr = _clamp_threshold(feature, raw.get("threshold"))
        action = str(raw.get("action", "scale_rhat")).strip()
        action = action if action in ACTIONS else "scale_rhat"
        mag = _clamp_magnitude(action, raw.get("magnitude"))
        if thr is None or mag is None:
            return None
        side = str(raw.get("side", "all")).strip()
        skel = Rule(rid, str(raw.get("cat", "evolved"))[:40], "", "", feature,
                    cmp_ if cmp_ in (">", "<") else ">", thr, action, mag,
                    side if side in SIDES else "all")
        return Edit("ADD", rid, rationale,
                    replace(skel, cond=str(raw.get("cond", "")).strip() or render_cond(skel),
                            act=str(raw.get("act", "")).strip() or render_act(skel)))
    if op == "REMOVE" and base is not None:
        return Edit("REMOVE", rid, rationale)
    if op == "MODIFY_THRESHOLD" and base is not None:
        thr = _clamp_threshold(base.feature, raw.get("threshold"))
        if thr is None:
            return None
        return Edit("MODIFY_THRESHOLD", rid, rationale, new_threshold=thr,
                    new_cond=str(raw.get("cond", "")).strip() or None)
    if op == "MODIFY_WEIGHT" and base is not None:
        action = str(raw.get("action", base.action)).strip()
        action = action if action in ACTIONS else base.action
        mag = _clamp_magnitude(action, raw.get("magnitude", raw.get("weight")))
        if mag is None:
            return None
        return Edit("MODIFY_WEIGHT", rid, rationale, new_magnitude=mag, new_action=action,
                    new_act=str(raw.get("act", "")).strip() or None)
    return None


def apply_edits(
    rules: Sequence[Rule], edits: Sequence[Optional[Edit]],
    m_max: int = 18, delta_max: int = 3, compact_at: int = 12,
) -> Tuple[List[Rule], List[Edit]]:
    """应用 ≤delta_max 个原子编辑，强制 M_max 与 compactness 约束。"""
    cur: List[Rule] = list(rules)
    applied: List[Edit] = []
    selected = [e for e in edits if e is not None][:delta_max]
    n_remove = sum(1 for e in selected if e.op == "REMOVE")
    for e in selected:
        if e.op == "ADD":
            if len(cur) >= m_max or (len(cur) >= compact_at and n_remove == 0):
                continue  # 硬上限 / compactness：≥12 条后新增须伴随删除
            if e.rule is None or any(r.id == e.rule.id for r in cur):
                continue
            cur.append(e.rule)
            applied.append(e)
        elif e.op == "REMOVE":
            for i, r in enumerate(cur):
                if r.id == e.rule_id:
                    cur.pop(i)
                    applied.append(e)
                    break
        elif e.op == "MODIFY_THRESHOLD":
            for i, r in enumerate(cur):
                if r.id == e.rule_id and e.new_threshold is not None:
                    cur[i] = replace(r, threshold=e.new_threshold,
                                     cond=e.new_cond or render_cond(
                                         replace(r, threshold=e.new_threshold)))
                    applied.append(e)
                    break
        elif e.op == "MODIFY_WEIGHT":
            for i, r in enumerate(cur):
                if r.id == e.rule_id and e.new_magnitude is not None:
                    action = e.new_action or r.action
                    cur[i] = replace(r, magnitude=e.new_magnitude, action=action,
                                     act=e.new_act or render_act(
                                         replace(r, magnitude=e.new_magnitude, action=action)))
                    applied.append(e)
                    break
    return cur, applied


def parse_json_object(text: str) -> Optional[dict]:
    """从 LLM 输出中稳健提取 JSON 对象；失败返回 None。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j <= i:
        return None
    try:
        obj = json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None
