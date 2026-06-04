from __future__ import annotations

import csv
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .engine import run_simulation, run_sweep, validate_bandwidth_input
from .io_utils import write_json

ENGINE_VERSION = "v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExperimentRecord:
    experiment_id: str
    experiment_name: str
    template_name: Optional[str]
    mode: Literal["single", "sweep"]
    status: Literal["success", "failed"]
    created_at: str
    finished_at: str
    engine_version: str
    input_config: Dict[str, Any]
    output_files: List[str]
    result_summary: Dict[str, Any]
    error_message: Optional[str] = None


class JsonlExperimentStore:
    def __init__(self, store_path: str | Path) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text("", encoding="utf-8")

    def append(self, record: ExperimentRecord) -> None:
        with self.store_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def list_records(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        with self.store_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def get(self, experiment_id: str) -> Dict[str, Any]:
        for record in self.list_records():
            if record["experiment_id"] == experiment_id:
                return record
        raise KeyError(f"Experiment not found: {experiment_id}")


def apply_experiment_template(raw_config: Dict[str, Any], template_name: str | None) -> Dict[str, Any]:
    config = dict(raw_config)
    if template_name is None:
        return config
    if template_name == "single_point":
        bw = config.get("link_bandwidth_gbps_single", config.get("link_bandwidth_gbps", 100))
        if isinstance(bw, list):
            config["link_bandwidth_gbps"] = int(bw[0])
        else:
            config["link_bandwidth_gbps"] = int(bw)
        return config
    if template_name == "bandwidth_sensitivity":
        bw = config.get(
            "link_bandwidth_gbps_sweep",
            config.get("link_bandwidth_gbps", [10, 50, 100, 200, 400]),
        )
        if isinstance(bw, int):
            config["link_bandwidth_gbps"] = [bw]
        else:
            config["link_bandwidth_gbps"] = [int(v) for v in bw]
        return config
    raise ValueError(f"Unknown template_name: {template_name}")


def _write_rows_csv(path: str | Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _result_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload["mode"] == "single":
        metrics = payload["metrics"]
        return {
            "total_latency_s": metrics["total_latency_s"],
            "effective_compute_pflops": metrics["effective_compute_pflops"],
            "bottleneck_stage": metrics["bottleneck_stage"],
            "prefill_peak_memory_gb": metrics.get("prefill_peak_memory_gb"),
            "single_star_peak_memory_gb": metrics.get("single_star_peak_memory_gb"),
            "decode_latency_s_per_token": metrics.get("decode_latency_s_per_token"),
            "decode_total_latency_s": metrics.get("decode_total_latency_s"),
            "decode_effective_compute_pflops": metrics.get("decode_effective_compute_pflops"),
            "decode_energy_efficiency_tokens_per_j": metrics.get("decode_energy_efficiency_tokens_per_j"),
            "decode_bottleneck": metrics.get("decode_bottleneck"),
        }
    rows = payload["rows"]
    best_row = min(rows, key=lambda x: x["total_latency_s"]) if rows else {}
    return {
        "knee_bandwidth_gbps": payload.get("knee_bandwidth_gbps"),
        "best_latency_s": best_row.get("total_latency_s"),
        "best_bandwidth_gbps": best_row.get("link_bandwidth_gbps"),
        "best_decode_latency_s_per_token": best_row.get("decode_latency_s_per_token"),
        "best_decode_total_latency_s": best_row.get("decode_total_latency_s"),
        "best_decode_effective_compute_pflops": best_row.get("decode_effective_compute_pflops"),
        "best_decode_energy_efficiency_tokens_per_j": best_row.get("decode_energy_efficiency_tokens_per_j"),
        "best_decode_bottleneck": best_row.get("decode_bottleneck"),
    }


def run_experiment(
    raw_config: Dict[str, Any],
    output_root: str | Path,
    store_path: str | Path,
    experiment_name: str | None = None,
    template_name: str | None = None,
) -> Dict[str, Any]:
    exp_id = str(uuid.uuid4())
    created_at = _now_iso()
    output_dir = Path(output_root) / exp_id
    output_dir.mkdir(parents=True, exist_ok=True)

    config = apply_experiment_template(raw_config, template_name)
    validate_bandwidth_input(config["link_bandwidth_gbps"])
    input_path = output_dir / "input_config.json"
    write_json(input_path, config)

    try:
        bw = config["link_bandwidth_gbps"]
        if isinstance(bw, int):
            payload = run_simulation(config, bandwidth_gbps=bw)
            result_json = output_dir / "result_single.json"
            write_json(result_json, payload)
            output_files = [str(input_path), str(result_json)]
        else:
            payload = run_sweep(config, bandwidths_gbps=[int(v) for v in bw])
            result_json = output_dir / "result_sweep.json"
            result_csv = output_dir / "result_sweep.csv"
            write_json(result_json, payload)
            _write_rows_csv(result_csv, payload["rows"])
            output_files = [str(input_path), str(result_json), str(result_csv)]

        record = ExperimentRecord(
            experiment_id=exp_id,
            experiment_name=experiment_name or f"experiment-{exp_id[:8]}",
            template_name=template_name,
            mode=payload["mode"],
            status="success",
            created_at=created_at,
            finished_at=_now_iso(),
            engine_version=ENGINE_VERSION,
            input_config=config,
            output_files=output_files,
            result_summary=_result_summary(payload),
        )
    except Exception as exc:  # pragma: no cover - defensive path
        record = ExperimentRecord(
            experiment_id=exp_id,
            experiment_name=experiment_name or f"experiment-{exp_id[:8]}",
            template_name=template_name,
            mode="single",
            status="failed",
            created_at=created_at,
            finished_at=_now_iso(),
            engine_version=ENGINE_VERSION,
            input_config=config,
            output_files=[str(input_path)],
            result_summary={},
            error_message=str(exc),
        )
        JsonlExperimentStore(store_path).append(record)
        raise

    JsonlExperimentStore(store_path).append(record)
    return {
        "record": asdict(record),
        "payload": payload,
    }


def run_batch_experiments(
    raw_configs: List[Dict[str, Any]],
    output_root: str | Path,
    store_path: str | Path,
    template_name: str | None = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for idx, raw_config in enumerate(raw_configs):
        results.append(
            run_experiment(
                raw_config=raw_config,
                output_root=output_root,
                store_path=store_path,
                experiment_name=f"batch-{idx + 1}",
                template_name=template_name,
            )
        )
    return results


def compare_result_summary(base: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    shared_keys = sorted(set(base.keys()) & set(candidate.keys()))
    for key in shared_keys:
        b = base[key]
        c = candidate[key]
        if isinstance(b, (int, float)) and isinstance(c, (int, float)):
            if b != 0:
                diff[key] = {
                    "base": b,
                    "candidate": c,
                    "delta": c - b,
                    "relative_delta": (c - b) / b,
                }
            else:
                diff[key] = {"base": b, "candidate": c, "delta": c - b}
        elif b != c:
            diff[key] = {"base": b, "candidate": c}
    return diff


def reproduce_experiment(
    experiment_id: str,
    output_root: str | Path,
    store_path: str | Path,
) -> Dict[str, Any]:
    store = JsonlExperimentStore(store_path)
    old_record = store.get(experiment_id)
    rerun = run_experiment(
        raw_config=old_record["input_config"],
        output_root=output_root,
        store_path=store_path,
        experiment_name=f"reproduce-{experiment_id[:8]}",
        template_name=old_record.get("template_name"),
    )
    comparison = compare_result_summary(old_record.get("result_summary", {}), rerun["record"]["result_summary"])
    return {
        "source_experiment_id": experiment_id,
        "reproduced_experiment_id": rerun["record"]["experiment_id"],
        "comparison": comparison,
    }
