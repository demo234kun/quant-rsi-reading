# Microsoft RD-Agent 复现记录

- **仓库**：https://github.com/microsoft/RD-Agent
- **论文**：R&D-Agent-Quant（arXiv:2505.15155，NeurIPS 2025）
- **本地路径**：`reproduction/RD-Agent-main/`
- **复现日期**：2026-10-03

## 一、项目概况

- 微软开源的自动化研发框架，含量化（fin/qlib）、数据科学、通用 CoSTEER 等场景
- 测试套件用 pytest，marker `offline` 标记不依赖外部 API 的测试

## 二、实际执行结果

在现有环境（F:\Python\python.exe）补装离线依赖：psutil、fuzzywuzzy、python-Levenshtein、streamlit、randomname、litellm、humanize、genson、traitlets、nbformat、selenium、webdriver-manager。

对 9 个独立 offline 测试文件执行：

| 测试文件 | 结果 |
|---|---|
| test/log/server/test_security.py | pass |
| test/utils/test_archive_security.py | pass |
| test/utils/test_conda_security.py | pass |
| test/scenarios/data_science/test_secure_parsing.py | pass（11 项） |
| test/core/test_serialization.py | 1 失败（见下），其余 pass |
| test/utils/test_artifact_transport.py | pass |
| test/scenarios/data_science/test_debug_data.py | pass |
| test/rl/test_ui_data_loader.py | pass |
| test/utils/test_misc.py | pass |

**总计：129 passed, 1 failed**

## 三、唯一失败项分析（平台问题，非逻辑错误）

- 测试：`test/core/test_serialization.py::test_signed_pickle_round_trip`
- 断言：密钥文件权限位 `st_mode & 0o777 == 0o600`（Unix 权限）
- 实际：Windows 不支持 Unix 权限位，文件模式恒为 `0o666`（33206 & 511 = 438）
- **结论**：这是测试在 Windows 上的平台兼容性问题，签名 pickle 往返逻辑本身未失败。

## 四、未执行项及原因

| 项目 | 原因 |
|---|---|
| `test/utils/test_import.py`（虽标记 offline） | 它 import 整个 rdagent 包，需全部重依赖（pydantic-ai、prefect、mlflow、datasets、azure 等），未完整安装 |
| 整个 test 目录 | 非 offline 测试需 LLM API key / conda / docker / 外部网络 |
| 端到端量化 R&D | 需 LLM API key + qlib 数据下载 |

## 五、结论

- RD-Agent 测试套件真实可跑；离线安全/序列化/解析类测试 **129/130 通过**，唯一失败是 Windows 权限平台问题；
- 核心自动研发闭环依赖 LLM API 与完整重依赖，未在本次验证，**不声称端到端结果可复现**。
