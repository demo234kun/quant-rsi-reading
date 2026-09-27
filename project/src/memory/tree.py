"""
发现树记忆。

每轮实验一条记录，YAML/JSONL 结构化存储。
节点带 regime 标签，供 RCER 回放。
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import date
from typing import List, Optional, Dict


@dataclass
class ExperimentNode:
    experiment_id: str
    timestamp: str
    regime_at_time: Optional[int]       # 实验时市场所处 regime
    hypothesis: str                       # 为什么试这个
    expression: str                      # DSL 表达式
    parent_exp: Optional[str] = None   # 从哪条演化来
    val_regime_ic: Dict[int, float] = field(default_factory=dict)
    test_regime_ic: Dict[int, float] = field(default_factory=dict)
    status: str = "pending"             # pending / accepted / rejected
    failure_reason: Optional[str] = None
    notes: str = ""


class DiscoveryTree:
    """发现树：JSONL 追加写。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.nodes: List[ExperimentNode] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.nodes.append(ExperimentNode(**json.loads(line)))

    def add(self, node: ExperimentNode):
        self.nodes.append(node)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(node), ensure_ascii=False) + "\n")

    def get_nodes_by_regime(self, regime: int) -> List[ExperimentNode]:
        """RCER：只取同 regime 的节点。"""
        return [n for n in self.nodes if n.regime_at_time == regime]

    def get_recent(self, n: int = 10) -> List[ExperimentNode]:
        return self.nodes[-n:]

    def fuel_status(self, regime: int, min_nodes: int = 20) -> dict:
        """新 regime 燃料检测。"""
        same = self.get_nodes_by_regime(regime)
        return {
            "regime": regime,
            "n_nodes": len(same),
            "fuel_ok": len(same) >= min_nodes,
            "message": (
                f"regime {regime} 只有 {len(same)} 条历史"
                if len(same) < min_nodes
                else f"regime {regime} 经验充足 ({len(same)} 条)"
            ),
        }
