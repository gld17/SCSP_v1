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

ASTRA-sim currently runs the full Chakra execution graph as an event-driven simulation. It reports aggregate wall, GPU, communication, and overlap times, but it does not distinguish SCSP's old analytical prefill/decode pipeline stages. These `SimulationMetrics` fields are therefore unsupported and returned as placeholder values, with field names listed in `unsupported_fields`:

- `data_tx_latency_s`
- `inter_stage_latency_s`
- `stage1_compute_latency_s`
- `stage2_compute_latency_s`
- `decode_latency_s_per_token`
- `decode_total_latency_s`
- `decode_compute_latency_s_per_token`
- `decode_memory_latency_s_per_token`
- `decode_effective_compute_pflops`
- `decode_bottleneck`
- `prefill_compute_time_s`
- `prefill_memory_time_s`
- `prefill_time_s`
- `prefill_bottleneck`
- `decode_energy_efficiency_tokens_per_j`
- `total_inference_time_s`
- `prefill_peak_memory_bytes`
- `prefill_peak_memory_gb`
- `single_star_peak_memory_bytes`
- `single_star_peak_memory_gb`
- `prefill_weight_memory_bytes`
- `prefill_kv_memory_bytes`
- `prefill_activation_peak_memory_bytes`
- `prefill_workspace_memory_bytes`

Extending these metrics requires either splitting or annotating the stage-generated ET by phase, or adding new phase-aware counters inside ASTRA-sim.
