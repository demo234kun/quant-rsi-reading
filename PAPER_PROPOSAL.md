# 论文设计：RegimeSeal —— Regime-Aware Recursive Self-Improvement in a Sealed Factor-Discovery Sandbox

> 状态：设计稿 v2（2026-09-28）
> 目标：投 ICLR / NeurIPS（Industry Track）或 Quantitative Finance 期刊
> v2 修订：把"递归自我改进"从口号变成可见的闭环——谁提案、谁学习、怎么进化、怎么证明比上一轮好

---

## 1. 一句话

**现有 RSI 量化系统要么密封但不学（AQuA），要么学但不密封（QuantEvolver），而且都在平稳假设下工作——市场 regime 一切换，历史经验就变成负资产。RegimeSeal 把"递归"具体化成一个四轮闭环：提案 → 密封评估 → 失败模式提取 → 策略演化，每一轮都基于上一轮的结果改变下一轮的提案分布。**

---

## 2. 现有工作的 Gap（基于本库 7 篇）

| 论文 | 做了什么 | 没解决什么 |
|---|---|---|
| AQuA (2608.12841) | 密封沙箱 + operatorization，双指标纪律 | prompt-loop 不沉淀经验；跨 regime 聚合分数；跑完 1000 个因子系统和刚开始一样笨 |
| AutoScientist-Quant (2608.28632) | 单一 controller 预算调度 | CSI 单市场；无 regime 感知；controller 决策是静态规则 |
| QuantEvolver (2605.15412) | RFT 把反馈训进权重 | DSL 不密封；无 regime 标签；微调是离线一次性，不是递归 |
| Dream-RSI (2609.14858) | 发现树回放，元层做梦 | PIT 时间衰减不区分 regime；做梦不改变提案策略 |
| Astar (2608.27287) | 8B 生产 RSI 闭环 | 广告召回非金融；奖励模型 15% 错误率 |
| EVOQUANT | verifier-guided 策略优化 | verifier 在环内，无密封 |
| 05 综述 (2607.07663) | 三根缰绳框架 | 指出"裁判密封"和"τ>1"都没解决，但无方法 |

### 两个核心 Gap

**Gap 1：密封 vs 学习的矛盾**
- 密封（AQuA）防泄漏，但 agent 每次 run 都从零开始，经验只存在外部 memory 文件里，不进入模型权重。
- RFT（QuantEvolver）把经验训进权重，但为此打开了更大的代码生成面，泄漏风险上升。
- **没人在密封 DSL 内做递归 RFT**——即：每一轮的反馈都改变下一轮的提案，而不是离线一次性微调。

**Gap 2：跨 regime 的经验污染**
- 所有因子挖掘论文都在全历史窗口上聚合 IC。
- 但 2019 牛市小盘有效的因子，在 2024 熊市大盘可能完全反向。
- Dream-RSI 的 PIT 加权只按时间衰减，不区分"牛市"和"熊市"。
- **没人做 regime-conditioned 的递归回放**：当前在哪个 regime，就只回放同 regime 的历史失败模式来指导下一轮。

---

## 3. RSI 递归闭环（本文核心）

这是 v2 新增的核心章节——"递归"不是比喻，是一个四轮循环，每一轮都有明确的输入输出。

