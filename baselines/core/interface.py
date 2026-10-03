"""
统一方法接口：所有论文方法都规约为“产出一个预测信号”，
然后由同一个 evaluator 评估，从而在同一批数据上形成可比较的 baseline。
"""
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd

from .data import Dataset


@dataclass
class MethodMetrics:
    """统一评估结果（同一口径，所有方法通用）。"""
    method: str
    category: str
    paper_id: str
    dataset: str
    n_test_days: int
    n_symbols: int
    horizon: int
    direction: int                      # val 估计、test 固定的多空方向
    mean_ic: float                      # 日均横截面 Pearson IC
    ic_ir: float                        # mean(IC)/std(IC)
    mean_rank_ic: float                 # 日均横截面 Spearman RankIC
    rank_ic_ir: float
    long_short_ann_return: float        # 分层多空年化（成本后）
    long_short_sharpe: float
    max_drawdown: float
    turnover: float
    cost_bps: float
    fidelity: str = "faithful_core"     # faithful_core / llm_replaced_by_rule / simplified
    notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class BaselineMethod(ABC):
    #: 方法名（用于文件命名，小写+下划线，如 "aqua"）
    name: str = "base"
    #: 分类
    category: str = "other"
    #: 对应论文编号（如 "01"）
    paper_id: str = ""
    #: 忠实度说明
    fidelity: str = "faithful_core"
    notes: str = ""

    def fit(self, ds: Dataset) -> "BaselineMethod":
        """在 train + validation 上学习/进化（默认无操作）。"""
        return self

    @abstractmethod
    def produce_signal(self, ds: Dataset, split: str = "test") -> pd.Series:
        """产出指定 split 的信号，MultiIndex (date, symbol)。"""

    def run(self, ds: Dataset) -> tuple[MethodMetrics, pd.Series]:
        """模板：fit -> 在 test 产出信号 -> 统一评估。

        返回 (MethodMetrics, 日净收益 Series)。日净收益与 metrics 里的 Sharpe 同源，
        供滚动窗口 / DSR / White RC 复用，避免二次回测导致口径不一致。
        """
        from .evaluator import evaluate_signal
        self.fit(ds)
        signal = self.produce_signal(ds, split="test")
        return evaluate_signal(self, ds, signal)


def save_metrics(metrics: MethodMetrics, results_dir: Path, dataset_name: str) -> Path:
    """统一保存：results/<dataset>/<method>.json"""
    d = Path(results_dir) / dataset_name
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{metrics.method}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, ensure_ascii=False, indent=2)
    return path
