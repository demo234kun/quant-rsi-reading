# OpenEvolve 复现记录

- **仓库**：https://github.com/algorithmicsuperintelligence/OpenEvolve
- **定位**：AlphaEvolve 开源实现（进化式编码智能体，island + map-elites）
- **本地路径**：`reproduction/openevolve-main/`
- **复现日期**：2026-10-03

## 一、项目概况

- 依赖很轻：openai、pyyaml、numpy、tqdm、flask、dacite
- 测试套件庞大（约 65 个测试文件），覆盖数据库、岛屿（island）、种群策略、map-elites、迁移、
  检查点、并行、提示采样等内部逻辑

## 二、实际执行结果

环境：F:\Python\python.exe（补装 dacite、flask、pyyaml、tqdm），对整个 tests 目录执行：

**576 passed，4 failed，17 errors（另含 65 个 subtests 通过）**

## 三、4 个失败项分析（全部为 Windows 平台兼容性，非逻辑错误）

| 测试 | 失败原因 |
|---|---|
| test_template_dir_resolution | 测试假设绝对路径为 Unix 形式 `/absolute/path`，Windows 下被转成 `C:\absolute\path`（路径分隔符差异） |
| test_api_key_from_env | Windows 临时文件占用 PermissionError WinError 32（文件锁差异） |
| test_reasoning_effort_config | 同类 yaml 临时文件问题 |
| test_process_parallel | Windows 进程终止后不立即抛 ProcessLookupError（进程模型差异） |

## 四、17 个 errors 分析（全部为 integration / with_llm）

- 全部位于 tests/integration/ 下，名称含 `_with_llm` / `real_integration` / `full_evolution_loop`
- 需要真实 LLM API key 与网络调用，无 key 环境无法运行，属于预期跳过

## 五、结论

- OpenEvolve 内部进化逻辑测试真实可跑，**576 项通过**；
- 4 个失败是 Windows 平台兼容性问题，非算法逻辑错误；
- 17 个集成测试需真实 LLM API，未验证，**不声称端到端进化结果可复现**。
