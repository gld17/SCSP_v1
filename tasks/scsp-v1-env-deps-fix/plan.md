# SCSP_v1 环境依赖修复与端口占用排查

## Goal Description

修复 SCSP_v1 项目运行环境中的三项问题：安装缺失的 fastapi 依赖以支持 test_web_api.py 通过；安装 matplotlib 以支持 sweep 扫描结果的可视化曲线生成；排查并解决 `python run_web.py` 启动时的端口占用报错。

---

## Acceptance Criteria

### AC-1: fastapi 依赖安装完成，test_web_api.py 测试通过
- **Positive Tests**：
  - `python3 -c "from fastapi.testclient import TestClient"` 成功执行，无 ModuleNotFoundError；
  - `uv run --with pytest python -m pytest tests/test_web_api.py -v` 执行结果为 PASSED（非 SKIPPED）；
  - TestClient 能够成功创建并发起对 `/api/health` 的请求，返回 `{"status":"ok"}`。
- **Negative Tests**：
  - 导入 TestClient 时抛出 ModuleNotFoundError；
  - test_web_api.py 仍被标记为 SKIPPED；
  - 测试运行时抛出 ImportError 或 AttributeError。

### AC-2: matplotlib 依赖安装完成，sweep 扫描可生成图表
- **Positive Tests**：
  - `python3 -c "import matplotlib"` 成功执行，无 ModuleNotFoundError；
  - `python3 run_scsp.py --config <含带宽列表的配置> --output-prefix <dir>` 执行后，`plot_file` 字段存在且指向一个已生成的图片文件；
  - 生成的图片文件格式为 PNG，大小 > 0 bytes。
- **Negative Tests**：
  - 导入 matplotlib 时抛出 ModuleNotFoundError；
  - sweep 结果中仍包含 `plot_error: No module named 'matplotlib'`；
  - plot 文件生成失败但无任何错误提示。

### AC-3: run_web.py 支持自定义端口，端口占用问题有明确解决方案
- **Positive Tests**：
  - `python3 run_web.py --help` 显示支持 `--port` 参数（或等效方式）；
  - 当端口 8000 被占用时，用户可通过指定其他端口（如 `python3 run_web.py --port 8001`）成功启动服务；
  - 服务启动后 `/api/health` 在新端口上返回正常响应；
  - 提供清晰的说明：如何检查已有服务进程、如何停止已有进程、如何在不同端口启动。
- **Negative Tests**：
  - 端口被占用时仍强制绑定 8000 导致启动失败；
  - `--port` 参数未生效或参数解析异常；
  - 用户无法获知已有服务进程的存在。

### AC-4: 现有测试全部通过（无回归）
- **Positive Tests**：
  - `python3 -m py_compile scsp/*.py` 无语法错误；
  - `uv run --with pytest python -m pytest tests/test_astra_integration.py tests/test_experiment.py -v` 全部通过；
  - 新安装依赖后，原有代码逻辑未被破坏。
- **Negative Tests**：
  - 安装新依赖后引入版本冲突导致现有测试失败；
  - py_compile 报错；
  - 任何有效测试失败。

### AC-5: 依赖变更可追溯，不污染全局环境
- **Positive Tests**：
  - 所有新依赖安装到项目本地环境（`.venv/`）或通过 `uv` 的 `--with` 参数临时安装，不修改系统 Python 环境；
  - 如有新增的 requirements 或依赖声明文件，已记录到项目目录中（如 `requirements.txt` 或 `pyproject.toml`）；
  - `git status` 确认无意外文件被修改或提交。
- **Negative Tests**：
  - 使用 `sudo pip install` 或类似方式修改系统 Python 环境；
  - 新依赖版本与现有代码不兼容导致运行时错误；
  - 依赖变更未记录，后续环境重建时遗漏。

---

## Implementation Notes

- 代码中禁止出现 AC-、Milestone、Step、Phase 等 plan 标记。
- 依赖安装优先使用 `uv`（项目已有 `.venv`），避免污染系统环境。
- `run_web.py` 的端口参数修改属于最小改动，不引入 argparse 以外的复杂逻辑。
- 所有变更需确认不影响 ASTRA-sim 桥接和现有测试流程。
- 安装依赖产生的缓存（pip cache、uv cache）不提交到 git。

---

## Path Boundaries

- **可接受的实现范围**：
  - 安装 fastapi（含 testclient）和 matplotlib 到项目本地环境；
  - 修改 `run_web.py` 支持 `--port` 命令行参数；
  - 补充/更新依赖声明文件（如 requirements.txt）。
- **不可接受的方向**：
  - 修改 Web API 路由或业务逻辑；
  - 修改 ASTRA-sim C++ 引擎源码或重新编译；
  - 修改 `engine.py` 或 `astra_sim_bridge.py` 的核心逻辑；
  - 重写前端页面。
