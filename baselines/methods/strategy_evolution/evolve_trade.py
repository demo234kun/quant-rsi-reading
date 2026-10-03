"""
EvolveTrade（论文 08）复现：经验驱动的自然语言策略自演化。

论文核心机制（见 papers/strategy_evolution/08_EvolveTrade/note.md 与原文 §3、§5、§6.3）：
  1. 交易智能体（Trading Agent）：冻结骨干 LLM + 固定工具集 T={价格检索, 新闻检索, 代码解释器}。
     其行为完全由系统提示词——即“文本参数化策略” π_t——控制；策略规定工具调用优先级、
     信号校验与风控规则。每个交易日输出资产权重 w_t 及逐资产推理 d_t，构成决策轨迹 h_t=(w_t,d_t)。
  2. 经验反馈 R_t=(h_t, g_t)：g_t 是组合/逐资产已实现收益。论文强调单靠收益歧义极大
     （亏损可能源于流程缺陷，也可能是市场随机冲击），因此必须把决策轨迹与收益配对，
     Policy Agent 才能区分“可修复的流程问题”与“噪声”。
  3. 策略智能体（Policy Agent）：独立 LLM，低频触发（论文每 N=5 个交易日一批）。
     每批 B_k 结束执行 f_update(π, B)=LLM(I_update, π, B)：读取旧策略、本批轨迹、收益反馈，
     诊断后重写完整策略文本 π_{t+1}；骨干 LLM 与工具接口全程冻结。
  论文关键消融：Full(收益+轨迹) SR 0.64 vs 仅收益(移除轨迹) 0.43 vs 关闭演化 0.42。

本复现怎么做（机制→实现）：
  - policy 是真实自然语言文档，含固定机器可读 schema：## tool_priority / ## signal_weights /
    ## validation_rules / ## risk_rules 四个小节 + 自由散文诊断。由同目录 `evolve_trade_policy.py`
    的确定性编译器 `compile_policy` 解析为可执行配置 PolicyConfig，仅文本解析与数值裁剪，绝不 eval。
  - 固定“工具集” = 6 个技术指标（rsi14/ema20_gap/macd_hist/atr_pct/boll_pos/mom10）。
    policy 真实驱动信号构建（见 `_evaluate_policy`）：signal_weights 做横截面 z 加权；
    tool_priority 指定“主证据”校验门；validation_rules 要求足够多指标同向确认否则减半；
    risk_rules 对高波动股降权、留现金缓冲、限制单票集中度。policy 文本因此不是装点，而是执行配置。
  - 决策轨迹逐日记录：访问了哪些工具（指标）及其均值/符号、中间信号统计、确认通过率、
    高波动占比、最终仓位权重向量，以及当日组合收益；每批汇总后交给 Policy Agent。
  - Policy Agent 通过 core.llm.TextLLM 真实调用（tag="evolve_trade"，磁盘缓存）；
    输入 = 当前策略文本 + 本批决策轨迹 + 本批已实现收益 + 粗体制标签，输出 = 重写后的策略文本。
  - 论文关键消融已实现：构造参数 `use_trace=False` 时 Policy Agent 只看得到收益、看不到轨迹
    （复现论文“仅收益反馈”对照）。
  - 验证窗口按轮切成 n_rounds 批，每批结束重写策略；最终冻结的策略用于 test 信号。

未复现及原因（诚实标注）：
  - 论文交易智能体是“冻结 LLM + 真实工具调用（含新闻检索与代码解释器）”。本复现设计上
    test 期零 LLM 调用（防泄漏 + 控成本），因此用**确定性解释器**代替工具调用型交易智能体：
    被迭代对象仍是 policy 文本，机制上等价于“策略控制信息获取/校验/风控流程”，
    但没有 LLM 实时的推理与工具调用行为。这是本复现的核心替代（见 notes）。
  - 无新闻/情绪/基本面数据：论文用 news_searcher 工具，本复现只用价格技术指标（诚实价格代理）。
  - 论文是 15 只美股蓝筹 + 现金的多头 simplex；本复现是 CSI300 日频横截面多空信号。
  - 论文 I_update 诊断提示词细节未完全公开（Appendix G 仅给出模板），本复现自写等价诊断指令，
    并把硬约束（工具集固定、只改流程规则、不 eval）显式写入 system prompt。
  - 论文 N=5（约 21 日窗口内 4 次更新）；本复现验证窗口 84 日，为把 LLM 预算控制在 6 次调用，
    改为 6 轮等长批（每批 14 日）。轮数由构造参数 `n_rounds` 控制。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from core.data import Dataset
from core.interface import BaselineMethod
from core.indicators import indicator_table
from core.llm import TextLLM, LLMUnavailable

from .evolve_trade_policy import (
    INDICATORS,
    INITIAL_POLICY,
    POLICY_SYSTEM,
    PolicyConfig,
    compile_policy,
    default_config,
)


class EvolveTrade(BaselineMethod):
    """EvolveTrade：策略文本 π_t 由 Policy Agent 依据轨迹+收益逐批重写。"""

    def __init__(self, n_rounds: int = 6, use_trace: bool = True) -> None:
        self.name = "evolve_trade"
        self.category = "strategy_evolution"
        self.paper_id = "08"
        self.fidelity = "paper_ablation_added"
        self.notes = ("policy 文本演化闭环 + 决策轨迹 + 轨迹消融忠实；"
                      "交易执行用确定性解释器替代 live 工具调用智能体；"
                      "论文新闻/代码工具换成 6 个价格指标；N=5 改为 6 轮以控 LLM 预算")
        self.n_rounds = n_rounds
        self.use_trace = use_trace          # 论文消融：False=仅收益，True=收益+决策轨迹
        self.llm: TextLLM | None = None
        self.final_cfg: PolicyConfig | None = None
        self.final_policy_text = ""
        self.policy_log: List[Dict] = []
        self.trace_log: List[Dict] = []
        self.degraded = False

    # -- 数据/指标（用 dates_through 做 warmup，确保 split 起点不出 NaN）--
    @staticmethod
    def _indicator_panel(ds: Dataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
        cols = ["open", "high", "low", "close", "volume", "ret"]
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]
        return indicator_table(panel)

    @staticmethod
    def _zscore(ind: pd.DataFrame) -> pd.DataFrame:
        def _z(s: pd.Series) -> pd.Series:
            sd = float(s.std())
            return (s - s.mean()) / sd if np.isfinite(sd) and sd > 0 else s * 0.0
        return ind.groupby(level=0, group_keys=False).transform(_z)

    # -- 确定性解释器：policy -> 信号 + 逐日诊断 --
    def _evaluate_policy(
        self, ind: pd.DataFrame, cfg: PolicyConfig
    ) -> Tuple[pd.Series, pd.DataFrame]:
        cols = [c for c in INDICATORS if c in ind.columns]
        z = self._zscore(ind[cols])
        w = cfg.normalized_weights()

        base = pd.Series(0.0, index=ind.index)
        for c in cols:
            wc = w.get(c, 0.0)
            if wc != 0.0:
                base = base + z[c] * wc
        sign_base = np.sign(base)

        # validation：数同向且有效的指标个数；不足则减半
        confirm = pd.Series(0, index=ind.index)
        for c in cols:
            wc = w.get(c, 0.0)
            if wc == 0.0:
                continue
            agree = ((np.sign(z[c]) == np.sign(wc)) & (np.sign(z[c]) == sign_base)
                     & (z[c].abs() >= cfg.min_abs_z))
            confirm = confirm + agree.astype(int)
        pass_confirm = confirm >= cfg.require_confirmations
        # tool_priority：最高优先级“主证据”必须与合成方向一致，否则减半
        active_pri = [c for c in cfg.priority if c in cols and w.get(c, 0.0) != 0.0]
        if active_pri:
            pass_confirm = pass_confirm & (np.sign(z[active_pri[0]]) == sign_base)
        gate = pd.Series(np.where(pass_confirm, 1.0, 0.5), index=ind.index)

        # risk：高波动降权
        high_vol = pd.Series(False, index=ind.index)
        if "atr_pct" in ind.columns:
            high_vol = ind["atr_pct"] > cfg.vol_cap_pct
            gate = gate * np.where(high_vol, 0.5, 1.0)
        score = base * gate

        # 转成每日多空权重向量（多头半仓 / 空头半仓），再施加集中度与现金约束
        pos, neg = score.clip(lower=0.0), (-score).clip(lower=0.0)
        lp = (pos / pos.groupby(level=0).transform("sum").replace(0.0, np.nan)).fillna(0.0)
        sp = (neg / neg.groupby(level=0).transform("sum").replace(0.0, np.nan)).fillna(0.0)
        weights = (0.5 * lp - 0.5 * sp).clip(lower=-cfg.max_position, upper=cfg.max_position)
        weights = (weights * (1.0 - cfg.cash_buffer)).replace([np.inf, -np.inf], 0.0).fillna(0.0)

        diag = pd.DataFrame({
            "score_mean": score.groupby(level=0).mean(),
            "score_std": score.groupby(level=0).std(ddof=0),
            "confirm_pass_frac": pass_confirm.groupby(level=0).mean(),
            "high_vol_frac": high_vol.groupby(level=0).mean(),
            "max_abs_weight": weights.abs().groupby(level=0).max(),
        })
        az = z.abs().groupby(level=0).mean()
        az.columns = [f"absz_{c}" for c in az.columns]
        mz = z.groupby(level=0).mean()
        mz.columns = [f"meanz_{c}" for c in mz.columns]
        return weights.rename("signal"), diag.join(az).join(mz)

    # -- 验证窗口内部收益（只用 val 内部 close，绝不触碰 test 价格）--
    @staticmethod
    def _val_internal_returns(ds: Dataset) -> pd.Series:
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(ds.val_dates)]
        close = panel["close"].sort_index()
        return close.groupby(level=1).transform(lambda s: s.shift(-1) / s - 1.0)

    @staticmethod
    def _portfolio_return(sig: pd.Series, ret: pd.Series) -> pd.Series:
        df = pd.concat([sig.rename("w"), ret.rename("r")], axis=1).dropna()
        if df.empty:
            return pd.Series(dtype=float)
        return (df["w"] * df["r"]).groupby(level=0).sum()

    @staticmethod
    def _summarize_returns(daily: pd.Series) -> Dict[str, float]:
        if daily.empty:
            return {"mean": 0.0, "cum": 0.0, "vol": 0.0, "win": 0.0}
        return {"mean": float(daily.mean()), "cum": float((1.0 + daily).prod() - 1.0),
                "vol": float(daily.std(ddof=0)), "win": float((daily > 0).mean())}

    @staticmethod
    def _regime_label(ret_batch: pd.Series) -> str:
        if ret_batch.empty:
            return "未知"
        m = float(ret_batch.mean())
        return "上涨" if m > 0.0015 else ("回撤" if m < -0.0015 else "震荡")

    def _build_trace(self, k: int, bd: pd.DatetimeIndex, cfg: PolicyConfig,
                     sig: pd.Series, diag: pd.DataFrame) -> Dict:
        """组装本批真实决策轨迹：工具使用、中间信号、最终仓位权重、逐日诊断。"""
        d = diag[diag.index.isin(bd)]
        pri = [c for c in cfg.priority if abs(cfg.weights.get(c, 0.0)) > 0]
        primary = pri[0] if pri else None
        s_b = sig[sig.index.get_level_values(0).isin(bd)]
        avg_w = s_b.groupby(level=1).mean() if not s_b.empty else pd.Series(dtype=float)
        daily = []
        for day in bd:
            if day not in d.index:
                continue
            row = d.loc[day]
            mz = float(row[f"meanz_{primary}"]) if primary and f"meanz_{primary}" in d else 0.0
            daily.append({"date": str(pd.Timestamp(day).date()), "primary_tool": primary,
                          "primary_meanz": mz, "confirm_pass_frac": float(row["confirm_pass_frac"]),
                          "high_vol_frac": float(row["high_vol_frac"]),
                          "score_mean": float(row["score_mean"]), "score_std": float(row["score_std"])})
        return {
            "round": k, "n_days": int(len(d)), "primary_tool": primary,
            "weights": {c: float(cfg.weights.get(c, 0.0)) for c in INDICATORS},
            "priority": list(cfg.priority),
            "tool_usage": {c: float(d[f"absz_{c}"].mean()) if f"absz_{c}" in d else 0.0
                           for c in INDICATORS},
            "confirm_pass_frac": float(d["confirm_pass_frac"].mean()) if len(d) else 0.0,
            "high_vol_frac": float(d["high_vol_frac"].mean()) if len(d) else 0.0,
            "score_mean": float(d["score_mean"].mean()) if len(d) else 0.0,
            "score_std": float(d["score_std"].mean()) if len(d) else 0.0,
            "weights_avg": {str(s): float(v) for s, v in avg_w.items()},
            "daily": daily,
        }

    @staticmethod
    def _format_trace(trace: Dict) -> str:
        """把轨迹压成适合 LLM 上下文的摘要（论文也面临轨迹超长问题）。"""
        tu = sorted(trace["tool_usage"].items(), key=lambda kv: -kv[1])
        lines = [
            f"批次 round={trace['round']} 交易日数={trace['n_days']} 主证据工具={trace['primary_tool']}",
            "工具使用(平均|z|降序): " + ", ".join(f"{k}={v:.2f}" for k, v in tu),
            f"校验确认通过率={trace['confirm_pass_frac']:.2f} 高波动占比={trace['high_vol_frac']:.2f}",
            f"中间信号 score_mean={trace['score_mean']:.3f} score_std={trace['score_std']:.3f}",
            "逐日诊断:",
        ]
        lines += [f"  {r['date']} {r['primary_tool']}={r['primary_meanz']:+.2f} "
                  f"confirm={r['confirm_pass_frac']:.2f} highvol={r['high_vol_frac']:.2f} "
                  f"score_mean={r['score_mean']:+.3f}" for r in trace["daily"]]
        top = sorted(trace["weights_avg"].items(), key=lambda kv: -abs(kv[1]))[:6]
        if top:
            lines.append("最终仓位权重(batch均值, top按|w|): "
                         + ", ".join(f"{s}={v:+.3f}" for s, v in top))
        return "\n".join(lines)

    def _policy_user(self, policy_text: str, trace: Dict, ret: Dict, regime: str) -> str:
        parts = [
            f"当前策略 π:\n{policy_text}",
            f"市场体制标签: {regime}",
            "本批次已实现收益反馈: "
            f"日均={ret['mean']:+.4f} 累计={ret['cum']:+.4f} 日波动={ret['vol']:.4f} 胜率={ret['win']:.2f}",
        ]
        if self.use_trace:  # 消融开关：关闭时 Policy Agent 看不到轨迹
            parts.append("本批次决策轨迹摘要:\n" + self._format_trace(trace))
        else:
            parts.append("本批次决策轨迹: 不可用（消融设置：仅使用已实现收益反馈）")
        parts.append("请基于以上证据重写策略：只修改有证据支持的规则，保留仍然有效的规则。")
        return "\n\n".join(parts)

    # -- 策略演化外环：仅在 train+val 上迭代；test 期零 LLM --
    def fit(self, ds: Dataset) -> "EvolveTrade":
        self.llm = TextLLM(tag="evolve_trade", temperature=0.4, max_tokens=1800)
        self.policy_log, self.trace_log = [], []
        self.policy_text = INITIAL_POLICY
        cfg, _ = compile_policy(INITIAL_POLICY, default_config())
        if not self.llm.available:
            self.degraded = True
            self.fidelity = "llm_replaced_by_rule"
            self.notes += "；无 LLM 凭据，策略演化降级为固定初始策略"
            self.final_cfg, self.final_policy_text = cfg, self.policy_text
            return self

        ind = self._indicator_panel(ds, ds.dates_through("validation"))
        ret_val = self._val_internal_returns(ds)
        val = ds.val_dates
        starts = np.linspace(0, len(val), max(1, self.n_rounds) + 1).astype(int)
        for k in range(max(1, self.n_rounds)):
            bd = val[starts[k]:starts[k + 1]]
            if len(bd) == 0:
                continue
            sig, diag = self._evaluate_policy(ind, cfg)
            ret_bd = ret_val[ret_val.index.get_level_values(0).isin(bd)]
            daily = self._portfolio_return(sig[sig.index.get_level_values(0).isin(bd)], ret_bd)
            trace = self._build_trace(k, bd, cfg, sig, diag)
            trace["realized"] = self._summarize_returns(daily)
            self.trace_log.append(trace)
            user = self._policy_user(self.policy_text, trace, trace["realized"],
                                     self._regime_label(ret_bd))
            try:  # Policy Agent 真实 LLM 调用：约 1 次/轮
                new_text = self.llm.complete(POLICY_SYSTEM, user,
                                             purpose=f"policy_refine_round_{k}")
            except LLMUnavailable as e:  # 显式降级：冻结当前策略并标注 fidelity
                self.degraded = True
                self.fidelity = "llm_replaced_by_rule"
                self.notes += f"；第{k}轮 LLM 调用失败({type(e).__name__})，冻结当前策略"
                break
            cfg, warns = compile_policy(new_text, cfg)
            self.policy_log.append({"round": k, "policy": new_text, "warnings": warns,
                                    "weights": dict(cfg.weights), "priority": list(cfg.priority)})
            self.policy_text = new_text
        self.final_cfg, self.final_policy_text = cfg, self.policy_text
        return self

    # -- 冻结策略的确定性执行：零 LLM、零 test 泄漏 --
    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        if self.final_cfg is None:
            raise RuntimeError("必须先用 train+val 调用 fit()，再 produce_signal()")
        ind = self._indicator_panel(ds, ds.dates_through(split))
        sig, _ = self._evaluate_policy(ind, self.final_cfg)
        target = ds._dates_of(split)
        out = sig[sig.index.get_level_values(0).isin(target)]
        return out.replace([np.inf, -np.inf], 0.0).fillna(0.0)
