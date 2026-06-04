# Round 1 Summary

## 本 round 完成的 AC

| AC | 目标 | 状态 | 交付物 |
|----|------|------|--------|
| AC-5 | 前端仿真入口可运行状态验证 | ✅ 完成 | 7 个 API 端点全部端到端验证通过 |

## 验证环境准备

- 安装 `fastapi==0.136.3`, `uvicorn==0.49.0`, `requests==2.34.2` 到 seespace venv
- 启动 `python3 run_web.py` (uvicorn on 0.0.0.0:8000)
- 使用 Qwen2.5-VL-3B 作为测试模型

## API 端点验证详情

### 1. Health Check — `GET /api/health`
- **状态**: ✅ 200
- **响应**: `{"status":"ok"}`

### 2. Single Simulation — `POST /api/simulations/single`
- **状态**: ✅ 200
- **测试模型**: Qwen2.5-VL-3B
- **响应**: `mode=single`, `total_latency_s=18.92415663`
- **说明**: ASTRA-sim 后端编译产物可用，仿真链路端到端正常

### 3. Sweep Simulation — `POST /api/simulations/sweep`
- **状态**: ✅ 200
- **测试模型**: Qwen2.5-VL-3B
- **带宽列表**: `[10, 50]`
- **响应**: `mode=sweep`, `rows_count=2`, `knee_bandwidth_gbps=50.0`
- **说明**: 扫参仿真正常，返回结果包含每带宽点的延迟与瓶颈分析

### 4. Run Experiment — `POST /api/experiments/run`
- **状态**: ✅ 200
- **模板**: `bandwidth_sensitivity`
- **响应**: `status=success`, `experiment_id=10c9925b-97ef-46...`
- **说明**: 实验管理正常，记录写入 `experiments/records.jsonl`

### 5. List Experiments — `GET /api/experiments`
- **状态**: ✅ 200
- **响应**: `count=11`
- **说明**: 历史实验记录可正常列出

### 6. Get Experiment Detail — `GET /api/experiments/{id}`
- **状态**: ✅ 200
- **响应**: `name=api-test-qwen3b-v1`, `status=success`
- **说明**: 按 experiment_id 查询详情正常

### 7. Reproduce Experiment — `POST /api/experiments/reproduce/{id}`
- **状态**: ✅ 200
- **响应**: `reproduced_id=d6c7bc79-b1ff-4a...`
- **说明**: 实验复现功能正常，生成新的 experiment_id

## 已知问题/说明

- `/api/simulations/sweep` 返回数据结构为 `{"mode":"sweep","knee_bandwidth_gbps":...,"rows":[...]}`，其中结果数组键名为 `rows` 而非 `results`。测试脚本已据此调整，API 行为正常。
- ASTRA-sim 编译产物（`astra-sim/build/astra_analytical/build/bin/AstraSim_Analytical_*`）已存在且可用，无需重新编译。
- 测试脚本已保存至 `tasks/scsp-v1-cleanup-alignment/impl/test_api_full.py` 和 `test_experiment_api.py` 供后续复用。
