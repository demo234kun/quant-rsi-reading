"""
密封评估沙箱。

铁律：
- 有两个文件：selection_metric（validation，可随便看）和 final_metric（test，只跑一次）
- 数据切分 train/embargo/test 写死，agent 无权改
- 输出 per-regime IC 向量，不是全历史 IC
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Dict, Optional
import json
from pathlib import Path


@dataclass
class SplitConfig:
    train_end: str       # e.g. "2022-12-31"
    embargo_end: str     # e.g. "2023-06-30"（隔离带）
    test_start: str      # e.g. "2023-07-01"


def make_split(dates: pd.Index, cfg: SplitConfig) -> Dict[str, pd.Index]:
    """返回 train / embargo / test 三段日期索引。"""
    train = dates[dates <= cfg.train_end]
    embargo = dates[(dates > cfg.train_end) & (dates <= cfg.embargo_end)]
    test = dates[dates >= cfg.test_start]
    return {"train": train, "embargo": embargo, "test": test}


def per_regime_ic(
    factor: pd.Series,       # MultiIndex (date, symbol)
    fwd_ret: pd.Series,      # MultiIndex (date, symbol)，未来 N 天收益
    regime_labels: pd.Series,  # date -> regime
    dates: pd.Index,
) -> Dict[int, float]:
    """计算 per-regime Spearman IC。

    返回 {regime_id: ic}，每个 regime 一个数。
    """
    # 对齐
    df = pd.DataFrame({"factor": factor, "fwd": fwd_ret}).dropna()
    df = df.join(regime_labels.rename("regime"), on="date", how="left")
    df = df.dropna(subset=["regime"])

    out = {}
    for r, sub in df.groupby("regime"):
        # 每日横截面 Spearman 相关，再平均
        daily_ic = sub.groupby(level=0).apply(
            lambda g: g["factor"].corr(g["fwd"], method="spearman")
            if len(g) > 5 else np.nan
        ).dropna()
        out[int(r)] = float(daily_ic.mean()) if len(daily_ic) > 0 else float("nan")
    return out


@dataclass
class EvalResult:
    factor_id: str
    expression: str
    regime_ic: Dict[int, float]      # per-regime IC
    mean_abs_ic: float               # |IC| 平均
    sharpe_proxy: float              # |IC| / std(IC) * sqrt(252)
    n_regimes_significant: int       # 几个 regime 下 |IC|>0.02
    split: str                       # "validation" or "test"

    def to_dict(self):
        return asdict(self)


class SealedEvaluator:
    """密封评估器。

    用法：
        ev = SealedEvaluator(split_cfg, regime_labels, fwd_ret)
        res_val = ev.validate(factor, "f1", "cs_rank(volume)")
        # agent 可以看 res_val
        res_test = ev.finalize(factor, "f1", "cs_rank(volume)")  # 只跑一次
    """

    def __init__(self, split_cfg: SplitConfig, regime_labels: pd.Series, fwd_ret: pd.Series):
        self.cfg = split_cfg
        self.regime_labels = regime_labels
        self.fwd_ret = fwd_ret
        self._finalized = set()  # 已跑过 finalize 的 factor_id

    def validate(self, factor: pd.Series, factor_id: str, expression: str) -> EvalResult:
        """在 train+embargo 上评估（agent 可看）。"""
        return self._eval(factor, factor_id, expression, split="validation")

    def finalize(self, factor: pd.Series, factor_id: str, expression: str) -> EvalResult:
        """在 test 上评估（每个 factor_id 只允许调一次）。"""
        if factor_id in self._finalized:
            raise RuntimeError(f"factor {factor_id} already finalized! 这是犯规。")
        self._finalized.add(factor_id)
        return self._eval(factor, factor_id, expression, split="test")

    def _eval(self, factor, factor_id, expression, split):
        all_dates = factor.index.get_level_values(0).unique()
        splits = make_split(all_dates, self.cfg)
        dates = splits["train"] if split == "validation" else splits["test"]
        # validation 用 train 段（不含 embargo，embargo 是隔离带）
        # test 用 test 段

        # 截取对应日期的 factor
        f = factor[factor.index.get_level_values(0).isin(dates)]
        fr = self.fwd_ret[self.fwd_ret.index.get_level_values(0).isin(dates)]
        rl = self.regime_labels[self.regime_labels.index.isin(dates)]

        regime_ic = per_regime_ic(f, fr, rl, dates)
        ics = list(regime_ic.values())
        valid_ics = [v for v in ics if not np.isnan(v)]
        mean_abs = float(np.mean(np.abs(valid_ics))) if valid_ics else 0.0
        std_abs = float(np.std(valid_ics)) if len(valid_ics) > 1 else 1.0
        sharpe_proxy = mean_abs / (std_abs + 1e-8) * np.sqrt(252)
        n_sig = sum(1 for v in valid_ics if abs(v) > 0.02)

        return EvalResult(
            factor_id=factor_id,
            expression=expression,
            regime_ic=regime_ic,
            mean_abs_ic=mean_abs,
            sharpe_proxy=sharpe_proxy,
            n_regimes_significant=n_sig,
            split=split,
        )


def save_result(result: EvalResult, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
