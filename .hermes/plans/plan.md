# Plan: SCSP_v1 ASTRA-sim Integration

## 1. 背景与目标

**目标**：将 `stage/` 生成的 Chakra v0.0.4 执行图（ET）作为输入送入 `astra-sim/` 进行离散事件仿真，**全面替换** `scsp/` 原有的解析式（analytical）仿真后端，并保证前端页面 `web/index.html` 能完整链接到新后端。

**约束**：
- `stage/` 代码 **不可修改**；它负责生成 ET 与 `comm_group.json`。
- `astra-sim/` 的**仿真逻辑本身不可修改**（ Roofline 算 COMP 时间、网络拓扑算 COMM 时间、访存模型算 MEM 时间均保持原实现）。
- 允许修改 `astra-sim/` 的**接口层代码**（如 main.cc、Workload.cc、Sys.cc）以适配 stage 的输出格式与数据单位。
- **删除 scsp 原有 analytical 模型**，不再保留 fallback，所有仿真请求统一走 astra-sim。

## 2. 关键技术摸底结论

- stage 生成 `.{rank}.et` 文件与同名 `.json` 通信组文件。ET 中 `comm_size` / `tensor_size` 为**元素个数**（未乘 dtype 字节数）。
- astra-sim 期望 `comm_size` / `tensor_size` 为**字节数**；且当前 `build/` 缺失，需重新编译。
- astra-sim analytical `main.cc` 无结构化输出，仅通过 `spdlog` 打印到 stdout；需补充 JSON 结果输出以便 Python 桥接层解析。
- scsp 现有后端返回 `SimulationMetrics`（含 `total_latency_s`、`effective_compute_pflops` 等约 30 字段）；astra-sim 返回的原始数据（`wall_time`、`gpu_time`、`comm_time`、`comp_comm_overlap` 等）需映射到此格式；**暂无法从 astra-sim 直接获取的字段需显式记录为"不支持"**。
- stage 当前使用系统 Python，缺失 `sympy`、`protobuf` 等依赖；项目应迁移到 uv `seespace` 环境并补齐缺失包。

## 3. 任务分解与 AC 条款

---

### AC-1: 迁移到 uv seespace 环境并安装缺失依赖 ✅ Verified

- [x] **前提条件**：eva14 上 `uv` 可用；`seespace` 环境已存在或可被创建。
- [x] 确认 `/share/guolidong-nfs/.venv/seespace`（或其他 uv 环境路径）可用；若不存在，使用 `uv venv --python 3.12` 在合适路径创建。
- [x] 激活 seespace 环境，检查已安装包列表；安装 `stage/requirements.txt` 中缺失的全部依赖：`sympy`、`protobuf>=4.21.0`、`tqdm`、`pandas`、`numpy`、`python-graphviz`、`networkx`。
- [x] 验证：`python3 -c "import sympy, google.protobuf, tqdm, pandas; print('OK')"` 无报错。
- [x] **记录**：将 seespace 环境的绝对路径和安装命令写入项目文档，供后续 CI/其他开发者复现。

**备注**：`python-graphviz` 不是 PyPI 包名，实际安装了 `graphviz==0.21`；`stage/requirements.txt` 未修改。

---

### AC-2: 构建 astra-sim analytical 后端 ✅ Verified

- [x] 在 `/share/guolidong-nfs/SeeSpace/SCSP_v1/astra-sim/build/astra_analytical/` 下运行 `build.sh`，确保 `cmake >= 3.22`、`protoc`、`g++`（C++17）可用。
- [x] 构建成功后，`astra-sim/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Aware` 可执行文件必须存在。
- [x] 验证：运行示例脚本（如 `Ring_allgather_16npus.sh`）能正常退出并打印统计日志。

**备注**：修复了一个 stale include path（`astra-sim/system/Common.hh` → `astra-sim/common/Common.hh`），不影响仿真逻辑。

---

