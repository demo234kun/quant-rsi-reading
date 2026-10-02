# AutoResearch 行业深度调查 精读（Deep Reading）

> 说明：本篇不是单篇论文，而是一篇**行业深度调查**（汇编公开来源），故模板中"作者/数据集/模型结构"等条目按行业调查形态适配；事实均来自原文存档，未披露处明确标注。

---

## 1. 文章基础元信息

| 项目 | 内容 |
|---|---|
| **文章标题** | 从 Jane Street 那个 150 亿美元的七月说起——AutoResearch 如何进入顶级对冲基金与自营交易公司 |
| **作者** | 公众号作者（具体署名未在存档中披露） |
| **机构** | 不适用（行业调查） |
| **发表会议/期刊** | 不适用（微信公众号文章） |
| **文章链接** | https://mp.weixin.qq.com/s/z0B8QFnsfrPQ3y6JVhQv-A |
| **对应论文** | 无单一论文；汇编多篇公开报道与研究（详见引用） |
| **代码链接** | 无 |
| **关键词** | AutoResearch、AI 量化、harness（测试工装）、评估工程学、因子挖掘、拥挤交易、生存事故、对冲基金 |
| **TLDR** | 闭环一下午就能拼，真正的护城河是"测试工装"——它决定系统会不会骗自己；这张产业地图还附了 LTCM、Knight、灵均等真实事故账单。 |

**核心事件锚点**：2026 年 7 月 Jane Street 单月亏损约 150 亿美元（FT 率先报道）。

---

## 2. 核心精读问答

### Q1 研究问题：这篇文章试图说明什么？

**背景**："AI 自动做量化研究"（AutoResearch）正从学术概念走向顶级机构的真实部署。

**痛点**：闭环（假设→构建→评估→选择→记忆→下一轮）本身不难，一个研究生一下午就能拼出来；难的是**系统会不会骗自己**。

**文章目标**：
1. 画出 AutoResearch 的产业地图（桥水、Man、Citadel、Jane Street、幻方等真实部署）
2. 说明真正值钱的是 **harness（测试工装）**，而非生成候选的模型
3. 用历史事故（LTCM、Knight、Archegos、灵均）说明 harness 失效的代价

### Q2 相关研究 / 四代搜索引擎演进

| 代 | 范式 | 代表作 | 分水岭 / 缺陷 |
|---|---|---|---|
| 1 | 遗传规划（GP） | AutoAlpha（2020） | 表达式树变异/交叉；bloat（膨胀）顽疾 |
| 2 | 强化学习 | AlphaGen（KDD 2023，Qlib） | PPO + 非法动作掩码 + 增量奖励 |
| 3 | LLM × 记忆 × 进化 | FunSearch → AlphaEvolve → AlphaMemo → AQuA | **评估器从"适应度函数"升级为"独立工程对象"** |

> 真正的分水岭不是"生成候选的模型更聪明"，而是**评估器的地位变了**——矩阵乘法有形式化对错，回测却可以被贿赂。

### Q3 解决方案：文章给出的框架

**AutoResearch 闭环**：
```
假设 → 构建(因子表达式/模型config) → 评估器打分 → 选存活者 → 证据写回记忆 → 下一轮
```

**Harness（测试工装）四要素**：
1. 受限 DSL（因果性由构造保证）
2. 密封评估器（数据划分/特征/标签/打分逻辑焊死）
3. 双指标纪律（优化指标 ≠ 上报指标）
4. 全程审计链

**评估工程学（行业真正的护城河）**：
- **度量预测力**：IC 家族（Pearson/Spearman/ICIR）。量级感：美股 30 分钟单特征 IC 全在 ±0.03 内；Gu-Kelly-Xiu（RFS 2020）证明最好 NN 月度样本外 R² 仅 0.33%–0.40%
- **防"试出来的好结果"**：White Reality Check（2000）、Bailey-López de Prado Deflated Sharpe、Harvey-Liu-Zhu t>3.0、López de Prado purged k-fold + embargo
- **防 AI 作弊**：RewardHackingAgents、SpecBench——agent 会篡改评估器、污染测试集
- **成本与容量**：AQuA Sharpe 2.50 是 2bp 假设下的模拟；大奖章用约 100 亿美元规模上限守了三十年 Sharpe

**记忆三种形态（2026 与前代的本质区别）**：
1. 结构化搜索记忆（AlphaMemo 存"哪条路径死在哪一步"）
2. 信念库（AQuA 的 Memory/Beliefs/Policy 三件套）
3. 群体记忆（Numerai meta-model 按质押权重聚合全球数据科学家）

### Q4 信息来源与核查方法（替代"可复现细节"）

- 类型：行业调查，汇编公开报道、SEC 执法文件、交易所公告、学术论文
- 数据/结论的可信度依赖**原始一手来源**（FT、SEC、交易所、公司官网）
- 局限：部分机构内部系统的细节来自媒体报道（如 Man AlphaGPT 据 AI Street 报道），属"一方称"，需谨慎
- 本文无代码、无数据集，不可"复现"，只能核查引用

