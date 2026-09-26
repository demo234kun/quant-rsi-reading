# Quant Papers · 量化研究精读库

> 一个个人收藏库：收集"递归自我改进（RSI）× 量化交易"方向的精致文章。
> 每篇含：论文全文 PDF · 微信解读原文存档 · 个人解读笔记 · 个人思考。
> 创建：2026-09-27

---

## 🧭 这个库在看什么

主线只有一条：**当 AI 开始自动做量化研究，它怎么不骗自己？**

五篇文章构成一个递进的逻辑链：

```
05_RSI_ThreeReins  ── 总框架：三根缰绳（裁判 / 燃料 / 传动 τ）
        │
        ├── 01_AQuA              ── 缰绳一最严样本：评估器焊死，密封沙箱（学术）
        ├── 03_Astar             ── 缰绳一工业样本：环内学习型裁判 + 外圈真实 A/B（生产）
        ├── 04_Dream-RSI         ── 缰绳三 τ>1 样本：元层做梦，不重训就继承（研究）
        │
        └── 02_AutoResearch_Industry ── 产业落地：桥水/Man/Citadel/幻方已经在花钱买
```

---

## 📚 文章索引表

| # | 文章 | 作者 / 来源 | 一句话概括 | 关键词 | 对应论文 | 个人思考 |
|---|------|------------|-----------|--------|----------|----------|
| 01 | [AQuA：递归自我改进的量化研究 Agent](papers/01_AQuA/notes.md) | Jiacheng Guo 等（Princeton / Ant / Stanford） | 两个互不连通的量化研究系统（挖因子 + 调模型），把打分的尺子焊死在 agent 够不到的地方 | RSI · 密封沙箱 · operatorization · 双指标纪律 · embargo · 因子挖掘 · 时序模型 | [arXiv:2608.12841](https://arxiv.org/abs/2608.12841) | [思考](papers/01_AQuA/thoughts.md) |
| 02 | [AutoResearch 行业深度调查](papers/02_AutoResearch_Industry/notes.md) | 公众号深度调查（汇编公开来源） | 从 Jane Street 150 亿美元七月说起，把 AI 自动量化追到桥水/Man/Citadel/幻方的真实部署与事故账单 | harness · 四代搜索引擎 · 评估工程学 · 记忆 · 事故史 · 桥水 AIA · AlphaGPT · 幻方/DeepSeek | 无单篇论文（汇编） | [思考](papers/02_AutoResearch_Industry/thoughts.md) |
| 03 | [Astar：8B 模型在生产环境跑 RSI](papers/03_Astar/notes.md) | 阿里 × 浙江大学 | 一个 8B 专用模型只会一件事——提出 AI 系统下一步演化方向；Lazada 广告召回无人值守 20 轮，GMV +4.86% | RSI · 工业闭环 · pairwise 数据工程 · 奖励模型 · GRPO · 增量校准 · 真实 A/B · Lazada | [arXiv:2608.27287](https://arxiv.org/abs/2608.27287) | [思考](papers/03_Astar/thoughts.md) |
| 04 | [Dream-RSI：在历史发现树上做梦](papers/04_Dream-RSI/notes.md) | Google 系团队 | 不重训模型，让"找知识的方法"在历史发现树上做梦进化；元层自改进，执行层一行不改 | RSI · 元层探索 · 发现树回放 · 反事实 · PIT 加权 · Lasso · τ>1 | [arXiv:2609.14858](https://arxiv.org/abs/2609.14858) ｜ [代码](https://github.com/zhengkid/Dream-RSI) | [思考](papers/04_Dream-RSI/thoughts.md) |
| 05 | [RSI 三根缰绳：全局框架](papers/05_RSI_ThreeReins/notes.md) | 公众号综述（自建框架） | 把整个 RSI 领域压成最小回路 + 三根缰绳：裁判在哪环内、燃料从哪来、改进多少传回改进者 | RSI 框架 · 裁判拓扑 · 模型坍缩 · 传动系数 τ · 六十年八站 · 四家族 | 综述坐标 [arXiv:2607.07663](https://arxiv.org/abs/2607.07663) | [思考](papers/05_RSI_ThreeReins/thoughts.md) |

---

## 🗂 目录结构

```
quant_library/
├── README.md                          ← 你在这里
└── papers/
    ├── 01_AQuA/
    │   ├── paper.pdf                  ← arXiv 全文
    │   ├── wechat.md                   ← 微信解读原文存档
    │   ├── notes.md                    ← 个人解读笔记
    │   └── thoughts.md                 ← 个人思考
    ├── 02_AutoResearch_Industry/
    │   ├── wechat.md
    │   ├── notes.md
    │   └── thoughts.md
    ├── 03_Astar/
    │   ├── paper.pdf
    │   ├── wechat.md
    │   ├── notes.md
    │   └── thoughts.md
    ├── 04_Dream-RSI/
    │   ├── paper.pdf
    │   ├── wechat.md
    │   ├── notes.md
    │   └── thoughts.md
    └── 05_RSI_ThreeReins/
        ├── wechat.md
        ├── notes.md
        └── thoughts.md
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

---

## 🛣 建议阅读路线

- **第一次读**：05（框架）→ 01（最严样本）→ 03（工业样本）
- **做量化关心落地**：01 → 03 → 02
- **关心方法论/不做量化**：05 → 04 → 03
- **想看行业八卦与事故**：02

---

## ⚠️ 数据真实性声明

- 所有论文数字来自 arXiv 摘要 / 论文 PDF / 微信解读原文，未编造。
- 微信文章均已存档到对应 `wechat.md`，未做改写。
- 标注"模拟"的数字均为论文作者口径，未实盘验证。
- 行业调查（02）中的机构业绩为公开媒体口径，不构成投资建议。
- 个人思考（`thoughts.md`）为本人观点，与论文无关。
