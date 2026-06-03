from __future__ import annotations

import json
import re
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from .config import normalize_raw_config
from .models import SimulationMetrics


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = REPO_ROOT / "stage"
MODEL_REGISTRY = REPO_ROOT / "configs" / "model_registry.json"
STAGE_MODEL_CONFIG_DIR = STAGE_DIR / "models" / "model_configs"
SEESPACE_PYTHON = Path("/share/guolidong-nfs/.venv/seespace/bin/python3")
ASTRA_SIM_BIN = (
    REPO_ROOT
    / "astra-sim"
    / "build"
    / "astra_analytical"
    / "build"
    / "bin"
    / "AstraSim_Analytical_Congestion_Aware"
)
RESULT_PREFIX = "ASTRA_SIM_RESULT:"


UNSUPPORTED_FIELDS = [
    "data_tx_latency_s",
    "inter_stage_latency_s",
    "stage1_compute_latency_s",
    "stage2_compute_latency_s",
    "decode_latency_s_per_token",
    "decode_total_latency_s",
    "decode_compute_latency_s_per_token",
    "decode_memory_latency_s_per_token",
    "decode_effective_compute_pflops",
    "decode_bottleneck",
    "prefill_compute_time_s",
    "prefill_memory_time_s",
    "prefill_time_s",
    "prefill_bottleneck",
    "decode_energy_efficiency_tokens_per_j",
    "total_inference_time_s",
    "prefill_peak_memory_bytes",
    "prefill_peak_memory_gb",
    "single_star_peak_memory_bytes",
    "single_star_peak_memory_gb",
    "prefill_weight_memory_bytes",
    "prefill_kv_memory_bytes",
    "prefill_activation_peak_memory_bytes",
    "prefill_workspace_memory_bytes",
]


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return slug.strip("._-") or "scsp_model"


def _load_model_registry() -> Dict[str, Any]:
    if not MODEL_REGISTRY.exists():
        raise FileNotFoundError(f"Model registry not found: {MODEL_REGISTRY}")
    return json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))


def _stage_model_name(model_name: str, registry: Dict[str, Any]) -> str:
    if (STAGE_MODEL_CONFIG_DIR / f"{model_name}.json").exists():
        return model_name

    entry = registry.get(model_name, {})
    registered_name = (
        entry.get("structure", {}).get("model_name")
        if isinstance(entry, dict)
        else None
    )
    candidates = [
        registered_name,
        model_name.lower().replace(".", "_").replace("-", "_"),
        model_name.lower().replace(".", "_"),
    ]
    for candidate in candidates:
        if candidate and (STAGE_MODEL_CONFIG_DIR / f"{candidate}.json").exists():
            return str(candidate)

    available = sorted(
        p.stem for p in STAGE_MODEL_CONFIG_DIR.glob("*.json") if p.name != "schema.json"
    )
    raise ValueError(
        f"No stage model config found for '{model_name}'. Available stage models: {available}"
    )


def _model_parameters(model_name: str, registry: Dict[str, Any]) -> Dict[str, Any]:
    entry = registry.get(model_name)
    if isinstance(entry, dict):
        structure = entry.get("structure")
        if isinstance(structure, dict):
            return structure
    return {}


