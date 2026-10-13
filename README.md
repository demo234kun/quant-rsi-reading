# Quant Papers · 量化研究精读库


## 📚 文章索引

### 🥇 数据进化（Data Evolution）

> 数据/标签一旦开放给 agent 迭代，最易引入泄漏（AQuA 因此把数据焊死），且"新数据是否更好"缺外部判据。下列三篇是这一方向目前找到的真实工作（2025–2026）。

| 文章 | 结构阅读 | 问题阅读 | 微信原文 | 作者来源 | 概括 | 个人笔记 |
|------|---------|---------|----------|----------|------|----------|
| [R&D-Agent-Quant](papers/data_evolution/12_RD-Agent-Quant/notes.md) | [📖](papers/data_evolution/12_RD-Agent-Quant/deep_reading.md) | [❓](papers/data_evolution/12_RD-Agent-Quant/questions.md) | — | Yuante Li 等（Microsoft） | 首个 data-centric 多智能体，因子-模型联合优化；Research/Development 闭环 + 多臂老虎机调度，ARR 最高约 2×、因子少 70% | [✏️](papers/data_evolution/12_RD-Agent-Quant/thoughts.md) |
| [TradingGroup](papers/data_evolution/13_TradingGroup/notes.md) | [📖](papers/data_evolution/13_TradingGroup/deep_reading.md) | [❓](papers/data_evolution/13_TradingGroup/questions.md) | — | Feng Tian, Flora D. Salim, Hao Xue | 多智能体交易系统，自我反思 + 端到端数据合成/标注管线，用交易活动数据反哺后训练；含动态止损/止盈 | [✏️](papers/data_evolution/13_TradingGroup/thoughts.md) |
| [FactorEngine](papers/data_evolution/14_FactorEngine/notes.md) | [📖](papers/data_evolution/14_FactorEngine/deep_reading.md) | [❓](papers/data_evolution/14_FactorEngine/questions.md) | — | Qinhong Lin, Ruitao Feng 等 | 程序级因子挖掘，因子=图灵完备代码；知识注入把研报转为可执行因子，经验知识库支持从失败学习 | [✏️](papers/data_evolution/14_FactorEngine/thoughts.md) |

---

### 🔢 因子进化（Factor Evolution）