```
┌──────────────────────────────────────────────────────────────┐
│                     Round t (第 t 轮)                         │
│                                                              │
│  ┌──────────┐   因子表达式   ┌──────────┐                     │
│  │  P_t     │ ───────────→ │  E_t     │                     │
│  │ 提案器   │               │ 密封评估  │                     │
│  │ (propose)│               │ (eval)   │                     │
│  └──────────┘               └────┬─────┘                     │
│       ↑                           │ per-regime IC              │
│       │                           │ accepted/rejected          │
│       │                           ↓                            │
│  ┌──────────┐               ┌──────────┐                     │
│  │  A_t     │ ←─────────── │  L_t     │                     │
│  │ 策略演化  │   更新提案    │ 失败模式  │                     │
│  │ (adapt)  │   策略参数    │ 提取      │                     │
│  └──────────┘               │ (learn)  │                     │
│                              └──────────┘                     │
│                                                              │
│  Round t+1 的 P_{t+1}  ≠  Round t 的 P_t                     │
│  ——这就是"递归"：提案器每轮都变了                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 P_t：提案器如何随轮次改变

**Round 0（冷启动）**：纯随机 + 先验知识
- 从 15 个密封算子中随机组合表达式（深度 ≤3）
- 先验知识：手工种子因子（动量/反转/波动率/成交量）

**Round 1–N**：从失败模式中学习后提案

提案器不是固定的 LLM prompt。它的提案分布由三个参数决定：

```
π_t = {
  op_weights_t,      # 每个算子被选中的概率
  depth_t,           # 表达式深度偏好
  regime_bias_t,     # 当前 regime 下优先尝试哪类算子
  negative_set_t,    # 黑名单：这些表达式模式被拒过，避开
}
```

每轮结束后，L_t 提取的失败模式会更新 π_t。

### 3.2 L_t：失败模式提取（关键新模块）

这是 v1 缺失的——系统怎么"学习"？不是把分数喂回 LLM，而是**从 rejected 节点中归纳结构化的失败模式**。

每个 rejected 因子不只是"失败"，而是被打上结构化标签：

| 失败模式标签 | 判定规则 | 案例（我们真实跑出的） |
|---|---|---|
| `REGIME_REVERSE` | 同一因子在 R1 IC=-0.083，在 R3 IC=+0.039 | f1_volume_ratio 在 R1 反向 |
| `NOISE` | 所有 regime \|IC\| < 0.01 | f3_trend 样本外 IC≈0 |
| `COST_EATEN` | 毛 Sharpe > 1 但净 Sharpe < 0.3（换手率吃掉收益） | 高频调仓因子 |
| `DEGENERATE` | 因子值横截面方差 ≈ 0（所有股票值一样） | 滚动窗口太短 |
| `LOOKAHEAD` | 因果性测试不过（密封层直接拦截） | 算子越界 |

提取逻辑：
```
对每个 rejected 节点：
  if per-regime_ic_signs == 不一致: 标签 = REGIME_REVERSE
  if all |IC| < 0.01:             标签 = NOISE
  if gross_sharpe - net_sharpe > 0.5: 标签 = COST_EATEN
  ...
```

### 3.3 A_t：策略演化（π_t 怎么更新）

每轮结束后，根据 L_t 提取的失败模式更新 π_t：

```
规则 1：如果连续 k 轮某算子组合被打 REGIME_REVERSE：
  → 降低 op_weights 中该组合的概率 ×0.5
  → 同时记录"在 R1 regime 下这个算子组合反向"

规则 2：如果某 regime 下 accepted 率 < 10%：
  → regime_bias_t 转向其他 regime 的有效算子组合

规则 3：如果所有失败模式都是 NOISE：
  → depth_t 从 3 降到 2（简单表达式更稳健）

规则 4：新 regime 燃料不足（节点 < 20）：
  → 暂停自动提案，触发"需要人注入新假设"信号
```

### 3.4 递归的可度量性

"递归有没有效"不是主观判断，而是可测量的：

```
定义：第 t 轮的提案质量 Q_t
  Q_t = mean(per-regime IC) over 该轮 accepted 因子

递归有效 ⟺ Q_{t+1} > Q_t （在相同预算下）
```

对比基线：
- **无递归（AQuA-seal）**：prompt-loop 每轮重置，Q_t 是平的
- **离线 RFT（QuantEvolver）**：只在 Round 0 前微调一次，Q_t 跳一下然后平
- **递归（RegimeSeal）**：Q_t 应该单调上升（或至少 staircase 上升）

---

## 4. 方法：四个组件

### C1: Regime-Tagged Sealed DSL（密封层）

```
┌─────────────────────────────────────────────────┐
│  密封层（AI 无权改）                              │
│  ├── 算子表（15 个，数学证明因果）                │
│  ├── 标签定义（forward return，行业中性化）       │
│  ├── 数据切分（train/embargo/test）              │
│  └── Regime 标注器                                │
│      └── 在 train 窗口上用无监督聚类              │
│          （K-Means on 6 个宏观因子）              │
│      └── agent 只能"选择在哪个 regime 下评估"，   │
│          不能改 regime 标签                        │
└─────────────────────────────────────────────────┘
```

关键：因子不再有"全历史 IC"，而是有 **per-regime IC 向量** [IC_R1, IC_R2, IC_R3, IC_R4]。

### C2: L_t 失败模式提取器

见 §3.2。这是连接"评估"和"策略演化"的桥梁。

### C3: RCER — Regime-Conditioned Experience Replay

发现树每个节点带 regime 标签 + 失败模式标签。元策略做梦时：

```
当前 regime = R3（熊市小盘）
    ↓
回放候选 = 树中 regime == R3 的节点（不是所有节点按时间衰减）
    ↓
回放内容 = 该 regime 下的 accepted 模式 + rejected 失败模式
    ↓
