# RegimeSeal

> Regime-Aware Recursive Self-Improvement in a Sealed Factor-Discovery Sandbox
> 个人研究项目 · Phase 1：密封沙箱跑通（不接 LLM）

## 设计原则

1. **密封优先**：算子表数学上保证因果，AI 无权改数据切分/标签/评估器
2. **Regime 感知**：per-regime IC 向量替代全历史 IC
3. **端到端可跑**：合成数据先跑通管线，真实数据留接口

## 目录

```
project/
├── README.md
├── configs/           # 数据切分、算子表、regime 配置
├── src/
│   ├── data/         # 数据加载（合成/真实接口）
│   ├── regime/       # regime 聚类与标注
│   ├── dsl/          # 密封算子表
│   ├── evaluator/     # 密封评估沙箱
│   ├── memory/        # 发现树记忆
│   └── controller/   # 预算感知元策略
├── scripts/          # 端到端运行脚本
├── tests/            # 算子因果性单测
└── data/             # 本地数据缓存
```

## Phase 1 目标

- [x] DSL 算子表 + 因果性单测
- [x] 合成数据生成
- [x] Regime 聚类
- [x] 密封评估器（per-regime IC）
- [x] 发现树记忆（YAML 结构化）
- [ ] 端到端脚本：手动提案 → 评估 → 入树
- [ ] 真实 A股数据接口（akshare）
