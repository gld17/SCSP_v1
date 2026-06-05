You are the Builder in a PBR Coding workflow. Your job is to implement the following plan by modifying the specified files in /share/guolidong-nfs/SeeSpace/SCSP_v1. You must NOT modify any files under stage/ or astra-sim/ directories.

## CRITICAL RULES
1. Only implement; do NOT review or judge your own work.
2. After finishing, write a summary of exactly what you changed to tasks/scsp-v1-astra-integration-cleanup/impl/round-0-summary.md.
3. Mark AC statuses as "Implemented" only; NEVER mark anything as "Verified".
4. Do NOT add AC-/Milestone/Step/Phase markers into production code.
5. Do NOT delete any files; only edit existing ones.
6. All model structure parameters (llm_* and vision_* structural fields) must be removed from SCSP config and passed only via model registry / stage model configs.
7. Direct CLI argument passing: no mapping tables, no abstraction layers. Simply read from config dict and append to cmd list.

## ACCEPTANCE CRITERIA SUMMARY

### AC-1: Remove legacy simulation fields from backend + archive in docs
- In `scsp/models.py`: Remove all legacy fields from `SimulationMetrics`. Keep only: total_samples, total_latency_s, effective_compute_flops, effective_compute_pflops, ideal_peak_pflops, compute_utilization, bottleneck_stage.
- In `scsp/astra_sim_bridge.py`: Remove `UNSUPPORTED_FIELDS` list and its usage in the returned dict.
- In `README-astra-integration.md`: Add a new top-level section "## Legacy Metrics Reference" that lists all removed legacy fields and their original meaning. Update the existing "## Unsupported Metrics" section to reference this new archive section instead of duplicating the list.
- In `web/index.html`: Remove all references to legacy fields in rendering/display logic.

### AC-2: Frontend adapts to astra-sim real results
- `astra_sim_bridge.py` `_map_metrics`: Derive `bottleneck_stage` from astra_result: if `comm_time_ns / gpu_time_ns > 0.5` then "communication", else "compute". Remove hardcoded "unknown".
- `web/index.html`: Update KPI cards and charts to source from `total_latency_s`, `effective_compute_pflops`, `compute_utilization`, `bottleneck_stage`. Do NOT remove scene/sat visualization, app navigation, or config form DOM structures.

### AC-3: Mock fallback explicit + dev-only
- In `web/index.html`:
  - Define `const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';`
  - In every `catch` block that currently silently falls back to `mockRows`, FIRST call `toast('后端仿真接口调用失败，请检查服务状态', {type:'error'});` or equivalent. Then ONLY if `isDev`, fall back to mockRows. If NOT isDev, show error state and leave data empty.
  - In `init()` health check `catch`, same rule: if isDev show "API 不可用（已启用 mock 展示）", else show "API 状态：不可用".
  - Update `mockRows` to remove legacy fields (data_tx_latency_s, inter_stage_latency_s, stage1_compute_latency_s, stage2_compute_latency_s). Keep only fields that astra-sim produces.

### AC-4: Align SCSP config with stage CLI (direct pass, no mapping table)
Changes to `scsp/config.py`:
- `V1SimulationConfig` dataclass:
  - REMOVE: `num_images`, `llm_num_hidden_layers`, `llm_hidden_size`, `llm_num_attention_heads`, `llm_num_key_value_heads`
  - ADD: `batch: int = 1`, `sp: int = 1`, `ep: int = 1`, `vision_dp: int = 1`, `vision_tp: int = 1`, `vision_pp: int = 1`, `vision_ep: int = 1`, `text_dp: int = 1`, `text_tp: int = 1`, `text_pp: int = 1`, `text_ep: int = 1`, `weight_sharded: bool = False`, `activation_recompute: bool = False`, `chakra_schema_version: str = "v0.0.1"`, `print_gpu_vram: bool = False`, `include_backward: bool = False`
  - Keep all SCSP-specific legacy fields unchanged (big_star_peak_pflops, image_resolution, tile_size, inter_sat_distance_km, etc.)
