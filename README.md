# 金融 Agent 自进化精读库 · RSI Reading Library

> 22 篇论文，六个栏目。点文章标题直接进 arXiv HTML 全文；📄 是本地 notes.md，📖 结构阅读，❓ 问题阅读，🔗 微信解读，✏️ 个人笔记。

**导航**：[🛡 门槛控制](#-门槛控制--gating-control) ｜ [🔢 因子挖掘进化](#-因子挖掘进化--factor-mining-evolution) ｜ [📈 策略进化](#-策略进化--strategy-evolution) ｜ [♻️ 进化机制](#️-进化机制--evolution-mechanism) ｜ [🧠 记忆系统](#-记忆系统--memory-systems) ｜ [🌐 泛投资与财富管理](#-泛投资与财富管理--cross-asset--wealth-management)

---

## 🛡 门槛控制 · Gating Control

> 把"什么算成功"焊死在 agent 够不到的地方，防回测漂亮、实盘崩。

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [FinForesight：金融深度研究系统的诊断式回测基准](https://arxiv.org/html/2611.01621v1) [📄](papers/gating/22_FinForesight/notes.md) | [📖](papers/gating/22_FinForesight/deep_reading.md) | [❓](papers/gating/22_FinForesight/questions.md) | [🔗](https://mp.weixin.qq.com/s/QWcK390BgdsZghcRIM5JZA) | Fengyuan Liu, Mukai Li, Jieshun You 等（港大 / 港理工 / 剑桥 / 兰大 / GIM AI / 海豚科技） | A 股·美股·港股三市场、四类预测任务 + 两项能力诊断分开计分；harness 把检索证据锁在预测日可得范围，用预训练期 / 截断后 / 实时三种评测互校 | [✏️](papers/gating/22_FinForesight/thoughts.md) |
| [RSI 三根缰绳：全局框架](https://arxiv.org/html/2607.07663v2) [📄](papers/gating/05_RSI_ThreeReins/notes.md) | [📖](papers/gating/05_RSI_ThreeReins/deep_reading.md) | [❓](papers/gating/05_RSI_ThreeReins/questions.md) | [🔗](https://mp.weixin.qq.com/s/wf1KOGRfXpefa0vtw8OdMw) | 公众号综述（自建框架） | 把整个 RSI 领域压成最小回路 + 三根缰绳：裁判在哪环内、燃料从哪来、改进多少传回改进者 | [✏️](papers/gating/05_RSI_ThreeReins/thoughts.md) |

---

## 🔢 因子挖掘进化 · Factor Mining Evolution

> 假设 → 因子代码 → 回测反馈 → 再进化，这条链上谁迭代得更快。**本库重点板块。**

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [AQuA：递归自我改进的量化研究 Agent](https://arxiv.org/html/2608.12841v3) [📄](papers/factor_mining/01_AQuA/notes.md) | [📖](papers/factor_mining/01_AQuA/deep_reading.md) | [❓](papers/factor_mining/01_AQuA/questions.md) | [🔗](https://mp.weixin.qq.com/s/MEgyuiGTxyOlxVJ2EnVBzQ) | Jiacheng Guo 等（Princeton / Ant / Stanford） | 两个互不连通的量化研究系统（挖因子 + 调模型），把打分的尺子焊死在 agent 够不到的地方 | [✏️](papers/factor_mining/01_AQuA/thoughts.md) |
| [Astar：8B 模型在生产环境跑 RSI](https://arxiv.org/html/2608.27287v1) [📄](papers/factor_mining/03_Astar/notes.md) | [📖](papers/factor_mining/03_Astar/deep_reading.md) | [❓](papers/factor_mining/03_Astar/questions.md) | [🔗](https://mp.weixin.qq.com/s/Eb6vKO6fvefasBvc-JJ9dQ) | 阿里 × 浙江大学 | 一个 8B 专用模型只会一件事——提出 AI 系统下一步演化方向；Lazada 广告召回无人值守 20 轮，GMV +4.86% | [✏️](papers/factor_mining/03_Astar/thoughts.md) |
| [AutoScientist-Quant：把量化研究当预算搜索](https://arxiv.org/html/2608.28632v2) [📄](papers/factor_mining/06_AutoScientist-Quant/notes.md) | [📖](papers/factor_mining/06_AutoScientist-Quant/deep_reading.md) | [❓](papers/factor_mining/06_AutoScientist-Quant/questions.md) | — | Zongqian Li 等（含 Google DeepMind 背景） | 和 AQuA 同期对手；单一 controller 根据剩余预算统一调度从假设到 deployable strategy 的全流程 | [✏️](papers/factor_mining/06_AutoScientist-Quant/thoughts.md) |
| [QuantEvolver：把反馈从 prompt 搬进权重](https://arxiv.org/html/2605.15412v1) [📄](papers/factor_mining/07_QuantEvolver/notes.md) | [📖](papers/factor_mining/07_QuantEvolver/deep_reading.md) | [❓](papers/factor_mining/07_QuantEvolver/questions.md) | — | Lingzhe Zhang 等（Philip S. Yu 团队） | RFT 替代 prompt-loop；把可执行回测评估转成 Miner LLM 参数更新，Diversity-Complementarity Reward 抗趋同 | [✏️](papers/factor_mining/07_QuantEvolver/thoughts.md) |
| [R&D-Agent-Quant](https://arxiv.org/html/2505.15155v2) [📄](papers/factor_mining/12_RD-Agent-Quant/notes.md) | [📖](papers/factor_mining/12_RD-Agent-Quant/deep_reading.md) | [❓](papers/factor_mining/12_RD-Agent-Quant/questions.md) | — | Yuante Li 等（Microsoft） | 首个 data-centric 多智能体，因子-模型联合优化；Research/Development 闭环 + 多臂老虎机调度，ARR 最高约 2×、因子少 70% | [✏️](papers/factor_mining/12_RD-Agent-Quant/thoughts.md) |
| [FactorEngine](https://arxiv.org/html/2603.16365v3) [📄](papers/factor_mining/14_FactorEngine/notes.md) | [📖](papers/factor_mining/14_FactorEngine/deep_reading.md) | [❓](papers/factor_mining/14_FactorEngine/questions.md) | — | Qinhong Lin, Ruitao Feng 等 | 程序级因子挖掘，因子=图灵完备代码；知识注入把研报转为可执行因子，经验知识库支持从失败学习 | [✏️](papers/factor_mining/14_FactorEngine/thoughts.md) |
| [XALPHA：记忆驱动的 AI 量化研究员](https://arxiv.org/html/2607.08332v3) [📄](papers/factor_mining/16_XALPHA/notes.md) | [📖](papers/factor_mining/16_XALPHA/deep_reading.md) | [❓](papers/factor_mining/16_XALPHA/questions.md) | — | Ziwei Li 等 | 多源研究记忆系统整合研报知识 + 历史发现反馈；Macro Brain 规划研究主题选 Archetype，Micro Brain 把假设转成可执行因子代码并做事前三方对齐 | [✏️](papers/factor_mining/16_XALPHA/thoughts.md) |
| [Beyond Prompting: Autonomous Factor Investing via Agentic AI](https://arxiv.org/html/2603.14288v2) [📄](papers/factor_mining/17_BeyondPrompting/notes.md) | [📖](papers/factor_mining/17_BeyondPrompting/deep_reading.md) | [❓](papers/factor_mining/17_BeyondPrompting/questions.md) | — | Allen Yikuan Huang, Zheqi Fan | 不依赖手动 prompt，把模型作为自驱动引擎内生生成可解释交易信号；严格样本外验证 + 经济逻辑要求防过拟合；美股多空组合 Sharpe 3.11、年化收益 59.53% | [✏️](papers/factor_mining/17_BeyondPrompting/thoughts.md) |

---

## 📈 策略进化 · Strategy Evolution

> 交易策略、交易行为本身怎么自迭代。

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [EvolveTrade：经验驱动的策略自进化](https://arxiv.org/html/2609.17632v1) [📄](papers/strategy/08_EvolveTrade/notes.md) | [📖](papers/strategy/08_EvolveTrade/deep_reading.md) | [❓](papers/strategy/08_EvolveTrade/questions.md) | — | Sehee Kim, Yumin Choi, Minki Kang, Sung Ju Hwang（KAIST） | 工具使用型 LLM 交易 agent，每天从自身交易经验重写 policy（policy self-evolution，逐 refinement） | [✏️](papers/strategy/08_EvolveTrade/thoughts.md) |
| [SHARP：自进化、可审计的规则策略](https://arxiv.org/html/2605.06822v1) [📄](papers/strategy/09_SHARP/notes.md) | [📖](papers/strategy/09_SHARP/deep_reading.md) | [❓](papers/strategy/09_SHARP/questions.md) | — | Xiwen Chen, Wenhui Zhu, Songzhu Zheng, Kashif Rasul 等（Morgan Stanley / ASU / Columbia） | 神经符号框架，策略 = 人类可读条件-动作规则；归因 agent 定位失效规则，做原子化编辑 | [✏️](papers/strategy/09_SHARP/thoughts.md) |
| [AlgoEvolve：交易程序的元进化](https://arxiv.org/html/2606.26173v1) [📄](papers/strategy/10_AlgoEvolve/notes.md) | [📖](papers/strategy/10_AlgoEvolve/deep_reading.md) | [❓](papers/strategy/10_AlgoEvolve/questions.md) | — | Dhruv Sharma, Gautam Shroff（IIIT Delhi） | LLM 进化框架，生成/评估/迭代可执行 Python 交易策略，涌现 regime-adaptive 规则自主切换 | [✏️](papers/strategy/10_AlgoEvolve/thoughts.md) |
| [TradingGroup](https://arxiv.org/html/2508.17565v1) [📄](papers/strategy/13_TradingGroup/notes.md) | [📖](papers/strategy/13_TradingGroup/deep_reading.md) | [❓](papers/strategy/13_TradingGroup/questions.md) | — | Feng Tian, Flora D. Salim, Hao Xue | 多智能体交易系统，自我反思 + 端到端数据合成/标注管线，用交易活动数据反哺后训练；含动态止损/止盈 | [✏️](papers/strategy/13_TradingGroup/thoughts.md) |
| [F²Agent：多模态金融交易智能体融合](https://arxiv.org/html/2608.05668v1) [📄](papers/strategy/15_F2Agent/notes.md) | [📖](papers/strategy/15_F2Agent/deep_reading.md) | [❓](papers/strategy/15_F2Agent/questions.md) | — | Changshuo Liu, Yanzheng Jin, Shangfeng Cai 等（NUS） | 多模态智能体交易框架：分层专用 agent 提取模态信号 + 模态感知自适应融合 + 噪声鲁棒一致性正则化；跑赢 16 个基线，年化收益平均提升 20%+ | [✏️](papers/strategy/15_F2Agent/thoughts.md) |

---

## ♻️ 进化机制 · Evolution Mechanism

> 不碰具体业务，只研究"自我改进"这台机器本身怎么转。

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [Dream-RSI：在历史发现树上做梦](https://arxiv.org/html/2609.14858v2) [📄](papers/mechanism/04_Dream-RSI/notes.md) | [📖](papers/mechanism/04_Dream-RSI/deep_reading.md) | [❓](papers/mechanism/04_Dream-RSI/questions.md) | [🔗](https://mp.weixin.qq.com/s/NwO-gQl96t_gumJhPs2kEA) | Google 系团队 | 不重训模型，让"找知识的方法"在历史发现树上做梦进化；元层自改进，执行层一行不改 | [✏️](papers/mechanism/04_Dream-RSI/thoughts.md) |
| [Darwin Gödel Machine：自我改进 agent 的开放式进化](https://arxiv.org/html/2505.22954v3) [📄](papers/mechanism/21_DarwinGodelMachine/notes.md) | [📖](papers/mechanism/21_DarwinGodelMachine/deep_reading.md) | [❓](papers/mechanism/21_DarwinGodelMachine/questions.md) | — | Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune（UBC / Sakana AI） | 迭代修改自身代码 + 编码基准实证验证；达尔文式进化 archive，从 archive 采样 agent 自修改生成新版本，有趣且有改进的保留为下一代父母。[代码](https://github.com/jennyzzt/dgm) ｜ [项目页](https://sakana.ai/dgm/) | [✏️](papers/mechanism/21_DarwinGodelMachine/thoughts.md) |

---

## 🧠 记忆系统 · Memory Systems

> 专家经验怎么变成模型能调用、能更新、能忘的记忆。

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [KISS：科学仿真的知识基础设施](https://arxiv.org/html/2605.17856v1) [📄](papers/memory/18_KISS/notes.md) | [📖](papers/memory/18_KISS/deep_reading.md) | [❓](papers/memory/18_KISS/questions.md) | [🔗](https://mp.weixin.qq.com/s/iwuaa75L3XTFSMGFV2nTUw) | Ziwei Li, Liujun Zhu, Yuchen Liu 等 | 把专家经验外化为可验证建模算子 + 分阶段领域协议 + 诊断恢复机制；3000 次试验中带 KI 的 agent 端到端仿真成功率达 84%（无 KI <40%）；KDT 工具包自动生成 14 个地球科学领域 117 个模型的 KI。[代码](https://github.com/lzwei196/knowledge_dissection_toolkit) ｜ [平台](https://app.hydrocraft.ai) | [✏️](papers/memory/18_KISS/thoughts.md) |
| [MemTrial：记忆什么时候可信](https://arxiv.org/html/2610.11732v2) [📄](papers/memory/24_MemTrial/notes.md) | [📖](papers/memory/24_MemTrial/deep_reading.md) | [❓](papers/memory/24_MemTrial/questions.md) | — | Guanghao Wu, Zhuo Cai, Shoujin Wang | 用同一天的反事实设计实验（8 份草稿 + 班扎夫值）测出经验"改变了什么"，层级贝叶斯跨日池化，只在价值预测过未见日期时才信任，否则锚回 1/N；真实基准最多比 1/N 低 2.2%，而最强经验学习 agent 低 15–38% | [✏️](papers/memory/24_MemTrial/thoughts.md) |

---

## 🌐 泛投资与财富管理 · Cross-Asset & Wealth Management

> 不止单标的股票：组合、多资产、财富管理层的决策。

| 文章 | 结构阅读 | 问题阅读 | 微信解读 | 作者 | 一句话概括 | 笔记 |
|------|---------|---------|----------|------|-----------|------|
| [Recursive Multi-Agent：递归组合策略](https://arxiv.org/html/2605.25311v2) [📄](papers/cross_asset/11_RecursiveMultiAgent/notes.md) | [📖](papers/cross_asset/11_RecursiveMultiAgent/deep_reading.md) | [❓](papers/cross_asset/11_RecursiveMultiAgent/questions.md) | — | Jing Yang, Penghao Liang, Yichao Wu 等（Northeastern University） | 地缘不确定性下 4 专家 agent + Manager 迭代优化 portfolio；健康分递归加权、三触发熔断（回撤/GRS/波动）、约束均值-方差。论文用 RL 语汇定义风险感知 reward（Eq.9，λ₁=0.8、λ₂=1.5），但未给出梯度训练过程，DQN 仅作对照 baseline | [✏️](papers/cross_asset/11_RecursiveMultiAgent/thoughts.md) |
| [LiveOption：LLM Agent 的结构化期权交易评测](https://arxiv.org/html/2609.33470v2) [📄](papers/cross_asset/23_LiveOption/notes.md) | [📖](papers/cross_asset/23_LiveOption/deep_reading.md) | [❓](papers/cross_asset/23_LiveOption/questions.md) | — | Haochen Luo, Yifan Li, Binh Minh An 等 7 人（NeurIPS 2026） | 三套期权任务（组合 overlay / 财报事件 / 0DTE）+ 分层指标在真实执行与资金约束下评测；8 个模型对冲口径主动收益全负，0DTE 与财报多数场次亏损、中位数全负，均值为正靠少数尾部 | [✏️](papers/cross_asset/23_LiveOption/thoughts.md) |
| [SOTA：让 LLM 选策略而不是选合约](https://arxiv.org/html/2610.10407v1) [📄](papers/cross_asset/25_SOTA/notes.md) | [📖](papers/cross_asset/25_SOTA/deep_reading.md) | [❓](papers/cross_asset/25_SOTA/questions.md) | — | Yizhen Xie, Mengyang Liu（NeurIPS 2026 Agenthon Workshop） | 九类策略族 + 确定性解析器把"几千张合约"压成策略级决策，Qwen3.8-27B 走 SFT + GRPO；六个月样本外总收益 18.32%、Sharpe 1.60、MDD 8.96%，规则与监督基线全亏；RL 阶段保留新闻会把收益打到 −2.72% | [✏️](papers/cross_asset/25_SOTA/thoughts.md) |

---

**收录约定**

- 每篇一个目录，六件套：`paper.pdf`、`notes.md`、`deep_reading.md`、`questions.md`、`thoughts.md`、`wechat.md`（无对应材料则不建）。
- 编号 01–25 保持不重排（02、19、20 已删除），新论文顺延 26 起。
- 「文章」列直连 arXiv HTML 全文版，后面 📄 是本地 `notes.md`。
- 「微信解读」列只放已核验能打开的公众号原文；没有对应文章的填 `—`，不补占位链接。
