# 论文设计：RegimeSeal —— Regime-Aware Recursive Self-Improvement in a Sealed Factor-Discovery Sandbox

> 状态：设计稿（2026-09-28）
> 目标：投 ACL / ICLR / NeurIPS（Industry Track）或 Quantitative Finance 期刊
> 基于本库 7 篇论文的 gap 分析

---

## 1. 一句话

**现有 RSI 量化系统要么密封但不学（AQuA），要么学但不密封（QuantEvolver），而且都在平稳假设下工作——市场 regime 一切换，历史经验就变成负资产。RegimeSeal 同时解决这两个问题：在密封 DSL 内做 RFT 经验沉淀，并且按 regime 标签隔离历史回放。**

---

## 2. 现有工作的 Gap（基于本库 7 篇）

| 论文 | 做了什么 | 没解决什么 |
|---|---|---|
| AQuA (2608.12841) | 密封沙箱 + operatorization，双指标纪律 | 选择泄漏靠治理约定非结构；prompt-loop 不沉淀经验；跨 regime 聚合分数 |
| AutoScientist-Quant (2608.28632) | 单一 controller 预算调度 | CSI 单市场；无 regime 感知 |
| QuantEvolver (2605.15412) | RFT 把反馈训进权重 | DSL 不密封（扩大泄漏面）；无 regime 标签 |
| Dream-RSI (2609.14858) | 发现树回放，元层做梦 | 合成任务（Lasso）；PIT 时间衰减不区分 regime 类型；非平稳靠补丁 |
| Astar (2608.27287) | 8B 生产 RSI 闭环 | 广告召回非金融；奖励模型 15% 错误率 |
| EVOQUANT | verifier-guided 策略优化 | verifier 在环内，无密封 |
| 05 综述 (2607.07663) | 三根缰绳框架 | 指出"裁判密封"和"τ>1"都没解决，但无方法 |

### 两个核心 Gap

**Gap 1：密封 vs 学习的矛盾**
- 密封（AQuA）防泄漏，但 agent 每次 run 都从零开始，经验只存在外部 memory 文件里，不进入模型权重。
- RFT（QuantEvolver）把经验训进权重，但为此打开了更大的代码生成面，泄漏风险上升。
- **没人在密封 DSL 内做 RFT**——即：DSL 算子表数学上保证因果（密封），但小模型在这个受限空间内被历史案例微调（学习）。

**Gap 2：跨 regime 的经验污染**
- 所有因子挖掘论文都在全历史窗口上聚合 IC。
- 但 2019 牛市小盘有效的因子，在 2024 熊市大盘可能完全反向。
- Dream-RSI 的 PIT 加权只按时间衰减，不区分"牛市"和"熊市"——一个 2021 牛市的案例即使权重低，也会污染 2024 熊市的回放。
- **没人做 regime-conditioned 的经验回放**：当前在哪个 regime，就只回放同 regime 的历史。

---

## 3. 方法：三个核心组件

### C1: Regime-Tagged Sealed DSL

```
┌─────────────────────────────────────────────────┐
│  密封层（AI 无权改）                              │
│  ├── 算子表（横截面/时序/算术，数学证明因果）      │
│  ├── 标签定义（forward return，行业中性化）       │
│  ├── 数据切分（train/embargo/test）              │
│  └── Regime 标注器                                │
│      └── 在 train 窗口上用无监督聚类              │
│          （K-Means on 6 个宏观因子）              │
│          自动识别 K=4 个 regime：                  │
│          R1=牛市小盘, R2=牛市大盘,                │
│          R3=熊市小盘, R4=熊市大盘                 │
│      └── agent 只能"选择在哪个 regime 下评估"，   │
│          不能改 regime 标签                        │
└─────────────────────────────────────────────────┘
```

关键设计：
- Regime 标签在 train 窗口上一次性聚类固定，embargo/test 窗口用最近中心分配。
- 因子不再有"全历史 IC"，而是有 **per-regime IC 向量** [IC_R1, IC_R2, IC_R3, IC_R4]。
- 一个因子只有在 ≥2 个 regime 下 IC 同号且显著，才算"稳健"；只在单个 regime 下有效的因子标记为"regime-specific"。

### C2: Regime-Conditioned Experience Replay（RCER）

发现树每个节点带 regime 标签。元策略做梦时：

```
当前 regime = R3（熊市小盘）
    ↓
回放候选 = 树中 regime == R3 的节点
    ↓
（不是：按时间衰减选所有节点）
    ↓
如果 R3 节点 < 20 条：
    触发"燃料不足"信号 → 通知人注入新数据/新假设
```

与 Dream-RSI PIT 的区别：

| | PIT 加权 | RCER |
|---|---|---|
| 选择方式 | 时间近的权重高 | regime 相同才选 |
| 牛市案例污染熊市？ | 权重低但仍参与 | 完全隔离 |
| 新 regime 怎么办 | 权重自动衰减 | 节点不足触发外部燃料 |

### C3: Sealed RFT（sRFT）

在密封 DSL 内微调一个 7B 小模型当因子提案器：

```
训练数据（全部来自 train 窗口，永远不见 test）：
  正样本 = 通过密封评估的因子表达式
  负样本 = 被拒的因子表达式（含失败原因：换手过高/IC 不显著/前视）
  
奖励 = Diversity-Complementarity Reward（学 QuantEvolver）
  = α × IC_regime_same + β × (1 - max_correlation_to_existing_library)
```