如果 R3 节点 < 20 条：触发"燃料不足"信号
```

与 Dream-RSI PIT 的区别：

| | PIT 加权 | RCER |
|---|---|---|
| 选择方式 | 时间近的权重高 | regime 相同才选 |
| 牛市案例污染熊市？ | 权重低但仍参与 | 完全隔离 |
| 回放内容 | 只有成功节点 | 成功 + 失败模式 |
| 新 regime 怎么办 | 权重自动衰减 | 节点不足触发外部燃料 |

### C4: sRFT — Sealed Recursive Fine-Tuning

在密封 DSL 内微调一个小模型当因子提案器，但**不是离线一次性，而是递归**：

```
Round 0: 冷启动（随机 + 先验）
    ↓
Round 1–10: 收集足够 (因子表达式, per-regime IC, 失败模式标签) 三元组
    ↓
Round 11: 用这 10 轮的数据做一次 LoRA 微调
    ↓
Round 11+ 的提案器 = 微调后的模型（提案分布变了）
    ↓
Round 20: 再收集 10 轮，再微调一次
    ↓
...（递归）
```

训练数据（全部来自 train 窗口，永远不见 test）：
- 正样本 = 通过密封评估的因子表达式
- 负样本 = 被拒的因子表达式（**带结构化失败模式标签**）
- 奖励 = Diversity-Complementarity Reward
  = α × IC_regime_same + β × (1 - max_correlation_to_existing_library)

关键安全保证：
- 训练数据只来自 train+validation，test 数据物理隔离
- 模型只生成 DSL 表达式（不生成自由 Python）
- 评估器在模型训练管线之外，模型永远看不到验证分数

---

## 5. 用我们真实跑出的结果演示这个循环

### Round 0 种子（真实结果，CSI300 49 只 × 1455 天）

| 因子 | R0 IC | R1 IC | R2 IC | R3 IC | Sharpe | 失败模式标签 |
|---|---|---|---|---|---|---|
| f1_volume_ratio | -0.013 | **-0.083** | -0.012 | -0.016 | -2.67 | `REGIME_REVERSE`（R1 反向） |
| f2_reversal | -0.006 | -0.052 | -0.011 | **+0.039** | +0.48 | `REGIME_SPECIFIC`（只在 R3 有效） |
| f3_trend | +0.003 | -0.009 | +0.026 | +0.003 | +0.30 | `NOISE`（全 regime 弱） |

### L_0 提取的失败模式

1. **在 R1 regime 下，成交量比率因子反向**（f1 贡献了 -0.083）
2. **反转因子只在 R3 有效**（f2 在 R1 是 -0.052）
3. **简单趋势因子是噪声**（f3 所有 regime |IC| < 0.03）

### A_0 更新提案策略 π_1

```
π_1.op_weights:
  - 降低 rolling_mean(volume, n) 的权重（R1 反向）
  - 提高 close.pct_change() 类表达式的权重（R3 有效）
  - 淘汰纯 rolling_mean(close) 类（噪声）

π_1.regime_bias:
  - R1: 优先尝试波动率类（不是成交量类）
  - R3: 优先延续反转类

π_1.negative_set:
  - 黑名单: cs_rank(volume / rolling_mean(volume, 20)) 类
