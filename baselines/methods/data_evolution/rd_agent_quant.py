"""
R&D-Agent-Quant（12）复现。

论文核心：data-centric 因子-模型联合优化，Research/Development 闭环，
多臂老虎机（MAB）自适应选择“因子改进 vs 模型改进”方向。

本复现：
  - factor arm：符号因子进化（与通用进化同构）
  - model arm：用 sklearn Ridge 在无泄漏滚动特征上训练，迭代正则配置
  - MAB：UCB 根据两臂历史 val |IC| 选择每轮迭代方向
  - 最终取 val 最优一侧产出信号
无 LLM 时因子结构变异用规则替代。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from core.data import Dataset
from core.expr import eval_expression
from core.interface import BaselineMethod
from core.llm import RuleBasedLLM
from core.evaluator import cross_section_ic_series
from core.evolution import SEED_EXPRESSIONS


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """无泄漏滚动特征（t 时刻可得）。"""
    close = panel["close"].groupby(level=1)
    vol = panel["volume"].groupby(level=1)
    f = pd.DataFrame(index=panel.index)
    f["mom_20"] = panel["close"].groupby(level=1).transform(lambda s: s / s.shift(20) - 1)
    f["rev_5"] = -panel["close"].groupby(level=1).transform(lambda s: s / s.shift(5) - 1)
    f["vol_20"] = panel["close"].groupby(level=1).transform(lambda s: s.rolling(20).std())
    f["vol_ratio"] = panel["volume"].groupby(level=1).transform(
        lambda s: s.rolling(5).mean() / s.rolling(20).mean())
    f["high_low"] = (panel["high"] - panel["low"]) / panel["close"]
    return f


class RDAgentQuant(BaselineMethod):
    def __init__(self, rounds: int = 6, llm=None, seed: Optional[int] = 0):
        self.name = "rd_agent_quant"
        self.category = "data_evolution"
        self.paper_id = "12"
        self.fidelity = "llm_replaced_by_rule"
        self.notes = "因子-模型联合优化、UCB 多臂调度忠实；factor 结构变异用规则替代 LLM"
        self.rounds = rounds
        self.llm = llm or RuleBasedLLM(seed=seed)
        self.rng = np.random.RandomState(seed)
        self.best_kind = "factor"
        self.best_factor_expr: Optional[str] = None
        self.best_model = None
        self.best_alpha: Optional[float] = None
        self.arm_value = {"factor": [], "model": []}
        self.arm_count = {"factor": 0, "model": 0}

    def _panel(self, ds, dates):
        cols = ["open", "high", "low", "close", "volume", "ret"]
        return ds.panel[ds.panel.index.get_level_values(0).isin(dates)][cols]

    def _factor_ic(self, expr, panel, fwd):
        try:
            sig = eval_expression(expr, panel)
            pic, _ = cross_section_ic_series(sig, fwd)
            return pic.mean() if len(pic) else np.nan
        except Exception:
            return np.nan

    def _train_model(self, ds, alpha):
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        tr_panel = self._panel(ds, ds.train_dates)
        Xtr = build_features(tr_panel)
        ytr = ds.fwd_ret_on("train")
        d = pd.concat([Xtr, ytr.rename("y")], axis=1).dropna()
        scaler = StandardScaler()
        Xs = scaler.fit_transform(d[[*Xtr.columns]])
        model = Ridge(alpha=alpha).fit(Xs, d["y"])
        return model, scaler, list(Xtr.columns)

    def _model_ic(self, model, scaler, feat_cols, ds, alpha):
        val_panel = self._panel(ds, ds.val_dates)
        Xv = build_features(val_panel)[feat_cols]
        d = pd.concat([Xv, ds.fwd_ret_on("validation").rename("y")], axis=1).dropna()
        if len(d) < 10:
            return np.nan
        pred = model.predict(scaler.transform(d[feat_cols]))
        pred_s = pd.Series(pred, index=d.index)
        pic, _ = cross_section_ic_series(pred_s, d["y"])
        return pic.mean() if len(pic) else np.nan

    def _ucb(self, total):
        out = {}
        for k in ("factor", "model"):
            mean = np.mean(self.arm_value[k]) if self.arm_value[k] else 0.0
            bonus = np.sqrt(2 * np.log(max(total, 1)) / self.arm_count[k]) if self.arm_count[k] else 1e3
            out[k] = mean + bonus
        return max(out, key=out.get)

    def fit(self, ds: Dataset):
        val_panel = self._panel(ds, ds.val_dates)
        val_fwd = ds.fwd_ret_on("validation")
        factor_pool = list(SEED_EXPRESSIONS)
        factor_scores = {e: self._factor_ic(e, val_panel, val_fwd) for e in factor_pool}
        alphas = [0.1, 1.0, 10.0, 100.0]
        model_scores = {}
        models = {}
        for a in alphas:
            m, sc, fc = self._train_model(ds, a)
            models[a] = (m, sc, fc)
            model_scores[a] = self._model_ic(m, sc, fc, ds, a)

        for t in range(self.rounds):
            arm = self._ucb(t)
            if arm == "factor":
                ranked = sorted(factor_scores.items(),
                                key=lambda kv: -abs(kv[1]) if np.isfinite(kv[1]) else 0)
                parent = ranked[0][0]
                cand = self.llm.mutate(parent, f"val IC={factor_scores[parent]:.3f}")
                if cand not in factor_scores:
                    factor_scores[cand] = self._factor_ic(cand, val_panel, val_fwd)
                best = max((v for v in factor_scores.values() if np.isfinite(v)),
                           key=abs, default=np.nan)
                self.arm_value["factor"].append(abs(best))
                self.arm_count["factor"] += 1
            else:
                a = float(self.rng.choice(alphas))
                m, sc, fc = self._train_model(ds, a)
                model_scores[a] = self._model_ic(m, sc, fc, ds, a)
                models[a] = (m, sc, fc)
                best = max((v for v in model_scores.values() if np.isfinite(v)),
                           key=abs, default=np.nan)
                self.arm_value["model"].append(abs(best))
                self.arm_count["model"] += 1

        best_factor = max(factor_scores.items(),
                          key=lambda kv: abs(kv[1]) if np.isfinite(kv[1]) else 0)
        best_model_choice = max(model_scores.items(),
                                key=lambda kv: abs(kv[1]) if np.isfinite(kv[1]) else 0)
        if abs(best_model_choice[1] if np.isfinite(best_model_choice[1]) else 0) > \
           abs(best_factor[1] if np.isfinite(best_factor[1]) else 0):
            self.best_kind = "model"
            self.best_alpha = best_model_choice[0]
            self.best_model, self._sc, self._fc = models[self.best_alpha]
        else:
            self.best_kind = "factor"
            self.best_factor_expr = best_factor[0]
        return self

    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        target = ds._dates_of(split)
        if self.best_kind == "factor":
            s = eval_expression(self.best_factor_expr,
                                self._panel(ds, ds.dates_through(split)))
            return s[s.index.get_level_values(0).isin(target)]
        panel = self._panel(ds, ds.dates_through(split))
        X = build_features(panel)[self._fc]
        valid = X.dropna()
        pred = self.best_model.predict(self._sc.transform(valid))
        s = pd.Series(pred, index=valid.index)
        return s[s.index.get_level_values(0).isin(target)]
