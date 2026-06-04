# SCSP_v1 前端网页与仿真引擎后端可运行性验证

## Goal Description

对 SCSP_v1 项目（`/share/guolidong-nfs/SeeSpace/SCSP_v1`）进行端到端可运行性验证，确保前端仿真网页可正常加载和交互，后端仿真引擎（含 ASTRA-sim 桥接）可正常执行单点仿真、带宽扫描和实验管理全流程。

---

## Acceptance Criteria

### AC-1: 前端网页服务可正常启动与访问
- **Positive Tests**：
  - 执行 `python3 run_web.py` 后，Web 服务在 `0.0.0.0:8000` 正常启动，无异常报错；
  - 浏览器或 curl 访问 `http://127.0.0.1:8000/` 成功返回 `web/index.html` 内容（HTTP 200）；
  - 页面静态资源（CSS/JS，内嵌在 HTML 中）正常渲染，无 404；
  - `/api/health` 返回 `{"status":"ok"}`（HTTP 200）。
- **Negative Tests**：
  - Web 服务启动时抛出 ImportError 或端口冲突异常；
  - 访问根路径返回 404 或 500；
  - 健康检查端点返回非 200 状态码。

### AC-2: 后端仿真引擎单次仿真可正常运行
- **Positive Tests**：
  - 通过命令行 `python3 run_scsp.py --config <config> --output-prefix <dir>` 执行单点仿真，exit code 为 0；
  - 使用 `model_name: "Qwen2.5-VL-3B"`、`link_bandwidth_gbps: 100` 等有效配置，仿真结果 JSON 中包含 `metrics.total_latency_s > 0` 和 `metrics.effective_compute_pflops > 0`；
  - 通过 API `POST /api/simulations/single` 发起相同配置的单点仿真，返回 JSON 与命令行结果一致（关键指标 `total_latency_s` 误差 < 1%）。
- **Negative Tests**：
  - 仿真命令 exit code 非 0 或抛出未捕获异常；
  - 返回结果中 `total_latency_s` 为 0、null 或负数；
  - API 返回 HTTP 500 或超时（>30s）。

### AC-3: 后端仿真引擎带宽扫描可正常运行
- **Positive Tests**：
  - 命令行使用 `link_bandwidth_gbps: [10, 50, 100]` 执行扫描，exit code 为 0；
  - 返回结果包含 `rows` 列表（长度等于带宽列表长度），每条记录含 `link_bandwidth_gbps` 和 `total_latency_s`；
  - 结果包含 `knee_bandwidth_gbps` 和 `knee_reason`；
  - 通过 API `POST /api/simulations/sweep` 发起扫描，返回结构与命令行一致。
- **Negative Tests**：
  - 扫描命令 exit code 非 0；
  - `rows` 为空或长度与输入带宽列表不符；
  - 所有 `total_latency_s` 为 0 或相同值（无变化）。

### AC-4: 实验管理全流程可正常运行
- **Positive Tests**：
  - API `POST /api/experiments/run` 使用 `template_name: "single_point"` 成功创建实验，返回记录含 `experiment_id` 和 `status: "success"`；
  - API `GET /api/experiments` 返回实验列表，count >= 1；
  - API `GET /api/experiments/{experiment_id}` 返回单条实验详情，字段完整；
  - API `POST /api/experiments/reproduce/{experiment_id}` 成功重现实验，返回新 `experiment_id` 和 `reproduced_experiment_id`；
  - 实验记录持久化到 `experiments/records.jsonl`，文件存在且内容合法。
- **Negative Tests**：
  - 实验创建返回 HTTP 500 或 `status: "error"`；
  - 实验列表为空（在已创建实验后）；
  - 使用有效 `experiment_id` 查询详情返回 404；
  - 重现实验返回 404 或 500。

### AC-5: 前后端联动与前端交互功能可运行
- **Positive Tests**：
  - 前端页面加载后，页面中的"单点仿真"按钮/表单可触发对 `/api/simulations/single` 的调用并获得非错误响应；
  - 前端页面中的"带宽扫描"按钮/表单可触发对 `/api/simulations/sweep` 的调用并获得非错误响应；
  - 前端页面中的"实验管理"区域可展示实验列表（调用 `/api/experiments`）；
  - 前端页面中的"运行实验"按钮可触发对 `/api/experiments/run` 的调用；
  - 上述前端调用的响应时间在 60 秒内（含 ASTRA-sim 执行时间）；
  - （可选）若服务器环境支持无头浏览器（如 playwright/puppeteer/selenium），通过无头浏览器加载 `http://127.0.0.1:8000/`，验证页面 DOM 渲染正常且按钮可点击触发对应 API 调用；若环境不支持，则降级为通过分析 `index.html` 中的 JS 调用逻辑并用 requests 模拟验证。
- **Negative Tests**：
  - 前端按钮点击后无任何网络请求发出；
  - 前端收到后端 500 错误且页面无错误提示；
  - 前端页面因 JS 报错导致按钮无法点击。

### AC-6: 现有测试全部通过（无回归）
- **Positive Tests**：
  - `python3 -m py_compile scsp/*.py` 无语法错误；
  - `uv run --with pytest --with requests python -m pytest tests/ -v` 全部通过；
  - 已删除的死测试文件（test_communication.py 等）不再存在于 tests/ 目录。
- **Negative Tests**：
  - py_compile 报错；
  - 任何有效测试失败；
  - 测试 import 时抛出 ModuleNotFoundError。

---

## Implementation Notes

- 代码中禁止出现 AC-、Milestone、Step、Phase 等 plan 标记。
- 若 ASTRA-sim 二进制（`AstraSim_Analytical_Congestion_Aware`）缺失，记录阻塞原因并标记相关 AC 为 BLOCKED，继续验证不依赖它的部分（如前端服务启动、健康检查）。
- 前端交互验证首选无头浏览器（若环境支持）；否则通过 API 测试脚本模拟（检查 index.html 中的 JS 调用逻辑并用 requests 验证）。
- 所有验证产生的运行时输出（`experiments/runs/`、`outputs/`、`log/`）不得提交到 git，应确认 `.gitignore` 已覆盖。
- **测试验证完成后，必须清理本轮临时产生的测试文件**（如临时 JSON 配置、临时输出目录、验证脚本生成的中间文件等），保持工作区干净。

---

## Path Boundaries

- **可接受的实现范围**：
  - 运行现有代码并验证其可运行性；
  - 编写验证脚本和测试用例；
  - 修复验证过程中发现的阻塞性 bug（仅最小修改以恢复可运行性）；
  - 更新 `.gitignore` 以覆盖新增的运行时输出目录；
  - 环境支持时引入无头浏览器做前端自动化验证。
- **不可接受的方向**：
  - 重写前端页面或后端 API 结构；
  - 修改 ASTRA-sim C++ 引擎源码或重新编译；
  - 修改 `configs/model_registry.json` 中的模型定义；
  - 重构 `engine.py` 或 `astra_sim_bridge.py` 的核心逻辑。