### Q5 核心材料：机构部署矩阵 + 事故账单

**顶级机构部署矩阵（公开来源）**：

| 机构 | 公开动作 |
|---|---|
| Bridgewater | AIA Labs：20 亿美元纯 ML 决策基金（2024），人管风控；后扩至 75 人、约 45 亿美元 |
| Man Group | AlphaGPT 自动走完"提假设→写代码→评估"；ManGPT 月活约半数员工 |
| Citadel | 2023 全公司 ChatGPT 授权；2026 接盘 Situational Awareness 约 160 亿美元仓位 |
| Jane Street | OCaml 生态最大工业用户；招 ML Researcher；2026.7 单月亏约 150 亿 |
| Two Sigma | 2018–19 Kaggle 新闻预测竞赛众包研究问题 |
| WorldQuant | 2016《101 Formulaic Alphas》全行业词汇表供应商 |
| 幻方量化 | 萤火二号约 1 万张 A100 → 2023 创立 DeepSeek，量化反哺前沿 AI 最完整样本 |
| Microsoft | Qlib + R&D-Agent-Quant 开源底座 |

**事故账单（harness 失效时的真实代价）**：

| 事故 | 代价 | 教训 |
|---|---|---|
| LTCM（1998） | 股东资本约 46 亿美元损失 | "模型永远成立"这个假设会错 |
| 2007 量化地震 | 高盛 GEE 当月 -22.5%；大奖章一周 -8.7% | 拥挤是集体事故，alpha 自带定时炸弹 |
| Knight Capital（2012） | 45 分钟亏约 4.6 亿美元；97 封告警邮件没人看 | 部署纪律 + 告警必须是告警 |
| Archegos（2021） | 瑞信约 55 亿、野村约 28.5 亿美元 | 总收益互换躲杠杆，看不见全貌 |
| 灵均（2024） | 1 分钟卖约 25.67 亿；限制交易 3 天 + 公开谴责；催生《程序化交易管理规定》 | 多次书面警示不改 = 组织失灵 |
| Situational Awareness / Jane Street（2026.7） | 单月 -67%；Jane Street 亏约 150 亿 | 剧本是经典杠杆+拥挤，道具换成 AI 股票 |

### Q6 创新点与可借鉴点

- **认知创新**：把"AI 量化"从叙事拉回可审计的零件（harness、评估器、记忆、事故）
- **方法启发**：看到任何"AI 自动挖 alpha"宣传，先问四个问题——DSL 如何保证因果？优化/上报指标是否分开？切分有没有 embargo？Sharpe 报不报成本假设与容量？
- **暗线启发（幻方）**：量化收益买算力→算力训模型→模型反哺研究，最终长出 DeepSeek；小团队不必追求通用大模型，但必须把研究过程数据沉淀为可复用资产

### Q7 不足与局限

1. 非学术论文，无统一一手数据，部分机构细节依赖媒体报道
2. 八座绕不开的山（过拟合、拥挤、非平稳、合规、容量、评估器被攻击、自动化天花板、黑箱信任）均未被解决
3. 2026 元研究指出：agent 自动开发 agent 很少打过人工基线，自动化天花板仍明显
4. 内部系统真实成效外部无法验证

---

## 3. 范式提炼

### 逻辑范式
```
事件锚点（Jane Street 巨亏）
  → 概念拆解（AutoResearch 闭环 vs harness）
  → 历史纵深（四代引擎 + 评估器地位演变）
  → 现状测绘（机构部署矩阵）
  → 风险印证（事故账单）
  → 结论（护城河是评估与纪律，不是生成模型）
```

### 技术范式
> "AI 提候选，自动评估器把关，好的留下进化"——但金融里评估器可被贿赂，所以评估工程学是核心资产；技术故障与组织失灵是同一张账单。

---

## 4. 后续研究拓展

- **值得做**：可审计的 AutoResearch 协议（DSL 因果证明、双指标、embargo、容量披露）
- **上位类**：金融科技、自主机器学习（AutoML）、AI 驱动科研
- **下位类**：因子挖掘、harness/评估器设计、风险监控与告警系统
- **同位类**：AQuA、AlphaGen、AI Scientist、TradingAgents
- **研究设计**：一手来源核查 + 事故复盘 + 部署对照

### 引用

- FT 2026.8 Jane Street 报道（中文媒体转述）
- Zuckerman G. The Man Who Solved the Market.
- Lowenstein R. When Genius Failed（LTCM）.
- Khandani A., Lo A. What Happened to the Quants in August 2007?
- López de Prado M. Advances in Financial Machine Learning, 2018.
- SEC 2013 Knight Capital 执法文件；上交所/深交所 2024 灵均公告
- Gu S., Kelly B., Xiu D. Empirical Asset Pricing via Machine Learning. RFS, 2020.
