from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationMetrics:
    total_samples: int
    total_latency_s: float
    effective_compute_flops: float
    effective_compute_pflops: float
    ideal_peak_pflops: float
    compute_utilization: float
    bottleneck_stage: str