```

### Round 1 的 P_1 应该提案什么

基于 π_1，下一轮应该试：
- 波动率反转：cs_rank(rolling_std(ret, 5) × lag(ret, 5))
- 但不是再试 volume_ratio 类

这就是递归——**系统从 f1 的失败中学到了"不要在 R1 做成交量比率"，下一轮自动避开**。

---

## 6. 实验设计

### 数据
- A股：CSI300 + CSI500 日线，2015–2025（含 2015 股灾、2018 熊市、2020 疫情、2024 小盘崩盘）
- 加密：BTC/ETH 日线，2020–2025
- 成本：A股双边 2bp，加密双边 5bp

### 基线
1. **AQuA-seal**：密封 DSL + prompt-loop（无递归，无 regime，无失败模式提取）
2. **QuantEvolver-RFT**：RFT 但离线一次性（不递归），DSL 不密封
3. **Dream-RSI-PIT**：发现树回放 + PIT 时间衰减（无 regime）
4. **RegimeSeal-noLearn**：密封 + regime，但 L_t/A_t 关掉（提案器每轮重置）
5. **RegimeSeal-full**：本文方法

### 关键实验

**E1: 递归有效吗？（核心实验）**
- 固定预算 1000 次实验，分成 10 轮（每轮 100 次）
- 画 Q_t 曲线（每轮的 mean per-regime IC）
- 预期：
  - AQuA-seal: Q_t 平的（每轮重置）
  - QuantEvolver-RFT: Q_0 跳一下然后平（离线微调）
  - RegimeSeal-full: Q_t 单调上升（递归学习）
  - RegimeSeal-noLearn: Q_t 平的（证明 L_t/A_t 是关键）

**E2: 跨 regime 样本外**
- test 窗口选在 regime 翻转期（2024-01 到 2024-03，A股小盘崩盘）
- 测：哪个方法在 regime 翻转后 IC 衰减最小？

**E3: 泄漏审计**
- 对每个方法跑"泄漏攻击"：给 agent 看 test 分数，看它能不能 hack
- 测：选择泄漏导致的 test IC 虚高幅度

**E4: 新 regime 燃料信号**
- 在 test 窗口注入一个全新 regime（比如 2025 年 AI 主题行情）
- 测：系统能不能自动检测"当前 regime 历史节点不足"并请求外部燃料

### 度量
- 主指标：**Q_t 曲线下面积**（递归是否有效）+ per-regime out-of-sample IC
- 辅助：deflated Sharpe、换手率、最大回撤
- 安全指标：泄漏审计分数（test IC - val IC 的 gap）

---

## 7. 预期贡献

1. **第一个把"递归"形式化为四轮闭环（P→E→L→A）的量化 RSI 系统**——不是比喻，是可测量的 Q_t 曲线
2. **失败模式提取器 L_t**——把"从 rejected 中学"从 prompt 技巧变成结构化模块
3. **第一个 regime-conditioned RSI 因子挖掘系统**——解决跨 regime 经验污染
4. **第一个在密封 DSL 内做递归 RFT 的架构**——证明密封和学习不矛盾
5. **新 regime 燃料需求信号**——把"什么时候该人介入"变成可检测信号

---

## 8. 风险与失败模式

| 风险 | 概率 | 缓解 |
|---|---|---|
| Q_t 曲线不上升（递归无效） | 中 | 如果失败，说明 L_t/A_t 规则太粗；转向用小模型自动学规则 |
| Regime 聚类 K=4 是主观选择 | 中 | K=2,3,4,5 敏感性分析；silhouette score 选 |
| sRFT 训练成本高 | 中 | 1.5B 模型 + LoRA 概念验证 |
| per-regime IC 样本太少 | 高 | 加密数据补样本；或放宽到 3 个 regime |
| AQuA 团队可能在 v3 加了 regime | 中 | 撞车则转向"递归闭环 + 失败模式提取"单做 Gap 1 |

---

## 9. 时间表

| 月 | 任务 |
|---|---|
| M1 | 数据管道 + 密封 DSL + regime 聚类（✅ 已完成） |
| M2 | 基线 AQuA-seal prompt-loop（3 个种子因子已跑通） |
| M3 | L_t 失败模式提取器 + A_t 策略演化规则 |
| M4 | RCER 发现树 + sRFT LoRA 微调 |
| M5 | E1–E4 实验跑完，画 Q_t 曲线 |
| M6 | 写作 + 投稿 |

---

## 10. 为什么这个创新点值得做

1. **真实痛点**：每个做量化的人都经历过"2021 年的策略 2024 年失效"，但没人把这个问题形式化成"递归闭环的失败模式提取"。
2. **可复现**：DSL + 公开数据（AKShare）+ 小模型，不依赖蚂蚁/谷歌内部基础设施。
3. **可证伪**：Q_t 曲线是明确的——如果递归无效，曲线是平的，这篇论文就不成立。
4. **有工程价值**：新 regime 燃料信号对个人研究者特别有用——系统告诉你"当前 regime 经验不足，该读新东西了"。

---

## 11. 当前已验证的真实结果（Phase 1）

| 项目 | 结果 |
|---|---|
| 密封算子因果性测试 | 15 个算子全部通过 |
| 测试套件 | 33/33 通过 |
| 真实 CSI300 数据 | 49 只股票 × 1455 天日线（新浪源） |
| f1_volume_ratio | Sharpe -2.67，R1 regime IC=-0.083（`REGIME_REVERSE`） |
| f2_reversal | Sharpe +0.48，R3 regime IC=+0.039（`REGIME_SPECIFIC`） |
| f3_trend | Sharpe +0.30，全 regime 弱（`NOISE`） |

这些是 Phase 1 的种子结果。Phase 2 要做的是：让系统自动从这 3 个结果中提取失败模式，改进 Round 1 的提案——而不是人工分析。
