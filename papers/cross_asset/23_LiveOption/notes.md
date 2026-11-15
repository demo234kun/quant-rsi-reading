# LiveOption：LLM Agent 的结构化期权交易评测

## 元信息

| 项 | 内容 |
|---|---|
| 论文来源 | arXiv:2609.33470v2 [cs.AI]（交叉 q-fin.CP）；v1 2026-09-27，v2 2026-10-25 |
| 论文题目 | LiveOption: Evaluating LLM Agents in Structured Option Trading with Nonlinear Payoffs |
| 作者 | Haochen Luo, Yifan Li, Binh Minh An, Xiaolong Luo, Zhengzhao Lai, Yuan Zhang, Chen Liu |
| 会议 | NeurIPS 2026（作者自述，arXiv 页面未标注） |
| 项目页 | https://liveoption.github.io/ |
| 链接 | HTML 全文 https://arxiv.org/html/2609.33470v2 ｜ PDF 本地 `paper.pdf` |

## 摘要级概览

股票方向性预测的评测已经很多，但衍生品市场的结构完全不同：收益非线性（Gamma/Theta/Vega 各自定价）、多腿组合要拼结构、执行受资金与保证金约束。LiveOption 把期权交易定义成"结构化序贯决策"，给出可复现环境 + 标准交互协议，做三套任务：

1. **Portfolio Overlay**：股票底仓不动，靠期权改变收益分布（收益增强：covered call / 现金担保 put；下行保护：long put / bear put spread）。
2. **Earnings Bet**：财报事件前后做短期方向与波动交易（T-2、T-1 建仓，T 至 T+2 滚动调整）。
3. **0DTE Intraday**：当日到期期权的高频决策，管急速时间衰减与 Gamma 风险。

评测分两层：结果层（组合层 AR/SR/MDD + 主动收益/IR；事件层 Win Rate、PnL%、payoff ratio、profit factor、no-trade rate，带 10,000 次 bootstrap 区间与配对符号翻转检验 + Holm 校正），行为层（策略构成、方向性 vs 结构性推理、仓位与杠杆、PnL 按希腊字母归因）。

主要结论：**当前 LLM agent 在多数期权场景拿不到有竞争力的收益**，而且"均值好看"经常是少数尾部场次撑起来的——这正是"回测好、实盘差"的期权版样本。

## 待精读清单

- [ ] §2 环境与交互协议：observation space、action space、资金/保证金约束怎么形式化
- [ ] §2.3 / 附录 G：Analysis Agent（AVSR 波动汇总 / QOCR 按到期与货币性分组）与 Execution Agent 的分工
- [ ] §3.2 Table 1–2：8 个模型 × 3 场景的完整结果
- [ ] §3.3.1 货币性与期限分布：为什么 tenors 是"模型属性"而非共性偏差
- [ ] §3.3.3 尾部风险：为什么均值是错的总结统计量
- [ ] §3.4 风险控制干预（intervention）实验怎么做
- [ ] 附录 C.6：PnL 的 Delta/Gamma/Theta/Vega 归因方法
- [ ] 附录 F.1：统计口径（block bootstrap、sign-flip、Holm）
