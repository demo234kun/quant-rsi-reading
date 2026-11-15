# AQuA 论文精读（Deep Reading）

> 模板：论文基础元信息 / 核心精读问答（Q1–Q7）/ 范式提炼 / 后续拓展
> 目标：面向可复现性，关键位置标注原文图 / 表引用
> 事实约束：所有数字来自论文原文（22 页）；论文未披露处明确标注 "未披露"，不做推测



***

## 1. 论文基础元信息



| 项目            | 内容                                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **论文标题**      | AQuA: Recursively Self-Improving Quantitative Trading Research Agents                                                                                               |
| **作者**        | Jiacheng Guo\*, Suozhi Huang\*, Yunlong Gao, Zihao Li, Jason Ge, Xu Kuang, Mengdi Wang（\* 共同一作）                                                                     |
| **机构**        | Princeton University（普林斯顿）、Ant Group（蚂蚁集团）、Stanford（斯坦福）                                                                                                            |
| **发表会议 / 期刊** | 暂无（arXiv 预印本，cs.CL）                                                                                                                                                 |
| **论文链接**      | [https://arxiv.org/abs/2608.12841](https://arxiv.org/abs/2608.12841)（v1 2026-08-13，v2 2026-08-17）                                                                   |
| **代码链接**      | **未提供**。论文明确写 "deployed expressions are withheld throughout"（部署的表达式全程不公开）；未给出 GitHub 仓库                                                                             |
| **关键词**       | recursive self-improvement (RSI)、sealed sandbox、data leakage、operatorization、factor discovery、model development、config-driven loop、embargo、out-of-sample evaluation |
| **TLDR**      | 先别急着让 AI 自动挖 alpha—— 把打分的尺子锁到它够不到的地方，AI 才不会在自我改进时偷看答案、把错误当成功经验反复放大。                                                                                                 |

**摘要核心**：研究量化投资中的递归自我改进 —— 一个自主系统能否用早期实验的证据改进后续实验提出的假设与候选。AQuA 含两个互不连通的语言模型驱动研究系统：一个做符号因子发现，一个做可训练模型开发。两个系统各自闭环，保留验证证据并用来指导后续提案。因子系统在加密宇宙达到组合信号 IC ≈ 0.190；模型系统在美股达到 per-stock IC +0.0843，转换成持有 Sharpe 最高 +2.50（2bp 双边成本），2021–2025 每年都为正。



***

## 2. 核心精读问答

### Q1 研究问题：这篇论文试图解决什么问题？

**背景**：量化投资研究是在一个巨大的因子与模型空间中搜索，微小的方法论错误就会变成 "看起来很有说服力但无法复现" 的回测。

**三个层次的痛点（论文 §1 递进）**：



1. **生成侧泄漏（code-generation leakage）**：写代码的 agent 可能无意中引入时间对齐或预处理错误，用了预测时点不可得的数据。临时审查 agent 可能漏掉，因为 "代码看起来语义合理"。

2. **错误会被递归放大**：一旦泄漏产生高分，这个实验会被存成 "成功先例" 并传播到后续迭代 ——RSI 会同时放大未发现的错误和真实发现。

3. **选择侧泄漏（repeated-access overfitting）**：prompt 指令和模型审查不是可靠的完整性边界。对固定 holdout 的重复访问会导致适应性过拟合（Blum & Hardt 2015）；语言模型 agent 已被观察到会利用错误指定的目标、评估器或奖励机制。

**研究动机（核心立场）**：

> 改进的是 "研究过程"，不是 "成功的定义"。AI 可以不断改 "下一步想试什么"，但永远无权改 "什么叫成功"。

**任务目标**：让泄漏诱发的动作对 agent 不可用（make leakage-inducing actions unavailable）—— 在自主迭代开始前固定数据划分、特征、标签、评估器。



***

### Q2 相关研究：有哪些相关研究？

论文 §2 分三条线梳理：



| 相关方向                 | 代表工作                                                                                                        | 优势        | 缺陷 / 本文缺口                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------ |
| **LLM 驱动的 alpha 挖掘** | 基于算子的因子搜索（Cui 2021；Zhang 2020）、遗传规划、强化学习（Yu 2023）；近期 AlphaGen、AlphaMemo、QuantaAlpha、QuantEvolver、AlphaPROBE | 能自动产出公式因子 | 要么聚焦因子发现，要么聚焦模型开发，**少有把 "递归自我改进" 单独在两者中分别研究的**   |
| **自主科研端到端 agent**    | AI Scientist（Lu 2024）、多 LLM 投票做投资决策（Miyazaki 2026；Singh 2025）                                               | 能跑完整科研闭环  | 数据泄漏问题仍靠 "审查"，未从结构上堵死                            |
| **金融时序深度模型**         | 卷积（Bai 2018）、状态空间模型（Gu & Dao 2023）、attention（Vaswani 2027）；Gu-Kelly-Xiu 2020                                | 预测力强      | 这些是组件，不是 "用证据自主循环" 的系统；本文贡献是概念性的 —— 系统积累证据而非从零开始 |

**研究缺口（本文落点）**：



* 把 "递归自我改进" 在因子发现和模型开发两个部分**分别实例化**，且不耦合两者

* 专门针对量化研究的失败模式 ——**数据泄漏**，让数据路径和评估器对 agent 不可达，而不是靠 agent 画图 / 审查



***

### Q3 解决方案：论文如何解决这个问题？

#### 1. 整体思路与框架

**图 1（Figure 1）** 给出共享研究环（Shared Research Loop），五步：



```
Hypothesis → Construct/Train → Evaluate → Validate → Select/Combine
                              ↑ Knowledge/Memory Update 闭环
```

每个系统在自己的领域内通过 "假设→构造 / 训练→评估→验证→选择 / 组合" 闭环，并做持久化的运行状态更新，指导下一次迭代。

**关键设计 ——Asymmetric Freedom（不对称自由）**：



* Agent 保留在其 DSL 内探索的自由

* 但评估器在适应面之外（evaluator is outside the adaptive surface）

**形式化（论文公式 2）**：

$s_k = \mathcal{V}(\mathcal{C}(\theta_k); \mathcal{S}), \quad \theta_k \in \Theta, \quad \mathcal{S}=(\mathcal{D},\mathcal{F},\mathcal{L},\mathcal{V})\ \text{sealed}$



* 四样东西密封：D（数据划分）、F（特征定义）、L（标签定义）、V（评估器）

* 每个动作是一个从受限空间 Θ 抽取的规格 θ，harness 编译并用密封评估器打分

* Θ 被定义为没有任何 θ 能改动 S

#### 2. 算法 / 框架逐条解释

**① 密封沙箱（Sealed Sandbox）**



* 是什么：迭代开始前由人类固定数据划分、特征 / 标签定义、评估器，模型永不编辑

* 为什么用：量化研究的核心失败模式是数据泄漏；密封后每个被记录的实验都是泄漏无关的

* 怎么用：模型只能 "引用" 冻结组件的 id，不能重定义

**② 算符化（Operatorization）—— 堵生成泄漏**



* 是什么：标准公式化 alpha 算子词表（源自 Kakushadze 2016《101 Formulaic Alphas》）


  * 叶子：原始字段（open/high/low/close/volume/vwap/returns）

  * 时序算子：lag、difference、moving correlation/covariance、trailing rank、rolling std、线性衰减加权

  * 横截面算子：rank、z-score、sector neutralization

  * 逐元素算术 + 条件判断

* 为什么用：每个时序算子只读其截至当前时间戳的回看窗口，每个横截面算子只读当前时间戳

* 关键数学性质：**因果性在复合下封闭（causality is closed under composition）**—— 任何由 O 中算子拼成的表达式都是因果的

* 论文公式 3 示例：$f = \text{rank}(\text{corr}(r^{1d}, v^{1d}, 20)) - \text{rank}(\text{std}(r^{1d}, 20))$

**③ 双指标分离（split metric）—— 堵选择泄漏**



* 是什么：搜索时 harness 返回给 agent 的唯一分数是**验证切片**上的 $s_k$；真正的 test 窗口配置冻结后只打一次分

* 为什么用：一个能反复读到最终指标的搜索，最终会学会 "专门选择" 它

* 怎么用：test 分数永不返回给 agent，也不用于排序候选

* **强度差异（论文自认）**：算符化是结构性保证；test 隔离是治理约定（governance），非密码学保证

**④ Part I 的 Manager 中介多 agent 架构**



* 是什么：1 个 AI Manager + 6 个专职 agent（Data Steward / Visual Analyst / Idea Miner / Factor Evaluator / Backtest Engineer / Research Librarian）

* 为什么用：agent 间从不直接对话，所有交接过 Manager—— 保持可审计、可复现

* 入口纪律：因子先以 \*\* 可证伪提案（falsifiable proposal）\*\* 出现，写清 hypothesis /mechanism/expected\_direction /falsification\_criteria/expected\_failure\_modes，之后才允许拼装

**⑤ Part II 的 config-driven loop**



* 是什么：一次实验 = 一个 config diff（只改 split/sampler/arch/loss/optim 这些已注册旋钮）

* 为什么用：一个 diff 对应一个变体，天然可比、泄漏无关

* 形式化（论文公式）：$\theta_H = \{c=(\text{split},\text{sampler},\text{arch},\text{loss},\text{optim})\}$

**⑥ 三层反馈环**



* 单次回测内：方向校准（测正反两个方向，保留解释干净的）

* 单次 run 内：失败提案更新信念状态

* 跨 run：Research Librarian 写结构化记录，下一轮规划读记忆（不从零开始）



***

### Q4 可复现细节：数据、模型、配置

> 说明：论文在多处明确 "具体因子 / 特征不公开"，下列未披露项如实标注。

**数据集**：



|             | Part I（因子发现）                                                                                                                   | Part II（模型开发）                                 |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| 市场          | 加密货币                                                                                                                           | 美股                                            |
| 频率          | 5 分钟                                                                                                                           | 30 分钟前瞻                                       |
| 输入字段        | open/high/low/close/volume，以及 open interest、basis rate、taker buy/sell ratio、long/short account ratio、top trader position ratio | 纯价量历史（price-volume features），按股标准化            |
| 标签          | ret\_open\_open\_h10、ret\_open\_open\_h30（事件窗口）                                                                                | 未来 30 分钟前瞻收益（lbl\_fwd）                        |
| 划分          | 20 个研究 epoch（Figure 3）                                                                                                         | 训练 2010–2019，**2020 整年 embargo**，测试 2021–2025 |
| universe 规模 | 论文以 BTCUSDT\_5m 举例；**完整币种数量未披露**                                                                                               | **股票数量未披露**                                   |

**模型结构（Part II，Figure 5 / Listing 2）**：



* 输入：per-entity z-score，state\_window=64

* 多尺度 1D 卷积前端：conv scales \[3,5,15]，kernel 1/5/15，多 dilation

* 多分辨率 block：fine（repeat 4，block \[temporal\_conv /sequence\_mixer/state\_space]）、coarse（repeat 2，block \[sequence\_mixer /feedforward]）

* 融合：cross-attention

* block repeat 3：cross-entity-mixer、temporal-conv/depthwise、feedforward

* readout：gate \[fine, coarse, panel]，pool \[last, mean, attn]

* 预测头：configurable MLP 或 SwiGLU，输出每股一个标量

**训练设置（Listing 2）**：



* sampler：stratified minute，batch 8192

* 损失：spearman\_ic、huber\_csz、turnover\_reg

* 优化器：AdamW，lr 3.0e-4，schedule=cosine，precision=bf16，ddp=8

* 评估：cost\_bps=2，walk-forward=expanding

* **参数量、训练时长、硬件型号：未披露**（仅见 ddp=8，暗示 8 路分布式）

**评价指标**：



* Part I：组合 Spearman IC

* Part II：per-stock raw IC（时序 Pearson）、per-stock R² = mean (IC²)、threshold long/short Sharpe（2bp 双边）

**复现坑点**：



1. 因果性必须由算子构造保证，不能靠 "记得 shift"

2. train/test 之间必须留 embargo（论文用一整年）

3. 选择指标只能在 validation 上看，test 只跑一次

4. 论文未开源，复现需自建算子表 + 数据管线



***

### Q5 实验部分：论文做了哪些实验？

#### 主实验一：Part I 因子发现（Figure 3，加密 5 分钟）



| 系统              | Combined Spearman IC |
| --------------- | -------------------- |
| **AQuA Part I** | **\~0.190**          |
| AlphaMemo（适配）   | 0.171                |
| AlphaGen（适配）    | 0.151                |
| LSTM            | 0.137                |
| LightGBM        | 0.106                |
| Alpha158 风格基线   | 0.075                |



* 组合 IC 随 20 个 epoch 单调上升（Figure 3 蓝线 fit / 黑线 held-out 几乎重合）

* 单因子 IC 仅 0.026–0.037——**强度来自组合，不来自神规则**

#### 主实验二：Part II 模型对比（Table 2，held-out 2021–2025）



| 模型                | 族                 | raw IC      |
| ----------------- | ----------------- | ----------- |
| Linear (Ridge)    | linear            | +0.0251     |
| LGB               | gradient boosting | +0.0397     |
| xLSTM             | recurrent         | +0.0434     |
| LSTM              | recurrent         | +0.0535     |
| GRU               | recurrent         | +0.0613     |
| **Ours (hybrid)** | hybrid            | **+0.0843** |



* 单特征 IC 均 ≤ 0.031（Table 1）—— 可预测信号在联合、非线性、时序结构里

* per-stock R² = 1.20%

#### 策略层实验（Table 3 / Figure 6）



| 配置                                      | Sharpe@2bp |
| --------------------------------------- | ---------- |
| Sector-neutral book                     | +2.15      |
| + causal volatility targeting           | +2.50      |
| fully causal walk-forward（no hindsight） | +2.00      |

#### 逐年稳健性（Table 4，held-out）



| 年份     | 2021 | 2022     | 2023 | 2024 | 2025 |
| ------ | ---- | -------- | ---- | ---- | ---- |
| Sharpe | +1.7 | **+3.5** | +1.9 | +1.8 | +2.7 |



* 五年全正，含 2022 回撤年 —— 不是单一 regime 驱动

* Figure 6 显示策略净值平滑爬升，2022 不跟随 QQQ 回撤

#### 案例分析（Appendix A，worked iteration）



* 第一轮：open-interest crash 后弱反弹是否预测反转 ——"OI crash rebound flow gap"，单因子 IC 0.026–0.037

* 第二轮：目标改为 quiet-market volume expansion，复用同一套架构，只换规划不改评估器

#### 事故复盘（Appendix B）



* 日内成交量参与率，分母用全天总量，泄漏未来信息

* 症状：holdout IC 高得离谱、重新切分就消失；人工审计才定位

* 教训：LLM 审 LLM 代码是 advisory 不是 structural → 催生 operatorization



***

### Q6 创新点与可借鉴点



| 层次       | 创新                                                                |
| -------- | ----------------------------------------------------------------- |
| **理论创新** | 把 "自我改进" 严格限定在 "研究过程" 层；把泄漏区分为生成泄漏与选择泄漏两个独立通道；确立 "因果性在复合下封闭"      |
| **方法创新** | 不对称自由（agent 在 DSL 内自由、评估器在适应面外）；优化指标 ≠ 上报指标；config diff 即实验       |
| **工程创新** | Manager 中介的多 agent 编排（agent 不互相对话）；可证伪提案先于表达式；三条嵌套反馈环；一整年 embargo |

**可迁移到自己工作的部分**：



1. 先用 DSL 而非自由代码，从构造上保证因果

2. 从第一天就分两个文件：selection\_metric（可看）/final\_metric（冻结后只跑一次）

3. 时间序列切分必留 embargo

4. 用持久化记忆让下一轮带着历史观测，而非从零开始



***

### Q7 论文不足与局限性

论文 §7 明确承认：



1. **范围限制**：单市场单频率（Part I 加密 5 分钟；Part II 美股 30 分钟），不保证迁移到其他市场 / 频率

2. **未实盘**：所有指标是换手成本模型下的模拟，2bp 成本未经验证

3. **人机边界**：系统由人设定目标、开闭沙箱、监督流程，是 "在边界内自主" 而非 "无人值守"

4. **两条防线强度不对等**：数据 / 特征路径的密封是结构性的；test 窗口隔离是治理纪律而非硬技术壁垒

5. **两条线不连通**：Part I 因子不能直接喂 Part II 模型（耦合会引入新泄漏）；论文 §6 讨论了耦合是 "自然的下一步"

6. **容量问题未披露**：Sharpe 2.5 对应的资金容量、滑点、冲击成本均未给出

7. **不可复现性**：未开源、未披露具体因子 / 参数，外部无法精确复现



***

## 3. 范式提炼

### 逻辑范式



```
背景（量化研究 = 巨大空间搜索）
  → 痛点（微小方法错误 → 不可复现的回测；RSI 放大错误）
  → 诊断（两种泄漏通道：生成 + 选择）
  → 方案（密封沙箱：算符化堵生成、双指标堵选择；不对称自由）
  → 验证（两个独立系统各自闭环 + 基线对比 + 逐年稳健 + 附录事故自曝）
  → 结论（在"研究过程"层做递归改进，"成功定义"焊死）
```

### 技术范式（剥离场景后的通用套路）

> **"AI 提出候选，自动评估器把关，好的留下继续进化；但要先保证评估器本身可信。"**



1. **受限表达空间**：让 "错误动作" 在语言 / 规格层面无法表达，而非事后审查

2. **验证层级**：把信号按强度排序（形式验证 > 过程奖励 > 裁判 > 自我评估），改进强度与层级一致

3. **搜索面与报告面分离**：被优化的指标 ≠ 被报告的指标

4. **记忆闭环**：每个实验都转成可复用知识，指导下一轮

5. **适用边界**：范式成立的前提是任务能被 DSL 表达；一旦需要 "提出全新数据维度 / 标签"，DSL 封不住



***

## 4. 后续研究拓展

### 值得进一步做的研究话题



1. **耦合两条线**：在模型循环开始前固定因子集，把因子库作为 Part II 沙箱的另一个冻结组件

2. **Regime 条件化（本文未做）**：因子在不同市场 regime 下方向会翻转，可做 regime-conditioned 经验回放

3. **学习型失败模式（sRFT）**：把失败模式从 "规则提示" 升级为 "训进权重"

4. **治理级度量**：给出可审计的自我改进度量协议（综述指出这是最空缺方向）

5. **多市场 / 多频率迁移**：验证密封沙箱是否跨市场通用

6. **容量与成本建模**：真实换手率、滑点、冲击成本、涨跌停 / 停牌约束

### 研究主题 / 问题



* **上位类**：自主机器学习（AutoML）、AI 驱动科研（AI for Science）、递归自我改进（RSI）

* **下位类**：因子挖掘、模型架构搜索、超参优化、回测过拟合防控

* **同位类**：AI Scientist、AutoScientist、AlphaGen/AlphaMemo/QuantEvolver、self-rewarding / self-play / self-evolving

### 数据类型



* 高频盘口 / 分钟级价量 / 日频截面 / 另类数据（情绪、持仓、资金流）

* 本文：加密 5 分钟 + 美股 30 分钟

### 研究设计



* 因果 walk-forward + embargo + 单次 finalize

* 因子层（IC）与策略层（Sharpe）双指标

* 数据驱动选 regime 数（silhouette）

* 规则版 vs 学习版（sRFT）对照



***

## 引用



* 论文：Guo J., Huang S., Gao Y., et al. AQuA: Recursively Self-Improving Quantitative Trading Research Agents. arXiv:2608.12841, 2026. [https://arxiv.org/abs/2608.12841](https://arxiv.org/abs/2608.12841)

* 综述：Chen M., Wang L., Qu B. Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous Research Loops. arXiv:2607.07663, 2026. [https://arxiv.org/abs/2607.07663](https://arxiv.org/abs/2607.07663)

* 算子源头：Kakushadze Z. 101 Formulaic Alphas. arXiv:1601.00999, 2016. [https://arxiv.org/abs/1601.00999](https://arxiv.org/abs/1601.00999)

* 奠基：Bailey D., Borwein J., López de Prado M., Zhu Q. The Probability of Backtest Overfitting. Journal of Computational Finance, 2017.

* 多重检验：Harvey C., Liu Y., Zhu H. …and the Cross-Section of Expected Returns. Review of Financial Studies, 2016.

* 微信解读存档：本目录 `./wechat.md`