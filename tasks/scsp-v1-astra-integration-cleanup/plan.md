# SCSP_v1 Astra-sim 集成清理与接口对齐

## Goal Description

完成 SCSP_v1 项目从旧仿真逻辑到 stage + astra-sim 新仿真逻辑的彻底清理和适配：
1. 从后端代码中移除旧仿真字段，并在说明文档中保留字段清单供后续迭代参考；
2. 前端替换为基于 astra-sim 真实仿真结果的展示，星座构型/天基应用/模型配置降级保留为后续扩展接口；
3. mock 回退机制改为显式 toast 提示，且仅在 dev 模式可用；
4. 对齐 SCSP 仿真配置与 stage CLI 参数，模型参数统一从模型配置文件走，直接参数传递（无需映射表）；
5. 不改动 stage/ 和 astra-sim/ 目录下任何文件。

## Acceptance Criteria

### AC-1: 旧仿真字段从后端移除并在文档中归档
- **Positive Tests**：
  - `scsp/models.py` 中 `SimulationMetrics` 不再包含任何旧仿真字段（data_tx_latency_s, inter_stage_latency_s, stage1_compute_latency_s, stage2_compute_latency_s, decode_latency_s_per_token, decode_total_latency_s, decode_compute_latency_s_per_token, decode_memory_latency_s_per_token, decode_effective_compute_pflops, decode_bottleneck, prefill_compute_time_s, prefill_memory_time_s, prefill_time_s, prefill_bottleneck, decode_energy_efficiency_tokens_per_j, total_inference_time_s, prefill_peak_memory_bytes, prefill_peak_memory_gb, single_star_peak_memory_bytes, single_star_peak_memory_gb, prefill_weight_memory_bytes, prefill_kv_memory_bytes, prefill_activation_peak_memory_bytes, prefill_workspace_memory_bytes）。保留的字段仅为 astra-sim 能产出的指标：total_samples, total_latency_s, effective_compute_flops, effective_compute_pflops, ideal_peak_pflops, compute_utilization, bottleneck_stage。
  - `astra_sim_bridge.py` 中移除 `UNSUPPORTED_FIELDS` 列表及其在返回结果中的引用。
  - 在 `README-astra-integration.md` 中新建 "Legacy Metrics Reference" 章节，完整列出上述已被移除的旧字段及其原始含义，作为后续迭代的参考文档（不放在 "Unsupported Metrics" 中，而是作为独立归档章节）。
  - 前端 `web/index.html` 不再引用上述旧字段进行展示或计算。
- **Negative Tests**：
  - 清理后 `python3 -m py_compile scsp/models.py` 和 `python3 -m py_compile scsp/astra_sim_bridge.py` 均通过，无语法错误。
  - 不删除 `scsp/models.py` 文件本身，只删除字段定义。
  - 文档归档后，代码中不再有任何地方引用旧字段。

### AC-2: 前端展示适配 astra 仿真结果
- **Positive Tests**：
  - 前端 KPI 卡片和图表展示的数据来源从旧字段切换为 astra-sim 返回的真实字段：`total_latency_s`, `effective_compute_pflops`, `compute_utilization`, `bottleneck_stage`。
  - `astra_sim_bridge.py` 返回的 `metrics` 中，`bottleneck_stage` 的值根据 `astra_result` 中 `gpu_time_ns` 和 `comm_time_ns` 的比例推导：若 `comm_time_ns / gpu_time_ns > 0.5` 则标为 `"communication"`，否则标为 `"compute"`（不再硬编码 `"unknown"`）。
  - 星座构型（scene/sat 可视化）、天基应用（页面导航）、模型配置（表单输入）保持现有 HTML 结构和交互，仅移除依赖旧字段的数值展示逻辑。
- **Negative Tests**：
  - 前端页面加载后，所有图表和 KPI 数值均能正确渲染，控制台无 `undefined` 引用报错。
  - 不删除前端页面中的场景可视化（scene/sat）和配置表单 DOM 结构。

### AC-3: Mock 回退机制显式化与 Dev 模式限制
- **Positive Tests**：
  - 前端所有 `catch` 块中静默回退到 `mockRows` 的逻辑改为：先通过 `toast()` 或 `alert()` 显式提示用户 "后端仿真接口调用失败，请检查服务状态"。
  - 仅当 `window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'` 时，才允许继续展示 `mockRows` 作为降级数据；否则直接显示错误状态，不再填充 mock 数据。
  - `init()` 函数中的 health check 失败后，同样遵循上述规则：dev 环境才启用 mock，非 dev 环境显示 "API 不可用" 状态。
- **Negative Tests**：
  - 在非 localhost 域名下访问页面，若后端不可用时页面显示明确的错误提示，不展示任何 mock 数据。
  - 在 localhost 下访问，若后端不可用，toast 提示后仍可展示 mock 数据用于前端开发调试。

### AC-4: SCSP 配置与 stage CLI 参数对齐（直接传递，无映射表）

