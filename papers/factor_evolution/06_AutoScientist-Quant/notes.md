# AutoScientist-Quant：把量化研究当预算搜索问题 —— 解读笔记

> **论文**：AutoScientist-Quant: Self-Evolving Coding Agents for Automatic Research in Quantitative Investment
> **作者**：Zongqian Li, Yaoyiran Li, Yaohui Guo, Ming Zhang, Nigel Collier, Eugene Ie
> **arXiv**：[2608.28632](https://arxiv.org/abs/2608.28632)（v1 2026-08-05，v2 2026-09-01）
> **代码**：未公开（待查）

---

## 一句话定位

和 AQuA 同月撞题的直接对手。AQuA 把研究拆成两条互不相通的产线（挖因子 + 调模型），AutoScientist-Quant 反着来：**用一个 controller 把整个量化研究（从假设到可部署策略）当成一个有预算的搜索问题统一调度**。

## 它指出前人的三个弱点

1. **搜索过程不能在 run 中自适应**——大多数 agent 是固定流程，不能中途改路线；
2. **自动化只到 alpha 生成就停了**——选哪个因子库、选哪个模型，还是人来；
3. **alpha 发现会偷看 test window**——loop feedback 或代码问题导致前视。

## 核心设计：单一 Controller + 共享 Memory

把整个量化研究建模为**预算化搜索**：

```
剩余预算 t ──→ Controller ──→ {
  这一轮做什么: improve / combine / pivot / stop
  扩展哪个节点
  生成多少个 alpha
  从共享 memory 检索哪些历史轨迹
}
```

关键决策点全由同一个 controller 根据**剩余预算**条件化：
- 预算多 → 敢 pivot（大跳方向）；
- 预算少 → 选最稳的 improve。

同一个 core 还负责：
- **从因子库里挑库**（library selection）；
- **调模型**（model tuning）；
- 闭环从假设一直走到 deployable strategy。

## 防泄漏：两个被修掉的 lookahead 问题

论文明确说"review the evaluation pipeline reused from prior work, fix two lookahead problems, keep feedback window disjoint from held-out test window"——feedback window 和 test window 不相交，所有比较测的是真泛化。

> 这和 AQuA 的 embargo 隔离带是同一件事，只是表述不同。

## 结果

- CSI 系列 universe 上，几乎所有 setting 的几乎所有指标都最好；
- 结论跨多个 backbone（不同 LLM）和多个 market 都成立。

## 与 AQuA 的对照

| 维度 | AQuA | AutoScientist-Quant |
|---|---|---|
| 研究过程 | 两条互不相通产线（因子/模型） | 单一 controller 统一调度 |
| 自适应 | 三层反馈环（单次/单 run/跨 run） | controller 根据剩余预算实时决策 |
| 闭环范围 | Part I 挖因子、Part II 调模型，不连通 | 从假设一路到 deployable strategy |
| 记忆 | Memory/Beliefs/Policy 三件套 | 共享 trajectory memory，controller 决定检索什么 |
| 防泄漏 | operatorization + 双指标纪律 + embargo | 修两个 lookahead + feedback/test window 不相交 |
| 测试市场 | 加密 5min + 美股 30min | CSI（A 股）系列 |

> **AQuA 是"分而治之，每条线自己闭环"；AutoScientist-Quant 是"一个大脑调度一切"。** 两种哲学，值得并列读。

## 局限

- 摘要未披露具体 IC/Sharpe 数字（需读 PDF 实验节）；
- 作者团队有 Google 背景（Eugene Ie），但未说明是否开源；
- "一个 controller 调度一切"在预算紧张时可能反而不如分治稳定——论文应该做了 ablation，但需细读。

## 引用

- 论文：https://arxiv.org/abs/2608.28632
- 对照：AQuA (arXiv:2608.12841)
