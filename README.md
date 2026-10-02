# Quant Papers · 量化研究精读库

> 一个个人收藏库：收集"递归自我改进（RSI）× 量化交易"方向的精致文章。
> 每篇含：论文全文 PDF · 微信解读原文存档（如有）· 个人解读笔记 · 个人思考。
> 创建：2026-09-27 ｜ 更新：2026-10-03

---

## 🧭 这个库在看什么

主线只有一条：**当 AI 开始自动做量化研究，它怎么不骗自己？**

按"被迭代对象"把论文分成三类（外加综述 / 方法论）：

```
┌──────────────┬──────────────────────────────────────────────────┐
│ 数据进化      │ 迭代数据源 / 标签 / 特征构造（本库 3 篇，最易泄漏）    │
├──────────────┼──────────────────────────────────────────────────┤
│ 因子进化      │ 迭代符号因子表达式 / 因子生成模型（本库 4 篇）        │
├──────────────┼──────────────────────────────────────────────────┤
│ 策略进化      │ 迭代组合规则 / 仓位 / 风控 / 交易决策（本库 4 篇）    │
├──────────────┼──────────────────────────────────────────────────┤
│ 其他          │ 综述 / 行业调查 / 元层方法论（本库 3 篇）           │
└──────────────┴──────────────────────────────────────────────────┘
```

```
原始逻辑链（保留）：

05_RSI_ThreeReins  ── 总框架：三根缰绳（裁判 / 燃料 / 传动 τ）
        │
        ├── 01_AQuA              ── 因子：评估器焊死，密封沙箱（学术）
        ├── 06_AutoScientist-Quant ── 因子：单一 controller 统一调度（对照）
        ├── 03_Astar             ── 因子：环内学习型裁判 + 外圈真实 A/B（生产）
        ├── 07_QuantEvolver      ── 因子：经验训进权重，RFT 替代 prompt-loop
        ├── 08_EvolveTrade       ── 策略：LLM 从交易经验重写自己的 policy
        ├── 09_SHARP             ── 策略：可审计符号规则，原子化编辑
        ├── 10_AlgoEvolve        ── 策略：交易程序元进化，涌现 regime-adaptive
        ├── 11_RecursiveMultiAgent ── 策略：组合策略递归 + 风险感知 RL
        ├── 04_Dream-RSI         ── 元层：做梦进化，不重训就继承
        │
        └── 02_AutoResearch_Industry ── 产业落地：桥水/Man/Citadel/幻方
```

---

## 📚 文章索引

### 🥇 数据进化（Data Evolution）

> 数据/标签一旦开放给 agent 迭代，最易引入泄漏（AQuA 因此把数据焊死），且"新数据是否更好"缺外部判据。下列三篇是这一方向目前找到的真实工作（2025–2026）。