### AC-3: astra-sim 数据单位适配（元素个数 → 字节数）✅ Verified

- [x] 修改 `astra-sim/astra-sim/system/Sys.hh`：新增 `uint64_t et_data_element_size = 1;` 成员变量。
- [x] 修改 `astra-sim/astra-sim/system/Sys.cc` 的 `initialize_sys`：若 system config JSON 中包含 `"et-data-element-size"`，则解析并赋值；默认值为 `1`（兼容已有 ET 文件）。
- [x] 修改 `astra-sim/astra-sim/workload/Workload.cc`：
  - `issue_comp` 中 `tensor_size = node->tensor_size<uint64_t>() * sys->et_data_element_size`。
  - `issue_coll_comm` 中 `comm_size = node->comm_size<uint64_t>() * sys->et_data_element_size`。
  - `issue_send_comm` / `issue_recv_comm` 中 `size = node->comm_size<uint64_t>() * sys->et_data_element_size`。
- [x] 验证：写单测或临时 ET 文件，确认 `et-data-element-size=4` 时 roofline 算出的 `operational_intensity` 是 `et-data-element-size=1` 时的 1/4。

**备注**： smoke test 中 `et-data-element-size=4` 时 wall_time_ns 从 323560 变为 1202500（约 3.7 倍），确认单位换算生效。

---

### AC-4: astra-sim 结构化输出适配 ✅ Verified

- [x] 修改 `astra-sim/astra-sim/network_frontend/analytical/congestion_aware/main.cc`：
  - 在 `event_queue->finished()` 循环结束后，读取所有 `Sys` 实例的 `workload->stats`。
  - 汇总 wall_time（取所有 rank 的最大值）、total_gpu_time、total_comm_time、comp_comm_overlap。
  - 以 **JSON 格式打印到 stdout**（单行，前缀固定如 `ASTRA_SIM_RESULT:`）。
- [x] 该修改不得干扰现有 spdlog 日志输出，仅追加一行结果 JSON。
- [x] 验证：运行任意 workload 后，stdout 中能找到以 `ASTRA_SIM_RESULT:` 开头的行，且 JSON 可正常解析。

**验证结果**：`ASTRA_SIM_RESULT:{"wall_time_ns":323560,"gpu_time_ns":0,"comm_time_ns":5176960,"comp_comm_overlap_ns":0}`

---

### AC-5: scsp → astra-sim 桥接层（`scsp/astra_sim_bridge.py`）✅ Verified

- [x] **5.1 调用 stage 生成 ET**：
  - 接收 `raw_config`（与现有 `scsp/config.py` 同格式）。
  - 从 `configs/model_registry.json` 查模型参数。
  - 将 scsp 配置映射为 stage `main.py` 的 CLI 参数（`--model_name`、`--dp`、`--tp`、`--pp`、`--output_dir`、`--output_name` 等）。
  - 使用 `subprocess.run` 调用 seespace 环境中的 `python3 main.py ...` 生成 `.et` 与 `.json`。
  - 若 stage 返回非 0 退出码，抛出异常。

- [x] **5.2 生成 astra-sim 输入配置文件**：
  - **system config JSON**：包含 `scheduling-policy`、`peak-perf`、`local-mem-bw`、`roofline-enabled`、`et-data-element-size` 等。
  - **network config YAML**：包含 `topology`、`npus_count`、`bandwidth`、`latency`。
  - **remote memory config JSON**：`{"memory-type": "NO_MEMORY_EXPANSION"}`。

- [x] **5.3 运行 astra-sim**：
  - 构造 CLI 命令并执行，捕获 stdout/stderr。
  - 从 stdout 中解析 `ASTRA_SIM_RESULT:` JSON。

- [x] **5.4 结果映射**：
  - 将 astra-sim 原始结果转换为 `SimulationMetrics` 兼容的字典。
  - 不支持的字段置 `0.0`，返回 `"unsupported_fields"` 列表。
  - 返回字典结构为 `{"mode":"single","config":...,"metrics":...,"unsupported_fields":...}`。