| 文章 | 结构阅读 | 问题阅读 | 微信原文 | 作者来源 | 概括 | 个人笔记 |
|------|---------|---------|----------|----------|------|----------|
| [AQuA：递归自我改进的量化研究 Agent](papers/factor_evolution/01_AQuA/notes.md) | [📖](papers/factor_evolution/01_AQuA/deep_reading.md) | [❓](papers/factor_evolution/01_AQuA/questions.md) | [🔗](https://mp.weixin.qq.com/s/MEgyuiGTxyOlxVJ2EnVBzQ) | Jiacheng Guo 等（Princeton / Ant / Stanford） | 两个互不连通的量化研究系统（挖因子 + 调模型），把打分的尺子焊死在 agent 够不到的地方 | [✏️](papers/factor_evolution/01_AQuA/thoughts.md) |
| [Astar：8B 模型在生产环境跑 RSI](papers/factor_evolution/03_Astar/notes.md) | [📖](papers/factor_evolution/03_Astar/deep_reading.md) | [❓](papers/factor_evolution/03_Astar/questions.md) | [🔗](https://mp.weixin.qq.com/s/Eb6vKO6fvefasBvc-JJ9dQ) | 阿里 × 浙江大学 | 一个 8B 专用模型只会一件事——提出 AI 系统下一步演化方向；Lazada 广告召回无人值守 20 轮，GMV +4.86% | [✏️](papers/factor_evolution/03_Astar/thoughts.md) |
| [AutoScientist-Quant：把量化研究当预算搜索](papers/factor_evolution/06_AutoScientist-Quant/notes.md) | [📖](papers/factor_evolution/06_AutoScientist-Quant/deep_reading.md) | [❓](papers/factor_evolution/06_AutoScientist-Quant/questions.md) | — | Zongqian Li 等（含 Google DeepMind 背景） | 和 AQuA 同期对手；单一 controller 根据剩余预算统一调度从假设到 deployable strategy 的全流程 | [✏️](papers/factor_evolution/06_AutoScientist-Quant/thoughts.md) |
| [QuantEvolver：把反馈从 prompt 搬进权重](papers/factor_evolution/07_QuantEvolver/notes.md) | [📖](papers/factor_evolution/07_QuantEvolver/deep_reading.md) | [❓](papers/factor_evolution/07_QuantEvolver/questions.md) | — | Lingzhe Zhang 等（Philip S. Yu 团队） | RFT 替代 prompt-loop；把可执行回测评估转成 Miner LLM 参数更新，Diversity-Complementarity Reward 抗趋同 | [✏️](papers/factor_evolution/07_QuantEvolver/thoughts.md) |
| [Beyond Prompting: Autonomous Factor Investing via Agentic AI](papers/factor_evolution/17_BeyondPrompting/notes.md) | [📖](papers/factor_evolution/17_BeyondPrompting/deep_reading.md) | [❓](papers/factor_evolution/17_BeyondPrompting/questions.md) | — | Allen Yikuan Huang, Zheqi Fan | 不依赖手动 prompt，把模型作为自驱动引擎内生生成可解释交易信号；严格样本外验证 + 经济逻辑要求防过拟合；美股多空组合 Sharpe 3.11、年化收益 59.53% | [✏️](papers/factor_evolution/17_BeyondPrompting/thoughts.md) |
| [XALPHA：记忆驱动的 AI 量化研究员](papers/factor_evolution/16_XALPHA/notes.md) | [📖](papers/factor_evolution/16_XALPHA/deep_reading.md) | [❓](papers/factor_evolution/16_XALPHA/questions.md) | [🔗](https://mp.weixin.qq.com/s/iwuaa75L3XTFSMGFV2nTUw) | Ziwei Li 等 | 多源研究记忆系统整合研报知识 + 历史发现反馈；Macro Brain 规划研究主题选 Archetype，Micro Brain 把假设转成可执行因子代码并做事前三方对齐 | [✏️](papers/factor_evolution/16_XALPHA/thoughts.md) |

---

### 📈 策略进化（Strategy Evolution）

| 文章 | 结构阅读 | 问题阅读 | 微信原文 | 作者来源 | 概括 | 个人笔记 |
|------|---------|---------|----------|----------|------|----------|
| [EvolveTrade：经验驱动的策略自进化](papers/strategy_evolution/08_EvolveTrade/notes.md) | [📖](papers/strategy_evolution/08_EvolveTrade/deep_reading.md) | [❓](papers/strategy_evolution/08_EvolveTrade/questions.md) | — | Sehee Kim, Yumin Choi, Minki Kang, Sung Ju Hwang（KAIST） | 工具使用型 LLM 交易 agent，每天从自身交易经验重写 policy（policy self-evolution，逐 refinement） | [✏️](papers/strategy_evolution/08_EvolveTrade/thoughts.md) |
| [SHARP：自进化、可审计的规则策略](papers/strategy_evolution/09_SHARP/notes.md) | [📖](papers/strategy_evolution/09_SHARP/deep_reading.md) | [❓](papers/strategy_evolution/09_SHARP/questions.md) | — | Xiwen Chen, Wenhui Zhu, Songzhu Zheng, Kashif Rasul（Morgan Stanley / ASU） | 神经符号框架，策略 = 人类可读条件-动作规则；归因 agent 定位失效规则，做原子化编辑 | [✏️](papers/strategy_evolution/09_SHARP/thoughts.md) |
| [AlgoEvolve：交易程序的元进化](papers/strategy_evolution/10_AlgoEvolve/notes.md) | [📖](papers/strategy_evolution/10_AlgoEvolve/deep_reading.md) | [❓](papers/strategy_evolution/10_AlgoEvolve/questions.md) | — | Dhruv Sharma, Gautam Shroff（IIIT Delhi） | LLM 进化框架，生成/评估/迭代可执行 Python 交易策略，涌现 regime-adaptive 规则自主切换 | [✏️](papers/strategy_evolution/10_AlgoEvolve/thoughts.md) |
| [Recursive Multi-Agent：递归组合策略](papers/strategy_evolution/11_RecursiveMultiAgent/notes.md) | [📖](papers/strategy_evolution/11_RecursiveMultiAgent/deep_reading.md) | [❓](papers/strategy_evolution/11_RecursiveMultiAgent/questions.md) | — | Jing Yang, Penghao Liang, Yichao Wu 等（Northeastern University） | 地缘不确定性下 4 专家 agent + Manager 迭代优化 portfolio；健康分递归加权、三触发熔断（回撤/GRS/波动）、约束均值-方差。论文用 RL 语汇并定义风险感知 reward（Eq.9，λ₁=0.8、λ₂=1.5），但**未给出梯度训练过程**（无 policy network / actor-critic / 参数更新），DQN 仅作对照 baseline；多智能体层在再平衡周期内不更新，作用是仲裁权重分歧 | [✏️](papers/strategy_evolution/11_RecursiveMultiAgent/thoughts.md) |
| [F²Agent：多模态金融交易智能体融合](papers/strategy_evolution/15_F2Agent/notes.md) | [📖](papers/strategy_evolution/15_F2Agent/deep_reading.md) | [❓](papers/strategy_evolution/15_F2Agent/questions.md) | — | Changshuo Liu, Yanzheng Jin, Shangfeng Cai 等（NUS） | 多模态智能体交易框架：分层专用 agent 提取模态信号 + 模态感知自适应融合 + 噪声鲁棒一致性正则化；跑赢 16 个基线，年化收益平均提升 20%+，GOOG 120.48%、TSLA 148.41% | [✏️](papers/strategy_evolution/15_F2Agent/thoughts.md) |

> 08–11、15 已有 PDF 与空白 md 骨架，内容待填充。

---

### 🗂 其他（综述 / 行业 / 方法论）

| 文章 | 结构阅读 | 问题阅读 | 微信原文 | 作者来源 | 概括 | 个人笔记 |
|------|---------|---------|----------|----------|------|----------|
| [AutoResearch 行业深度调查](papers/other/02_AutoResearch_Industry/notes.md) | [📖](papers/other/02_AutoResearch_Industry/deep_reading.md) | [❓](papers/other/02_AutoResearch_Industry/questions.md) | [🔗](https://mp.weixin.qq.com/s/z0B8QFnsfrPQ3y6JVhQv-A) | 公众号深度调查（汇编公开来源） | 从 Jane Street 150 亿美元七月说起，把 AI 自动量化追到桥水/Man/Citadel/幻方的真实部署与事故账单 | [✏️](papers/other/02_AutoResearch_Industry/thoughts.md) |
| [Dream-RSI：在历史发现树上做梦](papers/other/04_Dream-RSI/notes.md) | [📖](papers/other/04_Dream-RSI/deep_reading.md) | [❓](papers/other/04_Dream-RSI/questions.md) | [🔗](https://mp.weixin.qq.com/s/NwO-gQl96t_gumJhPs2kEA) | Google 系团队 | 不重训模型，让"找知识的方法"在历史发现树上做梦进化；元层自改进，执行层一行不改 | [✏️](papers/other/04_Dream-RSI/thoughts.md) |
| [RSI 三根缰绳：全局框架](papers/other/05_RSI_ThreeReins/notes.md) | [📖](papers/other/05_RSI_ThreeReins/deep_reading.md) | [❓](papers/other/05_RSI_ThreeReins/questions.md) | [🔗](https://mp.weixin.qq.com/s/wf1KOGRfXpefa0vtw8OdMw) | 公众号综述（自建框架） | 把整个 RSI 领域压成最小回路 + 三根缰绳：裁判在哪环内、燃料从哪来、改进多少传回改进者 | [✏️](papers/other/05_RSI_ThreeReins/thoughts.md) |
| [Darwin Gödel Machine：自我改进 agent 的开放式进化](papers/other/21_DarwinGodelMachine/notes.md) | [📖](papers/other/21_DarwinGodelMachine/deep_reading.md) | [❓](papers/other/21_DarwinGodelMachine/questions.md) | — | Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune（UBC / Sakana AI） | 迭代修改自身代码 + 编码基准实证验证；达尔文式进化 archive，从 archive 采样 agent 自修改生成新版本，有趣且有改进的保留为下一代父母。[代码](https://github.com/jennyzzt/dgm) ｜ [项目页](https://sakana.ai/dgm/) | [✏️](papers/other/21_DarwinGodelMachine/thoughts.md) |

---

### 🧠 专家知识库（Expert Knowledge Base）

> 把领域知识外化为 agent 可操作的结构化资产：memory、knowledge infrastructure、scaffolding、research memory。核心问题是"专家经验如何被拆解成 agent 能调用的模块"。

| 文章 | 结构阅读 | 问题阅读 | 微信原文 | 作者来源 | 概括 | 个人笔记 |
|------|---------|---------|----------|----------|------|----------|
| [KISS：科学仿真的知识基础设施](papers/expert_knowledge/18_KISS/notes.md) | [📖](papers/expert_knowledge/18_KISS/deep_reading.md) | [❓](papers/expert_knowledge/18_KISS/questions.md) | — | Ziwei Li, Liujun Zhu, Yuchen Liu 等 | 把专家经验外化为可验证建模算子 + 分阶段领域协议 + 诊断恢复机制；3000 次试验中带 KI 的 agent 端到端仿真成功率达 84%（无 KI <40%）；KDT 工具包自动生成 14 个地球科学领域 117 个模型的 KI。[代码](https://github.com/lzwei196/knowledge_dissection_toolkit) ｜ [平台](https://app.hydrocraft.ai) | [✏️](papers/expert_knowledge/18_KISS/thoughts.md) |
| [微信文章](papers/expert_knowledge/19_WeChat_MM/notes.md) | [📖](papers/expert_knowledge/19_WeChat_MM/deep_reading.md) | [❓](papers/expert_knowledge/19_WeChat_MM/questions.md) | [🔗](https://mp.weixin.qq.com/s/_EB4CsN1uCNpcvbzKzz_lA) | 微信公众号 | 待阅读后补充概括 | [✏️](papers/expert_knowledge/19_WeChat_MM/thoughts.md) |
| [微信文章](papers/expert_knowledge/20_WeChat_IuK/notes.md) | [📖](papers/expert_knowledge/20_WeChat_IuK/deep_reading.md) | [❓](papers/expert_knowledge/20_WeChat_IuK/questions.md) | [🔗](https://mp.weixin.qq.com/s/IuK1-0JGr43E9q1Eyf-PUQ) | 微信公众号 | 待阅读后补充概括 | [✏️](papers/expert_knowledge/20_WeChat_IuK/thoughts.md) |

---

## 🗂 目录结构

```
quant_library/
├── README.md                          ← 你在这里
├── DESIGN.md / PAPER_PROPOSAL.md / PAPER_DIRECTIONS.md / RESULTS.md
├── project/                           ← RegimeSeal 可运行研究管线
└── papers/
    ├── data_evolution/
    │   ├── 12_RD-Agent-Quant/ (paper.pdf, notes.md, questions.md, wechat.md, thoughts.md, deep_reading.md)
    │   ├── 13_TradingGroup/   (paper.pdf, notes.md, questions.md, wechat.md, thoughts.md, deep_reading.md)
    │   └── 14_FactorEngine/   (paper.pdf, notes.md, questions.md, wechat.md, thoughts.md, deep_reading.md)
    ├── factor_evolution/
    │   ├── 01_AQuA/        (paper.pdf, wechat.md, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 03_Astar/       (paper.pdf, wechat.md, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 06_AutoScientist-Quant/ (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 07_QuantEvolver/ (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 16_XALPHA/      (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   └── 17_BeyondPrompting/ (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    ├── strategy_evolution/
    │   ├── 08_EvolveTrade/          (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 09_SHARP/                (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 10_AlgoEvolve/           (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 11_RecursiveMultiAgent/  (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   └── 15_F2Agent/              (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    ├── expert_knowledge/
    │   ├── 18_KISS/        (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
    │   ├── 19_WeChat_MM/   (notes.md, questions.md, thoughts.md, deep_reading.md)
    │   └── 20_WeChat_IuK/  (notes.md, questions.md, thoughts.md, deep_reading.md)
    └── other/
        ├── 02_AutoResearch_Industry/ (wechat.md, notes.md, questions.md, thoughts.md, deep_reading.md)
        ├── 04_Dream-RSI/    (paper.pdf, wechat.md, notes.md, questions.md, thoughts.md, deep_reading.md)
        ├── 05_RSI_ThreeReins/ (wechat.md, notes.md, questions.md, thoughts.md, deep_reading.md)
        └── 21_DarwinGodelMachine/ (paper.pdf, notes.md, questions.md, thoughts.md, deep_reading.md)
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
14. **F²Agent**: Changshuo Liu, Yanzheng Jin, Shangfeng Cai, Peng Fang, Xiaokui Xiao, Beng Chin Ooi. *F²Agent: Financial Fusion of Agentic Intelligence for Multimodal Trading*. arXiv:2608.05668, 2026. https://arxiv.org/abs/2608.05668
15. **Beyond Prompting**: Allen Yikuan Huang, Zheqi Fan. *Beyond Prompting: An Autonomous Framework for Systematic Factor Investing via Agentic AI*. arXiv:2603.14288, 2026. https://arxiv.org/abs/2603.14288
16. **XALPHA**: *XALPHA: A Memory-Driven AI Quant Researcher for Hypothesis-to-Code Alpha Discovery*. arXiv:2607.08332, 2026. https://arxiv.org/abs/2607.08332
17. **KISS**: Ziwei Li, Liujun Zhu, Yuchen Liu, Yichen Zhao, Birk Li, Ruiqi Wu, Junliang Jin, Jianyun Zhang. *KISS: Knowledge Infrastructure for Scientific Simulation*. arXiv:2605.17856, 2026. https://arxiv.org/abs/2605.17856 ｜ 代码: https://github.com/lzwei196/knowledge_dissection_toolkit ｜ 平台: https://app.hydrocraft.ai
18. **Darwin Gödel Machine**: Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune. *Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents*. arXiv:2505.22954, 2025. https://arxiv.org/abs/2505.22954 ｜ 代码: https://github.com/jennyzzt/dgm ｜ 项目页: https://sakana.ai/dgm/
19. **MarkTechPost 对 AQuA 的报道**: https://www.marktechpost.com/2026/09/01/aqua-a-two-part-agentic-framework-for-autonomous-factor-discovery/

### 微信解读原文

1. AQuA 深度解读: https://mp.weixin.qq.com/s/MEgyuiGTxyOlxVJ2EnVBzQ
2. AutoResearch 行业深度调查: https://mp.weixin.qq.com/s/z0B8QFnsfrPQ3y6JVhQv-A
3. Astar 深读: https://mp.weixin.qq.com/s/Eb6vKO6fvefasBvc-JJ9dQ
4. Dream-RSI × 量化: https://mp.weixin.qq.com/s/NwO-gQl96t_gumJhPs2kEA
5. RSI 三根缰绳全景: https://mp.weixin.qq.com/s/wf1KOGRfXpefa0vtw8OdMw
6. XALPHA 解读: https://mp.weixin.qq.com/s/iwuaa75L3XTFSMGFV2nTUw
7. 微信文章: https://mp.weixin.qq.com/s/_EB4CsN1uCNpcvbzKzz_lA
8. 微信文章: https://mp.weixin.qq.com/s/IuK1-0JGr43E9q1Eyf-PUQ

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