def _positive_int(config: Dict[str, Any], key: str, default: int = 1) -> int:
    value = int(config.get(key, default) or default)
    if value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _run_stage(
    config: Dict[str, Any],
    model_params: Dict[str, Any],
    stage_model_name: str,
    output_dir: Path,
    output_prefix: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dp = _positive_int(config, "dp", 1)
    tp = _positive_int(config, "tp", 1)
    pp = _positive_int(config, "pp", 1)

    cmd = [
        str(SEESPACE_PYTHON),
        "main.py",
        "--model_name",
        stage_model_name,
        "--dp",
        str(dp),
        "--tp",
        str(tp),
        "--pp",
        str(pp),
        "--output_dir",
        str(output_dir),
        "--output_name",
        f"{output_prefix}.%d.et",
        "--mixed_precision",
        str(bool(config.get("mixed_precision", False))).lower(),
    ]

    model_type = model_params.get("model_type")
    if model_type:
        cmd.extend(["--model_type", str(model_type)])

    result = subprocess.run(
        cmd,
        cwd=STAGE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    workload_base = output_dir / output_prefix
    comm_group = output_dir / f"{output_prefix}.json"
    if not (output_dir / f"{output_prefix}.0.et").exists():
        raise RuntimeError(f"stage did not generate expected ET: {output_prefix}.0.et")
    if not comm_group.exists():
        raise RuntimeError(f"stage did not generate expected comm group: {comm_group}")
    return workload_base, comm_group


def _astra_network_topology(raw_topology: Any, npus_count: int) -> str:
    if not raw_topology:
        return "Switch" if npus_count <= 2 else "Ring"
    value = str(raw_topology)
    allowed = {"ring": "Ring", "switch": "Switch", "fullyconnected": "FullyConnected"}
    normalized = value.replace("_", "").replace("-", "").lower()
    return allowed.get(normalized, value)


def _write_astra_configs(
    config: Dict[str, Any],
    output_dir: Path,
    output_prefix: str,
) -> tuple[Path, Path, Path]:
    et_files = sorted(output_dir.glob(f"{output_prefix}.*.et"))
    if not et_files:
        raise RuntimeError(f"No ET files found for output prefix: {output_prefix}")
    npus_count = len(et_files)
    peak_perf_tflops = float(config.get("big_star_peak_pflops", 10.0)) * 1000.0
    local_mem_bw_gbps = float(config.get("local_mem_bw_gbps", 3350.0))
    et_data_element_size = 2 if bool(config.get("mixed_precision", False)) else 4

    system_config = {
        "scheduling-policy": "LIFO",
        "endpoint-delay": int(config.get("endpoint_delay", 1)),
        "active-chunks-per-dimension": int(config.get("active_chunks_per_dimension", 2)),
        "preferred-dataset-splits": int(config.get("preferred_dataset_splits", 4)),
        "all-reduce-implementation": ["ring"],
        "all-gather-implementation": ["ring"],
        "reduce-scatter-implementation": ["ring"],
        "all-to-all-implementation": ["ring"],
        "collective-optimization": str(config.get("collective_optimization", "localBWAware")),
        "local-mem-bw": local_mem_bw_gbps,
        "boost-mode": int(config.get("boost_mode", 0)),
        "track-local-mem": int(config.get("track_local_mem", 1)),
        "roofline-enabled": 1,
        "peak-perf": peak_perf_tflops,
        "et-data-element-size": et_data_element_size,
        "local-mem-trace-filename": str(output_dir / "mem_trace" / "local_memory_trace"),
    }

    link_bandwidth_gbps = float(config.get("link_bandwidth_gbps", 100.0))
    bandwidth_gbytes_per_s = float(config.get("astra_network_bandwidth_gbps", link_bandwidth_gbps / 8.0))
    latency_ns = float(config.get("astra_network_latency_ns", 500.0))
    topology = _astra_network_topology(
        config.get("network_topology", config.get("topology")),
        npus_count,
    )
    network_config = "\n".join(
        [
            "# Analytical Network Input File",
            f"topology: [ {topology} ]",
            f"npus_count: [ {npus_count} ]",
            f"bandwidth: [ {bandwidth_gbytes_per_s} ]",
            f"latency: [ {latency_ns} ]",
            "",
        ]
    )
    remote_memory_config = {"memory-type": "NO_MEMORY_EXPANSION"}

    system_path = output_dir / "system.json"
    network_path = output_dir / "network.yml"
    remote_memory_path = output_dir / "remote_memory.json"
    system_path.write_text(json.dumps(system_config, indent=2), encoding="utf-8")
    network_path.write_text(network_config, encoding="utf-8")
    remote_memory_path.write_text(json.dumps(remote_memory_config, indent=2), encoding="utf-8")
    return system_path, network_path, remote_memory_path


def _parse_astra_result(stdout: str) -> Dict[str, int]:
    for line in stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            payload = line[len(RESULT_PREFIX) :]
            parsed = json.loads(payload)
            return {
                "wall_time_ns": int(parsed.get("wall_time_ns", 0)),
                "gpu_time_ns": int(parsed.get("gpu_time_ns", 0)),
                "comm_time_ns": int(parsed.get("comm_time_ns", 0)),
                "comp_comm_overlap_ns": int(parsed.get("comp_comm_overlap_ns", 0)),
            }
    raise RuntimeError(f"ASTRA-sim output did not contain {RESULT_PREFIX}")


def _run_astra(
    workload_base: Path,
    comm_group: Path,
    system_path: Path,
    network_path: Path,
    remote_memory_path: Path,
) -> Dict[str, int]:
    cmd = [
        str(ASTRA_SIM_BIN),
        f"--workload-configuration={workload_base}",
        f"--comm-group-configuration={comm_group}",
        f"--system-configuration={system_path}",
        f"--network-configuration={network_path}",
        f"--remote-memory-configuration={remote_memory_path}",
    ]
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return _parse_astra_result(result.stdout)


def _map_metrics(config: Dict[str, Any], astra_result: Dict[str, int]) -> Dict[str, Any]:
    wall_time_ns = int(astra_result["wall_time_ns"])
    gpu_time_ns = int(astra_result["gpu_time_ns"])
    total_latency_s = wall_time_ns / 1e9
    ideal_peak_pflops = float(config.get("big_star_peak_pflops", 10.0))
    compute_utilization = (gpu_time_ns / wall_time_ns) if wall_time_ns else 0.0
    effective_compute_pflops = ideal_peak_pflops * compute_utilization

    metrics = SimulationMetrics(
        total_samples=int(config.get("num_images", 1)),
        total_latency_s=total_latency_s,
        data_tx_latency_s=0.0,
        inter_stage_latency_s=0.0,
        stage1_compute_latency_s=0.0,
        stage2_compute_latency_s=0.0,
        effective_compute_flops=effective_compute_pflops * 1e15,
        effective_compute_pflops=effective_compute_pflops,
        ideal_peak_pflops=ideal_peak_pflops,
        compute_utilization=compute_utilization,
        bottleneck_stage="unknown",
        total_inference_time_s=total_latency_s,
    )
    return asdict(metrics)


def run_astra_simulation(
    raw_config: Dict[str, Any],
    bandwidth_gbps: int | float | None = None,
) -> Dict[str, Any]:
    normalized = normalize_raw_config(raw_config)
    if bandwidth_gbps is not None:
        normalized["link_bandwidth_gbps"] = float(bandwidth_gbps)

    registry = _load_model_registry()
    model_name = str(normalized.get("model_name", "Qwen2.5-VL-7B"))
    model_params = _model_parameters(model_name, registry)
    stage_model_name = _stage_model_name(model_name, registry)

    run_id = uuid.uuid4().hex[:12]
    output_prefix = f"{_safe_slug(stage_model_name)}_{run_id}"
    output_dir = STAGE_DIR / "scsp_astra_bridge" / output_prefix

    workload_base, comm_group = _run_stage(
        normalized,
        model_params,
        stage_model_name,
        output_dir,
        output_prefix,
    )
    system_path, network_path, remote_memory_path = _write_astra_configs(
        normalized,
        output_dir,
        output_prefix,
    )
    astra_result = _run_astra(
        workload_base,
        comm_group,
        system_path,
        network_path,
        remote_memory_path,
    )

    metrics = _map_metrics(normalized, astra_result)
    return {
        "mode": "single",
        "config": normalized,
        "metrics": metrics,
        "unsupported_fields": list(UNSUPPORTED_FIELDS),
        "astra_sim_result": astra_result,
        "artifacts": {
            "stage_output_dir": str(output_dir),
            "workload_configuration": str(workload_base),
            "comm_group_configuration": str(comm_group),
            "system_configuration": str(system_path),
            "network_configuration": str(network_path),
            "remote_memory_configuration": str(remote_memory_path),
        },
    }
