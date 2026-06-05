You are continuing a PBR Coding build round. The previous round already modified scsp/models.py, scsp/config.py, scsp/astra_sim_bridge.py, and partially modified web/index.html. Your job is to finish the remaining work described below.

## CRITICAL RULES
1. Only implement; do NOT review or judge your own work.
2. Write a summary to tasks/scsp-v1-astra-integration-cleanup/impl/round-0-summary.md when done.
3. Mark AC statuses as "Implemented" only.
4. Do NOT add AC-/Milestone/Step/Phase markers into production code.
5. Do NOT delete any files; only edit existing ones.
6. Do NOT modify stage/ or astra-sim/ directories.

## REMAINING WORK

### 1. web/index.html — catch block fallback logic (AC-3)

The `isDev` constant and `toast()` function have already been added. Now update ALL catch blocks that silently fall back to `mockRows` or synthetic data:

**A. bandwidth_sweep catch block (around line 2960):**
Current code:
```javascript
} catch {
  rows = mockRows.filter((r) => bws.includes(r.link_bandwidth_gbps));
  if (!rows.length) rows = mockRows.slice();
}
```
Change to:
```javascript
} catch {
  toast("后端仿真接口调用失败，请检查服务状态", { type: "error" });
  if (isDev) {
    rows = mockRows.filter((r) => bws.includes(r.link_bandwidth_gbps));
    if (!rows.length) rows = mockRows.slice();
  } else {
    rows = [];
  }
}
```

**B. compute_sweep catch block (around line 2980):**
Current code:
```javascript
} catch {
  /* 单点失败则跳过，后续用示意数据补齐 */
}
```
Keep this as-is (it does not use mockRows, just skips the failed point).
But the fallback block AFTER the loop:
```javascript
if (!rows.length) {
  const baseP = Number(state.config.big_star_peak_pflops_single) || 10;
  plist.forEach((p) => {
    rows.push({
      single_star_pflops: p,
      total_latency_s: (mockRows[2].total_latency_s * baseP) / Math.max(p, 0.1)
    });
  });
}
```
Change to:
```javascript
if (!rows.length) {
  if (isDev) {
    const baseP = Number(state.config.big_star_peak_pflops_single) || 10;
    plist.forEach((p) => {
      rows.push({
        single_star_pflops: p,
        total_latency_s: (mockRows[2].total_latency_s * baseP) / Math.max(p, 0.1)
      });
    });
  }
}
```

**C. inter_sat_distance catch block (around line 3005):**
Current code:
```javascript
} catch {
  m = null;
}
if (m && Number.isFinite(Number(m.total_latency_s))) {
  rows.push({ inter_sat_distance_km: dist, ...m });
} else {
  rows.push({ inter_sat_distance_km: dist, total_latency_s: 88 + dist * 0.42 });
}
```
Change to:
```javascript
} catch {
  toast("后端仿真接口调用失败，请检查服务状态", { type: "error" });
  m = null;
}
if (m && Number.isFinite(Number(m.total_latency_s))) {
  rows.push({ inter_sat_distance_km: dist, ...m });
} else if (isDev) {
  rows.push({ inter_sat_distance_km: dist, total_latency_s: 88 + dist * 0.42 });
}
```

**D. overview fallback block (around line 3600):**
Current code:
```javascript
} catch {
  state.overviewResultsDisplayed = true;
  readConfigFromInputs();
  const sbw = state.config.link_bandwidth_gbps_single;
  const sp = state.config.big_star_peak_pflops_single;
  state.kpiOverviewRow = mockRows.find((r) => r.link_bandwidth_gbps === sbw) || mockRows[Math.min(2, mockRows.length - 1)];
  state.sweepRows = mockRows;
  state.bandwidthSensitivityRows = mockRows;
  state.computeSensitivityRows = [];
  showResult({ warning: "后端接口不可用，已回退 mock 数据。" });
  renderAll();
}
```
Change to:
```javascript
} catch {
  toast("后端仿真接口调用失败，请检查服务状态", { type: "error" });
  state.overviewResultsDisplayed = true;
  readConfigFromInputs();
  if (isDev) {
    const sbw = state.config.link_bandwidth_gbps_single;
    state.kpiOverviewRow = mockRows.find((r) => r.link_bandwidth_gbps === sbw) || mockRows[Math.min(2, mockRows.length - 1)];
    state.sweepRows = mockRows;
    state.bandwidthSensitivityRows = mockRows;
    state.computeSensitivityRows = [];
    showResult({ warning: "后端接口不可用，已回退 mock 数据。" });
  } else {
    showResult({ error: "后端接口不可用" });
  }
  renderAll();
}
```

