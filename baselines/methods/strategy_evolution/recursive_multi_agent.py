"""
RMATS（11）递归多智能体交易系统复现。

论文：Recursive Multi-Agent Trading System: Iterative Optimized Portfolio
      Strategy Under Geopolitical Uncertainty（arXiv:2605.25311）。

一、论文核心机制（下称“本复现怎么做”逐条对应，系数均已用 grep 在论文抽取文本核对）：
  1. 四个专家 agent（Sentiment / Report / Analysis / Risk），每个产出权重 w_i ∈ Δⁿ
     与置信度 c_i，以及自然语言/结构化信号（AgentMessage，Eq.6）。
  2. Manager 用「置信度 × 健康分」加权均值递归聚合（Eq.7）：
        w̄ = Σ_i (c_i·H_i·w_i) / Σ_i (c_i·H_i)
     迭代直到 ‖w̄(r+1) − w̄(r)‖₂ < ε = 0.005（Eq.8，论文核实）。
  3. 健康分（Eq.1）：H_i = 0.25·(A_i + S_i + R_i) − 0.25·L_i；论文取
     α=β=γ=δ=0.25、等权（论文 3.1 节“equal weights”）。
  4. 三触发熔断器（Eq.5）：CB = 1[DD<−6%] ∨ 1[GRS>0.52] ∨ 1[σ>1.8·σ̂₂₅₂]。
  5. 约束均值-方差优化（Eq.10）：max_w μᵀw − λ_MV·wᵀΣw，λ_MV=2，
     约束 ‖w‖₁≤L_max、w_s≤c_s、wᵀg(t)≤γ_geo，γ_geo 随 GRS 从 0.65 收紧到 0.45。

二、本复现怎么做（价格代理；本数据为 15 只 CSI300 日频股票，无 GPR/新闻/跨资产 ETF）：
  - 专家权重在单纯形 Δⁿ 上（论文 Eq.6 明确 w_i∈Δⁿ），最终信号即组合权重。
  - Sentiment：论文用 Caldara–Iacoviello GPR 指数 + 五分项 GRS。本复现无 GPR，
    五分项（VIX/防御轮动/黄金溢价/EM 压力/债市避险）在此面板不存在，
    替换为 5 个价格类风险代理：已实现波动率 / 20 日回撤 / 截面离散度 /
    相关性冲击 / 成交量冲击，权重沿用论文 0.30/0.20/0.20/0.15/0.15。
    GRS 高→低波动防御倾斜。
  - Report：照抄论文公式 w ∝ 1/σ + 0.12·m̃（252 日动量 m̃），c_report=0.52。
  - Analysis：论文为三状态 HMM（bull/bear/stress）+ Kalman 融合。本复现无 hmmlearn
    依赖且论文未给状态参数，用价格 regime（市场短/长期波动比）确定性代理，
    regime 内偏动量、压力下偏低波动。**不声称使用 HMM**。
  - Risk：论文用 EWMA 动态协方差 + CVaR。本复现用滚动 CVaR（5% 尾损失）倾斜，
    协方差用 EWMA（论文引 [27]）。
  - 健康分 A/S/R/L 的“自适应归一化”论文未给 → 本复现自定：各有界 squash 到 [0,1]
    后等权，并整体平移保证 H∈[0,1]（详见 _unit / fit）。
  - 熔断触发后的权重论文未规定 → 本复现自定“按风险严重度向低波动防御组合渐变”
    （graduated，呼应论文讨论中对 GPR 规则法“binary 100% defensive”的对比）。
  - MVO 的 μ 论文未给 → 本复现用聚合权重 w̄ 作期望收益代理（使 MVO 成为 w̄ 附近的
    约束投影）；Σ 用 EWMA 半衰期 60 日；约束集合（Σw=1, w≥0, w_i≤0.30, wᵀg≤γ_geo）
    为本文自定，因论文只写 ‖w‖₁≤L_max、w_s≤c_s、wᵀg≤γ_geo 而未给具体数值。

三、未复现及原因：
  - **不做任何强化学习训练**：论文正文没有策略梯度 / Q-learning / 价值网络 / 训练循环，
    Eq.9 的 R = r − 0.8σ − 1.5·max(0,DD−θ) 只是“声明的标量目标”，DQN 仅作对比 baseline。
    本复现因此完全不使用该 reward（既不训练也不排序），fidelity 不受影响。
  - 未复现 Caldara–Iacoviello GPR 月度指数（需外部数据源）、FinBERT 文本推理
    （论文列为 future work）、24 ETF 跨资产宇宙（本数据仅 15 只 A 股）、Kalman 融合与 HMM。
  - 论文是月度再平衡 / 812 日美股 ETF；本框架是日频 A 股横截面信号，口径不可对齐。

四、LLM 多智能体仲裁层（本复现新增；论文 RMATS 自身声明用确定性信号生成器、非 LLM 推理）：
  - 仓库审计要求「多智能体仲裁」必须有真实 LLM 参与，故 fit() 在 train+val 上做
    L=2 轮仲裁（每轮 5 次调用，共 10 次，tag="rmats" 磁盘缓存，重跑零成本）：
      * 4 次专家调用：每个专家只看到自己在 train+val 的紧凑诊断 JSON（val IC/ICIR、
        多空年化/Sharpe/回撤、与共识的 L1 分歧、递归平均轮数/收敛率、val 平均 GRS、
        当前确定性 c 与 H），输出 confidence_tilt∈[-0.5,0.5] 与 regime_pref∈[-1,1]；
      * 1 次 Manager 调用：看到 4 份提案 + 共识状态，输出各专家 conf_scale∈[0.5,1.5]、
        γ_geo 平移 geo_tilt∈[-0.10,0.10]、熔断防御倾斜偏置 defensive_bias∈[0,0.20]。
  - 冻结产物：self._llm_conf / _llm_regime_pref / _llm_geo_tilt / _llm_def_bias。
    produce_signal() 只确定性读取（零 LLM 调用），有效置信度
    c_i^eff(g) = clip(c_i · scale_i · (1 + 0.25·pref_i·(2g−1)), 0.05, 1.0)。
  - **仍是确定性代理的部分**：四专家原始权重公式（GRS 五分项价格代理、Report
    1/σ+0.12m̃、Analysis 价格 regime、Risk 滚动 CVaR）、健康分 H_i、Eq.7 递归聚合、
    三触发熔断阈值、约束 MVO —— LLM 只做「参数级」仲裁（置信度缩放 / regime 偏好 /
    γ_geo 平移 / 防御偏置），不产出原始权重向量，不替换任何论文机制。
  - 论文 Table 1 中 RMATS 的 LLM reasoning 一栏即为 "Proxy"，且正文明确 "not LLM
    inference"；本 LLM 层是仓库审计规则补充的仲裁参与，不是论文原文机制（notes 已声明）。
  - 无 LLM 凭据或调用失败：整层降级为恒等参数（tilt=0、scale=1、geo_tilt=0、
    def_bias=0），即精确回到纯确定性复现，并把 fidelity 改标 llm_replaced_by_rule。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import softmax

# 允许直接 `python recursive_multi_agent.py` 自测（被 run_all.py 导入时该路径已在 sys.path）
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.data import Dataset
from core.interface import BaselineMethod
from core.evaluator import cross_section_ic_series, long_short_backtest
from core.llm import LLMUnavailable, get_text_llm  # noqa: E402

try:  # 包内导入（run_all / audit 以包方式加载）
    from .sharp_rubric import parse_json_object
except ImportError:  # 直接 `python recursive_multi_agent.py` 自测时无包上下文
    from sharp_rubric import parse_json_object

# ---------------------------------------------------------------------------
# 论文核实过的超参（arXiv:2605.25311，已逐条 grep 核对）
# ---------------------------------------------------------------------------
HEALTH_W = 0.25            # Eq.1：α=β=γ=δ=0.25（论文 3.1 节 equal weights）
EPS_CONV = 0.005           # Eq.8 收敛判据
THETA_DD = -0.06           # Eq.5：θ_dd = −6%（20 日累计收益）
THETA_GEO = 0.52           # Eq.5：θ_geo = GPR 60 分位
THETA_VOL_MULT = 1.8       # Eq.5：θ_vol = 1.8·σ̂₂₅₂
LAMBDA_MV = 2.0            # Eq.10：λ_MV = 2
GAMMA_GEO_LOW_RISK = 0.65  # Eq.10：低风险 γ_geo
GAMMA_GEO_HIGH_RISK = 0.45 # Eq.10：高风险 γ_geo
REPORT_TILT = 0.12         # Report：w ∝ 1/σ + 0.12·m̃
C_REPORT = 0.52            # Report 固定置信度 c_rep
GRS_WEIGHTS = (0.30, 0.20, 0.20, 0.15, 0.15)  # 5 分项权重

# ---------------------------------------------------------------------------
# 论文未指定、由本复现选定并标注的常数
# ---------------------------------------------------------------------------
PER_ASSET_CAP = 0.30        # Eq.10 个股权重上限 c_s（论文未给数值）
EWMA_HALFLIFE = 60          # Eq.10 Σ 的 EWMA 半衰期（论文引 EWMA，未给窗口）
COV_WINDOW = 250            # EWMA 协方差最长回看窗口
CVAR_Q = 0.05               # Risk agent CVaR 置信水平（论文未给）
MAX_ROUNDS = 8              # 论文最大 3 轮；本复现收敛规则的兜底上限
BLEND_RHO = 0.5             # agent→共识的修订速率（论文未给 agent 修订式）
REGIME_VOL_MULT = 1.5       # Analysis regime 阈值（论文用 HMM，未给阈值）
DEFENSIVE_ALPHA_MIN = 0.30  # CB 触发后的最小防御倾斜（论文未给具体权重）

# ---------------------------------------------------------------------------
# LLM 多智能体仲裁层（本复现新增）：只在 fit 调用，produce_signal 零 LLM
# ---------------------------------------------------------------------------
LLM_ROUNDS = 2              # 仲裁轮数：每轮 4 专家 + 1 Manager = 5 次 LLM 调用
EXPERT_TILT_MAX = 0.5       # 专家 confidence_tilt 上限：c_i·(1+tilt)
CONF_SCALE_MIN = 0.5        # Manager 置信度缩放下限
CONF_SCALE_MAX = 1.5        # Manager 置信度缩放上限
REGIME_PREF_SCALE = 0.25    # regime 偏好对有效置信度的影响幅度（本复现自定）
GEO_TILT_MAX = 0.10         # Manager 对 γ_geo 的平移上限（仍夹在论文 0.65→0.45 内）
DEF_BIAS_MAX = 0.20         # Manager 对熔断防御倾斜 α 的偏置上限
LLM_DIAG_DAYS = 24          # 递归诊断采样日数（控制 prompt 体积与运行时）

_AGENTS = ("sentiment", "report", "analysis", "risk")

_EXPERT_SYSTEM = (
    "你是 RMATS 递归多智能体交易系统中的专家智能体（Sentiment / Report / Analysis / Risk 之一）。"
    "输入是你在 train+val 上的确定性诊断、当前确定性置信度与健康分、以及 Eq.7 递归聚合的收敛统计。"
    "你的任务：基于自身证据，对本 agent 的置信度提出乘性微调，并给出 regime 偏好——"
    "regime_pref>0 表示压力期（GRS 高）应更信任你的建议，<0 表示常态期更可信。"
    "只输出一个 JSON 对象，不要解释或 markdown。"
)

_MANAGER_SYSTEM = (
    "你是 RMATS 的 Manager 智能体，负责仲裁四个专家智能体（Sentiment/Report/Analysis/Risk）"
    "提交的置信度微调与 regime 偏好。你会看到四份提案与共识状态（递归轮数、分歧、val 平均 GRS、"
    "确定性置信度 c 与健康分 H）。你的任务：输出各专家最终置信度缩放、γ_geo 平移量、"
    "熔断后防御倾斜偏置。只输出一个 JSON 对象，不要解释或 markdown。"
)


def _xsz(s: pd.Series) -> pd.Series:
    """逐日横截面 z-score（无未来函数）。"""
    return s.groupby(level=0).transform(
        lambda g: (g - g.mean()) / g.std() if g.std() else g * 0.0)


def _unit(x: float, scale: float) -> float:
    """把无界指标 squash 到 [0,1]；论文未给 A/S/R/L 归一化公式，本复现自定。"""
    return float(0.5 * (1.0 + np.tanh(x / scale)))


def _to_simplex(score: np.ndarray, temp: float = 0.7) -> np.ndarray:
    """分数向量 → 单纯形 Δⁿ（softmax）。论文只说 w_i∈Δⁿ，映射式未给，本复现自定。"""
    s = np.nan_to_num(np.asarray(score, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    if s.size == 0:
        return s
    if np.allclose(s, s[0]):
        return np.full(s.size, 1.0 / s.size)
    return softmax(s / temp)


def _roll_cvar(a: np.ndarray) -> float:
    """滚动窗口的 q 分位均值（CVaR 代理）：低于 q 分位的收益之均值。"""
    v = a[np.isfinite(a)]
    if v.size < 20:
        return np.nan
    q = np.quantile(v, CVAR_Q)
    tail = v[v <= q]
    return float(tail.mean()) if tail.size else np.nan


def _avg_pairwise_corr(ret_wide: pd.DataFrame, win: int) -> pd.Series:
    """滚动 win 日资产两两平均相关系数（相关性冲击代理）。"""
    vals: List[float] = []
    idx = ret_wide.index
    for i in range(len(idx)):
        if i + 1 < win:
            vals.append(np.nan)
            continue
        sub = ret_wide.iloc[i + 1 - win:i + 1]
        c = sub.corr().to_numpy(dtype=float)
        n = c.shape[0]
        off = c[~np.eye(n, dtype=bool)]
        off = off[np.isfinite(off)]
        vals.append(float(off.mean()) if off.size else np.nan)
    return pd.Series(vals, index=idx)


class RecursiveMultiAgent(BaselineMethod):
    """RMATS 四专家 + LLM 参数级仲裁 + 健康分递归聚合 + 三触发熔断 + 约束 MVO。无 RL 训练。

    LLM 只在 fit() 参与仲裁（2 轮 × 4 专家 + 1 Manager = 10 次调用），产出粗粒度参数
    （置信度 tilt/scale、regime 偏好、γ_geo 平移、防御偏置）并冻结；produce_signal()
    纯确定性读取冻结参数，零 LLM 调用。专家原始权重公式仍是确定性价格代理。
    """

    def __init__(self) -> None:
        self.name = "recursive_multi_agent"
        self.category = "strategy_evolution"
        self.paper_id = "11"
        self.fidelity = "faithful_core"
        self.notes = (
            "四专家(Sentiment/Report/Analysis/Risk)+健康分+置信度加权递归聚合(ε=0.005)"
            "+三触发熔断(DD<-6%/GRS>0.52/sigma>1.8*sigma252)+约束MVO(λ_MV=2,γ_geo 0.65→0.45)"
            "忠实；LLM仲裁为参数级、不产出原始权重：fit 做 2 轮(每轮 4 专家+1 Manager)=10 次"
            "真实LLM调用(tag=rmats)，专家按自身 train+val 诊断输出 confidence_tilt∈[-0.5,0.5]"
            "与 regime_pref∈[-1,1]，Manager 仲裁输出 conf_scale∈[0.5,1.5]、γ_geo 平移∈[-0.10,0.10]、"
            "熔断防御偏置∈[0,0.20]；冻结于 _llm_conf/_llm_regime_pref/_llm_geo_tilt/_llm_def_bias，"
            "produce_signal 零LLM调用。GRS五分项用价格风险代理(波动/回撤/离散度/相关/量冲击)替代论文"
            "VIX/黄金/EM/债市；Analysis用价格regime代理论文HMM+Kalman(未声称HMM)；CB后权重与A/S/R/L"
            "归一化为本文自定替代。论文RMATS自身声明用确定性信号生成器、非LLM推理(Table1 LLM reasoning=Proxy)，"
            "本LLM仲裁层为仓库审计要求补充，非论文原文机制。论文4.1节定义了风险感知reward"
            "(Eq.9, λ1=0.8, λ2=1.5)且关键词含reinforcement learning，但全文未给出梯度训练过程"
            "(无policy network/actor-critic/参数更新)，DQN仅作对照baseline；故本复现以Eq.10约束MVO"
            "为实际优化器，不用Eq.9做训练。无LLM凭据/调用失败时降级为恒等参数并改标 "
            "fidelity=llm_replaced_by_rule。"
        )
        # fit() 冻结的产物
        self._symbols: List[str] = []
        self._health: Dict[str, float] = {}
        self._conf: Dict[str, float] = {}
        self._grs_bounds: List[Tuple[float, float]] = []
        self._g_bounds: Tuple[float, float] = (0.0, 1.0)
        # LLM 仲裁层：fit 期调用；produce_signal 期只读下面冻结的 _llm_* 参数
        self.llm = get_text_llm(tag="rmats", temperature=0.3, max_tokens=1200)
        self.degraded = False
        self.llm_rounds = LLM_ROUNDS
        self.llm_log: List[Dict[str, Any]] = []
        self._llm_conf: Dict[str, float] = {a: 1.0 for a in _AGENTS}
        self._llm_regime_pref: Dict[str, float] = {a: 0.0 for a in _AGENTS}
        self._llm_geo_tilt: float = 0.0
        self._llm_def_bias: float = 0.0
        if not self.llm.available:  # 无凭据：立即如实降级标注（幂等）
            self._degrade()

    # ------------------------------------------------------------------
    # 特征与市场风险序列
    # ------------------------------------------------------------------
    def _build(self, panel: pd.DataFrame
               ) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
        """构造个股特征与市场级风险序列（全部滚动，无未来函数）。"""
        syms = sorted(panel.index.get_level_values(1).unique())
        ret = panel["ret"]
        close = panel["close"]
        volume = panel["volume"]

        feat = pd.DataFrame(index=panel.index)
        feat["vol60"] = ret.groupby(level=1).transform(
            lambda s: s.rolling(60).std() * np.sqrt(252.0))
        feat["dvol60"] = ret.clip(upper=0).groupby(level=1).transform(
            lambda s: s.rolling(60).std() * np.sqrt(252.0))
        feat["mom252"] = ret.groupby(level=1).transform(
            lambda s: s.rolling(252).mean() * 252.0)
        feat["mom10"] = close.groupby(level=1).transform(
            lambda s: s / s.shift(10) - 1.0)
        m5 = ret.groupby(level=1).transform(lambda s: s.rolling(5).mean())
        m60 = ret.groupby(level=1).transform(lambda s: s.rolling(60).mean())
        sd60 = ret.groupby(level=1).transform(lambda s: s.rolling(60).std())
        feat["es"] = (m5 - m60) / sd60.replace(0.0, np.nan)   # 论文盈余惊喜代理
        feat["cvar5"] = ret.groupby(level=1).transform(
            lambda s: s.rolling(252).apply(_roll_cvar, raw=True))

        # 市场级序列（等权）
        mr = ret.groupby(level=0).mean()
        mkt = pd.DataFrame(index=mr.index)
        mkt["ret"] = mr
        mkt["vol20"] = mr.rolling(20).std() * np.sqrt(252.0)
        mkt["vol252"] = mr.rolling(252).std() * np.sqrt(252.0)
        mkt["dd20"] = (1.0 + mr).rolling(20).apply(np.prod, raw=True) - 1.0
        mkt["disp"] = ret.groupby(level=0).std()
        mkt["corr"] = _avg_pairwise_corr(
            panel["ret"].unstack(level=1).sort_index(), 60)
        totvol = volume.groupby(level=0).sum()
        mkt["vshock"] = totvol / totvol.rolling(60).mean()
        return feat, mkt, syms

    def _grs_raw(self, mkt: pd.DataFrame) -> pd.DataFrame:
        """GRS 五价格代理原始值（尚未归一化，越大越危险）。"""
        return pd.DataFrame({
            "vol": mkt["vol20"],       # ← 论文 VIX
            "dd": -mkt["dd20"],        # ← 论文防御轮动（回撤越大越危险）
            "disp": mkt["disp"],       # ← 论文黄金溢价（截面离散度）
            "corr": mkt["corr"],       # ← 论文 EM 压力（相关性冲击）
            "vshock": mkt["vshock"],   # ← 论文债市避险（成交量冲击）
        })

    def _grs_norm(self, raw: pd.DataFrame) -> pd.Series:
        """用 fit 冻结的 train+val 边界做 min-max 归一化后按论文权重合成 GRS∈[0,1]。"""
        if not self._grs_bounds:
            raise RuntimeError("必须先调用 fit() 以标定 GRS 归一化边界")
        comp = np.zeros((len(raw), len(self._grs_bounds)))
        for k, (lo, hi) in enumerate(self._grs_bounds):
            col = raw.iloc[:, k].to_numpy(dtype=float)
            comp[:, k] = np.clip((col - lo) / (hi - lo), 0.0, 1.0) if hi > lo else 0.5
        return pd.Series(comp @ np.asarray(GRS_WEIGHTS), index=raw.index)

    def _agent_scores(self, feat: pd.DataFrame, mkt: pd.DataFrame,
                      grs: pd.Series) -> Dict[str, pd.Series]:
        """四个专家的原始分数（尚未映射到单纯形）。"""
        zv = _xsz(feat["vol60"])
        zd = _xsz(feat["dvol60"])
        zm = _xsz(feat["mom252"])
        z1 = _xsz(feat["mom10"])
        zc = _xsz(feat["cvar5"])
        zi = _xsz(1.0 / feat["vol60"])
        d0 = feat.index.get_level_values(0)
        gdev = pd.Series(grs.reindex(d0).to_numpy(), index=feat.index)
        ratio = (mkt["vol20"] / mkt["vol252"]).reindex(d0).to_numpy(dtype=float)
        stress = pd.Series(
            np.clip((ratio - 1.0) / (REGIME_VOL_MULT - 1.0), 0.0, 1.0),
            index=feat.index)
        return {
            # GRS 高→防御(低波动)；GRS 低→risk-on
            "sentiment": (-zv) * (gdev - 0.5) * 2.0,
            # 论文 Report 公式：1/σ + 0.12·m̃
            "report": zi + REPORT_TILT * zm,
            # 价格 regime 代理 HMM：常态偏动量、压力偏低波动
            "analysis": z1 * (1.0 - stress) - zd * stress,
            # CVaR 尾损失越低权重越高
            "risk": -zc,
        }

    @staticmethod
    def _wide(s: pd.Series, syms: List[str]) -> pd.DataFrame:
        return s.unstack(level=1).reindex(columns=syms).sort_index()

    @staticmethod
    def _aggregate(props: Dict[str, np.ndarray], conf: Dict[str, float],
                   health: Dict[str, float]) -> np.ndarray:
        """Eq.7：w̄ = Σ c_i H_i w_i / Σ c_i H_i。"""
        num = np.zeros_like(next(iter(props.values())))
        den = 0.0
        for a in _AGENTS:
            ch = conf[a] * health[a]
            num = num + ch * props[a]
            den += ch
        if den <= 1e-12:
            return np.full(num.size, 1.0 / num.size)
        return num / den

    def _ewma_cov(self, ret_wide: pd.DataFrame, d: pd.Timestamp,
                  syms: List[str]) -> np.ndarray:
        """EWMA 动态协方差（论文 Eq.4 引 [27]；半衰期为本复现选择）。"""
        n = len(syms)
        pos = ret_wide.index.get_loc(d)
        win = min(COV_WINDOW, pos + 1)
        if win < 20:
            return np.eye(n) * 1e-4
        sub = ret_wide.iloc[pos + 1 - win:pos + 1].to_numpy(dtype=float)
        sub = sub[np.isfinite(sub).all(axis=1)]
        if len(sub) < 20:
            return np.eye(n) * 1e-4
        k = np.arange(len(sub))[::-1]                      # 0 = 最近
        lam = 0.5 ** (k / EWMA_HALFLIFE)
        lam = lam / lam.sum()
        mean = (lam[:, None] * sub).sum(axis=0)
        x = sub - mean
        cov = (x * lam[:, None]).T @ x
        return cov + np.eye(n) * 1e-6

    @staticmethod
    def _mvo(mu: np.ndarray, sigma: np.ndarray, g: np.ndarray,
             gamma: float, x0: np.ndarray) -> np.ndarray:
        """Eq.10 约束 MVO：min λ_MV·wᵀΣw − μᵀw。
        约束：Σw=1、w≥0（Δⁿ）、w_i≤c_s、wᵀg≤γ_geo。SLSQP 失败则投影降级。"""
        n = mu.size
        fun = lambda x: LAMBDA_MV * float(x @ sigma @ x) - float(mu @ x)
        jac = lambda x: 2.0 * LAMBDA_MV * (sigma @ x) - mu
        cons = [
            {"type": "eq", "fun": lambda x: float(x.sum()) - 1.0,
             "jac": lambda x: np.ones(n)},
            {"type": "ineq", "fun": lambda x: float(gamma - g @ x),
             "jac": lambda x: -g},
        ]
        try:
            res = minimize(fun, x0, jac=jac, method="SLSQP",
                           bounds=[(0.0, PER_ASSET_CAP)] * n, constraints=cons,
                           options={"maxiter": 80, "ftol": 1e-8})
            x = np.clip(res.x, 0.0, PER_ASSET_CAP)
            tot = float(x.sum())
            return x / tot if tot > 0 else x0
        except Exception:
            # 明确降级：QP 失败时把 w̄ 直接投影到约束集（裁剪后归一化）
            x = np.clip(x0, 0.0, PER_ASSET_CAP)
            tot = float(x.sum())
            return x / tot if tot > 0 else np.full(n, 1.0 / n)

    # ------------------------------------------------------------------
    # LLM 多智能体仲裁（仅在 fit 调用；produce_signal 只读冻结参数、零 LLM）
    # ------------------------------------------------------------------
    @staticmethod
    def _fnum(v: Any, default: float, lo: float, hi: float) -> float:
        """把 LLM 输出里的任意值安全转成 [lo,hi] 浮点；非法/非有限则返回 default。"""
        try:
            x = float(v)
        except (TypeError, ValueError):
            return float(default)
        if not np.isfinite(x):
            return float(default)
        return float(np.clip(x, lo, hi))

    @staticmethod
    def _tilted_conf(base: float, scale: float, regime_pref: float, gval: float) -> float:
        """有效置信度：c^eff = clip(c·scale·(1 + REGIME_PREF_SCALE·pref·(2g−1)), 0.05, 1.0)。"""
        regime_mult = 1.0 + REGIME_PREF_SCALE * float(regime_pref) * (2.0 * gval - 1.0)
        return float(np.clip(float(base) * float(scale) * regime_mult, 0.05, 1.0))

    def _effective_conf(self, a: str, gval: float) -> float:
        """produce_signal 专用：读冻结的 LLM 仲裁参数，确定性算有效置信度（零 LLM）。"""
        return self._tilted_conf(self._conf[a], self._llm_conf.get(a, 1.0),
                                 self._llm_regime_pref.get(a, 0.0), gval)

    def _degrade(self) -> None:
        """LLM 不可用/调用失败：显式降级为恒等参数并如实改标 fidelity/notes（幂等）。"""
        self.degraded = True
        if self.fidelity != "llm_replaced_by_rule":
            self.fidelity = "llm_replaced_by_rule"
            self.notes = ("LLM 后端不可用/调用失败，专家与 Manager 仲裁降级为确定性恒等参数；"
                          + self.notes)

    @staticmethod
    def _expert_fallback() -> Dict[str, Any]:
        """确定性回退：置信度不动（tilt=0），无 regime 偏好。"""
        return {"confidence_tilt": 0.0, "regime_pref": 0.0,
                "rationale": "确定性回退：LLM 不可用/输出不可解析，置信度与 regime 偏好不动",
                "source": "fallback"}

    @staticmethod
    def _manager_fallback() -> Dict[str, Any]:
        """确定性回退：不叠加任何仲裁偏移（等于纯确定性基线行为）。"""
        return {"conf_scale": {a: 1.0 for a in _AGENTS}, "geo_tilt": 0.0,
                "defensive_bias": 0.0, "source": "fallback",
                "rationale": "确定性回退：LLM 不可用/输出不可解析，不叠加任何仲裁偏移"}

    def _expert_proposal(self, agent: str, bundle: Dict[str, Any],
                         round_idx: int) -> Dict[str, Any]:
        """一次专家 LLM 调用：输出 confidence_tilt / regime_pref；失败走确定性回退。"""
        if self.degraded:
            return self._expert_fallback()
        user = (
            f"当前是第 {round_idx + 1}/{self.llm_rounds} 轮仲裁，你是专家 agent = {agent}。\n"
            "你在 train+val 上的确定性诊断：\n"
            + json.dumps(bundle, ensure_ascii=False, sort_keys=True)
            + "\n\n请输出 JSON："
            + '{"confidence_tilt": <[-0.5,0.5] 浮点>, "regime_pref": <[-1,1] 浮点>, '
            + '"rationale": "<一句话诊断>"}。\n'
            + "confidence_tilt 用于 c_i ← clip(c_i·(1+tilt), 0.05, 1.0)；"
            + "regime_pref>0 表示压力期（GRS 高）应更信任你的建议，<0 表示常态期更可信。"
        )
        try:
            text = self.llm.complete(_EXPERT_SYSTEM, user,
                                     purpose=f"rmats_expert_{agent}_round_{round_idx + 1}")
        except LLMUnavailable:
            self._degrade()
            return self._expert_fallback()
        obj = parse_json_object(text)
        if obj is None:  # 畸形 JSON：该次调用安全回退，不影响其他专家
            return self._expert_fallback()
        return {
            "confidence_tilt": self._fnum(obj.get("confidence_tilt"), 0.0,
                                          -EXPERT_TILT_MAX, EXPERT_TILT_MAX),
            "regime_pref": self._fnum(obj.get("regime_pref"), 0.0, -1.0, 1.0),
            "rationale": str(obj.get("rationale", ""))[:200],
            "source": "llm",
        }

    def _manager_arbitration(self, proposals: Dict[str, Dict[str, Any]],
                             consensus: Dict[str, Any], round_idx: int) -> Dict[str, Any]:
        """一次 Manager LLM 调用：仲裁四份提案，输出 conf_scale / geo_tilt / def_bias。"""
        if self.degraded:
            return self._manager_fallback()
        user = (
            f"当前是第 {round_idx + 1}/{self.llm_rounds} 轮仲裁。\n"
            "四个专家本轮提案：\n"
            + json.dumps(proposals, ensure_ascii=False, sort_keys=True)
            + "\n\n共识状态：\n"
            + json.dumps(consensus, ensure_ascii=False, sort_keys=True)
            + "\n\n请仲裁输出 JSON："
            + '{"conf_scale": {"sentiment": <[0.5,1.5]>, "report": <[0.5,1.5]>, '
            + '"analysis": <[0.5,1.5]>, "risk": <[0.5,1.5]>}, '
            + '"geo_tilt": <[-0.10,0.10] 浮点>, "defensive_bias": <[0,0.20] 浮点>, '
            + '"rationale": "<一句话>"}。\n'
            + "约束：conf_scale 乘到各专家确定性置信度上；geo_tilt 在论文 γ_geo 0.65→0.45 "
            + "区间内平移；defensive_bias 仅在熔断触发时叠加到防御倾斜 α。"
        )
        try:
            text = self.llm.complete(_MANAGER_SYSTEM, user,
                                     purpose=f"rmats_manager_round_{round_idx + 1}")
        except LLMUnavailable:
            self._degrade()
            return self._manager_fallback()
        obj = parse_json_object(text)
        if obj is None:
            return self._manager_fallback()
        raw = obj.get("conf_scale", {})
        if not isinstance(raw, dict):
            raw = {}
        return {
            "conf_scale": {a: self._fnum(raw.get(a), 1.0, CONF_SCALE_MIN, CONF_SCALE_MAX)
                           for a in _AGENTS},
            "geo_tilt": self._fnum(obj.get("geo_tilt"), 0.0, -GEO_TILT_MAX, GEO_TILT_MAX),
            "defensive_bias": self._fnum(obj.get("defensive_bias"), 0.0, 0.0, DEF_BIAS_MAX),
            "rationale": str(obj.get("rationale", ""))[:300],
            "source": "llm",
        }

    def _recursion_stats(self, scores: Dict[str, pd.Series], conf: Dict[str, float],
                         health: Dict[str, float], dates: pd.DatetimeIndex,
                         grs: pd.Series, syms: List[str]) -> Dict[str, Any]:
        """在 train+val 采样日上重放 Eq.7/Eq.8 递归，产出各 agent 与共识的分歧及收敛统计。
        只读 train+val 代理分数，供 LLM 诊断用；确定性、无未来函数、零 LLM。"""
        W = {a: self._wide(scores[a], syms) for a in _AGENTS}
        idx = W["report"].index
        use = idx[idx.isin(dates)]
        if len(use) == 0:
            return {"mean_rounds": float(MAX_ROUNDS), "converged_frac": 0.0,
                    "disagreement": {a: 0.0 for a in _AGENTS}, "grs_mean": 0.5}
        if len(use) > LLM_DIAG_DAYS:
            pick = np.linspace(0, len(use) - 1, LLM_DIAG_DAYS).round().astype(int)
            use = use[np.unique(pick)]
        rounds: List[int] = []
        converged: List[float] = []
        dis_sum = {a: 0.0 for a in _AGENTS}
        for d in use:
            raw = {a: W[a].loc[d].to_numpy(dtype=float) for a in _AGENTS}
            props = {a: _to_simplex(raw[a]) for a in _AGENTS}
            wbar = self._aggregate(props, conf, health)
            for a in _AGENTS:
                dis_sum[a] += 0.5 * float(np.abs(props[a] - wbar).sum())
            it_used, conv_flag = MAX_ROUNDS, 0.0
            for it in range(MAX_ROUNDS):
                p_new = {a: (1.0 - BLEND_RHO) * props[a] + BLEND_RHO * wbar
                         for a in _AGENTS}
                c_new = {}
                for a in _AGENTS:
                    dis = 0.5 * float(np.abs(p_new[a] - wbar).sum())
                    c_new[a] = conf[a] * (1.0 - min(1.0, dis))
                wbar_new = self._aggregate(p_new, c_new, health)
                delta = float(np.linalg.norm(wbar_new - wbar))
                props, wbar = p_new, wbar_new
                if delta < EPS_CONV:
                    it_used, conv_flag = it + 1, 1.0
                    break
            rounds.append(it_used)
            converged.append(conv_flag)
        n = float(len(use))
        grs_use = grs[grs.index.isin(dates)] if len(grs) else pd.Series(dtype=float)
        return {
            "mean_rounds": float(np.mean(rounds)),
            "converged_frac": float(np.mean(converged)),
            "disagreement": {a: dis_sum[a] / n for a in _AGENTS},
            "grs_mean": float(grs_use.mean()) if len(grs_use) else 0.5,
        }

    def _arbitrate_llm(self, scores: Dict[str, pd.Series], conf: Dict[str, float],
                       health: Dict[str, float], stats: Dict[str, Dict[str, float]],
                       val_safe: pd.DatetimeIndex, grs: pd.Series,
                       syms: List[str]) -> None:
        """L 轮「4 专家 + 1 Manager」LLM 仲裁，把参数冻结进 self._llm_*。
        输入仅来自 train+val（dates_fit 面板 + val_safe 统计），绝不触碰 test。"""
        conf_scale = {a: 1.0 for a in _AGENTS}
        regime_pref = {a: 0.0 for a in _AGENTS}
        geo_tilt, def_bias = 0.0, 0.0
        val_grs_mean = (float(grs[grs.index.isin(val_safe)].mean())
                        if len(val_safe) else 0.5)
        self.llm_log = []
        if not self.degraded:
            for r in range(self.llm_rounds):
                conf_eff = {a: self._tilted_conf(conf[a], conf_scale[a],
                                                 regime_pref[a], val_grs_mean)
                            for a in _AGENTS}
                rec = self._recursion_stats(scores, conf_eff, health, val_safe, grs, syms)
                proposals: Dict[str, Dict[str, Any]] = {}
                for a in _AGENTS:
                    bundle = {
                        "agent": a, "round": r + 1, "llm_rounds": self.llm_rounds,
                        "deterministic_conf": round(float(conf[a]), 4),
                        "deterministic_health": round(float(health[a]), 4),
                        "val_ic_mean": round(stats[a]["ic"], 4),
                        "val_ic_ir": round(stats[a]["ic_ir"], 4),
                        "val_ls_ann_ret": round(stats[a]["ann"], 4),
                        "val_ls_sharpe": round(stats[a]["sharpe"], 4),
                        "val_ls_mdd": round(stats[a]["mdd"], 4),
                        "agent_consensus_disagreement": round(rec["disagreement"][a], 4),
                        "recursion_mean_rounds": round(rec["mean_rounds"], 3),
                        "recursion_converged_frac": round(rec["converged_frac"], 3),
                        "val_grs_mean": round(val_grs_mean, 4),
                    }
                    proposals[a] = self._expert_proposal(a, bundle, r)
                consensus = {
                    "round": r + 1,
                    "mean_recursion_rounds": round(rec["mean_rounds"], 3),
                    "mean_converged_frac": round(rec["converged_frac"], 3),
                    "mean_disagreement": round(float(np.mean(
                        [rec["disagreement"][a] for a in _AGENTS])), 4),
                    "val_grs_mean": round(val_grs_mean, 4),
                    "deterministic_conf": {a: round(float(conf[a]), 4) for a in _AGENTS},
                    "deterministic_health": {a: round(float(health[a]), 4) for a in _AGENTS},
                }
                arb = self._manager_arbitration(proposals, consensus, r)
                for a in _AGENTS:
                    conf_scale[a] = float(np.clip(
                        conf_scale[a] * (1.0 + float(proposals[a]["confidence_tilt"]))
                        * float(arb["conf_scale"][a]), CONF_SCALE_MIN, CONF_SCALE_MAX))
                    regime_pref[a] = float(proposals[a]["regime_pref"])
                geo_tilt = float(arb["geo_tilt"])
                def_bias = float(arb["defensive_bias"])
                self.llm_log.append({"round": r + 1, "consensus": consensus,
                                     "proposals": proposals, "arbitration": arb})
        self._llm_conf = conf_scale
        self._llm_regime_pref = regime_pref
        self._llm_geo_tilt = geo_tilt
        self._llm_def_bias = def_bias

    # ------------------------------------------------------------------
    # 接口
    # ------------------------------------------------------------------
    def fit(self, ds: Dataset) -> "RecursiveMultiAgent":
        dates_fit = ds.dates_through("validation")           # 仅 train+val，绝不碰 test
        if len(dates_fit) == 0:
            raise ValueError("train+validation 区为空")
        if len(ds.test_dates) > 0:
            assert dates_fit.max() < ds.test_dates.min(), "fit() 不得接触 test 区"
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates_fit)]
        feat, mkt, syms = self._build(panel)

        grs_raw = self._grs_raw(mkt)
        cal_raw = grs_raw[grs_raw.index.isin(dates_fit)]
        self._grs_bounds = [
            (float(cal_raw.iloc[:, k].min()), float(cal_raw.iloc[:, k].max()))
            for k in range(cal_raw.shape[1])
        ]
        dvol_cal = feat["dvol60"][feat.index.get_level_values(0).isin(dates_fit)]
        self._g_bounds = (float(dvol_cal.min()), float(dvol_cal.max()))
        grs = self._grs_norm(grs_raw)
        scores = self._agent_scores(feat, mkt, grs)

        # 末 h 个 val 日的 fwd/next 收益会跨入 test；剔除以保证 fit 完全不接触 test
        val_safe = (ds.val_dates[:-ds.horizon]
                    if len(ds.val_dates) > ds.horizon else ds.val_dates)
        fwd = ds.fwd_ret_on("validation")
        nxt = ds.next_ret_on("validation")
        # 再按 val_safe 截断一次：确保 fwd/nxt 也不含任何跨入 test 的行
        fwd = fwd[fwd.index.get_level_values(0).isin(val_safe)]
        nxt = nxt[nxt.index.get_level_values(0).isin(val_safe)]
        health: Dict[str, float] = {}
        conf: Dict[str, float] = {}
        stats: Dict[str, Dict[str, float]] = {}
        for a in _AGENTS:
            s_val = scores[a][
                scores[a].index.get_level_values(0).isin(val_safe)].dropna()
            pic, _ = cross_section_ic_series(s_val, fwd)
            ic = float(pic.mean()) if len(pic) else 0.0
            ic_sd = float(pic.std()) if len(pic) > 1 else 0.0
            ic_ir = ic / ic_sd if ic_sd > 0 else 0.0
            # 论文只固定 c_report=0.52；其余 agent 置信度本复现按 val IC 自定
            conf[a] = C_REPORT if a == "report" else float(
                np.clip(0.5 + 0.5 * np.tanh(ic / 0.05), 0.05, 1.0))
            net, _, _ = long_short_backtest(s_val, nxt, direction=1)
            ann = sharpe = mdd = 0.0
            if len(net) > 2:
                ann = float(net.mean() * 252.0)
                sd = float(net.std() * np.sqrt(252.0))
                sharpe = ann / sd if sd > 0 else 0.0
                cum = (1.0 + net).cumprod()
                mdd = float(((cum - cum.cummax()) / cum.cummax()).min())
            acc = _unit(ic, 0.05)
            shp = _unit(sharpe, 1.0)
            rtn = _unit(ann, 0.30)
            loss = float(np.clip(-mdd / 0.30, 0.0, 1.0))
            h_raw = HEALTH_W * (acc + shp + rtn) - HEALTH_W * loss
            # 论文未给把 H 映射为正权重的方式；本复现平移并截断到 [0,1]
            health[a] = float(np.clip(h_raw + HEALTH_W, 1e-3, 1.0))
            stats[a] = {"ic": ic, "ic_ir": ic_ir, "ann": ann,
                        "sharpe": sharpe, "mdd": mdd}

        # ---- LLM 多智能体仲裁：L 轮 × (4 专家 + 1 Manager)，只读上述 train+val 诊断 ----
        self._arbitrate_llm(scores, conf, health, stats, val_safe, grs, syms)

        self._symbols = syms
        self._health = health
        self._conf = conf
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        if not self._health:
            raise RuntimeError("必须先调用 fit() 再 produce_signal()")
        dates_all = ds.dates_through(split)
        panel = ds.panel[ds.panel.index.get_level_values(0).isin(dates_all)]
        feat, mkt, syms = self._build(panel)
        self._symbols = syms
        grs = self._grs_norm(self._grs_raw(mkt))
        scores = self._agent_scores(feat, mkt, grs)

        W = {a: self._wide(scores[a], syms) for a in _AGENTS}
        iv = self._wide(1.0 / feat["vol60"], syms)
        lo, hi = self._g_bounds
        if hi > lo:
            gmat = ((self._wide(feat["dvol60"], syms) - lo) / (hi - lo)
                    ).clip(0.0, 1.0).fillna(0.5)
        else:
            gmat = self._wide(feat["dvol60"], syms) * 0.0 + 0.5
        ret_wide = panel["ret"].unstack(level=1).reindex(columns=syms).sort_index()
        target = set(ds._dates_of(split))

        out: Dict[Tuple[pd.Timestamp, str], float] = {}
        for d in W["report"].index:
            if d not in target:
                continue
            raw = {a: W[a].loc[d].to_numpy(dtype=float) for a in _AGENTS}
            props = {a: _to_simplex(raw[a]) for a in _AGENTS}
            gval = float(grs.get(d, 0.5))
            # LLM 仲裁冻结参数在此确定性生效；本函数绝不调用 LLM（审计硬约束）
            conf_eff = {a: self._effective_conf(a, gval) for a in _AGENTS}
            # --- 递归聚合（Eq.7/Eq.8）：把上轮 w̄ 反馈给 agent 修订，直至收敛 ---
            wbar = self._aggregate(props, conf_eff, self._health)
            for _ in range(MAX_ROUNDS):
                p_new = {a: (1.0 - BLEND_RHO) * props[a] + BLEND_RHO * wbar
                         for a in _AGENTS}
                # 与共识分歧越大、置信度越低（论文未给修订式，本复现自定）
                c_new = {}
                for a in _AGENTS:
                    dis = 0.5 * float(np.abs(p_new[a] - wbar).sum())
                    c_new[a] = conf_eff[a] * (1.0 - min(1.0, dis))
                wbar_new = self._aggregate(p_new, c_new, self._health)
                delta = float(np.linalg.norm(wbar_new - wbar))
                props, wbar = p_new, wbar_new
                if delta < EPS_CONV:
                    break
            # --- 约束 MVO（Eq.10）---
            mu = wbar
            sigma = self._ewma_cov(ret_wide, d, syms)
            grow = np.nan_to_num(gmat.loc[d].to_numpy(dtype=float), nan=0.5)
            frac = float(np.clip((gval - THETA_GEO) / (1.0 - THETA_GEO), 0.0, 1.0))
            gamma = GAMMA_GEO_LOW_RISK - (GAMMA_GEO_LOW_RISK - GAMMA_GEO_HIGH_RISK) * frac
            # Manager 的 γ_geo 平移仍夹在论文 0.65→0.45 区间内
            gamma = float(np.clip(gamma + self._llm_geo_tilt,
                                  GAMMA_GEO_HIGH_RISK, GAMMA_GEO_LOW_RISK))
            w_final = self._mvo(mu, sigma, grow, gamma, mu.copy())
            # --- 三触发熔断（Eq.5）---
            dd = float(mkt["dd20"].get(d, np.nan))
            v20 = float(mkt["vol20"].get(d, np.nan))
            v252 = float(mkt["vol252"].get(d, np.nan))
            trig_dd = np.isfinite(dd) and dd < THETA_DD
            trig_geo = gval > THETA_GEO
            trig_vol = (np.isfinite(v20) and np.isfinite(v252) and v252 > 0
                        and v20 > THETA_VOL_MULT * v252)
            if trig_dd or trig_geo or trig_vol:
                # CB 后权重论文未给：本复现自定按严重度向低波动防御组合渐变
                sev = 0.0
                if np.isfinite(dd):
                    sev = max(sev, (THETA_DD - dd) / abs(THETA_DD))
                sev = max(sev, (gval - THETA_GEO) / max(1e-9, 1.0 - THETA_GEO))
                if np.isfinite(v20) and np.isfinite(v252) and v252 > 0:
                    sev = max(sev, v20 / (THETA_VOL_MULT * v252) - 1.0)
                alpha = float(np.clip(
                    DEFENSIVE_ALPHA_MIN + (1.0 - DEFENSIVE_ALPHA_MIN) * max(0.0, sev)
                    + self._llm_def_bias,
                    0.0, 1.0))
                defensive = _to_simplex(iv.loc[d].to_numpy(dtype=float))
                w_final = (1.0 - alpha) * w_final + alpha * defensive
            for j, sym in enumerate(syms):
                out[(d, sym)] = float(w_final[j])

        if not out:
            return pd.Series(dtype=float)
        s = pd.Series(out)
        s.index = pd.MultiIndex.from_tuples(s.index, names=["date", "symbol"])
        return s.sort_index()


if __name__ == "__main__":
    from core.data import make_dataset

    _ds = make_dataset()
    _m = RecursiveMultiAgent().fit(_ds)
    _sig = _m.produce_signal(_ds, "test")
    print(f"test_days={_sig.index.get_level_values(0).nunique()} "
          f"n={len(_sig)} nan_ratio={_sig.isna().mean():.4f}")
    print(f"health={_m._health}")
    print(f"conf={_m._conf}")
    print(f"llm_backend={_m.llm.backend_name} degraded={_m.degraded} fidelity={_m.fidelity}")
    print(f"llm_stats={_m.llm.stats}")
    print(f"llm_conf={_m._llm_conf}")
    print(f"llm_regime_pref={_m._llm_regime_pref} "
          f"geo_tilt={_m._llm_geo_tilt:.4f} def_bias={_m._llm_def_bias:.4f}")
