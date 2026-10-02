"""
FlipSearch v2: 直接算 IC（更快），不用 SealedEvaluator。
"""
from __future__ import annotations
import sys, re, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.dsl.operators import OPERATORS, list_operators
from src.regime.cluster import regime_summary
from src.evaluator.sealed import SplitConfig
from src.controller.adapter import cold_start_policy
from src.controller.proposer import propose_factors


def _eval_expr(expr, panel):
    local = {op: OPERATORS[op] for op in OPERATORS}
    local["panel"] = panel
    for f in ["close", "volume", "open", "high", "low", "ret"]:
        expr = re.sub(rf'\b{f}\b', f"panel['{f}']", expr)
    try:
        return eval(expr, {"__builtins__": {}}, local)
    except Exception:
        return None


def _per_regime_ic(factor, fwd, regime_arr):
    df = pd.DataFrame({"f": factor.values, "r": fwd.values, "regime": regime_arr},
                      index=factor.index).dropna()
    out = {}
    for r in sorted(df["regime"].dropna().unique()):
        daily = []
        for d, g in df[df["regime"] == r].groupby(level=0):
            if len(g) >= 5:
                ic = spearmanr(g["f"], g["r"])[0]
                if np.isfinite(ic):
                    daily.append(ic)
        if daily:
            out[int(r)] = float(np.mean(daily))
    return out


def run(n_factors=100):
    print("=" * 70)
    print(f"FlipSearch: {n_factors} factors, forward vs flipped (real CSI300)")
    print("=" * 70)

    panel = pd.read_parquet(ROOT / "data" / "csi300_daily.parquet").sort_index()
    dates = panel.index.get_level_values(0).unique().sort_values()
    n = len(dates)
    cfg = SplitConfig(
        train_end=str(dates[int(n*0.6)].date()),
        embargo_end=str(dates[int(n*0.7)].date()),
        test_start=str(dates[int(n*0.8)].date()),
    )
    td = dates[dates <= pd.Timestamp(cfg.train_end)]
    rl, _, _ = regime_summary(panel, pd.Series(True, index=td), n_regimes=4)

    fwd = panel.groupby(level="symbol")["close"].pct_change(5).shift(-5)
    test_dates = dates[dates >= pd.Timestamp(cfg.test_start)]
    tmask = panel.index.get_level_values(0).isin(test_dates)

    ptest = panel[tmask]
    ftest = fwd[tmask]
    rarr = rl.reindex(ptest.index.get_level_values(0)).values

    policy = cold_start_policy(list_operators())
    results, tested, gr = [], 0, 0
    print(f"\n{panel.index.get_level_values(1).nunique()} stocks, test {len(test_dates)} days\n")

    while tested < n_factors:
        policy.round = gr
        exprs = propose_factors(policy, n=20, seed=gr * 13)
        gr += 1
        for expr in exprs:
            if tested >= n_factors:
                break
            f = _eval_expr(expr, panel)
            if f is None:
                continue
            ft = f[tmask]
            if len(ft.dropna()) < 200:
                continue
            fic = _per_regime_ic(ft, ftest, rarr)
            if not fic:
                continue
            ric = _per_regime_ic(-ft, ftest, rarr)

            fm = float(np.mean(list(fic.values())))
            rm = float(np.mean(list(ric.values())))
            fs = [np.sign(v) for v in fic.values()]
            rs = [np.sign(v) for v in ric.values()]
            isrev = bool(all(s <= 0 for s in fs if s) and any(s > 0 for s in rs) and abs(fm) > 0.01)

            results.append({
                "expr": expr,
                "top_op": re.match(r"(\w+)\(", expr).group(1),
                "fwd_ic": fm, "flip_ic": rm, "gain": rm - fm,
                "reversed": isrev, "fwd_regime": fic, "flip_regime": ric,
            })
            tested += 1
            if tested % 20 == 0:
                nr = sum(1 for x in results if x["reversed"])
                print(f"  {tested}/{n_factors}  reversed={nr} ({100*nr/tested:.0f}%)")

    print("\n" + "=" * 70)
    nt = len(results)
    nr = sum(1 for x in results if x["reversed"])
    gains = [x["gain"] for x in results]
    print(f"  tested: {nt}")
    print(f"  DIRECTION_REVERSED: {nr} ({100*nr/nt:.1f}%)")
    print(f"  mean signed-IC change: {np.mean(gains):+.5f}")
    print(f"  median signed-IC change: {np.median(gains):+.5f}")

    print("\n  by operator:")
    bo = {}
    for x in results:
        bo.setdefault(x["top_op"], {"t": 0, "r": 0})
        bo[x["top_op"]]["t"] += 1
        if x["reversed"]:
            bo[x["top_op"]]["r"] += 1
    for op, s in sorted(bo.items(), key=lambda x: -x[1]["t"]):
        if s["t"] >= 3:
            print(f"    {op:15s}: {s['r']}/{s['t']} ({100*s['r']/s['t']:.0f}%)")

    print("\n  top 5 gains:")
    for x in sorted(results, key=lambda x: -x["gain"])[:5]:
        print(f"    {x['gain']:+.4f}  {x['expr'][:70]}")

    out = ROOT / "data" / "flipsearch.json"
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2, default=str)
    print(f"\n  saved: {out}")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
