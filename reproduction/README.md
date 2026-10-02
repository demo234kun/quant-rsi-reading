# 复现实验（Reproduction）

对库中/相关工作中**真正开源**的框架，在本地实际下载、安装、运行测试，记录真实结果。
完整框架代码与第三方代码不在本库重复存放（见各记录中的原仓库链接）。

## 复现成果一览

| 框架 | 类型 | 测试结果 | 复现记录 |
|---|---|---|---|
| **QuantaAlpha** | 因子进化 | 因子 DSL 解析器 13/13 通过；无正式 pytest 套件 | [记录](QuantaAlpha_REPRODUCTION.md) |
| **Microsoft RD-Agent** | 数据/研发（含 R&D-Agent-Quant） | 离线测试 **129 passed**，1 失败（Windows 权限位） | [记录](RD-Agent_REPRODUCTION.md) |
| **OpenEvolve** | 策略/程序进化（AlphaEvolve 开源实现） | **576 passed**，4 失败（Windows 平台），17 errors 需 LLM | [记录](OpenEvolve_REPRODUCTION.md) |
| Dream-RSI | 元层 | 仓库只有论文与图片，**代码未发布**，无法复现 | — |

## 说明

- 所有数字来自本次实际执行（环境：Windows，F:\Python\python.exe），未虚构；
- 标记为 `_with_llm` / `integration` 的测试需真实 LLM API key，未执行；
- 少量失败项经核对为 Windows 平台兼容性问题（Unix 路径/权限/进程语义），非算法逻辑错误；
- 上层自动进化/收益结果依赖 LLM 与数据，未在本次端到端验证，不声称其可复现。
