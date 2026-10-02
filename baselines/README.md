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
│   └── evolution.py            # 通用符号进化（变异→评估→选择）
├── methods/
│   ├── factor_lib.py           # 静态对照因子（不进化）
│   ├── data_evolution/         # 12 R&D-Agent-Quant / 13 TradingGroup / 14 FactorEngine
│   ├── factor_evolution/       # 01 AQuA / 03 Astar / 06 AutoScientist / 07 QuantEvolver
│   └── strategy_evolution/     # 08 EvolveTrade / 09 SHARP / 10 AlgoEvolve / 11 RMATS
├── scripts/
│   ├── run_all.py              # ★ 统一全量入口（小样本 / --full）
│   ├── build_summary.py        # 从 JSON 汇总生成对比表
│   ├── smoke_test.py           # 冒烟测试
│   └── test_*.py               # 分分类测试
└── results/<dataset>/*.json    # 真实结果
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
```

> 数据依赖：真实 CSI300 前复权日线，由 `project/src/data/real_akshare.py` 经 akshare 下载并缓存为
> parquet（`project/data/csi300_daily.parquet`，已被 `.gitignore`）。框架不自带任何虚构数据。

---

## 4. Baseline 对比表（`csi300_small`）

> 真实数据：**15 只 × 84 个测试日**，horizon=5，信号方向在 **validation** 估计（test 固定，防选择泄漏），
> 多空组合用次日收益、等权 top/bottom，扣 **2bp/单边** 成本。

### 静态对照因子

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `low_vol_20` | — | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | faithful_core |
| `momentum_20` | — | -0.0828 | -0.254 | -0.0965 | -0.298 | +0.027 | +0.08 | -0.167 | +0.857 | faithful_core |
| `reversal_5` | — | +0.0271 | +0.081 | +0.0457 | +0.138 | -0.519 | -1.49 | -0.245 | +1.548 | faithful_core |
| `volume_ratio` | — | +0.0629 | +0.232 | +0.0589 | +0.239 | -0.907 | -2.97 | -0.281 | +0.849 | faithful_core |

### 数据进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `factor_engine` | 14 FactorEngine | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | llm_replaced_by_rule |
| `rd_agent_quant` | 12 R&D-Agent-Quant | +0.0491 | +0.151 | +0.1003 | +0.277 | -0.331 | -1.09 | -0.217 | +0.389 | llm_replaced_by_rule |
| `trading_group` | 13 TradingGroup | -0.0296 | -0.085 | -0.0637 | -0.178 | +0.267 | +0.75 | -0.185 | +2.254 | simplified |

### 因子进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `aqua` | 01 AQuA | +0.0941 | +0.304 | +0.1302 | +0.419 | +0.036 | +0.13 | -0.175 | +0.643 | llm_replaced_by_rule |
| `astar` | 03 Astar | +0.0894 | +0.338 | +0.0922 | +0.346 | +0.786 | +3.08 | -0.068 | +0.214 | llm_replaced_by_rule |
| `auto_scientist` | 06 AutoScientist | +0.0271 | +0.085 | +0.0863 | +0.245 | -0.151 | -0.52 | -0.198 | +0.373 | llm_replaced_by_rule |
| `quant_evolver` | 07 QuantEvolver | +0.0426 | +0.156 | +0.0718 | +0.282 | -0.178 | -0.54 | -0.218 | +1.270 | weight_rft_omitted |

### 策略进化

| 方法 | 对应论文 | 均值IC | ICIR | RankIC | RankICIR | 多空年化 | Sharpe | 最大回撤 | 换手 | fidelity |
|------|----------|--------|------|--------|----------|----------|--------|----------|------|----------|
| `algo_evolve` | 10 AlgoEvolve | -0.0617 | -0.171 | -0.0712 | -0.223 | -0.383 | -1.11 | -0.215 | +1.016 | meta_evolution_approx |
| `evolve_trade` | 08 EvolveTrade | -0.0662 | -0.183 | -0.0736 | -0.230 | +0.078 | +0.22 | -0.149 | +1.111 | policy_text_approx |
| `recursive_multi_agent` | 11 RecursiveMultiAgent | -0.0580 | -0.168 | -0.0759 | -0.245 | -0.051 | -0.17 | -0.228 | +0.873 | faithful_core |
| `sharp` | 09 SHARP | -0.0444 | -0.172 | -0.0137 | -0.042 | -0.299 | -1.03 | -0.208 | +1.063 | faithful_core |

---

## 5. 关键发现（诚实，不美化）

1. **低波动因子是本小样本 test 期（2024-08→2024-12）最强信号**：`low_vol_20` IC=+0.0894、Sharpe=+3.08。
   `factor_engine`、`astar` 也都独立收敛到同一因子（数字完全相同），说明进化搜索在受限空间里确实找到了它。
2. **经典动量 / 反转在本 test 期横截面方向相反**：`momentum_20` IC=−0.0828（20 日动量在该窗口反转），
   短反转 `reversal_5` IC 仅 +0.0271 且组合为负——方向与有效性高度依赖时间窗口。
3. **基于技术指标的「策略进化」四法在本小样本 IC 全部为负**：技术指标（RSI/MACD/EMA 等）按经验
   加权的信号在 84 天 test 上横截面预测方向错误。这不代表论文方法无效（论文用 5 分钟 / 美股 / 更长周期、
   且含 LLM），而是**该口径下的真实复现结果**；同时也提示技术指标在日频 A 股横截面的局限。
4. **IC 与组合 Sharpe 不总是同向**：如 `volume_ratio` IC=+0.063 但多空 Sharpe=−2.97（高换手、两端集中），
   说明 IC 不足以单独判定一个信号的可交易性。

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

> 本环境未配置 LLM API，故所有「LLM 提案」步骤均由确定性规则完成，已逐一标注；
> 配置 `OPENAI_API_KEY` 后 `core/llm.py` 可切换为真实 LLM 后端，数字应重新实测。

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

- **小样本、短 test**：15 只 × 84 test 日，结果对时间窗口与市场状态高度敏感，不能据此做稳定结论；
  需用 `--full` 及多年滚动 / deflated Sharpe 等进一步验证。
- **无 LLM / 无新闻 / 无基本面**：策略类论文的语义（新闻、FDA、政策、5 分钟盘口）未复现，
  仅以价格代理；论文绝对数值不可对齐。
- **未做权重级自改进**：LoRA / RFT 等真正更新模型权重的环节被省略。
- **市场仅 CSI300 日线**：未跨市场、跨资产、跨频率验证。
