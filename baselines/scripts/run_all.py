"""
统一全量 baseline 入口：在同一批真实数据上跑全部方法并保存结果。

用法：
    python scripts/run_all.py                # 小样本（默认）
    python scripts/run_all.py --full         # 全样本（49 只 × 1455 天，较慢）
所有方法规约为产出一个预测信号（MultiIndex date×symbol），由同一评估器评估，
从而在同一批数据上形成可比较 baseline。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.data import make_dataset
from core.interface import save_metrics
from methods.factor_lib import (
    FixedExpressionMethod, HANDFACTORS)
from methods.data_evolution.factor_engine import FactorEngine
from methods.data_evolution.rd_agent_quant import RDAgentQuant
from methods.data_evolution.trading_group import TradingGroup
from methods.factor_evolution.aqua import AQuA
from methods.factor_evolution.astar import Astar
from methods.factor_evolution.auto_scientist import AutoScientist
from methods.factor_evolution.quant_evolver import QuantEvolver
from methods.strategy_evolution.evolve_trade import EvolveTrade
from methods.strategy_evolution.sharp import SHARP
from methods.strategy_evolution.algo_evolve import AlgoEvolve
from methods.strategy_evolution.recursive_multi_agent import RecursiveMultiAgent

RESULTS = Path(__file__).resolve().parents[1] / "results"


def build_methods():
    methods = [FixedExpressionMethod(name=n, expression=e) for n, e in HANDFACTORS.items()]
    methods += [
        # 数据进化
        FactorEngine(), RDAgentQuant(), TradingGroup(),
        # 因子进化
        AQuA(), Astar(), AutoScientist(), QuantEvolver(),
        # 策略进化
        EvolveTrade(), SHARP(), AlgoEvolve(), RecursiveMultiAgent(),
    ]
    return methods


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="全样本")
    ap.add_argument("--n-symbols", type=int, default=15)
    ap.add_argument("--n-days", type=int, default=420)
    args = ap.parse_args()

    if args.full:
        ds = make_dataset(name="csi300_full", n_symbols=49, n_days=1455, horizon=5)
    else:
        ds = make_dataset(name="csi300_small", n_symbols=args.n_symbols,
                          n_days=args.n_days, horizon=5)

    for m in build_methods():
        met, _net = m.run(ds)
        save_metrics(met, RESULTS, ds.name)
        print(f"[{m.name:22s}] IC={met.mean_ic:+.4f} RankIC={met.mean_rank_ic:+.4f} "
              f"Sharpe={met.long_short_sharpe:+.2f} [{m.fidelity}]")
    print("ALL BASELINES DONE")


if __name__ == "__main__":
    main()
