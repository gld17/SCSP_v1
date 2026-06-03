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
