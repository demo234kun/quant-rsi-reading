# Baselines — 统一可插拔的 RSI 量化研究复现框架

本目录对 `quant-rsi-reading` 收录的 RSI（Recursive Self-Improvement，递归自我改进）论文做
**可运行复现**。核心目标：**同一批真实数据，用同一套接口与评估器，把不同论文方法压成可比较的 baseline。**

> 硬约束：所有数字均由真实数据在本地真实跑出，无任何模拟 / 虚构 / 推演。复现不完整处用
> `fidelity` 与 `notes` 明确标注，绝不冒充完全复现。

---

## 1. 设计理念

**所有方法都规约为「产出一个预测信号」**——一个 `MultiIndex (date, symbol)` 的 `Series`，
再由**同一个评估器**计算 IC / RankIC / 多空组合表现。这样：

- 因子方法（表达式）、数据方法（合成/特征）、策略方法（指标/规则）可在**同一批数据**上横向比较；
- 新增方法只需实现接口，无需改动数据与评估，真正做到可插拔；
- 数据切分、评估规则对所有方法冻结，防止方法侧改动切分造成数据泄露。

统一管线：

```
真实 parquet ──► Dataset（严格时间切分 train/val/test）
                        │
                        ▼
        Method.fit()（在 train/val 上学习，可多轮进化）
                        │
                        ▼
 Method.produce_signal()（test 信号，只依赖 test 及之前）
                        │
                        ▼
  统一 Evaluator（IC / RankIC / 多空回测，扣成本）
                        │
                        ▼
        results/<dataset>/<method>.json（真实结果）
```

---

## 2. 目录结构

```
baselines/
├── core/                       # 框架核心（与具体方法无关）
│   ├── data.py                 # 数据层：Dataset、make_dataset、真实 parquet 加载
│   ├── interface.py            # 抽象基类 BaselineMethod、统一指标 MethodMetrics、保存
│   ├── evaluator.py            # 统一评估：横截面 IC/RankIC、多空回测（扣成本）
│   ├── expr.py                 # 安全表达式引擎（白名单 AST）
│   ├── indicators.py           # 技术指标（RSI/EMA/MACD/ATR/布林，按 symbol 分组）
│   ├── llm.py                  # 可插拔 LLM 后端（无 key 时用规则变异）
│   ├── evolution.py            # 通用符号进化（变异→评估→选择）
│   └── stats.py                # 统计检验：Deflated Sharpe、White Reality Check、滚动 Sharpe
├── methods/
│   ├── factor_lib.py           # 静态对照因子（不进化）
│   ├── data_evolution/         # 12 R&D-Agent-Quant / 13 TradingGroup / 14 FactorEngine
│   ├── factor_evolution/       # 01 AQuA / 03 Astar / 06 AutoScientist / 07 QuantEvolver
│   └── strategy_evolution/     # 08 EvolveTrade / 09 SHARP / 10 AlgoEvolve / 11 RMATS
├── scripts/
│   ├── run_all.py              # ★ 统一全量入口（小样本 / --full）
│   ├── run_rolling.py          # ★ 滚动窗口入口（多段不重叠 test）
│   ├── build_rolling_summary.py# 滚动汇总：DSR + White Reality Check
│   ├── build_summary.py        # 从 JSON 汇总生成对比表
│   ├── audit_leakage.py        # 泄漏与 LLM 调用审计（[--full]）
│   ├── smoke_test.py           # 冒烟测试
│   └── test_*.py               # 分分类测试
├── results/<dataset>/*.json    # 真实结果
└── results/rolling/<run>/      # 滚动窗口：每方法每窗 JSON + 日净收益 + 汇总
```

---

## 3. 快速开始

```bash
# 小样本（默认：15 只 × 420 交易日，train 252 / val 84 / test 84）
python scripts/run_all.py

# 全样本（49 只 × 1455 交易日，较慢）
python scripts/run_all.py --full

# 仅生成对比表（从已有 JSON）
python scripts/build_summary.py

# 滚动窗口：5 段互不重叠的 test（默认全样本口径见 §4.3）
python scripts/run_rolling.py --full --n-windows 5 --test-size 100 --val-size 42

# 对滚动结果做多重检验校正（DSR + White Reality Check）
python scripts/build_rolling_summary.py --full --n-windows 5 --n-bootstrap 10000

# 泄漏与 LLM 调用审计
python scripts/audit_leakage.py [--full]

# 全样本下 algo_evolve 单个方法就要 ~6min，用 --only 分批跑完
python scripts/audit_leakage.py --full --only evolve_trade sharp recursive_multi_agent
python scripts/audit_leakage.py --full --only algo_evolve
```

