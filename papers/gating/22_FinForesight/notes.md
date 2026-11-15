# FinForesight · 笔记

> 论文来源：arXiv:2611.01621v1 [cs.CL]
> 论文题目：FinForesight: A Diagnostic Backtesting Benchmark for Deep Research Systems in Financial Forecasting

## 1. 论文基础元信息

| 项目 | 内容 |
| --- | --- |
| **论文来源** | arXiv:2611.01621v1 [cs.CL] |
| **论文题目** | FinForesight: A Diagnostic Backtesting Benchmark for Deep Research Systems in Financial Forecasting |
| **作者** | Fengyuan Liu, Mukai Li, Jieshun You, Yilin Zheng, Chenjia Min, Yizhou Zhang, Harper Chen, Qi Liu |
| **提交时间** | 2026-11-01（v1，Sun, 1 Nov 2026 06:16:56 UTC） |
| **学科分类** | cs.CL（Computation and Language）；交叉 cs.LG |
| **论文链接** | https://arxiv.org/abs/2611.01621 |
| **DOI** | https://doi.org/10.48550/arXiv.2611.01621 |
| **代码 / 数据** | 论文声明 code and benchmark data 公开（具体仓库地址待从 PDF 正文核实） |
| **本地存档** | `paper.pdf`（已下载 v1 全文） |

## 2. 摘要级概览（仅来自 arXiv 摘要，未经精读扩写）

**要解决的问题**：金融预测需要在不确定下综合「正在演化的证据」并推理，深度研究系统（deep research systems）因此在预测任务上有潜力。但评测其预测能力很难：
- 历史回测可能奖励「记住的结果」或「预测日之后才可得的信息」；
- 实时（live）预测虽然杜绝直接看到已实现结果，但反馈只在事件落地后才回来。

**做法**：FinForesight —— 面向金融深度研究系统的「诊断式回测基准」（diagnostic backtesting benchmark），目的是拿到及时反馈的同时还能给历史表现打分。

**覆盖范围**：中国市场、美国市场、香港市场；四类预测任务 —— 估值（valuation）、收益排序（return ranking）、事件方向（event direction）、未来财务基本面（future financial fundamentals）。另有两项能力诊断任务 —— 反事实推理（counterfactual reasoning）、金融计算（financial calculation），与预测表现分开计分。

**机制**：harness-compatible 框架，把检索到的证据限制在预测日当时可得的信息范围内。

**评测设计**：对比三类评测 —— 预训练期（pretraining-era）、截断后已落地（resolved post-cutoff）、实时（live），用来检验受控回测能否逼近未来真实表现。

**摘要给出的主要发现**：
1. 多数时间维度的比较中，预训练期得分高于截断后得分（说明存在记忆成分）；
2. 检索控制越严格，截断后回测与实时结果之间的差距越小；
3. 另做了预测归因（forecasting attribution）与鲁棒性分析：分数如何随检索策略变化、预测如何随 prompt 改写与数值扰动变化。

> 注：以上仅摘要口径。具体数据集规模、指标定义、各任务数值、消融与鲁棒性结果均标注「待精读」，不预填。

## 3. 待精读清单（TODO）

- [ ] 数据集：三市场的时间区间、样本量、标的范围、数据源
- [ ] 四类预测任务的评分函数与基线模型
- [ ] 两项诊断任务（反事实推理 / 金融计算）的题面构造与计分
- [ ] harness 如何界定「预测日可得信息」（数据截止、检索白名单）
- [ ] 预训练期 vs 截断后 vs 实时 的具体分数与差距数值
- [ ] 检索策略消融（retrieval policy）实验结果
- [ ] prompt 改写 / 数值扰动的鲁棒性曲线
- [ ] 代码与数据仓库地址、可复现性说明