- `normalize_raw_config`:
  - Remove `num_images` default (use `batch` instead with default 1)
  - Add defaults for all new fields listed above
  - Remove defaults for `llm_num_hidden_layers`, `llm_hidden_size`, `llm_num_attention_heads`, `llm_num_key_value_heads`
  - Keep `mixed_precision`, `dp`, `tp`, `pp`, `local_mem_bw_gbps` defaults
- `validate_raw_config`:
  - Remove validations for `llm_num_hidden_layers`, `llm_hidden_size`, `llm_num_attention_heads`, `llm_num_key_value_heads`
- `build_simulation_config`:
  - Remove construction args for `num_images` and `llm_*` fields
  - Add construction args for all new fields
- `dump_config_dict`:
  - Remove `num_images` and `llm_*` keys
  - Add all new field keys
  - Keep all SCSP-specific legacy fields

Changes to `scsp/astra_sim_bridge.py`:
- `_run_stage()` function: Build the CLI `cmd` list by directly reading from `config` dict:
  ```
  cmd = [str(SEESPACE_PYTHON), "main.py",
         "--model_name", stage_model_name,
         "--batch", str(config.get("batch", 1)),
         "--seq", str(config.get("decode_tokens", 1)),
         "--dp", str(config.get("dp", 1)),
         "--tp", str(config.get("tp", 1)),
         "--sp", str(config.get("sp", 1)),
         "--ep", str(config.get("ep", 1)),
         "--pp", str(config.get("pp", 1)),
         "--vision_dp", str(config.get("vision_dp", 1)),
         "--vision_tp", str(config.get("vision_tp", 1)),
         "--vision_pp", str(config.get("vision_pp", 1)),
         "--vision_ep", str(config.get("vision_ep", 1)),
         "--text_dp", str(config.get("text_dp", 1)),
         "--text_tp", str(config.get("text_tp", 1)),
         "--text_pp", str(config.get("text_pp", 1)),
         "--text_ep", str(config.get("text_ep", 1)),
         "--output_dir", str(output_dir),
         "--output_name", f"{output_prefix}.%d.et",
         "--mixed_precision", str(bool(config.get("mixed_precision", False))).lower(),
  ]
  ```
  - model_type: use `model_params.get("model_type")` (already present in registry), pass as `--model_type`
  - vision_image_size: parse from `config["image_resolution"]` (format "WxH", take max(width, height))
  - vision_patch_size: parse from `config["tile_size"]` (format "WxH", take max(width, height))
  - weight_sharded, activation_recompute, chakra_schema_version, print_gpu_vram, include_backward: read from config and append as `--weight_sharded`, etc. Only append if the value is truthy (or for string fields, if non-empty).
  - Do NOT pass any model structure parameters like --dmodel, --num_stacks, --head, --kvhead, --vision_hidden_size, etc.
- `_map_metrics`: Remove all legacy field assignments (data_tx_latency_s=0.0, inter_stage_latency_s=0.0, etc.). Only construct SimulationMetrics with the 7 retained fields.
- `run_astra_simulation` return dict: Remove `"unsupported_fields": list(UNSUPPORTED_FIELDS)` key entirely.

### AC-5: No regressions
- After all edits, run `python3 -m py_compile scsp/*.py` and verify no syntax errors.
- Run `python3 run_scsp.py --help` and `python3 run_web.py --help` successfully.
- Run `python3 -c "from scsp.web_api import app; print('OK')"` successfully.

## FILES TO MODIFY (in order)
1. `scsp/models.py`
2. `scsp/config.py`
3. `scsp/astra_sim_bridge.py`
4. `web/index.html`
5. `README-astra-integration.md`

## DO NOT MODIFY
- `stage/` directory
- `astra-sim/` directory
- `configs/model_registry.json` (read-only for model_type lookup)