**E. init() health check catch block (around line 3635):**
Current code:
```javascript
} catch {
  byId("healthText").textContent = "API 状态：不可用（已启用 mock 展示）";
}
```
Change to:
```javascript
} catch {
  if (isDev) {
    byId("healthText").textContent = "API 状态：不可用（已启用 mock 展示）";
  } else {
    byId("healthText").textContent = "API 状态：不可用";
  }
}
```

**F. model_scale catch block (around line 2980 in model_scale branch):**
Current code:
```javascript
} catch {
  memGb = NaN;
}
if (!Number.isFinite(memGb)) memGb = 6 + mi * 5;
```
Change to:
```javascript
} catch {
  toast("后端仿真接口调用失败，请检查服务状态", { type: "error" });
  memGb = NaN;
}
if (!Number.isFinite(memGb)) {
  if (isDev) memGb = 6 + mi * 5;
}
```

### 2. README-astra-integration.md — Legacy Metrics Reference (AC-1)

Add a new top-level section at the end of the file:

```markdown
## Legacy Metrics Reference

The following fields were previously part of `SimulationMetrics` but have been removed from the codebase because they are not produced by ASTRA-sim. They are preserved here for reference in future iterations that may reintroduce phase-aware simulation or analytical decomposition.

- `data_tx_latency_s` — Data transmission latency between pipeline stages.
- `inter_stage_latency_s` — Inter-stage communication latency.
- `stage1_compute_latency_s` — Compute latency of the first pipeline stage.
- `stage2_compute_latency_s` — Compute latency of the second pipeline stage.
- `decode_latency_s_per_token` — Per-token decode latency.
- `decode_total_latency_s` — Total decode latency across all tokens.
- `decode_compute_latency_s_per_token` — Per-token decode compute latency.
- `decode_memory_latency_s_per_token` — Per-token decode memory latency.
- `decode_effective_compute_pflops` — Decode-phase effective compute throughput.
- `decode_bottleneck` — Bottleneck identifier for the decode phase.
- `prefill_compute_time_s` — Prefill compute time.
- `prefill_memory_time_s` — Prefill memory time.
- `prefill_time_s` — Total prefill time.
- `prefill_bottleneck` — Bottleneck identifier for the prefill phase.
- `decode_energy_efficiency_tokens_per_j` — Decode energy efficiency in tokens per joule.
- `total_inference_time_s` — Total end-to-end inference time.
- `prefill_peak_memory_bytes` / `prefill_peak_memory_gb` — Peak memory during prefill.
- `single_star_peak_memory_bytes` / `single_star_peak_memory_gb` — Peak memory per star.
- `prefill_weight_memory_bytes` — Weight memory during prefill.
- `prefill_kv_memory_bytes` — KV-cache memory during prefill.
- `prefill_activation_peak_memory_bytes` — Activation peak memory during prefill.
- `prefill_workspace_memory_bytes` — Workspace memory during prefill.
```

Then update the existing "## Unsupported Metrics" section to reference the new archive section instead of listing all fields inline:

```markdown
## Unsupported Metrics

ASTRA-sim currently runs the full Chakra execution graph as an event-driven simulation. It reports aggregate wall, GPU, communication, and overlap times, but it does not distinguish SCSP's old analytical prefill/decode pipeline stages. The legacy metrics that were previously returned as placeholders are documented in [Legacy Metrics Reference](#legacy-metrics-reference) above.

Extending these metrics requires either splitting or annotating the stage-generated ET by phase, or adding new phase-aware counters inside ASTRA-sim.
```

### 3. Write summary file

Write `/share/guolidong-nfs/SeeSpace/SCSP_v1/tasks/scsp-v1-astra-integration-cleanup/impl/round-0-summary.md` with:

```markdown
# Round 0 Implementation Summary

## Files Modified
1. scsp/models.py
2. scsp/config.py
3. scsp/astra_sim_bridge.py
4. web/index.html
5. README-astra-integration.md

## AC Implementation Status
- AC-1: Implemented — legacy fields removed from models.py and astra_sim_bridge.py; archived in README.
- AC-2: Implemented — frontend KPI uses astra fields; bottleneck_stage derived from gpu_time_ns/comm_time_ns.
- AC-3: Implemented — mock fallback with explicit toast and dev-only guard.
- AC-4: Implemented — config aligned with stage CLI; direct parameter passing; model_type from registry.
- AC-5: Implemented — py_compile passes; run_scsp.py --help OK; run_web.py --help OK; web_api imports OK.

## Blockers/Issues
None.

## Verification Commands
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
git diff --stat
python3 -m py_compile scsp/*.py
python3 run_scsp.py --help
python3 run_web.py --help
/share/guolidong-nfs/.venv/seespace/bin/python3 -c "from scsp.web_api import app; print('OK')"
```
```
