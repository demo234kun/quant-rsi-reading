"""
滚动窗口入口：在**多段不重叠的 test 段**上重复整套 baseline，补上 §8 缺的两层检验。

与 run_all.py 的区别：
  - run_all.py 只有一段连续 test（84 天 / 291 天），无法回答"是否只在某段行情有效"
  - 本脚本把 test 切成 n_windows 段互不重叠的窗口，逐窗重新 fit + 评估，
    test 段拼起来正好覆盖样本末尾（最近的行情一定被评到）

防泄漏保证（由 verify_windows.py 的性质测试守住）：
  - 每窗 train < val < test 严格按时间不重叠
  - 各窗 test 段互不重叠，拼起来无重复计数
  - fit() 只看 train+val，produce_signal("test") 不看 test 标签

用法：
    python scripts/run_rolling.py                      # 5 窗 × 58 天（默认）
    python scripts/run_rolling.py --full               # 全样本
    python scripts/run_rolling.py --n-windows 8 --test-size 60
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

# Windows 控制台默认 GBK，会把中文与 × 打成乱码；统一强制 UTF-8。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from core.data import make_dataset, rolling_window_splits, window_view
from core.interface import save_metrics
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_all import build_methods

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="全样本（49 只 × 1455 天）")
    ap.add_argument("--n-symbols", type=int, default=15)
    ap.add_argument("--n-days", type=int, default=420)
    ap.add_argument("--n-windows", type=int, default=5)
    ap.add_argument("--test-size", type=int, default=58)
    ap.add_argument("--val-size", type=int, default=42)
    ap.add_argument("--min-train-size", type=int, default=252)
    ap.add_argument("--sliding", action="store_true",
                    help="滑窗 train（默认 expanding：用尽所有历史）")
    ap.add_argument("--train-size", type=int, default=252)
    ap.add_argument("--only", nargs="*", default=None,
                    help="只跑这些方法名（默认全部）。滚动窗口的 prompt 与单窗不同，"
                         "缓存基本不会命中，用 --only 先验证管线可显著省 LLM 调用")
    args = ap.parse_args()

    if args.full:
        ds = make_dataset(name="csi300_full", n_symbols=49, n_days=1455, horizon=5)
    else:
        ds = make_dataset(name="csi300_small", n_symbols=args.n_symbols,
                          n_days=args.n_days, horizon=5)

    all_dates = ds.dates
    splits = rolling_window_splits(
        all_dates, n_windows=args.n_windows, test_size=args.test_size,
        val_size=args.val_size, min_train_size=args.min_train_size,
        expanding=not args.sliding, train_size=args.train_size,
    )
    if not splits:
        print("窗口参数无法切出任何 test 段，请调小 --test-size / --val-size "
              "或增大 --n-days")
        return

    run_name = f"rolling_{ds.name}_w{len(splits)}"
    print(f"dataset={ds.name} symbols={ds.symbols.nunique()} "
          f"dates={len(all_dates)} windows={len(splits)}")
    for i, (tr, va, te) in enumerate(splits):
        print(f"  w{i}: train={len(tr)} val={len(va)} test={len(te)} "
              f"[{te.min().date()} .. {te.max().date()}]")

    # 每个方法在每个窗口都要重新 fit（窗口的 train 不同），
    # 所以 results/rolling/<dataset>/<method>/w<i>.json。
    out_root = RESULTS / "rolling" / run_name
    out_root.mkdir(parents=True, exist_ok=True)

    # 汇总用的日净收益长表：index=date, columns=method
    net_frames: dict[str, list[pd.Series]] = {}
    n_trials = 0

    methods = build_methods()
    if args.only:
        want = set(args.only)
        methods = [m for m in methods if m.name in want]
        missing = want - {m.name for m in methods}
        if missing:
            print(f"[warn] 未匹配到方法: {sorted(missing)}")
        if not methods:
            print("没有匹配到任何方法，退出。")
            return

    # run() 内部会先 fit() 再评估，所以每个窗口都会用该窗自己的 train 重新拟合。
    for m in methods:
        n_trials += 1
        method_dir = out_root / m.name
        method_dir.mkdir(parents=True, exist_ok=True)
        nets: list[pd.Series] = []
        for i, (tr, va, te) in enumerate(splits):
            wds = window_view(ds, f"{run_name}_w{i}", tr, va, te)
            met, net = m.run(wds)
            save_metrics(met, method_dir, f"w{i}")
            nets.append(net.rename(m.name))
            print(f"[{m.name:22s}] w{i} IC={met.mean_ic:+.4f} "
                  f"RankIC={met.mean_rank_ic:+.4f} Sharpe={met.long_short_sharpe:+.2f} "
                  f"days={met.n_test_days} [{met.fidelity}]")
        net_frames[m.name] = nets

    # 各方法 test 段拼接（段间不重叠 => 拼接即完整日频序列）
    net_long = pd.DataFrame(
        {name: pd.concat(series) for name, series in net_frames.items()}
    ).sort_index()
    net_long.index.name = "date"
    net_long.to_csv(out_root / "daily_net_returns.csv", encoding="utf-8")

    manifest = {
        "dataset": ds.name,
        "run_name": run_name,
        "n_symbols": int(ds.symbols.nunique()),
        "n_dates_total": int(len(all_dates)),
        "n_windows": len(splits),
        "n_methods": n_trials,
        "test_size": args.test_size,
        "val_size": args.val_size,
        "min_train_size": args.min_train_size,
        "expanding_train": not args.sliding,
        "train_size": args.train_size if args.sliding else None,
        "horizon": ds.horizon,
        "windows": [
            {
                "index": i,
                "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(te)),
                "train_start": str(tr.min().date()), "train_end": str(tr.max().date()),
                "val_start": str(va.min().date()), "val_end": str(va.max().date()),
                "test_start": str(te.min().date()), "test_end": str(te.max().date()),
            }
            for i, (tr, va, te) in enumerate(splits)
        ],
        "daily_net_returns": "daily_net_returns.csv",
        "total_test_days": int(len(net_long)),
        "methods": sorted(net_frames),
    }
    with open(out_root / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nnet returns: {net_long.shape[0]} days × {net_long.shape[1]} methods "
          f"-> {out_root / 'daily_net_returns.csv'}")
    print("ROLLING DONE")


if __name__ == "__main__":
    main()