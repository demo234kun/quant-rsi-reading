# FactorEngine 笔记

## 元信息

- **标题**：FactorEngine: A Program-level Knowledge-Infused Factor Mining Framework for Quantitative Investment
- **作者**：Qinhong Lin, Ruitao Feng, Yinglun Feng, Zhenxin Huang, Yukun Chen, Zhongliang Yang, Linna Zhou, Binjie Fei, Jiaqi Liu, Yu Li
- **arXiv**：https://arxiv.org/abs/2603.16365 （v3，2026-03-17）
- **代码**：待核实（需查正文/仓库）
- **分类**：数据进化（知识注入：把非结构化研报转为可执行因子程序；含经验知识库）

## 摘要（原文）

研究 Alpha 因子挖掘——在噪声、非平稳市场数据中自动发现预测信号；现实要求被挖掘因子可直接执行、可审计，且挖掘过程在规模上计算可行。

- 符号方法表达力受限；神经预测器常以可解释性换性能，易受 regime shift 与过拟合影响。
- **FactorEngine (FE)**：程序级因子发现框架，把因子表示为**图灵完备代码**，通过三个分离提升效果与效率：
  1. 逻辑修订 vs. 参数优化；
  2. LLM 引导的方向搜索 vs. 贝叶斯超参搜索；
  3. LLM 使用 vs. 本地计算。
- **知识注入 bootstrapping**：通过闭环多智能体"抽取-验证-代码生成"管线，把非结构化研报转为可执行因子程序；
- **经验知识库**：支持轨迹感知的精炼（含从失败中学习）。

在真实 OHLCV 数据上的大量回测显示，FE 产出的因子预测稳定性与组合影响显著更强（更高 IC/ICIR、Rank IC/ICIR，以及更好的 AR/Sharpe），达到 SOTA。

## 分类理由

- 知识注入数据：把非结构化研报（新数据源）转成因子程序，属"数据→因子"的进化；
- 经验知识库 + 从失败学习，兼具因子进化，但知识注入是其特色。

## 待核实

- 代码仓库、具体市场数据集与真实 IC/Sharpe 数字（待读 PDF 正文补入，不臆造）。