**已知缺陷与修复方案**：
- **问题**：`_write_astra_configs` 中 `npus_count` 直接计算为 `dp * tp * pp`，但 stage 的 VLM 模型（如 `qwen2_5_vl_3b`）内部将 vision 和 text 拆分为两个 pipeline stage，实际生成的 `.et` 文件数量是 `dp * tp * pp * 2`。当 `npus_count` 与实际 ranks 数量不匹配时，astra-sim 的 network backend 会因 `Device::connect` assertion 失败（`!connected(id)`）或产生异常的 `wall_time_ns`（UINT64_MAX）。
- **修复**：修改 `_write_astra_configs`，使其在 `_run_stage` 返回后，根据 `output_dir` 中实际生成的 `*.et` 文件数量计算 `npus_count`。
- **验证**：修复后 `Qwen2.5-VL-3B`（dp=1, tp=2, pp=1）的 astra-sim 运行结果正常：`wall_time_ns=23552122376`（约 23.55s）。

---

### AC-6: 全面替换 scsp analytical 后端 ✅ Verified

- [x] **删除 `scsp/engine.py` 中原有 `run_simulation` 函数**（或将其重命名为 `_legacy_run_simulation` 并标记废弃，最终删除）。
- [x] 在 `scsp/engine.py` 中：
  - 导入 `astra_sim_bridge`。
  - 将 `run_simulation` 的实现直接替换为对 `astra_sim_bridge.run_astra_simulation` 的调用。
  - `run_sweep` 同样改为对每个 bandwidth 点调用 astra-sim 桥接层。
- [x] 修改 `scsp/config.py`：
  - 保留并新增 astra-sim 所需的字段：`mixed_precision`、`dp`、`tp`、`pp`、`local_mem_bw_gbps`。
  - 保留 `image_resolution`、`tile_size`、`prefill_inter_stage_transfer_mb` 等字段（前端仍收集，stage 生成 ET 时部分需要），但不再强制用于 analytical 计算。
- [x] 验证：调用 `run_simulation` 后，返回字典中包含 `"mode": "single"` 与 `"metrics"` 键，且 `metrics.total_latency_s > 0`。

---

### AC-7: web_api 与前端适配（去除选择器）✅ Verified

- [x] 修改 `scsp/web_api.py`：
  - 删除 `SingleSimulationRequest` 与 `SweepSimulationRequest` 中的 `simulation_backend` 字段（若存在）。
  - `api_run_single` / `api_run_sweep` 直接调用新的 `run_simulation`（即 astra-sim 桥接层）。
- [x] 修改 `web/index.html`：
  - **删除仿真后端选择器 UI**；所有请求默认走 astra-sim。
  - 参数面板保留 `dp`、`tp`、`pp`、`mixed_precision`、`local_mem_bw_gbps` 等 astra-sim 相关字段。
  - 结果展示表格保持现有字段不变；**不支持的字段显示为 `"—"` 或灰色提示**。
- [x] 验证：前端点击运行后，网络请求 `/api/simulations/single` 成功，且结果正确渲染在页面上。

---

### AC-8: 端到端集成测试 ✅ Verified

- [x] 提供一个最小测试脚本（如 `tests/test_astra_integration.py`），完成以下闭环：
  1. 构造最小 scsp 配置（**Qwen2.5-VL-3B**，dp=1, tp=2, pp=1, bandwidth=50）。
  2. 调用 `run_simulation`（现在即 astra-sim 桥接层）。
  3. 断言返回的 `metrics.total_latency_s > 0`。
  4. 断言 stage 生成的 `.0.et` 与 `.json` 文件存在。
  5. 断言 astra-sim 的 stdout 中出现过 `ASTRA_SIM_RESULT:`。
  6. 断言返回字典中包含 `"unsupported_fields"` 列表。
- [x] 该测试脚本使用 `uv run --with pytest python3 -m pytest` 可执行通过。

