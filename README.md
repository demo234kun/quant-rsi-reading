# Quant Papers · 量化研究精读库

> 创建：2026-09-27 ｜ 更新：2026-10-03



## 📚 文章索引

### 🥇 数据进化（Data Evolution）

> ⚠️ **当前没有专门论文**。数据/标签一旦开放给 agent 迭代，最易引入泄漏（AQuA 因此把数据焊死），且"新数据是否更好"缺外部判据。这是明确的研究空白。

候选待补（已检索，未归档）：

| 文章 | 定位 | 链接 |
|---|---|---|
| R&D-Agent-Quant（微软，NeurIPS 2025） | 首个数据中心化多智能体，因子-模型联合优化，成本 <$10、ARR 约 2× | [arXiv:2505.15155](https://arxiv.org/abs/2505.15155) |
| TradingGroup | 含自动数据合成与标注 pipeline + 预测/风格/决策三类 agent | [arXiv:2508.17565](https://arxiv.org/abs/2508.17565) |
| FactorEngine | Bootstrapping（知识注入建池）→ Evolution → Integration | [arXiv:2603.16365](https://arxiv.org/abs/2603.16365) |

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
    ├── data_evolution/                ← （待补，当前空白）
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

### 相关奠基文献

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


