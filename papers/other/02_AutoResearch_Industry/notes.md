# AutoResearch 行业深度调查 —— 解读笔记

> **文章**：从 Jane Street 那个 150 亿美元的七月说起——AutoResearch 如何进入顶级对冲基金与自营交易公司
> **类型**：行业深度调查（非单篇论文，汇编公开来源）
> **微信原文**：[wechat.md](./wechat.md)
> **核心事件锚点**：2026 年 7 月 Jane Street 单月亏损约 150 亿美元（FT 率先报道）

---

## 一句话定位

这不是一篇论文，是一张**产业地图**：把"AI 自动做量化研究"这件事，从学术概念一路追到桥水、Man、Citadel、Jane Street、幻方的真实部署，并用 Knight/LTCM/灵均等事故说明 harness 为什么是真正的护城河。

## 核心框架：AutoResearch 闭环 + Harness

闭环本身不难（一个研究生一下午能拼出来）：

```
假设 → 构建(因子表达式/模型config) → 评估器打分 → 选存活者 → 证据写回记忆 → 下一轮
```

真正值钱的是 **harness（测试工装）**——它决定系统会不会骗自己：
- 受限 DSL（因果性由构造保证）
- 密封评估器（数据划分/特征/标签/打分逻辑焊死）
- 双指标纪律（优化指标 ≠ 上报指标）
- 全程审计链

## 量化为什么是 AutoResearch 最好的试验场

| 优势 | 劣势 |
|---|---|
| 评估可写成程序（IC/Sharpe/回撤） | 市场非平稳（规律会过期） |
| 反馈以天/分钟计 | 对手是活的（alpha 被 exploited 就死） |
| 同一批历史数据可并行跑上千实验 | 信噪比极低（最好信号只解释几个百分点方差） |

## 四代搜索引擎演进

| 代 | 范式 | 代表作 | 分水岭 |
|---|---|---|---|
| 1 | 遗传规划（GP） | AutoAlpha (2020) | 表达式树变异/交叉，bloat 顽疾 |
| 2 | 强化学习 | AlphaGen (KDD 2023, Qlib) | PPO + 非法动作掩码 + 增量奖励 |
| 3 | LLM × 记忆 × 进化 | FunSearch → AlphaEvolve → AlphaMemo → AQuA | **评估器从"适应度函数"升级为"独立工程对象"** |

> 真正的分水岭不是"生成候选的模型更聪明"，而是**评估器的地位变了**——矩阵乘法有形式化对错，回测可以被贿赂。

## 评估工程学（行业真正的护城河）

1. **度量预测力**：IC 家族（Pearson/Spearman/ICIR）。量级感：美股 30 分钟单特征 IC 全在 ±0.03 内；Gu-Kelly-Xiu 2020 RFS 证明最好 NN 月度样本外 R² 也只有 0.33%–0.40%。
2. **防"试出来的好结果"**：White Reality Check (2000)、Bailey-López de Prado Deflated Sharpe、Harvey-Liu-Zhu t>3.0、López de Prado purged k-fold + embargo。
3. **防 AI 时代作弊**：RewardHackingAgents、SpecBench——agent 会篡改评估器、污染测试集。
4. **成本与容量**：AQuA 的 2.50 Sharpe 是 2bp 假设下的模拟；大奖章用 ~100 亿美元规模上限守了三十年 Sharpe。

## 记忆三种形态（2026 与前代的本质区别）

- **结构化搜索记忆**：AlphaMemo 存"哪条路径死在哪一步"
- **信念库**：AQuA 的 Memory/Beliefs/Policy 三件套
- **群体记忆**：Numerai meta-model 把全球数据科学家按质押权重聚合

## 顶级机构部署矩阵（公开来源）

| 机构 | 公开动作 |
|---|---|
| Bridgewater | AIA Labs：20 亿美元纯 ML 决策基金（2024），人管风控；后扩至 75 人、~45 亿美元 |
| Man Group | AlphaGPT 自动走完"提假设→写代码→评估"；ManGPT 月活约半数员工 |
| Citadel | 2023 全公司 ChatGPT 授权；2026 接盘 Situational Awareness ~160 亿美元仓位 |
| Jane Street | OCaml 生态最大工业用户；招 ML Researcher；2026.7 单月亏 ~150 亿 |
| Two Sigma | 2018–19 Kaggle 新闻预测竞赛众包研究问题 |
| WorldQuant | 2016《101 Formulaic Alphas》全行业词汇表供应商 |
| 幻方量化 | 萤火二号 ~1 万张 A100 → 2023 创立 DeepSeek，量化反哺前沿 AI 最完整样本 |
| Microsoft | Qlib + R&D-Agent-Quant 开源底座 |

## 事故账单（harness 失效时的真实代价）

| 事故 | 代价 | 教训 |
|---|---|---|
| LTCM (1998) | 股东资本 ~46 亿美元损失 | "模型永远成立"这个假设会错 |
| 2007 量化地震 | 高盛 GEE 当月 -22.5%；大奖章一周 -8.7% | 拥挤是集体事故，alpha 自带定时炸弹 |
| Knight Capital (2012) | 45 分钟亏 ~4.6 亿美元；97 封告警邮件没人看 | 部署纪律 + 告警必须是告警 |
| Archegos (2021) | 瑞信 ~55 亿、野村 ~28.5 亿美元 | 总收益互换躲杠杆，看不见全貌 |
| 灵均 (2024) | 1 分钟卖 ~25.67 亿；限制交易 3 天 + 公开谴责；催生《程序化交易管理规定》 | 多次书面警示不改 = 组织失灵 |
| Situational Awareness / Jane Street (2026.7) | 单月 -67%；Jane Street 亏 ~150 亿 | 剧本是经典杠杆+拥挤，道具换成 AI 股票 |

## 八座绕不开的山

过拟合是原罪 / 拥挤与反身性 / 非平稳性 / 对抗与合规边界 / 容量与成本 / 评估器会被攻击 / 自动化天花板仍明显（2026 元研究：agent 自动开发 agent 很少打过人工基线）/ 黑箱信任是组织问题。

## 引用

- FT 2026.8 Jane Street 报道（中文媒体转述）
- Zuckerman《The Man Who Solved the Market》
- Lowenstein《When Genius Failed》
- Khandani & Lo《What Happened to the Quants in August 2007?》
- López de Prado《Advances in Financial Machine Learning》(2018)
- SEC 2013 Knight Capital 执法文件；上交所/深交所 2024 灵均公告