> 数据依赖：真实 CSI300 前复权日线，由 `project/src/data/real_akshare.py` 经 akshare 下载并缓存为
> parquet（`project/data/csi300_daily.parquet`，已被 `.gitignore`）。框架不自带任何虚构数据。

---

## 4. Baseline 对比表

同一套接口在**两套真实数据**上跑出：`csi300_small`（15 只 × 84 test 日）与 `csi300_full`
（49 只 × 291 test 日）。**任何结论必须两套一起看**——§5 显示单套样本下多个方法的 IC 符号会翻转，
只看一套会得出错误结论。

### 4.1 小样本 `csi300_small`（15 只 × 84 test 日）

> 真实数据：**15 只 × 84 个测试日**，horizon=5，信号方向在 **validation** 估计（test 固定，防选择泄漏），
> 多空组合用次日收益、等权 top/bottom，扣 **2bp/单边** 成本。

#### 静态对照因子

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `low_vol_20` | — | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | faithful_core |
| `momentum_20` | — | -0.0828 | -0.254 | -0.0965 | -0.298 | +0.027 | +0.08 | -0.167 | +0.857 | faithful_core |
| `reversal_5` | — | +0.0271 | +0.081 | +0.0457 | +0.138 | -0.519 | -1.49 | -0.245 | +1.548 | faithful_core |
| `volume_ratio` | — | +0.0629 | +0.232 | +0.0589 | +0.239 | -0.907 | -2.97 | -0.281 | +0.849 | faithful_core |

#### 数据进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `factor_engine` | 14 FactorEngine | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | llm_replaced_by_rule |
| `rd_agent_quant` | 12 R&D-Agent-Quant | +0.0491 | +0.151 | +0.1003 | +0.277 | -0.331 | -1.09 | -0.217 | +0.389 | llm_replaced_by_rule |
| `trading_group` | 13 TradingGroup | -0.0296 | -0.085 | -0.0637 | -0.178 | +0.267 | +0.75 | -0.185 | +2.254 | simplified |

#### 因子进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `aqua` | 01 AQuA | +0.0188 | +0.073 | +0.0157 | +0.060 | -0.440 | -1.64 | -0.205 | +0.730 | llm_replaced_by_rule |
| `astar` | 03 Astar | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | llm_replaced_by_rule |
| `auto_scientist` | 06 AutoScientist | +0.0271 | +0.085 | +0.0863 | +0.245 | -0.151 | -0.52 | -0.198 | +0.373 | llm_replaced_by_rule |
| `quant_evolver` | 07 QuantEvolver | -0.0460 | -0.193 | -0.0434 | -0.186 | -0.277 | -1.00 | -0.197 | +1.365 | weight_rft_omitted |

#### 策略进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `algo_evolve` | 10 AlgoEvolve | +0.0175 | +0.056 | +0.0303 | +0.096 | -0.233 | -0.79 | -0.175 | +1.016 | simplified |
| `evolve_trade` | 08 EvolveTrade | -0.0970 | -0.273 | -0.1296 | -0.409 | +0.338 | +1.03 | -0.152 | +0.968 | paper_ablation_added |
| `recursive_multi_agent` | 11 RecursiveMultiAgent | +0.0304 | +0.120 | +0.1060 | +0.325 | -0.062 | -0.20 | -0.176 | +0.849 | faithful_core |
| `sharp` | 09 SHARP | -0.0054 | -0.020 | -0.0026 | -0.008 | +0.039 | +0.15 | -0.244 | +1.103 | paper_ablation_added |

### 4.2 全样本 `csi300_full`（49 只 × 291 test 日）

> 与 §4.1 同接口、同 horizon、同 2bp/单边成本，只是样本更长更宽。**这张表推翻了 §4.1 的多条结论**，
> 是判断可信度的主要依据。

