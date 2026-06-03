from __future__ import annotations

from numbers import Integral
from typing import Any, Dict, List

from .astra_sim_bridge import run_astra_simulation
from .config import normalize_raw_config


def validate_bandwidth_input(value: Any) -> None:
    if isinstance(value, Integral):
        if value <= 0:
            raise ValueError("link_bandwidth_gbps must be a positive integer")
        return

    if isinstance(value, list):
        if not value:
            raise ValueError("link_bandwidth_gbps list cannot be empty")
        for item in value:
            if not isinstance(item, Integral):
                raise TypeError("link_bandwidth_gbps list items must be integers")
            if item <= 0:
                raise ValueError("link_bandwidth_gbps list items must be positive integers")
        return

    raise TypeError("link_bandwidth_gbps must be an integer or a list of integers")


def run_simulation(raw_config: Dict[str, Any], bandwidth_gbps: int | None = None) -> Dict[str, Any]:
    return run_astra_simulation(raw_config, bandwidth_gbps=bandwidth_gbps)


def _detect_performance_knee(rows: List[Dict[str, Any]]) -> tuple[float | None, str]:
    if len(rows) < 2:
        return None, "insufficient data"
    previous = float(rows[0].get("total_latency_s", 0.0) or 0.0)
    for row in rows[1:]:
        current = float(row.get("total_latency_s", 0.0) or 0.0)
        if previous <= 0:
            previous = current
            continue
        improvement = (previous - current) / previous
        if improvement < 0.05:
            return float(row["link_bandwidth_gbps"]), "latency improvement below 5%"
        previous = current
    return float(rows[-1]["link_bandwidth_gbps"]), "no clear knee detected"


def run_sweep(raw_config: Dict[str, Any], bandwidths_gbps: List[int] | None = None) -> Dict[str, Any]:
    normalized = normalize_raw_config(raw_config)
    if bandwidths_gbps is None:
        raw_bandwidths = normalized["link_bandwidth_gbps"]
        if isinstance(raw_bandwidths, list):
            bandwidths_gbps = [int(v) for v in raw_bandwidths]
        else:
            bandwidths_gbps = [int(raw_bandwidths)]
    rows: List[Dict[str, Any]] = []
    unsupported_fields: List[str] = []
    artifacts: List[Dict[str, Any]] = []
    for bandwidth in bandwidths_gbps:
        result = run_astra_simulation(normalized, bandwidth_gbps=bandwidth)
        metrics = dict(result["metrics"])
        metrics["link_bandwidth_gbps"] = int(bandwidth)
        rows.append(metrics)
        if not unsupported_fields:
            unsupported_fields = list(result.get("unsupported_fields", []))
        if "artifacts" in result:
            artifacts.append(result["artifacts"])
    knee_bw, knee_reason = _detect_performance_knee(rows)
    return {
        "mode": "sweep",
        "knee_bandwidth_gbps": knee_bw,
        "knee_reason": knee_reason,
        "rows": rows,
        "unsupported_fields": unsupported_fields,
        "artifacts": artifacts,
    }
