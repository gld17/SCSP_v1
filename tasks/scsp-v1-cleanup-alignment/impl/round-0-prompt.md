# Round 0 任务

## 本轮需完成的工作

完成以下代码修改，将 summary 写入：
`/share/guolidong-nfs/SeeSpace/SCSP_v1/tasks/scsp-v1-cleanup-alignment/impl/round-0-summary.md`

### 任务 1：config.py 与参考项目对齐（AC-1）

修改 `/share/guolidong-nfs/SeeSpace/SCSP_v1/scsp/config.py`：

1. 在 `V1SimulationConfig` dataclass 中，在 `inter_sat_distance_km` 字段之后添加两个新字段：
   ```python
   activation_load_store_ratio: float = 1.0
   local_mem_latency_ns: float = 0.0
   ```

2. 在 `normalize_raw_config` 函数中，在 `normalized.setdefault("inter_sat_distance_km", 10.0)` 之后添加：
   ```python
   normalized.setdefault("activation_load_store_ratio", 1.0)
   normalized.setdefault("local_mem_latency_ns", 0.0)
   normalized.pop("simulation_mode", None)
   ```

3. 在 `build_simulation_config` 函数返回 `V1SimulationConfig(...)` 的构造参数中，在 `inter_sat_distance_km` 之后添加：
   ```python
   activation_load_store_ratio=float(normalized.get("activation_load_store_ratio", 1.0)),
   local_mem_latency_ns=float(normalized.get("local_mem_latency_ns", 0.0)),
   ```

4. 在 `dump_config_dict` 函数返回的字典中，在 `inter_sat_distance_km` 之后添加：
   ```python
   "activation_load_store_ratio": config.activation_load_store_ratio,
   "local_mem_latency_ns": config.local_mem_latency_ns,
   ```

### 任务 2：版本号统一规范为 "v1"（AC-2）

修改以下三个文件中的版本号：

1. `/share/guolidong-nfs/SeeSpace/SCSP_v1/run_scsp.py`：
   - 将 `description="Run SCSP v0 simulation` 改为 `description="Run SCSP v1 simulation`
   - 将 `--output-prefix` 的默认值 `"outputs/v1"` 保持不变（已经是 v1）

2. `/share/guolidong-nfs/SeeSpace/SCSP_v1/scsp/web_api.py`：
   - 将 `app = FastAPI(title="SCSP API", version="0")` 改为 `app = FastAPI(title="SCSP API", version="v1")`

3. `/share/guolidong-nfs/SeeSpace/SCSP_v1/scsp/experiment.py`：
   - 将 `ENGINE_VERSION = "v0"` 改为 `ENGINE_VERSION = "v1"`

### 任务 3：清理死逻辑测试文件（AC-4）

SCSP_v1 项目中以下模块已不存在，但仍有测试文件引用它们，需要删除这些死测试文件：

- `tests/test_communication.py` — 引用已删除的 `scsp.communication`
- `tests/test_simulator_decode.py` — 引用已删除的 `scsp.simulator.run_v1_simulation`

注意：以下测试文件需要保留并验证它们能通过：
- `tests/test_astra_integration.py`
- `tests/test_experiment.py`
- `tests/test_web_api.py`

另外请检查 `tests/test_deployment.py` 和 `tests/test_metrics.py` 是否引用了不存在的模块，如果是则一并删除。

### 任务 4：验证无回归（AC-6）

修改完成后运行：
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
python3 -m py_compile scsp/*.py
```

然后运行有效测试：
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
uv run --with pytest --with requests python -m pytest tests/test_astra_integration.py tests/test_experiment.py tests/test_web_api.py -v
```

如果测试失败，请分析原因并在 summary 中报告。

### 禁止修改的文件

- `configs/model_registry.json`
- `astra-sim/` 子模块内部文件
- `stage/` 子模块内部文件
- `web/index.html`

## plan.md 全文

[plan.md 内容见 /share/guolidong-nfs/SeeSpace/SCSP_v1/tasks/scsp-v1-cleanup-alignment/plan.md]
