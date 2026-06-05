# SCSP ASTRA-sim Integration

## Environment Setup

Use the shared `seespace` Python environment:

```bash
source /share/guolidong-nfs/.venv/seespace/bin/activate
python3 -m pip install -r stage/requirements.txt
python3 -m pip install graphviz pytest
```

The current bridge calls `/share/guolidong-nfs/.venv/seespace/bin/python3` when it invokes `stage/main.py`.

## Build ASTRA-sim

Build the analytical backend from the repository root:

```bash
cd astra-sim/build/astra_analytical
./build.sh
```

The SCSP bridge expects this executable:

```text
astra-sim/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Aware
```

## SCSP Config Fields

`mixed_precision` controls the ET element-size mapping written to the ASTRA-sim system config. `true` maps `et-data-element-size` to `2` bytes, while `false` maps it to `4` bytes.

`dp`, `tp`, and `pp` are passed directly to `stage/main.py` as data, tensor, and pipeline parallelism. Their product is used as `npus_count` in the ASTRA-sim network config.

`local_mem_bw_gbps` is written to ASTRA-sim `local-mem-bw`.

`big_star_peak_pflops` is converted to ASTRA-sim `peak-perf` in TFLOPS by multiplying by `1000`.

`link_bandwidth_gbps` is converted to the analytical network YAML `bandwidth` value in GB/s by dividing by `8`.

## Unsupported Metrics

ASTRA-sim currently runs the full Chakra execution graph as an event-driven simulation. It reports aggregate wall, GPU, communication, and overlap times, but it does not distinguish SCSP's old analytical prefill/decode pipeline stages. The legacy metrics that were previously returned as placeholders are documented in [Legacy Metrics Reference](#legacy-metrics-reference) above.

Extending these metrics requires either splitting or annotating the stage-generated ET by phase, or adding new phase-aware counters inside ASTRA-sim.

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
