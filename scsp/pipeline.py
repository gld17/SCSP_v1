from __future__ import annotations

from typing import Dict


def pipeline_makespan_seconds(
    samples: int, stage0_s: float, stage1_s: float, stage2_s: float, sync_overhead_ms: float
) -> Dict[str, float]:
    """
    3-stage pipelined schedule:
    - stage0: sensing star to big-star-1 transfer
    - stage1: compute on big-star-1 + stage1->stage2 transfer
    - stage2: compute on big-star-2
    """
    if samples <= 0:
        raise ValueError("samples must be positive")

    sync_overhead_s = max(sync_overhead_ms, 0.0) / 1000.0
    stage0_eff = stage0_s + sync_overhead_s
    stage1_eff = stage1_s + sync_overhead_s
    stage2_eff = stage2_s + sync_overhead_s

    warmup = stage0_eff + stage1_eff + stage2_eff
    cycle = max(stage0_eff, stage1_eff, stage2_eff)
    makespan = warmup + (samples - 1) * cycle

    if cycle == stage0_eff:
        bottleneck = "remote_to_bigstar1_transfer"
    elif cycle == stage1_eff:
        bottleneck = "bigstar1_stage"
    else:
        bottleneck = "bigstar2_stage"

    return {
        "makespan_s": makespan,
        "cycle_s": cycle,
        "bottleneck": bottleneck,
        "stage0_eff_s": stage0_eff,
        "stage1_eff_s": stage1_eff,
        "stage2_eff_s": stage2_eff,
    }
