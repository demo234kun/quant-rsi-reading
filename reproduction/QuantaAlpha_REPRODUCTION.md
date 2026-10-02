# QuantaAlpha 复现记录

- **仓库**：https://github.com/QuantaAlpha/QuantaAlpha
- **论文**：arXiv:2602.07085（*QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining*）
- **本地路径**：`reproduction/QuantaAlpha-main/`
- **复现日期**：2026-10-03

## 一、项目概况

- 完整的因子挖掘 + 模型进化框架，基于 **RD-Agent 0.8.0 + pyqlib**
- 核心依赖：pyqlib、rdagent（pinned 0.8.0）、openai、langchain-community、docker、azure
- 含前端（frontend-v2）、CLI、pipeline、进化算子（mutation/crossover/controller）

## 二、自带测试的真实情况

| 项目 | 状态 | 说明 |
|---|---|---|
| 正式 pytest 套件 | ❌ 无 | 仓库无测试目录、无测试函数；requirements/test.txt 仅声明 pytest |
| `quantaalpha/factors/coder/test.py` | ❌ 跑不起来 | 引用不存在的 `template_debug.jinjia2`（实际只有 `template.jinjia2`），是遗留调试脚本 |
| `app/utils/health_check.py` | ⚠️ 依赖 Docker | 需拉 hello-world 镜像并运行容器 |

## 三、离线复现结果（本次实际执行）

完整 pipeline 需 LLM API key + qlib 数据 + Docker，无 key 环境无法跑。
转而验证**不依赖 LLM/Docker 的核心逻辑——因子 DSL 解析器**（`expr_parser.py`，基于 pyparsing）。

**新增测试**：`quantaalpha/factors/coder/test_parser_offline.py`
**结果：13/13 通过**，覆盖：

- 算术运算（→ ADD / SUBTRACT / MULTIPLY / DIVIDE）
- 比较运算（→ GT / LT / GE / EQ）
- 条件表达式（→ WHERE）
- 一元负号预处理（数字参与时保留算术形式，是设计行为）
- 函数嵌套（RANK(DELTA(...))）
- 论文 test.py 中的真实复杂因子（ZSCORE + 条件 + TS_QUANTILE）

环境：F:\Python\python.exe，numpy 1.26.4 / pandas 2.3.3 / sklearn 1.4.2 / pyparsing（已安装）。

## 四、未复现项及原因

| 项目 | 原因 |
|---|---|
| 端到端因子挖掘 | 需 LLM API key（openai / DashScope） |
| qlib 回测 | 需安装 pyqlib 并下载数据，未执行 |
| Docker 远程回测 | 需 Docker 环境 |
| 因子计算（function_lib） | 解析层已验证；计算层依赖 qlib 数据结构，未单独验证 |

## 五、结论

- QuantaAlpha 开源了**完整代码**，但未提供可直接运行的测试套件；
- 核心因子 DSL 解析器在离线环境下真实可跑、逻辑正确（13/13）；
- 上层自动进化能力依赖 LLM 与数据，未在本次验证，**不声称其收益结果可复现**。
