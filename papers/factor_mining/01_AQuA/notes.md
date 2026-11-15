# AQuA：递归自我改进的量化研究 Agent —— 解读笔记

> **论文**：AQuA: Recursively Self-Improving Quantitative Trading Research Agents
> **作者**：Jiacheng Guo, Suozhi Huang, Yunlong Gao, Zihao Li, Jian Ge, Xu Kuang, Mengdi Wang
> **机构**：Princeton / Ant Group / Stanford
> **arXiv**：[2608.12841](https://arxiv.org/abs/2608.12841)（v1 2026-08-13，v2 2026-08-17）
> **微信解读**：[原文存档](./wechat.md)

---

## 一句话定位

AQuA 不是"造了一个更聪明的量化 AI"，而是**先解决怎么让 AI 在自我改进时不偷看答案骗自己**——把打分的尺子锁在 agent 够不到的地方。

## 它到底在改哪一层

2026 年 RSI 综述（[arXiv:2607.07663](https://arxiv.org/abs/2607.07663)）把"自我改进"分四层：

| 层 | 改什么 | AQuA 碰不碰 |
|---|---|---|
| 部署行为 | 模型在线跑得更顺手 | ❌ |
| 训练策略 | 训练流程本身变好 | ❌ |
| 评估器 | 打分的尺子变准 | ❌ **焊死** |
| **研究过程** | 下一步试什么假设 | ✅ **只改这层** |

> 核心立场：**改进的是"研究过程"，不是"成功的定义"。** AI 可以不断改"下一步想试什么"，但永远无权改"什么叫成功"。

## 最狠的一段：附录 B 自曝事故

早期版本允许 agent 自己写特征代码，再由"审查 agent"检查是否有前视偏差。
一个特征："日内成交量占比" = 开盘到当前分钟的累计成交量 / 日成交量归一化项。
- 文字描述看起来完全回看；
- 但实现里的"日成交量归一化项"用的是**全天总成交量（含收盘后才知道的 bar）**；
- 于是每分钟都被偷偷写进了"当天最终成交了多少"这个未来信息。

结果：holdout IC 高得离谱，一重新切分数据就消失。

> **结论印在墙上**：让一个 LLM 去审查另一个 LLM 写的代码，只是**建议性**的，不是**结构性**的——因为写的人和审的人共享同一套盲点（同源模型，对"什么代码看起来正常"有一致错觉）。

## 核心设计：Asymmetric Freedom（不对称自由）

AI 能做的只有一件事：提交一个受限提案 μ。
以下四样东西在迭代开始前就被人类写死、AI 只能引用不能改：

```
s_k = V( C(μ_k); S ),  其中 S = (D, F, L, V) 全部密封
```

- **D** = 数据划分（splits）
- **F** = 特征定义
- **L** = 标签定义
- **V** = 评估器（打分逻辑）

### 两条泄漏通道，两种堵法

| 通道 | 是什么 | 怎么堵 | 强度 |
|---|---|---|---|
| **生成泄漏** (generation leakage) | AI 在写特征/标签时偷看未来 | **Operatorization（算符化）**：不让自由写代码，只能在预定义算符表里拼装；每个算符数学上只读回看窗口 | **结构性**（写不出来就是写不出来） |
| **选择泄漏** (selection leakage) | AI 反复看最终指标，学会"投其所好" | **优化指标 ≠ 上报指标**：搜索时只见验证集分数；测试窗口配置冻结后只打一次分，永不回流 agent | **治理约定**（靠纪律，非密码学保证） |

> 作者自己承认：两条防线强度不对等。第一条是结构，第二条是流程。

## 两条独立生产线

### Part I：符号因子发现（加密货币 5 分钟频）

- **架构**：1 个 AI Manager + 6 个专职 agent（Data Steward / Visual Analyst / Idea Miner / Factor Evaluator / Backtest Engineer / Research Librarian）；agent 之间**从不直接对话**，所有交接过 Manager。
- **入口纪律**：因子不是以表达式出现，而是先以**可证伪提案**出现——假设、机制、预测方向、证伪条件写清楚，才允许从算符注册表里拼装。
- **三层反馈环**：单次回测内方向校准 → 单次运行内信念更新 → 跨 run 记忆引导下一轮搜索。
- **算符词表源头**：WorldQuant 2016 年《101 Formulaic Alphas》——横截面算符（rank/z-score）+ 时序算符（滞后/差分/滚动相关）+ 逐元素算术，因果性由构造保证。

**结果（加密货币 5 分钟 universe，20 个研究 epoch）**：

| 系统 | Combined Spearman IC |
|---|---|
| **AQuA Part I** | **~0.190** |
| AlphaMemo（适配版） | 0.171 |
| AlphaGen（适配版） | 0.151 |
| LSTM | 0.137 |
| LightGBM | 0.106 |
| Alpha158 风格基线 | 0.075 |

单因子 IC 只有 0.026–0.037——**强度来自组合，不来自某条神规则**。

### Part II：可训练模型开发（美股 30 分钟前瞻）

- **入口纪律**：一次实验 = 一个 **config diff**（只改架构/损失/采样器/优化器这些已注册旋钮），一个 diff 一个变体，天然可比。
- **数据划分**：训练 2010–2019，**2020 整年 embargo 隔离带**（谁都不碰），测试 2021–2025 只打一次分。
- **模型架构**：多尺度 1D 卷积前端（kernel 1/5/15）→ 可配置主干（LSTM/Mamba/attention，报告用 attention）→ 横截面混合 → 门控融合 → 每股读out。

**结果**：

| 模型族 | Per-stock raw IC |
|---|---|
| Ridge 线性 | +0.0251 |
| LightGBM | +0.0397 |
| xLSTM | +0.0434 |
| LSTM | +0.0535 |
| GRU | +0.0613 |
| **AQuA hybrid** | **+0.0843** |

- Per-stock R² = 1.20%；
- 转成美元中性阈值多空策略，双边成本 2bp：
  - 行业中性化 Sharpe **+2.15**
  - + 因果波动率目标化 **+2.50**
  - 完全因果 walk-forward **+2.00**
- 2021–2025 逐年 Sharpe：+1.7 / +3.5 / +1.9 / +1.8 / +2.7，**五年全正**（含 2022 回撤年）。

> ⚠️ Part I 的 0.190 是加密货币 5 分钟 Spearman IC，Part II 的 0.0843 是美股 30 分钟 per-stock IC，**口径不同，论文反复强调不能互比**。

## 局限（论文自己承认 + 行业视角）

1. 全是模拟，未实盘；2bp 成本假设未经验证。
2. 单市场单频率：Part I 加密 5 分钟，Part II 美股 30 分钟。
3. 选择泄漏防线是治理约定，不是密码学保证。
4. 两条线不连通（不共享 agent/记忆/状态）——硬连会引入新泄漏。
5. 2.50 Sharpe 对应容量、滑点、冲击成本均未披露。
6. 对照 Gu-Kelly-Xiu (RFS 2020)：神经网络月度样本外 R² 也只有 0.33%–0.40%——AQuA 的量级落在严肃文献正常区间，不是神迹。

## 引用

- 论文：https://arxiv.org/abs/2608.12841
- MarkTechPost 解读：https://www.marktechpost.com/2026/09/01/aqua-a-two-part-agentic-framework-for-autonomous-factor-discovery/
- 相关奠基：Bailey & López de Prado《The Probability of Backtest Overfitting》(2014)；Harvey, Liu, Zhu (RFS 2016) 多重检验 t>3.0；López de Prado《AFML》(2018) purged k-fold + embargo。