| # | 文章 | 笔记 | 作者 / 来源 | 一句话概括 | 关键词 | 对应论文 | 代码 | 个人思考 |
|---|------|------|------------|-----------|--------|----------|------|----------|
| 12 | [R&D-Agent-Quant](papers/data_evolution/12_RD-Agent-Quant/notes.md) | Yuante Li 等（Microsoft） | 首个 data-centric 多智能体，因子-模型联合优化；Research/Development 闭环 + 多臂老虎机调度，ARR 最高约 2×、因子少 70% | data-centric · 因子-模型联合优化 · Co-STEER · 多臂老虎机 · feedback | [arXiv:2505.15155](https://arxiv.org/abs/2505.15155) | [microsoft/RD-Agent](https://github.com/microsoft/RD-Agent) | [思考](papers/data_evolution/12_RD-Agent-Quant/thoughts.md) |
| 13 | [TradingGroup](papers/data_evolution/13_TradingGroup/notes.md) | Feng Tian, Flora D. Salim, Hao Xue | 多智能体交易系统，自我反思 + 端到端数据合成/标注管线，用交易活动数据反哺后训练；含动态止损/止盈 | 数据合成 · 自我反思 · 多智能体 · 后训练 · 动态风控 | [arXiv:2508.17565](https://arxiv.org/abs/2508.17565) | 待核实 | [思考](papers/data_evolution/13_TradingGroup/thoughts.md) |
| 14 | [FactorEngine](papers/data_evolution/14_FactorEngine/notes.md) | Qinhong Lin 等 | 程序级因子挖掘，因子=图灵完备代码；知识注入把研报转为可执行因子，经验知识库支持从失败学习 | 知识注入 · 程序级因子 · 三分离 · 经验知识库 · 从失败学习 | [arXiv:2603.16365](https://arxiv.org/abs/2603.16365) | 待核实 | [思考](papers/data_evolution/14_FactorEngine/thoughts.md) |

---

### 🔢 因子进化（Factor Evolution）

| # | 文章 | 深度精读 | 作者 / 来源 | 一句话概括 | 关键词 | 对应论文 | 微信原文 | 个人思考 |
|---|------|---------|------------|-----------|--------|----------|----------|----------|
| 01 | [AQuA：递归自我改进的量化研究 Agent](papers/factor_evolution/01_AQuA/notes.md) | [📖 精读](papers/factor_evolution/01_AQuA/deep_reading.md) | Jiacheng Guo 等（Princeton / Ant / Stanford） | 两个互不连通的量化研究系统（挖因子 + 调模型），把打分的尺子焊死在 agent 够不到的地方 | RSI · 密封沙箱 · operatorization · 双指标纪律 · embargo · 因子挖掘 · 时序模型 | [arXiv:2608.12841](https://arxiv.org/abs/2608.12841) | [微信原文](https://mp.weixin.qq.com/s/MEgyuiGTxyOlxVJ2EnVBzQ) | [思考](papers/factor_evolution/01_AQuA/thoughts.md) |
| 03 | [Astar：8B 模型在生产环境跑 RSI](papers/factor_evolution/03_Astar/notes.md) | [📖 精读](papers/factor_evolution/03_Astar/deep_reading.md) | 阿里 × 浙江大学 | 一个 8B 专用模型只会一件事——提出 AI 系统下一步演化方向；Lazada 广告召回无人值守 20 轮，GMV +4.86% | RSI · 工业闭环 · pairwise 数据工程 · 奖励模型 · GRPO · 增量校准 · 真实 A/B · Lazada | [arXiv:2608.27287](https://arxiv.org/abs/2608.27287) | [微信原文](https://mp.weixin.qq.com/s/Eb6vKO6fvefasBvc-JJ9dQ) | [思考](papers/factor_evolution/03_Astar/thoughts.md) |
| 06 | [AutoScientist-Quant：把量化研究当预算搜索](papers/factor_evolution/06_AutoScientist-Quant/notes.md) | [📖 精读](papers/factor_evolution/06_AutoScientist-Quant/deep_reading.md) | Zongqian Li 等（含 Google DeepMind 背景） | 和 AQuA 同期对手；单一 controller 根据剩余预算统一调度从假设到 deployable strategy 的全流程 | RSI · budgeted search · controller · 共享 memory · CSI · 对照 AQuA | [arXiv:2608.28632](https://arxiv.org/abs/2608.28632) | — | [思考](papers/factor_evolution/06_AutoScientist-Quant/thoughts.md) |
| 07 | [QuantEvolver：把反馈从 prompt 搬进权重](papers/factor_evolution/07_QuantEvolver/notes.md) | [📖 精读](papers/factor_evolution/07_QuantEvolver/deep_reading.md) | Lingzhe Zhang 等（Philip S. Yu 团队） | RFT 替代 prompt-loop；把可执行回测评估转成 Miner LLM 参数更新，Diversity-Complementarity Reward 抗趋同 | RSI · RFT · Factor DSL · Regime Backtest · 抗趋同 · 因子挖掘 | [arXiv:2605.15412](https://arxiv.org/abs/2605.15412) | — | [思考](papers/factor_evolution/07_QuantEvolver/thoughts.md) |

---

### 📈 策略进化（Strategy Evolution）

| # | 文章 | 深度精读 | 作者 / 来源 | 一句话概括 | 关键词 | 对应论文 | 个人思考 |
|---|------|---------|------------|-----------|--------|----------|----------|
| 08 | EvolveTrade：经验驱动的策略自进化 | *待补* | — | 工具使用型 LLM 交易 agent，每天从自身交易经验重写 policy（policy self-evolution，逐 refinement） | 策略自进化 · policy 重写 · 工具使用 · 交易经验 | [arXiv:2609.17632](https://arxiv.org/abs/2609.17632) | *待补* |
| 09 | SHARP：自进化、可审计的规则策略 | *待补* | — | 神经符号框架，策略 = 人类可读条件-动作规则；归因 agent 定位失效规则，做原子化编辑 | 策略自进化 · 神经符号 · rubric policy · 规则归因 · 原子编辑 | [arXiv:2605.06822](https://arxiv.org/abs/2605.06822) | *待补* |
| 10 | AlgoEvolve：交易程序的元进化 | *待补* | — | LLM 进化框架，生成/评估/迭代可执行 Python 交易策略，涌现 regime-adaptive 规则自主切换 | 策略自进化 · 程序进化 · 严格测试 · regime-adaptive | [arXiv:2606.26173](https://arxiv.org/abs/2606.26173) | *待补* |
| 11 | Recursive Multi-Agent：递归组合策略 | *待补* | — | 地缘不确定性下多 agent 迭代优化 portfolio，RL 目标含风险/回撤惩罚（R=r−0.8σ−1.5·DD） | 策略自进化 · 多 agent · 组合 · 风险感知 RL · 回撤控制 | [arXiv:2605.25311](https://arxiv.org/abs/2605.25311) | *待补* |

> 08–11 目前仅有 PDF，`notes / thoughts / deep_reading` 待补。

---

### 🗂 其他（综述 / 行业 / 方法论）

| # | 文章 | 深度精读 | 作者 / 来源 | 一句话概括 | 关键词 | 对应论文 | 微信原文 | 个人思考 |
|---|------|---------|------------|-----------|--------|----------|----------|----------|
| 02 | [AutoResearch 行业深度调查](papers/other/02_AutoResearch_Industry/notes.md) | [📖 精读](papers/other/02_AutoResearch_Industry/deep_reading.md) | 公众号深度调查（汇编公开来源） | 从 Jane Street 150 亿美元七月说起，把 AI 自动量化追到桥水/Man/Citadel/幻方的真实部署与事故账单 | harness · 四代搜索引擎 · 评估工程学 · 记忆 · 事故史 · 桥水 AIA · AlphaGPT · 幻方/DeepSeek | 无单篇论文（汇编） | [微信原文](https://mp.weixin.qq.com/s/z0B8QFnsfrPQ3y6JVhQv-A) | [思考](papers/other/02_AutoResearch_Industry/thoughts.md) |
| 04 | [Dream-RSI：在历史发现树上做梦](papers/other/04_Dream-RSI/notes.md) | [📖 精读](papers/other/04_Dream-RSI/deep_reading.md) | Google 系团队 | 不重训模型，让"找知识的方法"在历史发现树上做梦进化；元层自改进，执行层一行不改 | RSI · 元层探索 · 发现树回放 · 反事实 · PIT 加权 · Lasso · τ>1 | [arXiv:2609.14858](https://arxiv.org/abs/2609.14858) ｜ [代码](https://github.com/zhengkid/Dream-RSI) | [微信原文](https://mp.weixin.qq.com/s/NwO-gQl96t_gumJhPs2kEA) | [思考](papers/other/04_Dream-RSI/thoughts.md) |
| 05 | [RSI 三根缰绳：全局框架](papers/other/05_RSI_ThreeReins/notes.md) | [📖 精读](papers/other/05_RSI_ThreeReins/deep_reading.md) | 公众号综述（自建框架） | 把整个 RSI 领域压成最小回路 + 三根缰绳：裁判在哪环内、燃料从哪来、改进多少传回改进者 | RSI 框架 · 裁判拓扑 · 模型坍缩 · 传动系数 τ · 六十年八站 · 四家族 | 综述坐标 [arXiv:2607.07663](https://arxiv.org/abs/2607.07663) | [微信原文](https://mp.weixin.qq.com/s/wf1KOGRfXpefa0vtw8OdMw) | [思考](papers/other/05_RSI_ThreeReins/thoughts.md) |

---

## 🗂 目录结构

```
quant_library/
├── README.md                          ← 你在这里
├── DESIGN.md / PAPER_PROPOSAL.md / PAPER_DIRECTIONS.md / RESULTS.md
├── project/                           ← RegimeSeal 可运行研究管线
└── papers/
    ├── data_evolution/
    │   ├── 12_RD-Agent-Quant/ (paper.pdf, notes.md, wechat.md, thoughts.md, deep_reading.md)
    │   ├── 13_TradingGroup/   (paper.pdf, notes.md, wechat.md, thoughts.md, deep_reading.md)
    │   └── 14_FactorEngine/   (paper.pdf, notes.md, wechat.md, thoughts.md, deep_reading.md)
    ├── factor_evolution/
    │   ├── 01_AQuA/        (paper.pdf, wechat.md, notes.md, thoughts.md, deep_reading.md)
    │   ├── 03_Astar/       (paper.pdf, wechat.md, notes.md, thoughts.md, deep_reading.md)
    │   ├── 06_AutoScientist-Quant/ (paper.pdf, notes.md, thoughts.md, deep_reading.md)
    │   └── 07_QuantEvolver/ (paper.pdf, notes.md, thoughts.md, deep_reading.md)
    ├── strategy_evolution/
    │   ├── 08_EvolveTrade/          (paper.pdf)
    │   ├── 09_SHARP/                (paper.pdf)
    │   ├── 10_AlgoEvolve/           (paper.pdf)
    │   └── 11_RecursiveMultiAgent/  (paper.pdf)
    └── other/
        ├── 02_AutoResearch_Industry/ (wechat.md, notes.md, thoughts.md, deep_reading.md)
        ├── 04_Dream-RSI/    (paper.pdf, wechat.md, notes.md, thoughts.md, deep_reading.md)
        └── 05_RSI_ThreeReins/ (wechat.md, notes.md, thoughts.md, deep_reading.md)
```

---

## 🧩 关键数字速查

| 指标 | 数值 | 出处 |
|---|---|---|
| AQuA Part I 加密货币组合 Spearman IC | ~0.190（单因子仅 0.026–0.037） | 01 |
| AQuA Part II 美股 per-stock IC | +0.0843（最强基线 GRU +0.0613） | 01 |
| AQuA 美元中性策略 Sharpe @2bp | +2.50（完全因果 walk-forward +2.00） | 01 |
| Astar 单提案真实执行成功率 | 0.6786（GPT-5.5 0.3071 / 人类 0.3229） | 03 |
| Astar 奖励模型 AUC | 0.8487（人类专家 0.6142） | 03 |
| Astar 线上 A/B | GMV +4.86%、广告收入 +1.82% | 03 |
| Dream-RSI 求解器 runtime | 3587ms → 2931ms（Gemini-3.1-Pro） | 04 |
| 自我裁判 24 代后报告/真实裂缝 | +1.19（密封裁判仅 -0.002） | 05 |
| Jane Street 2026.7 单月亏损 | ~150 亿美元 | 02 |
| AutoScientist-Quant | CSI universe 几乎所有指标最优（跨 backbone/market） | 06 |
| QuantEvolver | 三个 market benchmark 主指标全面超 LLM 基线 | 07 |
| 策略 08–11 | 关键数字待读 PDF 补 | 08–11 |

---

## 🛣 建议阅读路线

- **第一次读**：05（框架）→ 01（最严样本）→ 06（同期对照）→ 03（工业样本）
- **做因子**：01 → 06 → 03 → 07
- **做策略**：09（SHARP，最严谨）→ 08（EvolveTrade）→ 10（AlgoEvolve）→ 11
- **关心方法论 / 不做量化**：05 → 04 → 03 → 07
- **想看行业八卦与事故**：02

---

## 📖 引用与来源

### 论文

1. **AQuA**: Jiacheng Guo, Suozhi Huang, Yunlong Gao, Zihao Li, Jian Ge, Xu Kuang, Mengdi Wang. *AQuA: Recursively Self-Improving Quantitative Trading Research Agents*. arXiv:2608.12841, 2026. https://arxiv.org/abs/2608.12841
2. **Astar**: 阿里 × 浙江大学. arXiv:2608.27287, 2026. https://arxiv.org/abs/2608.27287
3. **Dream-RSI**: Google 系团队. arXiv:2609.14858, 2026. https://arxiv.org/abs/2609.14858 ｜ 代码: https://github.com/zhengkid/Dream-RSI
4. **RSI 四层框架综述**: arXiv:2607.07663, 2026. https://arxiv.org/abs/2607.07663
5. **AutoScientist-Quant**: Zongqian Li, Yaoyiran Li, Yaohui Guo, Ming Zhang, Nigel Collier, Eugene Ie. arXiv:2608.28632, 2026. https://arxiv.org/abs/2608.28632
6. **QuantEvolver**: Lingzhe Zhang et al. *From Feedback Loops to Policy Updates: Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery*. arXiv:2605.15412, 2026. https://arxiv.org/abs/2605.15412
7. **EvolveTrade**: *Experience-Driven Policy Refinement for Self-Evolving LLM Trading Agents*. arXiv:2609.17632, 2026. https://arxiv.org/abs/2609.17632
8. **SHARP**: *Self-Evolving Human-Auditable Rubric Policy for Financial Trading Agents*. arXiv:2605.06822, 2026. https://arxiv.org/abs/2605.06822
9. **AlgoEvolve**: *LLM-driven Meta-evolution of Algorithmic Trading Programs*. arXiv:2606.26173, 2026. https://arxiv.org/abs/2606.26173
10. **Recursive Multi-Agent Trading System**: *Iterative Optimized Portfolio Strategy Under Geopolitical Uncertainty*. arXiv:2605.25311, 2026. https://arxiv.org/abs/2605.25311
11. **R&D-Agent-Quant**: arXiv:2505.15155, 2025（NeurIPS 2025）. https://arxiv.org/abs/2505.15155
12. **TradingGroup**: arXiv:2508.17565, 2025. https://arxiv.org/abs/2508.17565
13. **FactorEngine**: arXiv:2603.16365, 2026. https://arxiv.org/abs/2603.16365
14. **MarkTechPost 对 AQuA 的报道**: https://www.marktechpost.com/2026/09/01/aqua-a-two-part-agentic-framework-for-autonomous-factor-discovery/

### 微信解读原文

1. AQuA 深度解读: https://mp.weixin.qq.com/s/MEgyuiGTxyOlxVJ2EnVBzQ
2. AutoResearch 行业深度调查: https://mp.weixin.qq.com/s/z0B8QFnsfrPQ3y6JVhQv-A
3. Astar 深读: https://mp.weixin.qq.com/s/Eb6vKO6fvefasBvc-JJ9dQ
4. Dream-RSI × 量化: https://mp.weixin.qq.com/s/NwO-gQl96t_gumJhPs2kEA
5. RSI 三根缰绳全景: https://mp.weixin.qq.com/s/wf1KOGRfXpefa0vtw8OdMw

### 相关奠基文献（笔记中引用）

- Bailey & López de Prado, *The Probability of Backtest Overfitting*, 2014.
- Harvey, Liu, Zhu, *…and the Cross-Section of Expected Returns*, RFS 2016.
- López de Prado, *Advances in Financial Machine Learning*, 2018（purged k-fold + embargo）.
- Gu, Kelly, Xiu, *Empirical Asset Pricing via Machine Learning*, RFS 2020.
- Kakushadze, Lauprete, Tulchinsky, *101 Formulaic Alphas*, WorldQuant 2016.
- Shumailov et al., *AI Models Collapse When Training on Their Own Outputs*, Nature 2024.
- Everitt et al., *Reward Tampering Problems and Solutions in Reinforcement Learning*, 2021.
- Zuckerman, *The Man Who Solved the Market*, 2019.
- Lowenstein, *When Genius Failed*, 2000.
- Khandani & Lo, *What Happened to the Quants in August 2007?*

---

## ⚠️ 数据真实性声明

- 所有论文数字来自 arXiv 摘要 / 论文 PDF / 微信解读原文，未编造。
- 微信文章均已存档到对应 `wechat.md`，未做改写。
- 08–11 四篇策略文章目前仅归档 PDF，关键数字与笔记标注"待读 PDF 补"，未预填。
- 数据进化类（R&D-Agent-Quant / TradingGroup / FactorEngine）已下载归档（12–14）；TradingGroup / FactorEngine 代码链接待核实。
- 标注"模拟"的数字均为论文作者口径，未实盘验证。
- 行业调查（02）中的机构业绩为公开媒体口径，不构成投资建议。
- 个人思考（`thoughts.md`）为本人观点，与论文无关。
