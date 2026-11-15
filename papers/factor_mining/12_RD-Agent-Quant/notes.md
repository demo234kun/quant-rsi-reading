# R&D-Agent-Quant 笔记

## 元信息

- **标题**：R&D-Agent-Quant: A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization
- **作者**：Yuante Li, Xu Yang, Xiao Yang, Minrui Xu, Xisen Wang, Weiqing Liu, Jiang Bian
- **arXiv**：https://arxiv.org/abs/2505.15155 （v2，2025-05-21）
- **代码**：https://github.com/microsoft/RD-Agent （论文摘要明确给出，本库已复现）
- **分类**：数据进化（data-centric，因子-模型联合优化）

## 摘要（原文）

金融市场因高维、非平稳、持续波动，对资产收益预测构成根本挑战。现有量化研究管线自动化程度有限、可解释性弱、因子挖掘与模型创新等关键环节协调割裂。论文提出 **RD-Agent(Q)**，首个 data-centric 的多智能体框架，通过协调的因子-模型联合优化，自动化量化策略的全栈研发。

RD-Agent(Q) 把量化过程拆为两个迭代阶段：
- **Research 阶段**：动态设定与目标对齐的提示、基于领域先验形成假设、映射为具体任务；
- **Development 阶段**：用代码生成智能体 Co-STEER 实现任务代码，在真实市场回测中执行。

两阶段通过 feedback 阶段连接，评估实验结果并指导后续迭代；用**多臂老虎机调度器**自适应选择方向。

实证：年化收益最高可达经典因子库的 **2 倍**，且因子用量减少 **70%**；在真实市场上优于 SOTA 深度时序模型。

## 分类理由

- 核心是 **data-centric**：围绕数据/因子与模型的联合优化，而非仅在模型层迭代；
- 多臂老虎机做方向选择，feedback 闭环驱动数据-因子-模型协同进化。

## 与本库主线的关系

- 已对其代码仓库（microsoft/RD-Agent）做离线测试：129 passed / 1 failed（Windows 权限位），见 `reproduction/RD-Agent_REPRODUCTION.md`。
