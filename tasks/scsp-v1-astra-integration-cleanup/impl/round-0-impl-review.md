# Round 0 IMPL Review

## Alignment Check

| AC | Status | Notes |
|---|---|---|
| AC-1 | Implemented with issues | Legacy fields removed from models.py and astra_sim_bridge.py; Legacy Metrics Reference added to README. But web/index.html still contains residual references to old fields in `extractFourQuantitiesFromMetrics` and `normalizeExpCurveRow`. |
| AC-2 | Implemented with issues | KPI rendering updated to astra fields; bottleneck_stage derivation correct. But `normalizeExpCurveRow` still references removed fields (`prefill_time_s`, `decode_latency_s_per_token`). |
| AC-3 | Implemented with issues | Toast + isDev guard added to catch blocks. But `getRows()` fallback to `mockRows` is not protected by `isDev` — in non-dev mode after overview failure, it still returns mockRows. |
| AC-4 | Implemented | Config fields aligned with stage CLI; direct parameter passing; model_type from registry; vision_image_size/patch_size parsed from resolution strings. |
| AC-5 | Implemented | py_compile passes; run_scsp.py --help OK; run_web.py --help OK; web_api imports OK in seespace venv. |

## Issues Found

1. **web/index.html `getRows()` — missing isDev guard (AC-3)**
   Location: line ~1998
   ```javascript
   return state.sweepRows.length ? state.sweepRows : mockRows;
   ```
   When overview API fails in non-dev mode, `state.sweepRows` is empty, but `getRows()` still falls back to `mockRows`. This violates the dev-only mock rule.

2. **web/index.html `normalizeExpCurveRow` — residual old field references (AC-1, AC-2)**
   Location: lines ~2875-2878
   ```javascript
   const hasEngine =
     Number.isFinite(Number(row.prefill_time_s)) && Number.isFinite(Number(row.decode_latency_s_per_token));
   ```
   These fields no longer exist in backend responses. The `hasEngine` branch is effectively dead code but should be cleaned up.

3. **web/index.html `extractFourQuantitiesFromMetrics` — residual old field references (AC-1)**
   Location: lines ~2831-2845
   This function references `prefill_time_s`, `decode_latency_s_per_token`, `decode_total_latency_s`, `decode_energy_efficiency_tokens_per_j`. Since `hasEngine` is always false now, this code is unreachable, but it should be removed to prevent future confusion.

4. **web/index.html model_scale — residual old field references (AC-1)**
   Location: line ~3008
   ```javascript
   const v = Number(m?.single_star_peak_memory_gb ?? m?.prefill_peak_memory_gb);
   ```
   These fields have been removed from backend. In non-dev mode this always yields NaN.

## Decision

**Requires fix round.** Builder must clean up residual old field references in web/index.html and add isDev guard to `getRows()`.

## Verification Commands After Fix
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
grep -n "prefill_time_s\|decode_latency_s_per_token\|decode_total_latency_s\|decode_energy_efficiency_tokens_per_j\|single_star_peak_memory_gb\|prefill_peak_memory_gb" web/index.html
# Should return only matches inside MODEL_REGISTRY_BASELINE JSON (expected)
grep -n "getRows" web/index.html
python3 -m py_compile scsp/*.py
python3 run_scsp.py --help
python3 run_web.py --help
/share/guolidong-nfs/.venv/seespace/bin/python3 -c "from scsp.web_api import app; print('OK')"
```
