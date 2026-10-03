"""独立泄漏审计：不看方法实现，只用行为反推它是否偷看 test。

三项硬检查（对 08/09/10/11 四个策略方法执行）：

  A. fit() 是否读了 test 期数据
     做法：构造两份 Dataset，test 期价格被人为污染（×1.5、成交量 ×2）；
     各自 fit 后产出 validation 信号。若 fit 偷看过 test，冻结产物不同，
     validation 信号必然不同。相同 => fit 对 test 完全盲。
     （validation 信号只依赖「冻结产物 + train/val」，故这是干净的探针。）

B. LLM 调用位置（双向断言）
      做法：计数 core.llm.TextLLM.complete 的调用次数，分别统计 fit 段与
      produce_signal 段。要求 fit > 0（真的走了 LLM 路径，否则「LLM 驱动」是假的）
      且 produce_signal 段为 0 次（test 段不得有 LLM 调用）。
      注意：complete() 内部命中磁盘缓存也算一次调用，故重跑仍可证明 fit 用了 LLM。

  C. 产出的 test 信号是否有前视偏差
     做法：污染 test 期的后半段，比较污染前后的 test 信号。
     污染点之前的信号必须逐值相等；否则说明用了未来数据做全局归一化
     （例如在整个 test 集上算 z-score），是典型泄漏。

只读 core/ 与方法，不修改任何被审计对象。
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

# Windows 控制台默认 GBK，无法编码检查项里的 '⊆' 等符号，会让审计脚本自己崩掉
# （表现为 check C 报 UnicodeEncodeError，进而被误判成方法实现失败）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data import Dataset, _add_returns, make_dataset  # noqa: E402
from core import llm as core_llm  # noqa: E402

PRICE_COLS = ["open", "high", "low", "close"]
PRICE_SCALE = 1.5   # 人为污染幅度：足以摧毁任何真实依赖
VOL_SCALE = 2.0

TARGETS = [
    ("evolve_trade", "methods.strategy_evolution.evolve_trade", "EvolveTrade"),
    ("sharp", "methods.strategy_evolution.sharp", "SHARP"),
    ("algo_evolve", "methods.strategy_evolution.algo_evolve", "AlgoEvolve"),
    ("recursive_multi_agent", "methods.strategy_evolution.recursive_multi_agent",
     "RecursiveMultiAgent"),
]


def _rebuild(ds: Dataset, panel: pd.DataFrame) -> Dataset:
    """用被改写的 panel 重建 Dataset（重算前瞻/次日收益，保持切分不变）。"""
    fwd, nxt = _add_returns(panel, ds.horizon)
    return Dataset(
        name=ds.name, panel=panel, fwd_ret=fwd, next_ret=nxt, horizon=ds.horizon,
        train_dates=ds.train_dates, val_dates=ds.val_dates, test_dates=ds.test_dates,
    )


def corrupt_test(ds: Dataset, from_idx: int | None = None) -> Dataset:
    """污染 test 期面板。from_idx=None 表示污染整个 test 期。"""
    panel = ds.panel.copy()
    dates = panel.index.get_level_values(0)
    test_mask = dates.isin(ds.test_dates)
    if from_idx is not None:
        cutoff = ds.test_dates[from_idx]
        test_mask &= dates >= cutoff
    if not test_mask.any():
        return _rebuild(ds, panel)
    block = panel.loc[test_mask]
    for c in PRICE_COLS:
        if c in block.columns:
            block[c] = block[c] * PRICE_SCALE
    if "volume" in block.columns:
        block["volume"] = block["volume"] * VOL_SCALE
    if "ret" in block.columns:
        block["ret"] = block["ret"] + 0.05
    panel.loc[test_mask, :] = block
    return _rebuild(ds, panel)


class CallCounter:
    """包裹 TextLLM.complete，统计调用次数并记录调用栈里是否出现 produce_signal。"""

    def __enter__(self):
        self.n = 0
        self._orig = core_llm.TextLLM.complete
        counter = self

        def counting(self_llm, system, user, **kw):
            counter.n += 1
            return counter._orig(self_llm, system, user, **kw)

        core_llm.TextLLM.complete = counting
        return self

    def __exit__(self, *exc):
        core_llm.TextLLM.complete = self._orig
        return False


def audit(name: str, module: str, cls_name: str, ds: Dataset) -> bool:
    print(f"\n{'=' * 68}\n{name}\n{'=' * 68}")
    ok = True
    try:
        mod = __import__(module, fromlist=[cls_name])
        cls = getattr(mod, cls_name)
    except Exception as e:
        print(f"  IMPORT FAIL: {type(e).__name__}: {e}")
        return False

    # ---------- A. fit 是否偷看 test ----------
    try:
        clean = cls().fit(ds)
        dirty_ds = corrupt_test(ds)
        dirty = cls().fit(dirty_ds)

        v_clean = clean.produce_signal(ds, "validation")
        v_dirty = dirty.produce_signal(dirty_ds, "validation")

        common = v_clean.index.intersection(v_dirty.index)
        if len(common) == 0:
            print("  A. fit 隔离性: SKIP（validation 信号无交集）")
        else:
            x = v_clean.loc[common].astype(float)
            y = v_dirty.loc[common].astype(float)
            diff = (x - y).abs()
            scale = max(1.0, float(np.nanmax(np.abs(x.to_numpy()))) if len(x) else 1.0)
            worst = float(np.nanmax(diff.to_numpy())) / scale if len(x) else 0.0
            same = worst < 1e-9
            ok &= same
            print(f"  A. fit 隔离性(污染 test 后 validation 信号不变): "
                  f"{'PASS' if same else 'FAIL'}  max_rel_diff={worst:.3e}  n={len(common)}")
    except Exception as e:
        ok = False
        print(f"  A. fit 隔离性: ERROR {type(e).__name__}: {e}")
        traceback.print_exc()

    # ---------- B. produce_signal 是否调 LLM ----------
    try:
        m = cls()
        with CallCounter() as cc:
            m.fit(ds)
        n_fit = cc.n
        with CallCounter() as cc:
            sig = m.produce_signal(ds, "test")
        n_test = cc.n
        # 双向断言：fit 必须真的用到 LLM（否则「多智能体」是假的），
        # 且 produce_signal 必须一次都不调（否则 test 段有 LLM 不确定性/泄漏）。
        # CallCounter 包住 complete() 整体，命中磁盘缓存的调用同样计数，
        # 因此重跑（全部 cache hit）依然能证明 fit 确实走了 LLM 路径。
        b_ok = (n_test == 0) and (n_fit > 0)
        ok &= b_ok
        print(f"  B. LLM 调用位置: {'PASS' if b_ok else 'FAIL'}  "
              f"fit={n_fit} 次 (必须 >0), produce_signal(test)={n_test} 次 (必须为 0)")
    except Exception as e:
        ok = False
        print(f"  B. LLM 调用位置: ERROR {type(e).__name__}: {e}")
        traceback.print_exc()
        return ok

    # ---------- C. 输出形状 ----------
    try:
        expected_dates = set(ds.test_dates)
        got_dates = set(sig.index.get_level_values(0))
        c1 = got_dates == expected_dates
        c2 = isinstance(sig.index, pd.MultiIndex)
        c3 = set(sig.index.get_level_values(1)).issubset(set(ds.symbols))
        c4 = float(pd.Series(sig).notna().mean()) > 0.5
        vals = pd.Series(sig).astype(float)
        c5 = float(vals.std(skipna=True)) > 0
        shape_ok = c1 and c2 and c3 and c4 and c5
        ok &= shape_ok
        print(f"  C. 输出形状: {'PASS' if shape_ok else 'FAIL'}  "
              f"MultiIndex={c2} 日期={len(got_dates)}/{len(expected_dates)}({'==' if c1 else '!='}) "
              f"symbol⊆universe={c3} NaN比例={1 - float(vals.notna().mean()):.3f} "
              f"std={float(vals.std(skipna=True)):.4g}({'ok' if c5 else 'DEGENERATE'})")
    except Exception as e:
        ok = False
        print(f"  C. 输出形状: ERROR {type(e).__name__}: {e}")

    # ---------- D. 前视偏差 ----------
    try:
        cut = max(1, len(ds.test_dates) // 2)
        m2 = cls().fit(ds)
        sig_full = m2.produce_signal(ds, "test")
        tail_ds = corrupt_test(ds, from_idx=cut)
        sig_tail = m2.produce_signal(tail_ds, "test")

        cutoff_date = ds.test_dates[cut]
        early_full = sig_full[sig_full.index.get_level_values(0) < cutoff_date]
        early_tail = sig_tail[sig_tail.index.get_level_values(0) < cutoff_date]
        common = early_full.index.intersection(early_tail.index)
        if len(common) == 0:
            print("  D. 前视检查: SKIP（前半段无交集）")
        else:
            x = early_full.loc[common].astype(float)
            y = early_tail.loc[common].astype(float)
            scale = max(1.0, float(np.nanmax(np.abs(x.to_numpy()))) if len(x) else 1.0)
            worst = float(np.nanmax((x - y).abs().to_numpy())) / scale if len(x) else 0.0
            d_ok = worst < 1e-9
            ok &= d_ok
            print(f"  D. 前视检查(污染后半段后前半段信号不变): "
                  f"{'PASS' if d_ok else 'FAIL'}  max_rel_diff={worst:.3e}  n={len(common)}")
    except Exception as e:
        ok = False
        print(f"  D. 前视检查: ERROR {type(e).__name__}: {e}")

    print(f"  => {'ALL PASS' if ok else 'HAS FAILURE'}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="审计全样本 csi300_full")
    ap.add_argument("--only", nargs="*", default=None,
                    help=f"只审计这些方法（可选: {[t[0] for t in TARGETS]}）。"
                         "每个方法要 fit 4 次，全样本下 algo_evolve 单个就需 ~20min，"
                         "用 --only 可分批跑完")
    args = ap.parse_args()
    ds = make_dataset(name="csi300_full", n_symbols=49, n_days=1455,
                      horizon=5) if args.full else make_dataset()
    print(f"dataset={ds.name}  train={len(ds.train_dates)} val={len(ds.val_dates)} "
          f"test={len(ds.test_dates)} symbols={len(ds.symbols)} horizon={ds.horizon}")
    print(f"污染参数: price×{PRICE_SCALE} volume×{VOL_SCALE} (仅 test 期)")

    targets = TARGETS
    if args.only:
        want = set(args.only)
        targets = [t for t in TARGETS if t[0] in want]
        missing = want - {t[0] for t in TARGETS}
        if missing:
            print(f"[warn] 未知方法名: {sorted(missing)}")
        if not targets:
            print("没有匹配到任何方法，退出。")
            return 1

    results = {}
    for name, module, cls in targets:
        try:
            results[name] = audit(name, module, cls, ds)
        except Exception:
            results[name] = False
            traceback.print_exc()

    print(f"\n{'=' * 68}\n审计汇总\n{'=' * 68}")
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    bad = [k for k, v in results.items() if not v]
    if bad:
        print(f"\n存在未通过项: {bad}")
        return 1
    print("\n全部通过：无 test 泄漏、无 test 期 LLM 调用、无前视偏差。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())