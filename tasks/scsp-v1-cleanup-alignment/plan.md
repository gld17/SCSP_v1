# SCSP_v1 参数对齐、前端验证与仓库清理

## Goal Description

对 SCSP_v1 项目（`/share/guolidong-nfs/SeeSpace/SCSP_v1`）进行三项迭代工作：
1. 与参考项目（`/share/guolidong-nfs/SeeSpace/SCSP`）核对并对齐仿真输入参数配置；
2. 验证前端仿真入口的可运行状态，以 Qwen2.5-VL-3B 为测试模型确保每个仿真按钮和实验管理功能正常；
3. 清理死逻辑、冗余脚本、垃圾文件，并规范版本号与命名。

---

## Acceptance Criteria

### AC-1: config.py 与参考项目对齐
- **Positive Tests**：
  - `scsp/config.py` 的 `V1SimulationConfig` dataclass 包含 `activation_load_store_ratio`（默认 1.0）和 `local_mem_latency_ns`（默认 0.0）两个字段；
  - `normalize_raw_config` 函数中对这两个字段执行 `setdefault`；
  - `normalize_raw_config` 函数执行 `normalized.pop("simulation_mode", None)` 以兼容历史请求；
  - `build_simulation_config` 和 `dump_config_dict` 正确处理这两个新字段；
  - 与参考项目的 `scsp/config.py` diff 仅保留合理差异（如 v1/v1.1 版本标识）。
- **Negative Tests**：
  - 字段缺失导致前端提交含 `activation_load_store_ratio` 的配置时后端报错；
  - 历史 payload 中的 `simulation_mode` 字段未被静默丢弃而引发异常。

### AC-2: 版本号统一规范为 "v1"
- **Positive Tests**：
  - `run_scsp.py` 的 `description` 文本包含 "SCSP v1"（而非 "v0"）；
  - `scsp/web_api.py` 的 `FastAPI(title="SCSP API", version="v1")`；
  - `scsp/experiment.py` 的 `ENGINE_VERSION = "v1"`（而非 "v0"）。
- **Negative Tests**：
  - 任何位置仍残留 "v0" 或 "0" 作为版本标识。

### AC-3: 清理垃圾文件与 orphan 编译缓存
- **Positive Tests**：
  - 项目根目录不存在空文件 `0`、`comm_size`、`stats`、`tensor_size`、`workload-`；
  - `scsp/__pycache__/` 中不存在无对应 `.py` 源文件的 orphan `.pyc`（如 `analysis.cpython-*.pyc`、`communication.cpython-*.pyc`、`deployment.cpython-*.pyc`、`metrics.cpython-*.pyc`、`model.cpython-*.pyc`、`simulator.cpython-*.pyc`、`task.cpython-*.pyc`）；
  - `tests/__pycache__/` 中不存在无对应 `.py` 源文件的 orphan `.pyc`；
  - `.pytest_cache/` 目录已清理。
- **Negative Tests**：
  - 上述垃圾文件或 orphan 缓存在清理后仍存在。

### AC-4: 清理死逻辑测试文件
- **Positive Tests**：
  - 删除或修复引用已不存在模块的测试文件：`tests/test_communication.py`（引用 `scsp.communication`）、`tests/test_simulator_decode.py`（引用 `scsp.simulator.run_v1_simulation`）；
  - 若保留 `tests/test_deployment.py`、`tests/test_metrics.py`，确认它们 import 的模块在当前代码库中真实存在且测试可通过；
  - 运行剩余有效测试命令 `uv run --with pytest --with requests python -m pytest tests/ -v` 全部通过。
- **Negative Tests**：
  - 测试 import 时抛出 `ModuleNotFoundError`；
  - 有效测试因清理而失败。

### AC-5: 前端仿真入口可运行（Qwen2.5-VL-3B 验证）
- **Positive Tests**：
  - 启动 Web 服务 `python3 run_web.py` 后，健康检查 `/api/health` 返回 `{"status":"ok"}`；
  - 通过前端页面或等效 API 调用，使用 `model_name: "Qwen2.5-VL-3B"`、`link_bandwidth_gbps: 100` 等参数执行：
    - `/api/simulations/single`（单点仿真）成功返回含 `metrics.total_latency_s` 的 JSON；
    - `/api/simulations/sweep`（带宽扫描）成功返回含 `rows` 和 `knee_bandwidth_gbps` 的 JSON；
    - `/api/experiments/run`（实验管理-创建实验）成功返回实验记录；
    - `/api/experiments`（实验管理-列表）成功返回历史实验列表；
    - `/api/experiments/{id}`（实验管理-查看详情）成功返回单条实验记录；
    - `/api/experiments/reproduce/{id}`（实验管理-重现实验）成功返回新实验记录与对比结果。
  - 所有 API 返回的 `metrics` 中包含非零的 `total_latency_s` 和 `effective_compute_pflops`。
- **Negative Tests**：
  - 任何 API 返回 HTTP 500 或超时；
  - 前端页面加载后无法触发仿真或实验管理操作。

### AC-6: 无回归
- **Positive Tests**：
  - 现有可运行测试（如 `test_astra_integration.py`、`test_experiment.py`、`test_web_api.py`）在清理后仍全部通过；
  - `python3 -m py_compile scsp/*.py` 无语法错误。
- **Negative Tests**：
  - 引入语法错误或破坏已有有效测试；
  - `configs/model_registry.json` 被意外修改或删除。

---

## Implementation Notes

- 代码中禁止出现 AC-、Milestone、Step、Phase 等 plan 标记。
- **仓库清理类操作**（删除垃圾文件、清理 orphan 缓存）由 Planner 直接执行，不进入 Builder 循环。
- **代码修改类操作**（config.py 字段补充、版本号字符串更新、测试文件删除）由 Builder（Codex）执行。
- 前端验证时若 ASTRA-sim 编译产物缺失，仅记录阻塞原因并继续其他 AC，不强制重新编译。
- 所有变更在 `master` 分支上进行，不创建新分支。

---

## Path Boundaries

- **可接受的实现范围**：
  - `scsp/config.py` 的字段补充与默认值设置；
  - 版本号字符串替换（`run_scsp.py`、`web_api.py`、`experiment.py`）；
  - 死测试文件的删除或修复；
  - 垃圾文件与编译缓存的删除；
  - 前端 API 的端到端验证。
- **不可接受的方向**：
  - 修改 `astra-sim/` 或 `stage/` 子模块内部的业务逻辑；
  - 重构 `engine.py` 或 `astra_sim_bridge.py` 的核心仿真调度逻辑；
  - 修改 `configs/model_registry.json` 中的模型参数定义；
  - 引入新的前端框架或重写 `web/index.html`。