#### 静态对照因子

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `low_vol_20` | — | +0.0399 | +0.185 | +0.0452 | +0.211 | +0.224 | +1.36 | -0.118 | +0.186 | faithful_core |
| `momentum_20` | — | -0.0367 | -0.150 | -0.0404 | -0.161 | -0.039 | -0.16 | -0.226 | +0.720 | faithful_core |
| `reversal_5` | — | +0.0073 | +0.031 | +0.0080 | +0.033 | -0.185 | -0.80 | -0.338 | +1.395 | faithful_core |
| `volume_ratio` | — | -0.0204 | -0.107 | -0.0245 | -0.134 | -0.016 | -0.09 | -0.223 | +0.844 | faithful_core |

#### 数据进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `factor_engine` | 14 FactorEngine | +0.0498 | +0.239 | +0.0549 | +0.264 | +0.083 | +0.50 | -0.125 | +0.321 | llm_replaced_by_rule |
| `rd_agent_quant` | 12 R&D-Agent-Quant | +0.0036 | +0.019 | +0.0025 | +0.014 | +0.042 | +0.24 | -0.162 | +1.186 | llm_replaced_by_rule |
| `trading_group` | 13 TradingGroup | -0.0150 | -0.075 | -0.0127 | -0.070 | -0.100 | -0.56 | -0.213 | +1.346 | simplified |

#### 因子进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `aqua` | 01 AQuA | +0.0529 | +0.245 | +0.0573 | +0.267 | +0.150 | +0.92 | -0.141 | +0.449 | llm_replaced_by_rule |
| `astar` | 03 Astar | +0.0459 | +0.220 | +0.0524 | +0.252 | +0.135 | +0.80 | -0.131 | +0.326 | llm_replaced_by_rule |
| `auto_scientist` | 06 AutoScientist | +0.0459 | +0.220 | +0.0524 | +0.252 | +0.135 | +0.80 | -0.131 | +0.326 | llm_replaced_by_rule |
| `quant_evolver` | 07 QuantEvolver | +0.0527 | +0.214 | +0.0639 | +0.264 | +0.232 | +1.21 | -0.170 | +0.698 | weight_rft_omitted |

#### 策略进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `algo_evolve` | 10 AlgoEvolve | +0.0017 | +0.009 | -0.0113 | -0.055 | -0.087 | -0.53 | -0.218 | +0.963 | simplified |
| `evolve_trade` | 08 EvolveTrade | -0.0411 | -0.176 | -0.0332 | -0.136 | -0.245 | -1.12 | -0.373 | +1.035 | paper_ablation_added |
| `recursive_multi_agent` | 11 RecursiveMultiAgent | -0.0067 | -0.050 | +0.0034 | +0.020 | -0.180 | -1.25 | -0.312 | +2.173 | faithful_core |
| `sharp` | 09 SHARP | +0.0098 | +0.046 | +0.0107 | +0.047 | -0.225 | -1.10 | -0.360 | +1.071 | paper_ablation_added |

> 复现命令：`python scripts/run_all.py`（小样本）/ `python scripts/run_all.py --full`（全样本）；
> 表格由 `scripts/build_summary.py` 从 `results/<dataset>/*.json` 自动生成，**勿手工改数字**。
> 08–11 四法已接入**真实 LLM**（DeepSeek）：小样本 fit 期调用 evolve_trade 6 / sharp 10 /
> algo_evolve 66 / rmats 10；全样本调用次数相同但 prompt 不同（缓存未命中，实测 rmats
> `api_call=10, cache_hit=0, error=0`）。两套样本 **test 期一律 0 次调用**，
> 用 `python scripts/audit_leakage.py [--full]` 复核，两套均 **16/16 PASS**。

### 4.3 滚动窗口 + 多重检验校正（`rolling_csi300_full_w5`）

§4.2 的 test 段仍是**一段连续时间**，因此"某方法是否只在某段行情有效"无法回答，
表里的"最优"也没有扣除**挑出最优这件事本身**的代价。本节补上这两层。

**设置**（全样本真实数据，49 只 × 1455 天，horizon=5，2bp/单边）：

- test 切成 **5 段互不重叠的窗口，每段 100 天**，合计 **500 个 test 日**
  （2022-12-09 → 2024-12-31），每段都覆盖到不同时段；
- train 用 **expanding**（用尽当时全部历史：913 → 1013 → 1113 → 1213 → 1313 天），val 固定 42 天；
- 每窗**重新 fit**，test 段拼接成 500 天日频净收益，直接喂给统计检验；
- DSR / RC 的输入与上表 Sharpe **同源**（同一 `net` 序列、同一方向、同一成本），
  由 `evaluate_signal()` 直接返回，不做二次回测。

