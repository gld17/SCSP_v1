# Review Report — SCSP_v1 参数对齐、前端验证与仓库清理

## 审查范围

- **任务**: SCSP_v1 三项迭代（参数对齐、前端验证、仓库清理）
- **提交范围**: `e5aceb9` (plan.md) → `c2acfa2` (最终)
- **变更文件**: 14 files, +222 / −334

---

## AC 通过情况

| AC | 状态 | 验证方式 |
|----|------|----------|
| AC-1 config.py 字段对齐 | ✅ PASS | `V1SimulationConfig` 新增 2 字段；`normalize_raw_config` 添加 `setdefault` + `pop("simulation_mode")`；Python 回归测试通过 |
| AC-2 版本号统一为 "v1" | ✅ PASS | 3 个文件中 "v0" → "v1"，全局搜索无残留 |
| AC-3 垃圾文件清理 | ✅ PASS | 根目录垃圾文件已删除；scsp/__pycache__ 和 tests/__pycache__ 的 orphan .pyc 已清理；.pytest_cache 已删除 |
| AC-4 死逻辑测试清理 | ✅ PASS | 4 个死测试文件 + scsp/simulator.py（废弃函数）+ `__init__.py` 导出项已删除 |
| AC-5 前端 API 可运行 | ✅ PASS | 7 个 API 端点全部验证通过（Qwen2.5-VL-3B）；single latency=18.92s；sweep rows=2 |
| AC-6 无回归 | ✅ PASS | `py_compile scsp/*.py` 全通过；`model_registry.json` 未修改 |

---

## 代码变更审查

### 新增字段（config.py）
- `activation_load_store_ratio: float = 1.0`
- `local_mem_latency_ns: float = 0.0`
- `normalized.pop("simulation_mode", None)` 兼容历史请求

**审查意见**: ✅ 字段命名与参考项目一致，默认值合理，兼容逻辑完备。

### 版本号替换
- `run_scsp.py`: "SCSP v0" → "SCSP v1"
- `scsp/web_api.py`: `version="0"` → `version="v1"`
- `scsp/experiment.py`: `ENGINE_VERSION = "v0"` → `"v1"`

**审查意见**: ✅ 替换彻底，无残留。

### 删除的文件
| 文件 | 删除原因 |
|------|----------|
| `scsp/simulator.py` | 仅含 `run_v1_simulation` 废弃占位，硬编码 `RuntimeError` |
| `tests/test_communication.py` | import 已删除的 `scsp.communication` |
| `tests/test_simulator_decode.py` | import 已废弃的 `scsp.simulator.run_v1_simulation` |
| `tests/test_deployment.py` | import 不存在的 `scsp.deployment` |
| `tests/test_metrics.py` | import 不存在的 `scsp.metrics` |

**审查意见**: ✅ 删除依据充分，删除后 `py_compile` 和全局搜索均无死引用。

### 仓库清理
- 根目录空文件 `0`、`comm_size`、`stats`、`tensor_size`、`workload-` 已删除
- `scsp/__pycache__/` 21 个 orphan `.pyc` 已清理（保留 10 个有源文件的缓存）
- `tests/__pycache__/` 2 个 orphan `.pyc` 已清理
- `.pytest_cache/` 已删除

**审查意见**: ✅ 清理干净，无过度删除。

---

## 前端 API 验证记录

| # | 端点 | 状态 | 响应摘要 |
|---|------|------|----------|
| 1 | GET /api/health | 200 | `{"status":"ok"}` |
| 2 | POST /api/simulations/single | 200 | mode=single, total_latency_s=18.92s |
| 3 | POST /api/simulations/sweep | 200 | mode=sweep, rows_count=2, knee=50.0 |
| 4 | POST /api/experiments/run | 200 | status=success, id=10c9925b... |
| 5 | GET /api/experiments | 200 | count=11 |
| 6 | GET /api/experiments/{id} | 200 | name=api-test-qwen3b-v1 |
| 7 | POST /api/experiments/reproduce/{id} | 200 | reproduced_id=d6c7bc79... |

**审查意见**: ✅ 全部端点正常工作，ASTRA-sim 编译产物可用，仿真链路完整。

---

## 未引入的变更（符合 Path Boundaries）

- ✅ 未修改 `astra-sim/` 或 `stage/` 子模块内部文件
- ✅ 未重构 `engine.py` 或 `astra_sim_bridge.py` 核心调度逻辑
- ✅ 未修改 `configs/model_registry.json`
- ✅ 未重写 `web/index.html`

---

## 结论

**所有 AC 均通过，代码变更干净、验证充分，准予进入 SETTLE。**
