You are continuing a PBR Coding build round. The previous round implemented the main changes but the IMPL Reviewer found residual issues in web/index.html. Fix ONLY the issues listed below. Do NOT touch any other files.

## CRITICAL RULES
1. Only implement; do NOT review or judge your own work.
2. Do NOT add AC-/Milestone/Step/Phase markers into production code.
3. Do NOT delete any files; only edit existing ones.
4. Do NOT modify stage/ or astra-sim/ directories.

## ISSUES TO FIX (all in web/index.html only)

### Issue 1: `getRows()` — missing isDev guard (AC-3)
Location: around line 1998
Current:
```javascript
function getRows() {
  if (!state.overviewResultsDisplayed) return [];
  if (state.bandwidthSensitivityRows.length) return state.bandwidthSensitivityRows;
  return state.sweepRows.length ? state.sweepRows : mockRows;
}
```
Change to:
```javascript
function getRows() {
  if (!state.overviewResultsDisplayed) return [];
  if (state.bandwidthSensitivityRows.length) return state.bandwidthSensitivityRows;
  if (state.sweepRows.length) return state.sweepRows;
  return isDev ? mockRows : [];
}
```

### Issue 2: `normalizeExpCurveRow` — residual old field references (AC-1, AC-2)
Location: around line 2868-2888
Current:
```javascript
function normalizeExpCurveRow(row, decodeTokens) {
  if (
    Number.isFinite(Number(row.prefill_latency_ms)) &&
    Number.isFinite(Number(row.decode_throughput_tokens_per_s))
  ) {
    return row;
  }
  const hasEngine =
    Number.isFinite(Number(row.prefill_time_s)) && Number.isFinite(Number(row.decode_latency_s_per_token));
  const q = hasEngine
    ? extractFourQuantitiesFromMetrics(row, decodeTokens)
    : estimateFourFromTotalLatencyS(Number(row.total_latency_s), decodeTokens);
  return {
    ...row,
    prefill_latency_ms: q.prefillMs,
    decode_throughput_tokens_per_s: q.decodeTps
  };
}
```
Change to:
```javascript
function normalizeExpCurveRow(row, decodeTokens) {
  if (
    Number.isFinite(Number(row.prefill_latency_ms)) &&
    Number.isFinite(Number(row.decode_throughput_tokens_per_s))
  ) {
    return row;
  }
  const q = estimateFourFromTotalLatencyS(Number(row.total_latency_s), decodeTokens);
  return {
    ...row,
    prefill_latency_ms: q.prefillMs,
    decode_throughput_tokens_per_s: q.decodeTps
  };
}
```

### Issue 3: `extractFourQuantitiesFromMetrics` — remove dead code (AC-1)
Location: around line 2831-2845
This entire function is now dead code because `hasEngine` is always false after backend field removal. Remove the function definition entirely.

### Issue 4: model_scale catch block — residual old field reference (AC-1)
Location: around line 3008
Current:
```javascript
const v = Number(m?.single_star_peak_memory_gb ?? m?.prefill_peak_memory_gb);
```
Change to:
```javascript
const v = Number(m?.single_star_peak_memory_gb);
```
Wait — these fields don't exist in astra-sim output. The model_scale experiment is a special case that measures peak memory per model scale. Since astra-sim does not currently produce memory metrics, this value will always be NaN from real data. We should keep the fallback behavior (dev-only synthetic value) but remove references to fields that no longer exist.

So change to:
```javascript
const v = Number(m?.single_star_peak_memory_gb);
if (Number.isFinite(v)) memGb = v;
```
Keep the rest of the fallback logic (including the isDev check for synthetic value) as-is.

## AFTER FIXING
Run these verification commands and report the results:
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
grep -n "prefill_time_s\|decode_latency_s_per_token\|decode_total_latency_s\|decode_energy_efficiency_tokens_per_j\|prefill_peak_memory_gb" web/index.html
# The ONLY matches should be inside the MODEL_REGISTRY_BASELINE JSON string (line ~1298), nowhere else.
grep -n "extractFourQuantitiesFromMetrics" web/index.html
# Should return no matches (function removed)
grep -n "getRows" web/index.html
python3 -m py_compile scsp/*.py
python3 run_scsp.py --help
python3 run_web.py --help
/share/guolidong-nfs/.venv/seespace/bin/python3 -c "from scsp.web_api import app; print('OK')"
```