| 方法 | 全段 Sharpe | DSR | DSR p | 逐窗 Sharpe 均值±std | 逐窗同号率 |
|---|---|---|---|---|---|
| `low_vol_20` | +1.25 | 0.4977 | 0.5023 | +1.29 ± 0.78 | 100% |
| `rd_agent_quant` | +0.70 | 0.2186 | 0.7814 | +0.71 ± 1.05 | 60% |
| `algo_evolve` | +0.70 | 0.2180 | 0.7820 | +0.76 ± 0.78 | 80% |
| `momentum_20` | +0.62 | 0.1871 | 0.8129 | +0.65 ± 1.15 | 80% |
| `astar` | +0.57 | 0.1670 | 0.8330 | +0.56 ± 1.32 | 80% |
| `factor_engine` | +0.44 | 0.1236 | 0.8764 | +0.52 ± 1.04 | 80% |
| `volume_ratio` | +0.34 | 0.0975 | 0.9025 | +0.40 ± 1.90 | 60% |
| `auto_scientist` | +0.01 | 0.0397 | 0.9603 | +0.04 ± 1.07 | 60% |
| `evolve_trade` | +0.01 | 0.0394 | 0.9606 | +0.00 ± 1.72 | 60% |
| `quant_evolver` | −0.03 | 0.0355 | 0.9645 | −0.01 ± 0.92 | 80% |
| `aqua` | −0.18 | 0.0218 | 0.9782 | −0.17 ± 1.74 | 60% |
| `sharp` | −0.31 | 0.0136 | 0.9864 | −0.28 ± 1.39 | 60% |
| `trading_group` | −0.57 | 0.0050 | 0.9950 | −0.31 ± 2.90 | 60% |
| `reversal_5` | −0.59 | 0.0047 | 0.9953 | −0.63 ± 0.98 | 80% |
| `recursive_multi_agent` | −0.69 | 0.0033 | 0.9967 | −0.71 ± 1.17 | 80% |

> 复现：`python scripts/run_rolling.py --full --n-windows 5 --test-size 100 --val-size 42`
> 后接 `python scripts/build_rolling_summary.py --full --n-windows 5 --n-bootstrap 10000`；
> 数字由 `results/rolling/rolling_csi300_full_w5/rolling_summary.json` 自动生成，**勿手工改数字**。

**White Reality Check**（联合检验：是否真的存在一个显著优于基准的策略）

| 基准 | p 值 | 最优方法 | 该方法日均超额 |
|---|---|---|---|
| 现金（0） | **0.4197** | `low_vol_20` | +0.000875 |
| 15 方法等权均值 | **0.5862** | `low_vol_20` | +0.000741 |

> p 值随 `n_bootstrap` 稳定（2000 / 10000 / 50000 → 0.4173 / 0.4197 / 0.4263），结论不依赖重采样次数。
> 注意读法：**H0 成立时 p ≈ Uniform(0,1)**，所以 p≈0.4 的含义是"与无 edge 完全一致"，
> **不是**"边缘显著"；只有 p 明显偏小才构成拒绝 H0 的证据。

**`n_trials` 敏感性**——这才是本节最重要的一张表：

| `n_trials` | 期望最优 Sharpe `SR0` | `low_vol_20` DSR | p |
|---|---|---|---|
| 1（天真：只测一个） | +0.0000 | 0.9598 | **0.0402** |
| **15（实际比较的方法数）** | **+0.0792** | **0.4977** | **0.5023** |
| 30（计入部分超参变体） | +0.0927 | 0.3800 | 0.6200 |
| 45（计入全部 fidelity/超参变体） | +0.1000 | 0.3205 | 0.6795 |
| 100（悲观上界） | +0.1132 | 0.2241 | 0.7759 |

`low_vol_20` 的 500 天日频 Sharpe 是 +1.25，**单看这一个数字毫无问题**。
但只要承认"我们是从 15 个方法里挑出最好的那个"，期望最优 Sharpe 就抬到 +0.079，
DSR 从 0.96 掉到 0.50——**从"显著"掉到"抛硬币"**。这就是数据窥探（data snooping）
的代价，也是为什么 §4.2 的表不能直接读成"哪个方法更好"。

---

## 5. 关键发现（诚实，不美化）

> 本节已按**两套样本**重写。`--full` 跑完后，§4.1 小样本得出的多条结论被推翻并已撤回；
> 保留下来的是两套样本都支持的结论。

