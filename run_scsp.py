#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from numbers import Integral
from pathlib import Path
from typing import Any, Dict, List

from scsp.engine import run_simulation, run_sweep, validate_bandwidth_input
from scsp.io_utils import write_csv, write_json
from scsp.visualization import plot_sweep_latency


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCSP v0 simulation (single or sweep)")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to JSON config file",
    )
    parser.add_argument(
        "--output-prefix",
        default="outputs/v1",
        help="Output directory. Single run writes '<dir>/single.json'; sweep writes '<dir>/sweep.json' and '<dir>/sweep.csv'",
    )
    return parser.parse_args()


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_single(raw: Dict[str, Any], bandwidth: int, output_prefix: str) -> Dict[str, Any]:
    payload = run_simulation(raw, bandwidth_gbps=bandwidth)
    output_path = f"{output_prefix}/single.json"
    write_json(output_path, payload)
    payload["output_file"] = output_path
    return payload


def _run_sweep(raw: Dict[str, Any], bandwidths: List[int], output_prefix: str) -> Dict[str, Any]:
    summary = run_sweep(raw, bandwidths_gbps=bandwidths)
    json_path = f"{output_prefix}/sweep.json"
    csv_path = f"{output_prefix}/sweep.csv"
    write_json(json_path, summary)
    write_csv(csv_path, summary["rows"])
    output_files = [json_path, csv_path]
    try:
        model_name = str(raw.get("model_name", Path(output_prefix).name))
        plot_path = plot_sweep_latency(summary["rows"], output_prefix, model_name=model_name)
        output_files.append(plot_path)
        summary["plot_file"] = plot_path
    except Exception as exc:
        summary["plot_error"] = f"failed to generate plot: {exc}"
    summary["output_files"] = output_files
    return summary


def main() -> None:
    args = parse_args()
    raw = _load_config(args.config)
    if "link_bandwidth_gbps" not in raw:
        raise KeyError("Missing required field: link_bandwidth_gbps")

    bandwidth = raw["link_bandwidth_gbps"]
    validate_bandwidth_input(bandwidth)

    if isinstance(bandwidth, Integral):
        result = _run_single(raw, int(bandwidth), args.output_prefix)
    else:
        result = _run_sweep(raw, [int(v) for v in bandwidth], args.output_prefix)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
