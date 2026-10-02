"""从 results/<dataset>/ 下所有 JSON 汇总，生成 Markdown 对比表。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

CATEGORY_ORDER = {
    "handcrafted": "静态对照因子",
    "data_evolution": "数据进化",
    "factor_evolution": "因子进化",
    "strategy_evolution": "策略进化",
}

PAPER = {
    "factor_engine": "14 FactorEngine", "rd_agent_quant": "12 R&D-Agent-Quant",
    "trading_group": "13 TradingGroup", "aqua": "01 AQuA", "astar": "03 Astar",
    "auto_scientist": "06 AutoScientist", "quant_evolver": "07 QuantEvolver",
    "evolve_trade": "08 EvolveTrade", "sharp": "09 SHARP",
    "algo_evolve": "10 AlgoEvolve", "recursive_multi_agent": "11 RecursiveMultiAgent",
}


def load_rows(dataset):
    rows = []
    for f in sorted((RESULTS / dataset).glob("*.json")):
        rows.append(json.loads(f.read_text(encoding="utf-8")))
    return rows


def fmt(x, p=4):
    return "N/A" if x is None else f"{x:+.{p}f}"


def table_for(rows):
    lines = [
        "| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |",
        "|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['method']}` | {PAPER.get(r['method'], '—')} "
            f"| {fmt(r['mean_ic'])} | {fmt(r['ic_ir'],3)} "
            f"| {fmt(r['mean_rank_ic'])} | {fmt(r['rank_ic_ir'],3)} "
            f"| {fmt(r['long_short_ann_return'],3)} | {fmt(r['long_short_sharpe'],2)} "
            f"| {fmt(r['max_drawdown'],3)} | {fmt(r['turnover'],3)} | {r['fidelity']} |")
    return "\n".join(lines)


def main():
    datasets = [d.name for d in RESULTS.iterdir() if d.is_dir()]
    for dataset in datasets:
        rows = load_rows(dataset)
        groups = {}
        for r in rows:
            groups.setdefault(r["category"], []).append(r)
        print(f"# Baseline 对比表（{dataset}）\n")
        n0 = rows[0]
        print(f"> 真实数据：{n0['n_symbols']} 只 × {n0['n_test_days']} 个测试日，"
              f"horizon={n0['horizon']}，方向在 validation 估计，成本 {n0['cost_bps']}bp/单边。\n")
        for cat in ["handcrafted", "data_evolution", "factor_evolution", "strategy_evolution"]:
            if cat in groups:
                print(f"## {CATEGORY_ORDER[cat]}\n")
                print(table_for(groups[cat]) + "\n")


if __name__ == "__main__":
    main()
