"""小样本冒烟测试：验证数据/表达式/评估/进化全链路。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.data import make_dataset
from core.interface import save_metrics
from methods.factor_lib import FixedExpressionMethod, HANDFACTORS
from core.evolution import SymbolicEvolutionBase

RESULTS = Path(__file__).resolve().parents[1] / "results"

ds = make_dataset(name="csi300_small", n_symbols=15, n_days=420, horizon=5)
print(f"dataset: {ds.symbols.nunique()} symbols, "
      f"train={len(ds.train_dates)} val={len(ds.val_dates)} test={len(ds.test_dates)}")

for name, expr in HANDFACTORS.items():
    m = FixedExpressionMethod(name, expr)
    metrics, _net = m.run(ds)
    save_metrics(metrics, RESULTS, ds.name)
    print(f"[{name:13s}] IC={metrics.mean_ic:+.4f} RankIC={metrics.mean_rank_ic:+.4f} "
          f"Sharpe={metrics.long_short_sharpe:+.2f}")

evo = SymbolicEvolutionBase(name="generic_evolution", rounds=3, pop_size=8,
                            n_mutants_per_round=5, seed=1)
m2, _net2 = evo.run(ds)
save_metrics(m2, RESULTS, ds.name)
print(f"[generic_evolution] best={evo.best_expr}")
print(f" IC={m2.mean_ic:+.4f} RankIC={m2.mean_rank_ic:+.4f} Sharpe={m2.long_short_sharpe:+.2f}")
print("SMOKE OK")