关键安全保证：
- 训练数据只来自 train+validation，test 数据物理隔离。
- 模型只生成 DSL 表达式（不生成自由 Python），密封算子表是约束。
- 评估器在模型训练管线之外，模型永远看不到验证分数。

---

## 4. 实验设计

### 数据
- A股：CSI300 + CSI500 分钟频，2015–2025（含 2015 股灾、2018 熊市、2020 疫情、2024 小盘崩盘）
- 加密：BTC/ETH 5 分钟频，2020–2025
- 成本：A股双边 2bp，加密双边 5bp

### 基线
1. **AQuA-seal**：密封 DSL + prompt-loop（无 RFT，无 regime）
2. **QuantEvolver-RFT**：RFT 但 DSL 不密封（有泄漏面）
3. **Dream-RSI-PIT**：发现树回放 + PIT 时间衰减（无 regime）
4. **RegimeSeal-full**：本文方法

### 关键实验

**E1: 跨 regime 样本外**
- 故意把 test 窗口选在 regime 翻转期（2024-01 到 2024-03，A股小盘崩盘）
- 测：哪个方法在 regime 翻转后 IC 衰减最小？
- 预期：RegimeSeal 在 R3/R4 节点充足时，翻转后 IC 保持；PIT 方法因回放了 R1/R2 节点而 IC 反向。

**E2: 泄漏审计**
- 对每个方法跑"泄漏攻击"：给 agent 看 test 分数，看它能不能 hack
- 测：选择泄漏导致的 test IC 虚高幅度
- 预期：AQuA-seal 和 RegimeSeal-sRFT 都低；QuantEvolver-RFT 高（因为不密封）

**E3: 经验沉淀效率**
- 固定预算 1000 次实验
- 测：第 100–200 次 vs 第 900–1000 次的 IC 提升幅度
- 预期：sRFT 比 prompt-loop 提升更大（因为经验进了权重）；RCER 比 PIT 提升更稳定

**E4: 新 regime 触发信号**
- 在 test 窗口注入一个全新 regime（比如 2025 年的 AI 主题行情，训练时没见过）
- 测：系统能不能自动检测"当前 regime 历史节点不足"并请求外部燃料
- 预期：RCER 触发信号；PIT 方法静默过拟合

### 度量
- 主指标：per-regime out-of-sample IC（不是全历史 IC）
- 辅助：deflated Sharpe、换手率、最大回撤
- 安全指标：泄漏审计分数（test IC - val IC 的 gap）

---

## 5. 预期贡献

1. **第一个 regime-conditioned RSI 因子挖掘系统**——解决跨 regime 经验污染
2. **第一个在密封 DSL 内做 RFT 的架构**——证明密封和学习不矛盾
3. **新 regime 燃料需求信号**——把"什么时候该人介入"从艺术变成可检测信号
4. **跨 regime IC 度量协议**——per-regime IC 向量替代全历史 IC

---

## 6. 风险与失败模式

| 风险 | 概率 | 缓解 |
|---|---|---|
| Regime 聚类 K=4 是主观选择 | 中 | 做 K=2,3,4,5 敏感性分析；用 silhouette score 选 |
| sRFT 训练成本高（7B 微调） | 中 | 先在 1.5B 模型上做概念验证；LoRA 微调 |
| per-regime IC 样本太少（每个 regime 只有 2–3 年） | 高 | 加密数据补样本；或放宽到 3 个 regime |
| AQuA 团队可能在 v3 就加了 regime | 中 | 2026-09 检查 arXiv 更新；如果撞车，转向"密封 RFT"单做 Gap 1 |
| 实验复现需要全市场分钟数据 | 中 | 用公开数据（AKShare/Yahoo）+ 合成数据兜底 |

---

## 7. 时间表（如果做）

| 月 | 任务 |
|---|---|
| M1 | 数据管道 + 密封 DSL 算子表 + regime 聚类 |
| M2 | 基线复现（AQuA-seal prompt-loop） |
| M3 | RCER 发现树 + 元策略 |
| M4 | sRFT 管线（LoRA 微调 7B） |
| M5 | E1–E4 实验跑完 |
| M6 | 写作 + 投稿 |

---

## 8. 为什么这个创新点值得做

1. **真实痛点**：每个做量化的人都经历过"2021 年的策略 2024 年失效"，但没人把这个问题形式化成 RSI 的一个组件。
2. **可复现**：DSL + 公开数据 + 小模型，不依赖蚂蚁/谷歌的内部基础设施。
3. **对话现有工作**：和 AQuA（密封但不学）、QuantEvolver（学但不密封）、Dream-RSI（回放但不 regime）都有明确对照。
4. **有工程价值**：新 regime 燃料信号对个人研究者特别有用——你不需要每周读 10 篇论文，系统告诉你"当前 regime 经验不足，该读新东西了"。

---

## 9. 可选的第二创新点（如果时间允许）

**"密封的学习型裁判"**：在 Astar 的学习型裁判和 AQuA 的密封裁判之间，设计一个中间态——用小模型当裁判，但这个小模型只在 train+validation 上训练，永远不见 test，且它的输出被外层规则检查器过滤。这样既灵活又不会偷看。这个可以作为 sRFT 的裁判模块，而不是单独一篇。