## CONTEXT: Current file contents

### scsp/models.py (CURRENT)
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationMetrics:
    total_samples: int
    total_latency_s: float
    data_tx_latency_s: float
    inter_stage_latency_s: float
    stage1_compute_latency_s: float
    stage2_compute_latency_s: float
    effective_compute_flops: float
    effective_compute_pflops: float
    ideal_peak_pflops: float
    compute_utilization: float
    bottleneck_stage: str
    decode_latency_s_per_token: float = 0.0
    decode_total_latency_s: float = 0.0
    decode_compute_latency_s_per_token: float = 0.0
    decode_memory_latency_s_per_token: float = 0.0
    decode_effective_compute_pflops: float = 0.0
    decode_bottleneck: str = "unknown"
    prefill_compute_time_s: float = 0.0
    prefill_memory_time_s: float = 0.0
    prefill_time_s: float = 0.0
    prefill_bottleneck: str = "unknown"
    decode_energy_efficiency_tokens_per_j: float = 0.0
    total_inference_time_s: float = 0.0
    prefill_peak_memory_bytes: float = 0.0
    prefill_peak_memory_gb: float = 0.0
    single_star_peak_memory_bytes: float = 0.0
    single_star_peak_memory_gb: float = 0.0
    prefill_weight_memory_bytes: float = 0.0
    prefill_kv_memory_bytes: float = 0.0
    prefill_activation_peak_memory_bytes: float = 0.0
    prefill_workspace_memory_bytes: float = 0.0
```

### scsp/config.py (CURRENT - partial, key sections)
V1SimulationConfig currently has: num_images, decode_tokens, llm_num_hidden_layers, llm_hidden_size, llm_num_attention_heads, llm_num_key_value_heads, vision_patch_size, vision_spatial_merge_size, mixed_precision, dp, tp, pp, local_mem_bw_gbps.
normalize_raw_config sets defaults for num_images, llm_*, vision_*, mixed_precision, dp, tp, pp, local_mem_bw_gbps.
validate_raw_config validates llm_num_hidden_layers, llm_hidden_size, llm_num_attention_heads, llm_num_key_value_heads.
build_simulation_config passes all these to V1SimulationConfig constructor.
dump_config_dict dumps all fields.

### scsp/astra_sim_bridge.py (CURRENT - partial, key sections)
UNSUPPORTED_FIELDS = [ ... 24 fields ... ]
_run_stage builds cmd with --model_name, --dp, --tp, --pp, --output_dir, --output_name, --mixed_precision, --model_type (optional).
_map_metrics constructs SimulationMetrics with ALL legacy fields set to 0.0/"unknown".
run_astra_simulation returns dict with "unsupported_fields": list(UNSUPPORTED_FIELDS).

### web/index.html (CURRENT - partial, key sections)
mockRows has 5 entries with legacy fields: data_tx_latency_s, inter_stage_latency_s, stage1_compute_latency_s, stage2_compute_latency_s.
Multiple catch blocks silently fall back to mockRows (bandwidth_sweep, compute_sweep fallback, inter_sat_distance fallback, overview fallback).
init() health check catch shows "API 状态：不可用（已启用 mock 展示）" unconditionally.

### README-astra-integration.md (CURRENT)
Has "## Unsupported Metrics" section listing all 24 legacy fields. Needs new "## Legacy Metrics Reference" archive section.

### configs/model_registry.json (READ-ONLY)
Registry entries have structure.model_type already (e.g., "vlm", "dense").

## OUTPUT
Write your changes directly to the files. Then write a summary to:
`/share/guolidong-nfs/SeeSpace/SCSP_v1/tasks/scsp-v1-astra-integration-cleanup/impl/round-0-summary.md`

The summary must list:
- Which files were modified
- Which AC items were implemented (only say "Implemented", never "Verified")
- Any blockers or issues encountered
- The exact git diff commands to run to verify your work