### 5.1 跨样本符号翻转普遍存在，单一样本不可信

同一份代码、同一套接口，只换样本，以下方法符号直接翻转：

| 方法 | `csi300_small` IC | `csi300_full` IC | 翻转 |
|---|---|---|---|
| `volume_ratio` | +0.0629 | **−0.0204** | ✅ 翻负 |
| `quant_evolver` | −0.0460 | **+0.0527** | ✅ 翻正 |
| `algo_evolve`（RankIC） | +0.0303 | **−0.0113** | ✅ 翻负 |
| `sharp` | −0.0054 | **+0.0098** | ✅ 翻正 |
| `evolve_trade`（Sharpe） | +1.03 | **−1.12** | ✅ 翻负 |

量级也普遍收缩 2–4 倍（`low_vol_20` +0.0894→+0.0399，`momentum_20` −0.0828→−0.0367）。
**结论：84 天小样本上的 IC 符号与排序不可作为选型依据**，任何单一样本排名都应视为噪声。

### 5.2 撤回：「低波动是最强信号」

§4.1 曾把 `low_vol_20`（IC=+0.0894、Sharpe=+3.08）写成最强信号。**全样本下不成立**：
`low_vol_20` IC 掉到 +0.0399、Sharpe +1.36，被 `aqua`(+0.0529)、`quant_evolver`(+0.0527)、
`factor_engine`(+0.0498) 全部超过。低波动异象本身仍在（两样本均为正），但**不是本基准里最强的**。

### 5.3 撤回：「接入 LLM 后 RMATS 转正」

这是本次最需要纠正的一条。§4.1 曾据 84 天结果称：接入真实 LLM 后 `recursive_multi_agent`
IC 由负转正（+0.0304）、RankIC=+0.1060 且「四法中横截面排序最好」，并推断原结论「部分源于 LLM 缺席」。

**全样本下该推断不成立**：

| `recursive_multi_agent` | small (84d) | full (291d) |
|---|---|---|
| 均值IC | +0.0304 | **−0.0067** |
| RankIC | +0.1060 | **+0.0034** |
| RankICIR | +0.325 | **+0.020**（弱 16 倍） |
| Sharpe | −0.20 | **−1.25** |
| 换手 | +0.849 | +2.173 |

84 天上的「转正」是窗口噪声，不是 LLM 的功劳。**接入 LLM 并不能挽救策略进化类方法**；
小样本上 RMATS 看起来最好，恰恰是因为它在 84 天窗口里过拟合了那个窗口。
我此前把「符号翻转」解读成「LLM 缺席所致」，是过度解读单一样本。

### 5.4 两套样本都支持的结论

1. **策略进化四法在本基准上无可观测 edge**：全样本 IC 全部接近 0
   （−0.0411 / +0.0017 / +0.0098 / −0.0067），且 **Sharpe 全为负**
   （−1.12 / −0.53 / −1.10 / −1.25）。注意这是"本基准上无证据"，不等于"论文方法无效"——
   语义输入只有价格、无新闻/基本面，且未做权重级自改进（§8）。
2. **换手是系统性拖累，且这是结构性的**：全样本 `recursive_multi_agent` 换手 **+2.173/日**
   为 15 个方法之最，2bp/单边成本下即使 IC 为正也会被成本吃掉。这条机制在两套样本都成立
   （small +0.849 → full +2.173），是**唯一能跨样本解释负 Sharpe 的因素**。
3. **`momentum_20` 是唯一符号稳定的静态因子**：两样本 IC 均为负
   （−0.0828 → −0.0367），20 日动量在该 A 股区间呈反转。
4. **进化搜索会收敛到同一解**：`astar` 与 `auto_scientist` 在**两套样本上数字完全相同**
   （small +0.0894/+0.0922，full +0.0459/+0.0524），说明二者独立收敛到同一因子——
   但收敛目标随样本改变（小样本是 `low_vol_20`，全样本不是）。
5. **`fidelity` 是运行结果而非静态标签**：凭据缺失或调用失败会降级为确定性兜底并自动改标
   `llm_replaced_by_rule`。本次两套运行 LLM 均可用，故 08/09 标 `paper_ablation_added`、
   10 标 `simplified`、11 标 `faithful_core`。**读他人结果必须连同 `fidelity` 与 `notes` 一起看。**

### 5.5 滚动窗口 + 多重检验后，没有任何方法站得住（§4.3）