**主人决策已确认**：
1. 删除 `num_images`，SCSP 中新增 `batch` 参数对应 stage `--batch`；`decode_tokens` 保持对应 `--seq`。
2. SCSP 并行度字段与 stage 完全一致：`dp`, `tp`, `sp`, `ep`, `pp`, `vision_dp`, `vision_tp`, `vision_pp`, `vision_ep`, `text_dp`, `text_tp`, `text_pp`, `text_ep`。
3. 所有模型结构参数（文本 backbone + Vision encoder）统一从模型配置文件走，SCSP 中不暴露 `llm_num_hidden_layers`, `llm_hidden_size`, `llm_num_attention_heads`, `llm_num_key_value_heads`, `vision_hidden_size`, `vision_num_hidden_layers`, `vision_num_attention_heads`, `vision_intermediate_size`, `vision_in_channels`, `vision_projection_size` 等字段。
4. SCSP 的数据相关配置与 stage 对齐：`image_resolution` 解析后映射为 `vision_image_size`（宽高中较大的值），`tile_size` 解析后映射为 `vision_patch_size`。
5. SCSP 独有的旧仿真字段（`big_star_peak_pflops`, `image_resolution`, `inter_sat_distance_km`, `tile_size` 等）完全保留，不映射到 stage。
6. 新增 stage 独有参数到 SCSP 配置：`weight_sharded`, `activation_recompute`, `chakra_schema_version`, `print_gpu_vram`, `include_backward`；不添加 `tpsp`。
7. 无需映射表，在 `_run_stage()` 中直接从 SCSP config 取参构造 CLI 参数列表。
8. `model_type`（dense/gpt/vlm/moe）通过模型注册表中的 `model_type` 字段自动推断，作为 `--model_type` 传递给 stage。

- **Positive Tests**：
  - `scsp/config.py` 的 `V1SimulationConfig` 和 `normalize_raw_config` 更新为包含上述字段：
    - 新增：`batch`, `sp`, `ep`, `vision_dp`, `vision_tp`, `vision_pp`, `vision_ep`, `text_dp`, `text_tp`, `text_pp`, `text_ep`, `weight_sharded`, `activation_recompute`, `chakra_schema_version`, `print_gpu_vram`, `include_backward`
    - 删除：`num_images`, `llm_num_hidden_layers`, `llm_hidden_size`, `llm_num_attention_heads`, `llm_num_key_value_heads`
    - 保留（旧仿真字段不映射到 stage）：`big_star_peak_pflops`, `image_resolution`, `tile_size`, `inter_sat_distance_km`, `prefill_inter_stage_transfer_mb`, `decode_inter_stage_transfer_kb`, `flops_per_sample`, `single_star_compute_utilization`, `prefill_compute_utilization`, `prefill_memory_utilization`, `decode_compute_utilization`, `decode_memory_utilization`, `single_node_memory_bandwidth_bytes_per_sec`, `prefill_memory_bytes_per_patch`, `decode_flops_per_token`, `decode_memory_bytes_per_token`, `inter_sat_latency_target_ms`, `peak_power_limit_kw`, `single_star_compute_payload_power_w`, `stage_split_ratio`, `fixed_sync_overhead_ms`, `activation_load_store_ratio`, `local_mem_bw_gbps`, `local_mem_latency_ns`
  - `_run_stage()` 构造 stage CLI 参数时直接传递：
    - `--batch` 从 `config["batch"]` 取
    - `--seq` 从 `config["decode_tokens"]` 取
    - `--dp` / `--tp` / `--sp` / `--ep` / `--pp` 直接取对应字段
    - `--vision_dp` / `--vision_tp` / `--vision_pp` / `--vision_ep` 直接取对应字段
    - `--text_dp` / `--text_tp` / `--text_pp` / `--text_ep` 直接取对应字段
    - `--model_name` 从注册表解析后的名称取
    - `--model_type` 从注册表 `model_type` 字段推断
    - `--mixed_precision` 直接取
    - `--vision_image_size` 从 `image_resolution` 解析（取 max(width, height)）
    - `--vision_patch_size` 从 `tile_size` 解析（取 max(width, height)）
    - `--weight_sharded`, `--activation_recompute`, `--chakra_schema_version`, `--print_gpu_vram`, `--include_backward` 直接取对应字段
    - 不传递任何模型结构参数（`--dmodel`, `--num_stacks`, `--head`, `--kvhead`, `--vision_hidden_size` 等）
  - 模型注册表 `configs/model_registry.json` 中包含 `model_type` 字段，用于推断 stage 的 `--model_type`。
- **Negative Tests**：
  - 不传递 stage CLI 中不存在的参数。
  - 不修改 stage/ 目录下的 `main.py` 或任何模型配置文件。
  - `python3 -m py_compile scsp/config.py` 通过无语法错误。

### AC-5: 无回归（前后端可运行）
- **Positive Tests**：
  - `python3 -m py_compile scsp/*.py` 所有文件均通过。
  - `python3 run_scsp.py --help` 正常输出帮助信息。
  - `python3 run_web.py --help` 正常输出帮助信息。
  - FastAPI 应用 `python3 -c "from scsp.web_api import app; print('OK')"` 正常导入无报错。
- **Negative Tests**：
  - 不引入新的 import 错误或语法错误。
  - 不修改 stage/ 和 astra-sim/ 目录下任何文件。

## Implementation Notes
- 代码中禁止出现 AC-、Milestone、Step、Phase 等 plan 标记。
- stage/ 和 astra-sim/ 目录下任何文件均不可修改、删除或移动。
- 前端 `mockRows` 可以保留但需移除旧字段，且仅用于 localhost dev 模式降级。
- 所有文件操作均通过 Hermes 工具完成，不直接输出代码到对话中。

## Path Boundaries
- 可接受的实现范围：SCSP_v1 项目根目录下的 `scsp/`、`web/`、`configs/`、`README-astra-integration.md` 文件。
- 不可接受的方向：修改 stage/ 或 astra-sim/ 目录下的任何文件；删除前端页面中的场景可视化或配置表单结构。
