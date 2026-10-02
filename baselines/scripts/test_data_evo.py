import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.data import make_dataset
from core.interface import save_metrics
from methods.data_evolution.factor_engine import FactorEngine
from methods.data_evolution.rd_agent_quant import RDAgentQuant
from methods.data_evolution.trading_group import TradingGroup

RESULTS = Path(__file__).resolve().parents[1] / "results"
ds = make_dataset(name="csi300_small", n_symbols=15, n_days=420, horizon=5)

for cls in [FactorEngine, RDAgentQuant, TradingGroup]:
    m = cls()
    met = m.run(ds)
    save_metrics(met, RESULTS, ds.name)
    print(f"[{m.name:16s}] IC={met.mean_ic:+.4f} RankIC={met.mean_rank_ic:+.4f} "
          f"Sharpe={met.long_short_sharpe:+.2f} dir={met.direction}")
print("DATA EVO OK")