这是本仓库目前**最强的负面结论**，且它比 §5.1 的"符号翻转"更根本：
即使符号不变、Sharpe 为正，**扣除"从 15 个里挑最好的"这件事本身**之后，edge 也不成立。

1. **White Reality Check 无法拒绝 H0**：对现金基准 p=0.4197，对等权基准 p=0.5862
   （p 随 `n_bootstrap` 稳定）。500 天、15 个方法，**没有一个显著优于零**。
2. **DSR 最高的 `low_vol_20` 也只有 0.4977**（p=0.5023）——即"抛硬币"，
   尽管它的 5 个窗口 Sharpe **全部为正**（同号率 100%，均值 +1.29）。
   **符号稳定 ≠ 统计显著**，这两件事必须分开说。
3. **`n_trials` 假设的代价是决定性的**：从 n_trials=1 到 15，
   `low_vol_20` 的 DSR 由 0.96（p=0.040，"显著"）掉到 0.50（p=0.50）。
   换句话说，**如果只报告最优方法的 Sharpe 和 p 值，就一定会得到一个假显著结果**。
4. **策略进化四法排在最末端**：`recursive_multi_agent` DSR=0.0033、`sharp` 0.0136、
   `evolve_trade` 0.0394、`algo_evolve` 0.2180。它们的逐窗 Sharpe 标准差也最大
   （`evolve_trade` ±1.72、`aqua` ±1.74），即**符号本身就在窗与窗之间来回翻**。
5. **逐窗 Sharpe 的离散度普遍大于均值**（如 `volume_ratio` +0.40 ± 1.90、
   `trading_group` −0.31 ± 2.90）。这直接量化了 §5.1 的现象：
   单窗口读数几乎全是噪声。

> 因此 §4.1 / §4.2 的表格**只能**用来描述"跑出来是什么"，**不能**用来选型。
> 要在本基准上宣称某个方法有效，最低门槛是：DSR 在 n_trials 计入全部超参变体后仍 > 0.95，
> 且 White RC（现金基准）p < 0.05。当前 15 个方法**无一满足**。

### 5.6 一句话总结

在 49 只 × 291 test 日（滚动口径 500 test 日）、horizon=5、2bp/单边、日频、仅价格特征的
口径下，**15 个方法没有一个显示出稳定且可交易的 edge**；小样本上出现过的高 IC / 高 Sharpe
基本都是窗口效应与数据窥探的产物。本仓库的价值在于
**接口一致 + 泄漏审计 + fidelity 标注 + 多重检验校正**，而非某个方法跑赢。

---

## 6. 保真度（fidelity）说明

| 标签 | 含义 |
|------|------|
| `faithful_core` | 核心机制忠实复现 |
| `llm_replaced_by_rule` | 论文中的 LLM 由规则变异（AST 换字段/窗口/算子）替代 |
| `simplified` | 对原机制做了简化 |
| `policy_text_approx` | 自然语言 policy 文本用指标权重近似 |
| `meta_evolution_approx` | 元进化用启发式集合 + 选择近似 |
| `weight_rft_omitted` | LoRA/RFT 等权重更新未复现 |
| `paper_ablation_added` | 核心机制已实现，且额外补做了论文的消融对照（如 returns-only vs returns+traces） |

> **LLM 已真实接入**：本环境通过 `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` 使用真实
> DeepSeek 后端（`deepseek-chat`），08/09/10/11 的 LLM 提案步骤均已实际调用，非规则替代。
> 响应按 `system+user+model` 哈希落盘缓存到 `baselines/cache/llm/<tag>/`，重跑默认命中缓存；
> 删除该目录或改 `temperature/max_tokens` 会触发重新调用。
> 若凭据缺失或调用最终失败，`TextLLM` 抛 `LLMUnavailable`，各方法捕获后降级为确定性兜底，
> 并把 `fidelity` 改写为 `llm_replaced_by_rule`、`notes` 追加降级说明——**降级是显式可见的，不会静默冒充**。
> 可用 `python scripts/audit_leakage.py [--full]` 复核每个方法的 LLM 调用次数与 test 段零调用；
> 小样本与全样本两套均已跑过，**均 16/16 PASS**（fit 隔离与前视检查 `max_rel_diff=0.000e+00`）。

---

## 7. 如何新增一个方法

继承 `core.interface.BaselineMethod`，实现 `fit` 与 `produce_signal`：

