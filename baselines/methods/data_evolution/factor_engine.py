"""
FactorEngine（14）程序级因子挖掘复现。

论文核心：因子=图灵完备代码；三个分离。本复现落地其中两个关键分离：
  (i) 逻辑修订（LLM/规则做方向搜索）vs 参数优化（本地网格/随机搜索，不调 LLM）
  (iii) LLM 使用 vs 本地计算（参数在本地算）
另含经验知识库（记录每次尝试，含失败）。
无 API key 时 LLM 用规则变异替代，fidelity 明确标注。
"""
from __future__ import annotations
import ast
import re
from typing import List, Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression, _preprocess
from core.interface import BaselineMethod
from core.llm import RuleBasedLLM
from core.evaluator import cross_section_ic_series

PARAM_GRID = [3, 5, 10, 20, 30]


def _replace_constants(text: str, value: int) -> str:
    """把表达式中所有 int 常量替换为 value（参数本地搜索）。"""
    pre = _preprocess(text)
    tree = ast.parse(pre, mode="eval")
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            n.value = value
    return ast.unparse(tree)


def _has_constant(text: str) -> bool:
    return any(isinstance(n, ast.Constant) and isinstance(n.value, int)
               for n in ast.walk(ast.parse(_preprocess(text), mode="eval")))


class FactorEngine(BaselineMethod):
    def __init__(self, rounds: int = 3, pop_size: int = 6, n_struct: int = 5,
                 llm=None, seed: Optional[int] = 0):
        self.name = "factor_engine"
        self.category = "data_evolution"
        self.paper_id = "14"
        self.fidelity = "llm_replaced_by_rule"
        self.notes = "逻辑用规则变异替代 LLM；参数本地网格搜索、经验库、三分离机制忠实"
        self.rounds = rounds
        self.pop_size = pop_size
        self.n_struct = n_struct
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.experience: List[dict] = []
        self.best_expr: Optional[str] = None

    def _panel(self, ds: Dataset, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]

    def _tune_and_score(self, struct: str, panel, fwd) -> tuple[float, str]:
        """参数本地搜索：对结构中的常量网格搜索，返回 (best_ic, final_expr)。"""
        candidates = [struct]
        if _has_constant(struct):
            candidates = [_replace_constants(struct, v) for v in PARAM_GRID]
        best_ic, best_expr = np.nan, struct
        for c in candidates:
            try:
                sig = eval_expression(c, panel)
                pic, _ = cross_section_ic_series(sig, fwd)
                ic = pic.mean() if len(pic) else np.nan
            except Exception:
                ic = np.nan
            self.experience.append({"expr": c, "val_ic": None if np.isnan(ic) else float(ic)})
            if np.isfinite(ic) and (not np.isfinite(best_ic) or abs(ic) > abs(best_ic)):
                best_ic, best_expr = ic, c
        return best_ic, best_expr

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")

        from core.evolution import SEED_EXPRESSIONS
        structs = list(SEED_EXPRESSIONS[: self.n_struct])
        scored = {}
        for s in structs:
            ic, expr = self._tune_and_score(s, val_panel, val_fwd)
            scored[expr] = ic

        for r in range(self.rounds):
            ranked = sorted(scored.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            parents = [e for e, _ in ranked[: self.pop_size]]
            for _ in range(self.n_struct):
                p = parents[np.random.randint(len(parents))]
                new_struct = self.llm.mutate(p, f"val IC={scored[p]:.4f}")
                ic, expr = self._tune_and_score(new_struct, val_panel, val_fwd)
                scored[expr] = ic
            ranked = sorted(scored.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            scored = dict(ranked[: self.pop_size])

        self.best_expr = sorted(scored.items(),
                                key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)[0][0]
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        s = eval_expression(self.best_expr, self._panel(ds, ds.dates_through(split)))
        return s[s.index.get_level_values(0).isin(ds._dates_of(split))]
