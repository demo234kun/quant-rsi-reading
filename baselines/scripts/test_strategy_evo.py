import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.data import make_dataset
from core.interface import save_metrics
from methods.strategy_evolution.evolve_trade import EvolveTrade
from methods.strategy_evolution.sharp import SHARP
from methods.strategy_evolution.algo_evolve import AlgoEvolve
from methods.strategy_evolution.recursive_multi_agent import RecursiveMultiAgent

RESULTS = Path(__file__).resolve().parents[1] / "results"
ds = make_dataset(name="csi300_small", n_symbols=15, n_days=420, horizon=5)

for cls in [EvolveTrade, SHARP, AlgoEvolve, RecursiveMultiAgent]:
    m = cls()
    met, _net = m.run(ds)
    save_metrics(met, RESULTS, ds.name)
    print(f"[{m.name:22s}] IC={met.mean_ic:+.4f} RankIC={met.mean_rank_ic:+.4f} "
          f"Sharpe={met.long_short_sharpe:+.2f}")
print("STRATEGY EVO OK")