```python
class MyMethod(BaselineMethod):
    def __init__(self):
        self.name = "my_method"
        self.category = "factor_evolution"   # data_ / factor_ / strategy_
        self.paper_id = "NN"
        self.fidelity = "faithful_core"
        self.notes = "..."

    def fit(self, ds: Dataset):
        ...   # 只用 train/val，可多轮进化
        return self

    def produce_signal(self, ds, split="test"):
        # 用 ds.dates_through(split) 完成 warmup，最后只保留目标 split
        ...
        return signal
```

在 `scripts/run_all.py` 的 `build_methods()` 中加入即可，结果自动保存为 JSON。

---

## 8. 局限性

- ~~**`--full` 已执行，但仍然只是单一连续窗口**~~ **已部分补上（§4.3）**：
  已补跑 5 段互不重叠的滚动窗口（每段 100 test 日、合计 500 test 日、2022-12-09 → 2024-12-31，
  train expanding 913→1313 天）。**但仍不是长历史**：可用的 test 段总共只有约 2 年，
  5 个窗口不足以区分"regime 依赖"与"纯噪声"，也没有做 per-regime 条件分析
  （如按波动率/趋势分桶后重算）。要真正回答"方法是否只在某段行情有效"，
  需要覆盖更长历史并显式做 regime 条件检验。
- ~~**未做多重检验校正**~~ **已补上（§4.3、§5.5）**：已实现 Deflated Sharpe Ratio
  （Bailey & López de Prado 2014）与 White Reality Check（2000，stationary bootstrap），
  结论是 15 个方法**无一**在校正后站得住。**但 `n_trials` 仍可能被低估**：
  DSR 用的是 15（实际比较的方法数），**未计入**超参搜索（RMATS 的 ε、`λ_MV`）
  与多 fidelity 变体。按 §4.3 的敏感性表，若真实试验数为 45，
  `low_vol_20` 的 DSR 会从 0.4977 进一步降到 0.3205——**结论方向不变，只会更强**。
  精确的试验数需要接入完整的超参搜索日志才能得到。
- **`evaluate_signal()` 的返回签名已改为 `(MethodMetrics, 日净收益 Series)`**：
  这是为了让 DSR / White RC 与表格里的 Sharpe **同源**（同一 `net` 序列、同一方向、
  同一成本口径），避免二次回测导致数字对不上。**任何自定义脚本若调用 `method.run(ds)`，
  需相应解包两个返回值**（`run_all.py` / `smoke_test.py` / `test_*.py` 已同步更新）。
- **滚动窗口下 LLM 缓存基本不命中**：每窗 train 区间不同 → prompt 不同 → 重新调用真实
  DeepSeek 后端（fit 期约 92 次调用/窗）。`run_rolling.py --only <方法名>` 可先验证管线、
  显著省调用；正式跑请预留调用配额。
- **换手与成本假设敏感**：2bp/单边是 A 股日内高频口径下的乐观假设；策略进化四法换手
  +0.96～+2.17/日，成本若升至 5bp 或按冲击函数非线性计费，负 Sharpe 会更差（§5.4.2）。
- **LLM 已接入，但语义输入仍只有价格**：08–11 的 LLM 调用是真实的（见 §6），然而喂给 LLM 的
  观测全部是**技术指标与价格风险代理**，没有新闻/研报/基本面/GPR/VIX。因此复现的是
  "LLM 在价格特征上做仲裁/编辑"，不是论文原文的语义场景；论文绝对数值不可对齐。
  RMATS 的 GRS 五分项用波动/回撤/离散度/相关/量冲击替代论文的 VIX/黄金/EM/债市，
  Analysis 的 HMM+Kalman regime 用价格波动比代理，均已在各方法 `notes` 标注。
- **未做权重级自改进**：LoRA / RFT 等真正更新模型权重的环节被省略（`quant_evolver` 标
  `weight_rft_omitted`）。LLM 只产出参数级建议，不更新任何网络权重。
- **RMATS 的 LLM 仲裁层是仓库要求补充，非论文机制**：论文自述用确定性信号生成器、非 LLM 推理
  （其 Table 1 的 LLM reasoning 一栏标为 Proxy）；本实现让 LLM 只调节 `conf_scale` /
  `regime_pref` / `γ_geo` 平移 / 熔断防御偏置等**粗参数**，不产出原始权重，详见该方法 `notes`。
- **市场仅 CSI300 日线**：未跨市场、跨资产、跨频率验证。
