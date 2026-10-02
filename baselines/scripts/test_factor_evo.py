import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.data import make_dataset
from core.interface import save_metrics
from methods.factor_evolution.aqua import AQuA
from methods.factor_evolution.astar import Astar
from methods.factor_evolution.auto_scientist import AutoScientist
from methods.factor_evolution.quant_evolver import QuantEvolver

RESULTS = Path(__file__).resolve().parents[1] / "results"
ds = make_dataset(name="csi300_small", n_symbols=15, n_days=420, horizon=5)

for cls in [AQuA, Astar, AutoScientist, QuantEvolver]:
    m = cls()
    met = m.run(ds)
    save_metrics(met, RESULTS, ds.name)
    print(f"[{m.name:15s}] IC={met.mean_ic:+.4f} RankIC={met.mean_rank_ic:+.4f} "
          f"Sharpe={met.long_short_sharpe:+.2f}")
print("FACTOR EVO OK")
