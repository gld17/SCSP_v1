from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def plot_sweep_latency(rows: List[Dict[str, Any]], output_prefix: str, model_name: str) -> str:
    output_dir = Path(output_prefix)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / "sweep_latency_vs_bandwidth.png"

    sorted_rows = sorted(rows, key=lambda x: x["link_bandwidth_gbps"])
    x = [row["link_bandwidth_gbps"] for row in sorted_rows]
    y = [row["total_latency_s"] for row in sorted_rows]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 5))
    plt.plot(x, y, marker="o", linestyle="-", linewidth=2)
    plt.xlabel("Inter-satellite Link Bandwidth (Gbps)")
    plt.ylabel("Total Latency (s)")
    plt.title(model_name)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()
    return str(plot_path)
