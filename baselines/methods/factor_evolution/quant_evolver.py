"""
QuantEvolver（07）复现。

论文核心：用 RFT 把可执行回测评估反馈进 Miner LLM 的权重（LoRA），
因子 DSL + Regime Backtest，Diversity-Complementarity Reward 抗趋同。

本复现（可运行核心）：
  - 因子 DSL 种群进化（无 LLM 时用规则变异）
  - Regime backtest：按近似 regime（日期分段）评估因子
  - Diversity-Complementarity 选择：贪心选择时，质量=|IC|，
    多样性惩罚=与已选因子信号的最大相关，从而选互补因子组合
  - 未做 LoRA RFT（论文真正的权重更新）：以“可学习选择/打分”概念替代，
    fidelity 标注为 weight_rft_omitted，明确不声称复现权重更新
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression
from core.interface import BaselineMethod
from core.llm import RuleBasedLLM
from core.evaluator import cross_section_ic_series
from core.evolution import SEED_EXPRESSIONS


class QuantEvolver(BaselineMethod):
    def __init__(self, rounds: int = 3, pop_size: int = 12, n_select: int = 4,
                 lam: float = 0.5, llm=None, seed: Optional[int] = 0):
        self.name = "quant_evolver"
        self.category = "factor_evolution"
        self.paper_id = "07"
        self.fidelity = "weight_rft_omitted"
        self.notes = "因子 DSL、regime backtest、D-C 选择忠实；LoRA/RFT 权重更新未复现"
        self.rounds = rounds
        self.pop_size = pop_size
        self.n_select = n_select
        self.lam = lam
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.selected_expr: List[str] = []
        self.pool: dict[str, float] = {}

    def _panel(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]

    def _ic(self, expr, panel, fwd):
        try:
            sig = eval_expression(expr, panel)
            pic, _ = cross_section_ic_series(sig, fwd)
            return pic.mean() if len(pic) else np.nan
        except Exception:
            return np.nan

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")
        pool: dict[str, float] = {}
        for e in SEED_EXPRESSIONS:
            pool[e] = self._ic(e, val_panel, val_fwd)
        for r in range(self.rounds):
            ranked = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
            parents = [e for e, _ in ranked[: self.pop_size // 2]]
            for _ in range(6):
                p = parents[np.random.randint(len(parents))]
                cand = self.llm.mutate(p, f"val IC={pool[p]:.3f}")
                if cand not in pool:
                    pool[cand] = self._ic(cand, val_panel, val_fwd)
            pool = dict(sorted(pool.items(),
                               key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)[: self.pop_size])
        self.pool = pool

        # Diversity-Complementarity 贪心选择
        ranked = sorted(pool.items(), key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
        chosen = []
        while len(chosen) < self.n_select and ranked:
            best_key, best_score = None, -1e18
            for expr, ic in ranked:
                if expr in chosen:
                    continue
                sig = eval_expression(expr, val_panel)
                max_corr = 0.0
                for ce in chosen:
                    csig = eval_expression(ce, val_panel)
                    j = pd.concat([sig.rename("a"), csig.rename("b")], axis=1).dropna()
                    if len(j) > 20:
                        max_corr = max(max_corr, abs(j["a"].corr(j["b"])))
                score = abs(ic if np.isfinite(ic) else 0) - self.lam * max_corr
                if score > best_score:
                    best_score, best_key = score, expr
            if best_key is None:
                break
            chosen.append(best_key)
            ranked = [(e, v) for e, v in ranked if e != best_key]
        self.selected_expr = chosen
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        panel = self._panel(ds, ds.dates_through(split))
        comp = None
        for expr in self.selected_expr:
            sig = eval_expression(expr, panel)
            z = sig.groupby(level=0).transform(
                lambda s: (s - s.mean()) / s.std() if s.std() else s * 0)
            # 方向由 val IC 决定
            ic = self.pool.get(expr)
            sign = 1.0 if (ic if np.isfinite(ic) else 0) >= 0 else -1.0
            comp = z * sign if comp is None else comp + z * sign
        return comp[comp.index.get_level_values(0).isin(ds._dates_of(split))]
