"""
AlgoEvolve 内层「受限 DSL 程序空间」（自定替代方案，见主文件 notes）。

论文内层进化「可执行 Python 交易程序」，并让 LLM 充当语义 CoT 变异算子。
直接运行 LLM 生成的任意 Python 不安全，因此本复现将程序空间限制为：
在 6 个技术指标上的受限算术表达式（白名单算子 + 白名单函数），
用自实现的 AST 遍历求值器计算，**绝不 eval/exec 原始文本**。
这保留了论文「进化可执行程序」的论点，但丢失「对任意 Python 做语义 mutation」的论点。

适应度严格照抄论文 §3：S = α·R + (1−α)·C，α=0.7。
- R = Total Return = 策略累计净 PnL（Long-Short 组合，扣 10bps=论文 0.1% 成本）
- C = Consistency = 策略收益跑赢「跨资产中位市场表现」的资产占比
论文未指定 R/C 的归一化与回测细则，故回测口径为自定（已标注）。
非法候选（DSL 违约 / 运行时异常 / 零有效交易）适应度为 −∞。
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ALPHA = 0.7
FEATURES: Tuple[str, ...] = ("rsi14", "ema20_gap", "macd_hist", "atr_pct", "boll_pos", "mom10")


class DSLViolation(ValueError):
    """候选程序违反受限 DSL 契约（应被赋 fitness −∞）。"""


# ---------------- 白名单函数（全部为无未来函数的截面 / 逐元素运算） ----------------
def _zs(x: pd.Series) -> pd.Series:
    """每日横截面 z-score（按 level=0 日期分组）。"""

    def _z(s: pd.Series) -> pd.Series:
        sd = s.std()
        if sd and np.isfinite(sd):
            return (s - s.mean()) / sd
        return s * 0.0

    return x.groupby(level=0).transform(_z)


def _rk(x: pd.Series) -> pd.Series:
    """每日横截面百分位排名（0~1）。"""
    return x.groupby(level=0).rank(pct=True)


def _sg(x: pd.Series) -> pd.Series:
    return np.sign(x)


def _ab(x: pd.Series) -> pd.Series:
    return x.abs()


def _cl(x: pd.Series, lo, hi) -> pd.Series:
    return x.clip(lo, hi)


def _wt(cond, a, b):
    """cond 为真取 a，否则取 b。"""
    if isinstance(a, pd.Series) or isinstance(b, pd.Series):
        aa = a if isinstance(a, pd.Series) else pd.Series(a, index=cond.index)
        bb = b if isinstance(b, pd.Series) else pd.Series(b, index=cond.index)
        return aa.where(cond, bb)
    return pd.Series(np.where(cond, a, b), index=cond.index)


def _mx(a, b):
    return np.maximum(a, b)


def _mn(a, b):
    return np.minimum(a, b)


FUNCS: Dict[str, Callable] = {
    "zs": _zs, "rk": _rk, "sg": _sg, "ab": _ab,
    "cl": _cl, "wt": _wt, "mx": _mx, "mn": _mn,
}
_ARITY: Dict[str, int] = {"zs": 1, "rk": 1, "sg": 1, "ab": 1, "cl": 3, "wt": 3, "mx": 2, "mn": 2}

_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load, ast.UnaryOp, ast.BinOp,
    ast.Compare, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.USub, ast.UAdd, ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq,
)


class _Evaluator:
    """白名单 AST 求值器：只计算我方定义的安全算子，不做属性/下标/任意对象调用。"""

    def __init__(self, ind: pd.DataFrame):
        self.ind = ind

    def value(self, node: ast.AST):
        if isinstance(node, ast.Expression):
            return self.value(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise DSLViolation("只允许数值常量")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in FEATURES:
                return self.ind[node.id]
            raise DSLViolation(f"未知标识符: {node.id}")
        if isinstance(node, ast.UnaryOp):
            v = self.value(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return v
            raise DSLViolation("不支持的一元运算")
        if isinstance(node, ast.BinOp):
            a = self.value(node.left)
            b = self.value(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                bv = b.replace(0, np.nan) if isinstance(b, pd.Series) else (np.nan if b == 0 else b)
                return a / bv
            raise DSLViolation("不支持的二元运算")
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise DSLViolation("只允许单个比较运算")
            left = self.value(node.left)
            right = self.value(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.Lt):
                return left < right
            if isinstance(op, ast.GtE):
                return left >= right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            raise DSLViolation("不支持的比较运算")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
                raise DSLViolation("仅允许白名单函数")
            if node.keywords:
                raise DSLViolation("不允许关键字参数")
            name = node.func.id
            if len(node.args) != _ARITY[name]:
                raise DSLViolation(f"{name}() 参数个数错误")
            args = [self.value(a) for a in node.args]
            return FUNCS[name](*args)
        raise DSLViolation(f"不支持的语法节点: {type(node).__name__}")


def validate_code(code: str) -> None:
    """静态校验候选程序；违反契约抛 DSLViolation。"""
    if not isinstance(code, str) or not code.strip():
        raise DSLViolation("空程序")
    if len(code) > 400:
        raise DSLViolation("程序超过 400 字符上限")
    try:
        tree = ast.parse(code.strip(), mode="eval")
    except SyntaxError as exc:
        raise DSLViolation(f"语法错误: {exc}") from exc
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise DSLViolation("程序过于复杂（节点数 > 80）")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise DSLViolation(f"不支持的语法节点: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in FEATURES and node.id not in FUNCS:
            raise DSLViolation(f"未知标识符: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
                raise DSLViolation("仅允许白名单函数")
            if len(node.args) != _ARITY[node.func.id]:
                raise DSLViolation(f"{node.func.id}() 参数个数错误")


def eval_program(code: str, ind: pd.DataFrame) -> pd.Series:
    """在指标表上求值候选程序，返回横截面 score。"""
    validate_code(code)
    tree = ast.parse(code.strip(), mode="eval")
    val = _Evaluator(ind).value(tree)
    if not isinstance(val, pd.Series):
        raise DSLViolation("程序必须产生一个横截面 Series，而不是常数")
    return val.replace([np.inf, -np.inf], np.nan).astype(float)


# ---------------- 适应度 S = α·R + (1−α)·C ----------------
@dataclass
class ProgramScore:
    fitness: float           # S；非法候选为 −inf
    total_return: float      # R = 累计净 PnL
    consistency: float       # C = 跑赢截面中位市场表现的资产占比
    effective_trades: int    # 非零权重数；0 视为零有效交易
    valid: bool
    error: str = ""


def _invalid(error: str) -> ProgramScore:
    return ProgramScore(fitness=-np.inf, total_return=float("nan"),
                        consistency=float("nan"), effective_trades=0,
                        valid=False, error=error)


def _daily_weights(sig: pd.Series, min_names: int) -> Optional[pd.DataFrame]:
    """每日按信号做等权多空分层，返回 行=date、列=symbol 的权重矩阵。"""
    df = pd.DataFrame({"sig": sig}).dropna()
    if df.empty:
        return None
    rows: Dict[pd.Timestamp, pd.Series] = {}
    for d, g in df.groupby(level=0):
        if len(g) < min_names:
            continue
        names = g.index.get_level_values(1)
        order = g["sig"].sort_values()
        k = max(1, int(np.ceil(len(order) / 5)))
        w = pd.Series(0.0, index=names)
        w.loc[order.index.get_level_values(1)[-k:]] = 1.0 / k
        w.loc[order.index.get_level_values(1)[:k]] = -1.0 / k
        rows[d] = w
    if not rows:
        return None
    return pd.DataFrame(rows).T.sort_index().fillna(0.0)


def score_program(code: str, ind: pd.DataFrame, nxt: pd.Series,
                  cost_bps: float = 10.0, min_names: int = 5) -> ProgramScore:
    """按论文 §3 计算 S = 0.7·R + 0.3·C；报错/违约/零有效交易 → −inf。"""
    try:
        sig = eval_program(code, ind)
    except DSLViolation as exc:
        return _invalid(f"DSL violation: {exc}")
    except Exception as exc:  # 运行时异常同样视为非法候选
        return _invalid(f"runtime error: {exc}")
    try:
        W = _daily_weights(sig, min_names)
    except Exception as exc:
        return _invalid(f"weight error: {exc}")
    if W is None:
        return _invalid("no cross-section with enough names")
    effective = int((W.to_numpy() != 0.0).sum())
    if effective == 0:
        return _invalid("zero effective trades")
    ret_mat = nxt.unstack(level=1).reindex(index=W.index, columns=W.columns).fillna(0.0)
    if ret_mat.empty:
        return _invalid("no forward returns in window")
    cost_rate = cost_bps / 1e4

    gross = (W * ret_mat).sum(axis=1)
    turn = W.diff().abs().sum(axis=1)
    turn.iloc[0] = W.iloc[0].abs().sum()
    net = gross - turn * cost_rate
    R = float(net.sum())  # Total Return = 累计 PnL（论文未指定是否复利，自定用求和）

    # C：逐资产策略收益 vs「跨 15 只股票」的中位市场表现（论文明确是跨资产）
    gross_a = (W * ret_mat).sum(axis=0)
    turn_a = W.diff().abs().sum(axis=0) + W.iloc[0].abs()
    strat_a = gross_a - turn_a * cost_rate
    mkt_a = (1.0 + ret_mat).prod(axis=0) - 1.0
    med = float(np.nanmedian(mkt_a.to_numpy())) if len(mkt_a) else float("nan")
    if not np.isfinite(med):
        C = 0.0
    else:
        C = float((strat_a > med).sum()) / float(max(1, len(strat_a)))

    S = ALPHA * R + (1.0 - ALPHA) * C
    return ProgramScore(fitness=float(S), total_return=float(R), consistency=float(C),
                        effective_trades=effective, valid=True)


# ---------------- 确定性种子程序 + 确定性变异（LLM 不可用时降级） ----------------
SEED_PROGRAMS: List[str] = [
    "zs(ema20_gap) + 0.5 * zs(macd_hist)",
    "-zs(rsi14) - zs(boll_pos)",
    "zs(mom10) - zs(atr_pct)",
    "zs(ema20_gap) * (1.0 - zs(atr_pct))",
]


def fallback_mutate_program(code: str, rng: np.random.RandomState) -> str:
    """无 LLM 时的确定性（带种子）程序变异：换指标 / 调常数 / 外层包 zs。"""
    try:
        tree = ast.parse(code.strip(), mode="eval")
    except SyntaxError:
        return SEED_PROGRAMS[int(rng.randint(len(SEED_PROGRAMS)))]
    names = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in FEATURES]
    consts = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
              and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
    mode = int(rng.randint(3))
    if mode == 0 and names:
        n = names[int(rng.randint(len(names)))]
        others = [f for f in FEATURES if f != n.id]
        n.id = others[int(rng.randint(len(others)))]
    elif mode == 1 and consts:
        n = consts[int(rng.randint(len(consts)))]
        n.value = float(n.value) + float(rng.uniform(-0.3, 0.3))
    else:
        inner = ast.unparse(tree.body)
        cand = f"zs({inner})"
        try:
            validate_code(cand)
            return cand
        except DSLViolation:
            return SEED_PROGRAMS[int(rng.randint(len(SEED_PROGRAMS)))]
    cand = ast.unparse(tree)
    try:
        validate_code(cand)
        return cand
    except DSLViolation:
        return SEED_PROGRAMS[int(rng.randint(len(SEED_PROGRAMS)))]