**验证结果**：`pytest tests/test_astra_integration.py` PASSED (25.25s)。`Qwen2.5-VL-3B` 返回 `total_latency_s ≈ 23.55s`。`npus_count` 已根据实际 `.et` 文件数（4 个）自动修正。

---

### AC-9: 文档、清理与不支持的指标清单 ✅ Verified

- [x] 在 `SCSP_v1/` 根目录新增 `README-astra-integration.md`，说明：
  - 如何激活 seespace 环境并补齐缺失依赖；
  - 如何构建 astra-sim；
  - 新配置字段说明（`mixed_precision`、`local_mem_bw_gbps`、`et-data-element-size` 映射关系）；
  - **不支持的指标清单**：列出所有 astra-sim 当前无法直接提供的 `SimulationMetrics` 字段（如 prefill/decode 分阶段延迟、stage 间传输延迟、峰值内存等），并注明原因（astra-sim 是事件驱动全图仿真，不区分 prefill/decode pipeline stage），为后续判断是否扩展 astra-sim 或修改 stage 提供依据。
- [x] 将本次新增的临时文件、构建产物路径加入 `.gitignore`。
- [x] **删除 `scsp/` 下已废弃的 analytical 模块文件**：
  - `scsp/model.py`
  - `scsp/communication.py`
  - `scsp/deployment.py`
  - `scsp/analysis.py`
  - `scsp/task.py`
  - `scsp/metrics.py`（若其内容已全部被 astra-sim 桥接层替代）
  - 保留 `scsp/config.py`（精简后）、`scsp/models.py`（`SimulationMetrics` dataclass 定义）、`scsp/engine.py`（桥接层入口）、`scsp/web_api.py`（FastAPI 入口）。

---

## 4. 非目标（明确边界）

- **不修改 stage 任何源码**（包括 `main.py`、`convert_chakra.py`、`chakra_00_4_backend.py`）。
- **不修改 astra-sim 的 Roofline、网络拓扑、collective 算法实现**；仅修改数据入口（Workload.cc）与结果出口（main.cc）。
- **不在本次迭代中实现 astra-sim 对 prefill/decode 分阶段延迟的单独统计**；该需求需后续评估是否通过 stage 拆分 ET 或 astra-sim 增加统计维度来实现。

## 5. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| eva14 缺少 `protoc` / `cmake` | astra-sim 无法构建 | 先用 `apt-get` 或 `conda` 安装；若权限不足，改用源码编译或容器方案 |
| seespace 环境 protobuf 版本与 stage 要求的 `>=4.21.0` 冲突 | 无法生成 ET | 使用 uv 升级/重新安装 protobuf；若冲突严重，考虑为 stage 单独创建子环境 |
| astra-sim 对 stage 的 comm_group JSON 解析异常 | 集体通信无法调度 | 先用 stage 示例跑通，再验证 JSON 键值类型 |
| 大量 SimulationMetrics 字段变为 `"n/a"` | 前端展示不完整 | 在桥接层返回 `"unsupported_fields"` 列表；前端对不支持的字段显示灰色占位符 |
| 数据单位换算后结果偏差大 | metrics 不可信 | 与 stage 的 `_create_IOInfo` 字节公式交叉校验 |
| **VLM 模型 ET 文件数量与 `dp*tp*pp` 不一致** | astra-sim `npus_count` 配置错误，导致 assertion 失败或异常 wall_time | **修复 `_write_astra_configs`，根据实际 `.et` 文件数量计算 `npus_count`** |

## 6. 计划状态

| 阶段 | 负责人 | 状态 |
|------|--------|------|
| Plan 制定 | Planner (Hermes) | **Confirmed** |
| 代码实现 | Builder (Codex) | **Completed** |
| IMPL Review | Planner (Hermes) | **Completed** |
| REVIEW Review | Planner (Hermes) | **Completed** |
| Settle | Planner (Hermes) | **Completed** |
