# Round 0 REVIEW Reviewer Report

## Diff Summary
- README-astra-integration.md | 54 +++++-----
- scsp/astra_sim_bridge.py    | 106 +++++++++++---------
- scsp/config.py              | 112 ++++++++++++---------
- scsp/models.py              | 24 -----
- web/index.html              | 240 ++++++++++++++++++--------------------------
- Total: 257 insertions(+), 279 deletions(-)

## AC Verification

### AC-1: Legacy simulation fields removed from backend; archived in README
- **PASS** — `SimulationMetrics` in scsp/models.py now contains only 7 fields (total_samples, total_latency_s, effective_compute_flops, effective_compute_pflops, ideal_peak_pflops, compute_utilization, bottleneck_stage).
- **PASS** — `UNSUPPORTED_FIELDS` list and `unsupported_fields` key removed from scsp/astra_sim_bridge.py.
- **PASS** — Legacy Metrics Reference section added to README-astra-integration.md with all 20+ archived fields.
- **PASS** — No residual old field references in web/index.html outside MODEL_REGISTRY_BASELINE JSON.

### AC-2: Frontend adapts to astra-sim real results
- **PASS** — Frontend KPI cards (`metricsResponseToKpiRow`) now map only astra fields.
- **PASS** — `bottleneck_stage` derived from `gpu_time_ns` vs `comm_time_ns` ratio in `_map_metrics`.
- **PASS** — Decomposition panel (`renderDonut`) switched to "ASTRA GPU时间" vs "ASTRA通信/等待时间".
- **PASS** — `extractFourQuantitiesFromMetrics` dead code removed.

### AC-3: Mock fallback explicit with toast + dev-only guard
- **PASS** — `toast()` function added.
- **PASS** — `isDev` constant added (`localhost || 127.0.0.1`).
- **PASS** — All catch blocks in sweep/overview/health check show toast error.
- **PASS** — `getRows()` fallback to mockRows protected by `isDev`.
- **PASS** — model_scale, inter_sat_distance, compute_sweep fallback all gated by `isDev`.

### AC-4: SCSP config aligned with stage CLI params
- **PASS** — V1SimulationConfig includes batch, sp, ep, vision_dp/tp/pp/ep, text_dp/tp/pp/ep, weight_sharded, activation_recompute, chakra_schema_version, print_gpu_vram, include_backward.
- **PASS** — `_run_stage()` passes all new fields directly as CLI args (--batch, --sp, --ep, --vision_dp, etc.).
- **PASS** — `model_type` auto-inferred from registry (`model_params.get("model_type")`).
- **PASS** — `vision_image_size` and `vision_patch_size` parsed from image_resolution and tile_size strings via `_max_dimension`.
- **PASS** — `total_samples` set from `config.get("batch", 1)` instead of old `num_images`.

### AC-5: Regression tests pass
- **PASS** — `python3 -m py_compile scsp/*.py` passes.
- **PASS** — `python3 run_scsp.py --help` works.
- **PASS** — `python3 run_web.py --help` works.
- **PASS** — `from scsp.web_api import app` imports OK in seespace venv.

## Issues / Risks
None identified.

## Decision
**APPROVED** — All ACs pass. No additional fix rounds needed.
