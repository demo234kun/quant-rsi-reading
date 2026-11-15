# QuantEvolver：把反馈从 prompt 搬进权重 —— 解读笔记

> **论文**：From Feedback Loops to Policy Updates: Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery
> **作者**：Lingzhe Zhang, Tong Jia, Yunpeng Zhai, Zixuan Xie, Chiming Duan, Minghua He, Philip S. Yu, Ying Li
> **arXiv**：[2605.15412](https://arxiv.org/abs/2605.15412)（2026-05-14）
> **代码**：未公开（待查）

---

## 一句话定位

当 LLM 挖因子的 feedback loop 越拉越长，prompt 里堆历史会爆 context、稀释信号、引入 feedback drift。QuantEvolver 的答案是：**别再把反馈写进 prompt 了，把它变成参数更新（RFT），让 Miner LLM 自己长记性。**

## 它指出的 prompt-loop 四个病

1. **Context 爆炸**：历史候选 + 反馈越堆越长；
2. **推理成本上升**：每轮都把全部历史塞进 context；
3. **有用信息被稀释**：早期信号被后期噪音淹没；
4. **Feedback drift**：loop 拉长后，模型偏离原始目标。

再加一个结构性问题：**大 LLM 的生成偏好太稳定**——产出的表达式长得像，候选冗余，搜索停滞。

## 方法：RFT 四步

```
高质量 seed factors
   ↓
构建 seed–time-window 多样化训练任务
   ↓
Miner LLM 生成可执行 Factor DSL 表达式
   ↓
Regime Backtest 评估
   ↓
Diversity-Complementarity Reward 优化 Miner LLM（参数更新，不是 prompt 追加）
```

训练过程中，高质量因子持续积累进 **Mined Factor Database**——既是训练数据来源，也是最终交付的因子库。

### Diversity-Complementarity Reward

这个奖励设计是关键：不只奖励 IC 高，还奖励**和已有因子库互补**。这直接对冲了"大 LLM 生成偏好稳定 → 表达式趋同"的病。

## 结果

- 三个真实 market benchmark 上，每个任务的主指标都超过现有 LLM-based 因子挖掘基线；
- 产出更高质量、更多样互补的因子池。

## 与本库其他文章的对照

| 维度 | AQuA Part I | Astar | QuantEvolver |
|---|---|---|---|
| 经验放哪 | Memory/Beliefs/Policy（外部记忆文件） | 训练进 8B 权重 | RFT 训练进 Miner LLM 权重 |
| 反馈形式 | prompt 里的三层反馈环 | 生产 A/B 回流重训练 | 参数更新（RFT） |
| 防趋同 | 101 Alphas 算符表 + 跨 epoch | 三段 hints 分层 | Diversity-Complementarity Reward |
| 裁判 | 密封沙箱 | 奖励模型 + 真实 A/B | Regime Backtest |

> QuantEvolver 和 Astar 是同一条路线：**经验训进权重，不堆 prompt**。区别是 Astar 训的是"下一步提什么方向"，QuantEvolver 训的是"下一条因子表达式长什么样"。

## 为什么这条路线重要

Prompt-loop 是 2023–2025 年 LLM agent 的默认范式（Reflexion 一系），但它有三个天花板：context 长度、推理成本、反馈漂移。RFT 路线（2025–2026）正在绕开这三个天花板——和 Astar 的发现一致：**经验没有贬值，它变成了训练数据**。

## 局限

- 摘要未披露具体 IC 数字（需读 PDF）；
- RFT 需要 seed factor 启动——冷启动质量决定上限；
- Regime Backtest 的具体设计未在摘要展开；
- 未说明 Miner LLM 基座大小。

## 引用

- 论文：https://arxiv.org/abs/2605.15412
- 对照：AQuA (2608.12841)、Astar (2608.27287)、FactorMiner (2602.14670)、AlphaAgentEvo (ICLR 2026)
