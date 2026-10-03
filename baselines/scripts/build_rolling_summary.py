"""
滚动窗口汇总：把 run_rolling.py 的日净收益变成**可证伪的统计结论**。

回答两个问题：
  1. 哪个方法的 Sharpe 撑得住多重检验校正？（DSR, Bailey & Lopez de Prado 2014）
  2. "最好的那个"是不是挑出来的偶然？（White Reality Check 2000）

关键口径（写进输出，避免以后自己骗自己）：
  - DSR / RC 的输入是 daily_net_returns.csv，与表格里的 Sharpe **同源**：
    同一 net 序列、同一方向、同一 2bp/单边成本。
  - n_trials 必须显式记录。同时输出 n_methods（实际比较的方法数）与
    n_trials_used（喂给 DSR 的试验数）。二者不等时说明还有超参搜索没计入，
    DSR 会偏乐观，必须在文档里说明。
  - RC 的 bootstrap 在**去均值后**的超额收益上重采样以施加 H0；
    H0 成立时 p ~ Uniform(0,1)，所以只有 p 明显偏小才算拒绝 H0。

用法：
    python scripts/build_rolling_summary.py
    python scripts/build_rolling_summary.py --full
    python scripts/build_rolling_summary.py --n-trials 45 --n-bootstrap 10000
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

# Windows 控制台默认 GBK，会把中文与 × 打成乱码；统一强制 UTF-8。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from core.stats import deflated_sharpe_ratio, rolling_sharpe, white_reality_check

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_run(run_name: str) -> tuple[pd.DataFrame, dict]:
    d = RESULTS / "rolling" / run_name
    if not d.exists():
        avail = sorted(p.name for p in (RESULTS / "rolling").glob("*")) \
            if (RESULTS / "rolling").exists() else []
        raise SystemExit(f"找不到 {d}\n已有 rolling 运行: {avail}")
    with open(d / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    net = pd.read_csv(d / "daily_net_returns.csv", index_col=0, parse_dates=True)
    return net, manifest


def per_window_sharpes(run_dir: Path, method: str, n_windows: int) -> list[float]:
    """save_metrics 会写到 <run>/<method>/w<i>/<method>.json（第三层是 dataset_name）。"""
    out = []
    for i in range(n_windows):
        p = run_dir / method / f"w{i}" / f"{method}.json"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            out.append(float(json.load(f)["long_short_sharpe"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="全样本 rolling")
    ap.add_argument("--n-windows", type=int, default=5,
                    help="窗口数（须与 run_rolling.py 实际写入的段数一致）")
    ap.add_argument("--n-trials", type=int, default=None,
                    help="喂给 DSR 的试验次数（默认=实际比较的方法数）")
    ap.add_argument("--n-bootstrap", type=int, default=5000)
    args = ap.parse_args()

    suffix = "full" if args.full else "small"
    run_name = f"rolling_csi300_{suffix}_w{args.n_windows}"
    net, manifest = load_run(run_name)
    run_dir = RESULTS / "rolling" / run_name

    n_methods = len(net.columns)
    n_trials = args.n_trials if args.n_trials is not None else n_methods
    n_obs = len(net)

    print(f"run={run_name}")
    print(f"  日频净收益: {n_obs} 天 × {n_methods} 方法")
    print(f"  窗口: {manifest['n_windows']} 段 test，互不重叠，合计 {n_obs} 天")
    print(f"  n_methods={n_methods}  n_trials_used={n_trials}")

    if n_obs != manifest.get("total_test_days"):
        print(f"  [warn] CSV 天数 {n_obs} != manifest {manifest.get('total_test_days')}")

    rows = []
    for m in net.columns:
        r = net[m].dropna()
        if len(r) < 3:
            continue
        ann_vol = float(r.std() * np.sqrt(252))
        ann_sr_annualized = float(r.mean() * 252 / ann_vol) if ann_vol > 0 else float("nan")
        d = deflated_sharpe_ratio(r.to_numpy(), n_trials=n_trials)
        wins = per_window_sharpes(run_dir, m, manifest["n_windows"])
        rs = rolling_sharpe(r, window=max(20, n_obs // 5))
        rows.append({
            "method": m,
            "n_days": int(len(r)),
            "daily_sr": float(r.mean() / r.std(ddof=1)) if r.std(ddof=1) > 0 else float("nan"),
            "sharpe_annualized": ann_sr_annualized,
            "dsr": d["dsr"],
            "dsr_pvalue": d["pvalue"],
            "sr0_expected_max": d["sr0"],
            "skew": d.get("skew"),
            "kurtosis": d.get("kurtosis"),
            "per_window_sharpe_mean": float(np.mean(wins)) if wins else float("nan"),
            "per_window_sharpe_std": float(np.std(wins, ddof=1)) if len(wins) > 1 else float("nan"),
            "per_window_sharpe_min": float(np.min(wins)) if wins else float("nan"),
            "per_window_sharpe_max": float(np.max(wins)) if wins else float("nan"),
            "per_window_sign_consistency": (
                float(max(np.mean(np.array(wins) > 0), np.mean(np.array(wins) < 0)))
                if wins else float("nan")
            ),
            "rolling_sharpe_last": float(rs.iloc[-1]) if len(rs) else float("nan"),
            "rolling_sharpe_mean": float(rs.mean()) if len(rs) else float("nan"),
        })

    summary = pd.DataFrame(rows).sort_values("dsr", ascending=False).reset_index(drop=True)

    # White RC：两个基准都报。
    #   cash        —— 基准=0，回答"有没有方法真的跑赢躺平"（本研究的主问题）
    #   equal_weight—— 基准=所有方法等权均值，回答"是不是只有相对最好"
    rc_cash = white_reality_check(net, benchmark=np.zeros(n_obs),
                                  n_bootstrap=args.n_bootstrap, seed=20240101)
    rc_eq = white_reality_check(net, benchmark=None,
                                n_bootstrap=args.n_bootstrap, seed=20240101)

    print("\n=== DSR（多重检验校正后的 Sharpe）===")
    print(f"{'method':22s} {'Sharpe':>8s} {'DSR':>7s} {'p':>7s} "
          f"{'SR0':>7s} {'wSharpe±':>16s} {'win%':>6s}")
    for _, r in summary.iterrows():
        print(f"{r['method']:22s} {r['sharpe_annualized']:+8.2f} {r['dsr']:7.4f} "
              f"{r['dsr_pvalue']:7.4f} {r['sr0_expected_max']:+7.3f} "
              f"{r['per_window_sharpe_mean']:+7.2f}±{r['per_window_sharpe_std']:<7.2f} "
              f"{r['per_window_sign_consistency']*100:5.0f}%")

    print("\n=== White Reality Check ===")
    print(f"  基准=现金(0)   p={rc_cash['pvalue']:.4f}  "
          f"最优={rc_cash['winner']}  日均超额={rc_cash['winner_mean_excess_per_period']:+.6f}")
    print(f"  基准=等权均值   p={rc_eq['pvalue']:.4f}  "
          f"最优={rc_eq['winner']}  日均超额={rc_eq['winner_mean_excess_per_period']:+.6f}")
    print("  读法：H0 成立时 p~Uniform(0,1)，p≈0.5 表示'与无 edge 一致'；")
    print("        只有 p 明显偏小才算拒绝 H0。")

    out_dir = run_dir
    payload = {
        "run_name": run_name,
        "dataset": manifest["dataset"],
        "n_obs": n_obs,
        "n_methods": n_methods,
        "n_trials_used_for_dsr": n_trials,
        "n_trials_note": (
            "n_trials_used = 实际比较的方法数。未计入超参搜索（如 RMATS 的 ε、λ_MV）"
            "与多 fidelity 变体，若真实试验数更大，DSR 会偏乐观。"
        ),
        "n_bootstrap": args.n_bootstrap,
        "cost_bps_per_side": 2.0,
        "returns_source": "daily_net_returns.csv（与 MethodMetrics.long_short_sharpe 同源）",
        "white_reality_check": {"cash": rc_cash, "equal_weight": rc_eq},
        "methods": summary.to_dict(orient="records"),
    }
    with open(out_dir / "rolling_summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=float)

    print(f"\n-> {out_dir / 'rolling_summary.json'}")
    print("ROLLING SUMMARY DONE")


if __name__ == "__main__":
    main()