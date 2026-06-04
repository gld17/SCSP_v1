from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Tuple

IMAGE_TYPE_DEFAULTS = {
    "RGB": {"channels": 3, "bytes_per_pixel": 2},
    "SAR": {"channels": 1, "bytes_per_pixel": 4},
}

CONFIG_SCHEMA_VERSION = "1.0"


def _parse_resolution(text: str) -> Tuple[int, int]:
    parts = text.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid resolution format: {text}")
    width, height = int(parts[0]), int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError(f"Resolution must be positive: {text}")
    return width, height


@dataclass(frozen=True)
class V1SimulationConfig:
    # Core variable parameters from README.
    image_resolution: str
    tile_size: str
    link_bandwidth_gbps: float
    prefill_inter_stage_transfer_mb: float
    decode_inter_stage_transfer_kb: float
    flops_per_sample: float
    peak_vram_gb: float
    model_name: str = "Qwen2.5-VL-7B"
    model_params: str = "7B"
    active_parameter_count: float = 7e9
    resident_parameter_count: float = 7e9
    image_type: Literal["RGB", "SAR"] = "RGB"

    # Task and system settings.
    num_images: int = 1
    decode_tokens: int = 1
    channels: int = 3
    bytes_per_pixel: int = 2
    big_star_peak_pflops: float = 10.0
    single_star_compute_utilization: float = 0.6
    prefill_compute_utilization: float = 0.50
    prefill_memory_utilization: float = 0.70
    decode_compute_utilization: float = 0.20
    decode_memory_utilization: float = 0.70
    single_node_memory_bandwidth_bytes_per_sec: float = 2.0e13
    prefill_memory_bytes_per_patch: float = 5.0e10
    decode_flops_per_token: float = 1.435e11
    decode_memory_bytes_per_token: float = 1.0e8
    llm_num_hidden_layers: int = 80
    llm_hidden_size: int = 8192
    llm_num_attention_heads: int = 64
    llm_num_key_value_heads: int = 8
    vision_patch_size: int = 14
    vision_spatial_merge_size: int = 2
    inter_sat_latency_target_ms: float = 1.0
    peak_power_limit_kw: float = 20.0
    single_star_compute_payload_power_w: float = 20000.0
    stage_split_ratio: float = 0.5
    fixed_sync_overhead_ms: float = 0.0
    inter_sat_distance_km: float = 10.0
    activation_load_store_ratio: float = 1.0
    local_mem_latency_ns: float = 0.0

    @property
    def image_wh(self) -> Tuple[int, int]:
        return _parse_resolution(self.image_resolution)

    @property
    def tile_wh(self) -> Tuple[int, int]:
        return _parse_resolution(self.tile_size)

    @property
    def big_star_peak_flops(self) -> float:
        return self.big_star_peak_pflops * 1e15


def load_config(path: str | Path) -> V1SimulationConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    raw.setdefault("image_type", "RGB")
    if "prefill_inter_stage_transfer_mb" not in raw or "decode_inter_stage_transfer_kb" not in raw:
        if "inter_stage_transfer_mb" in raw:
            legacy = float(raw["inter_stage_transfer_mb"])
            raw.setdefault("prefill_inter_stage_transfer_mb", legacy)
            raw.setdefault("decode_inter_stage_transfer_kb", legacy * 1000.0)
    return V1SimulationConfig(**raw)


def _to_param_count(raw_value: Any, fallback: float) -> float:
    try:
        n = float(raw_value)
    except (TypeError, ValueError):
        return fallback
    if n <= 0:
        return fallback
    # Some callers may pass "72" (B) while registry uses absolute counts.
    return n * 1e9 if n <= 1e6 else n


def _infer_param_counts_from_text(model_params: str, fallback: float) -> tuple[float, float]:
    text = str(model_params or "")
    m_resident = re.search(r"(\d+(?:\.\d+)?)\s*B", text, flags=re.IGNORECASE)
    resident = float(m_resident.group(1)) * 1e9 if m_resident else fallback
    m_active = re.search(r"A\s*(\d+(?:\.\d+)?)\s*B", text, flags=re.IGNORECASE)
    active = float(m_active.group(1)) * 1e9 if m_active else resident
    return active, resident


def normalize_raw_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize user input config to a versioned, validated dict.

    This function is the schema boundary for stage-1 API refactor.
    """
    normalized = dict(raw)
    normalized.setdefault("schema_version", CONFIG_SCHEMA_VERSION)
    normalized.setdefault("image_type", "RGB")
    normalized.setdefault("model_name", "Qwen2.5-VL-7B")
    normalized.setdefault("model_params", "7B")
    normalized.setdefault("flops_per_sample", 5e13)
    normalized.setdefault("num_images", 1)
    normalized.setdefault("image_resolution", "512x512")
    normalized.setdefault("decode_tokens", 1)
    normalized.setdefault("big_star_peak_pflops", 10.0)
    normalized.setdefault("single_star_compute_utilization", 0.6)
    normalized.setdefault("prefill_compute_utilization", 0.50)
    normalized.setdefault("prefill_memory_utilization", 0.70)
    normalized.setdefault("decode_compute_utilization", 0.20)
    normalized.setdefault("decode_memory_utilization", 0.70)
    normalized.setdefault("single_node_memory_bandwidth_bytes_per_sec", 2.0e13)
    normalized.setdefault("prefill_memory_bytes_per_patch", 5.0e10)
    normalized.setdefault("decode_flops_per_token", 1.435e11)
    normalized.setdefault("decode_memory_bytes_per_token", 1.0e8)
    model_structure = normalized.get("model_structure", {}) or {}
    parameter_count = model_structure.get("parameter_count", {}) if isinstance(model_structure, dict) else {}
    default_active, default_resident = _infer_param_counts_from_text(
        str(normalized.get("model_params", "7B")),
        7e9,
    )
    normalized.setdefault(
        "active_parameter_count",
        _to_param_count(parameter_count.get("active_unit", parameter_count.get("unit")), default_active),
    )
    normalized.setdefault(
        "resident_parameter_count",
        _to_param_count(parameter_count.get("resident_unit", parameter_count.get("unit")), default_resident),
    )
    llm = model_structure.get("llm", {}) if isinstance(model_structure, dict) else {}
    normalized.setdefault("llm_num_hidden_layers", int(llm.get("num_hidden_layers", 80) or 80))
    normalized.setdefault("llm_hidden_size", int(llm.get("hidden_size", 8192) or 8192))
    normalized.setdefault("llm_num_attention_heads", int(llm.get("num_attention_heads", 64) or 64))
    normalized.setdefault("llm_num_key_value_heads", int(llm.get("num_key_value_heads", 8) or 8))
    vision = model_structure.get("vision", {}) if isinstance(model_structure, dict) else {}
    normalized.setdefault("vision_patch_size", int(vision.get("patch_size", 14) or 14))
    normalized.setdefault(
        "vision_spatial_merge_size",
        int(vision.get("spatial_merge_size", 2) or 2),
    )
    normalized.setdefault("inter_sat_latency_target_ms", 1.0)
    normalized.setdefault("peak_power_limit_kw", 20.0)
    normalized.setdefault(
        "single_star_compute_payload_power_w",
        float(normalized.get("peak_power_limit_kw", 1.0)) * 1000.0,
    )
    normalized.setdefault("stage_split_ratio", 0.5)
    normalized.setdefault("fixed_sync_overhead_ms", 0.0)
    normalized.setdefault("inter_sat_distance_km", 10.0)
    normalized.setdefault("activation_load_store_ratio", 1.0)
    normalized.setdefault("local_mem_latency_ns", 0.0)
    normalized.pop("simulation_mode", None)
    normalized.setdefault("mixed_precision", False)
    normalized.setdefault("dp", 1)
    normalized.setdefault("tp", 1)
    normalized.setdefault("pp", 1)
    normalized.setdefault("local_mem_bw_gbps", 3350.0)

    if "prefill_inter_stage_transfer_mb" not in normalized or "decode_inter_stage_transfer_kb" not in normalized:
        if "inter_stage_transfer_mb" in normalized:
            legacy = float(normalized["inter_stage_transfer_mb"])
            normalized.setdefault("prefill_inter_stage_transfer_mb", legacy)
            normalized.setdefault("decode_inter_stage_transfer_kb", legacy * 1000.0)
    return normalized


def validate_raw_config(raw: Dict[str, Any]) -> None:
    required = [
        "image_resolution",
        "tile_size",
        "prefill_inter_stage_transfer_mb",
        "decode_inter_stage_transfer_kb",
        "peak_vram_gb",
    ]
    for key in required:
        if key not in raw:
            raise KeyError(f"Missing required field: {key}")

    image_type = str(raw.get("image_type", "RGB")).upper()
    if image_type not in IMAGE_TYPE_DEFAULTS:
        raise ValueError("image_type must be one of: RGB, SAR")
    if float(raw.get("single_node_memory_bandwidth_bytes_per_sec", 0)) <= 0:
        raise ValueError("single_node_memory_bandwidth_bytes_per_sec must be positive")
    for key in (
        "prefill_compute_utilization",
        "prefill_memory_utilization",
        "decode_compute_utilization",
        "decode_memory_utilization",
    ):
        val = float(raw.get(key, 0))
        if val <= 0 or val > 1:
            raise ValueError(f"{key} must be in (0, 1]")
    if float(raw.get("prefill_memory_bytes_per_patch", 0)) < 0:
        raise ValueError("prefill_memory_bytes_per_patch must be non-negative")
    if float(raw.get("decode_flops_per_token", 0)) < 0:
        raise ValueError("decode_flops_per_token must be non-negative")
    if float(raw.get("decode_memory_bytes_per_token", 0)) < 0:
        raise ValueError("decode_memory_bytes_per_token must be non-negative")
    if float(raw.get("active_parameter_count", 0)) <= 0:
        raise ValueError("active_parameter_count must be positive")
    if float(raw.get("resident_parameter_count", 0)) <= 0:
        raise ValueError("resident_parameter_count must be positive")
    if float(raw.get("active_parameter_count", 0)) > float(raw.get("resident_parameter_count", 0)):
        raise ValueError("active_parameter_count must be <= resident_parameter_count")
    if float(raw.get("single_star_compute_payload_power_w", 0)) <= 0:
        raise ValueError("single_star_compute_payload_power_w must be positive")
    if int(raw.get("llm_num_hidden_layers", 80)) <= 0:
        raise ValueError("llm_num_hidden_layers must be positive")
    if int(raw.get("llm_hidden_size", 8192)) <= 0:
        raise ValueError("llm_hidden_size must be positive")
    if int(raw.get("llm_num_attention_heads", 64)) <= 0:
        raise ValueError("llm_num_attention_heads must be positive")
    if int(raw.get("llm_num_key_value_heads", 8)) <= 0:
        raise ValueError("llm_num_key_value_heads must be positive")
    if int(raw.get("vision_patch_size", 14)) <= 0:
        raise ValueError("vision_patch_size must be positive")
    if int(raw.get("vision_spatial_merge_size", 2)) <= 0:
        raise ValueError("vision_spatial_merge_size must be positive")
    if int(raw.get("decode_tokens", 1)) < 1:
        raise ValueError("decode_tokens must be a positive integer")
    if float(raw.get("prefill_inter_stage_transfer_mb", 0)) < 0:
        raise ValueError("prefill_inter_stage_transfer_mb must be non-negative")
    if float(raw.get("decode_inter_stage_transfer_kb", 0)) < 0:
        raise ValueError("decode_inter_stage_transfer_kb must be non-negative")


def build_simulation_config(raw: Dict[str, Any], link_bandwidth_gbps: float) -> V1SimulationConfig:
    normalized = normalize_raw_config(raw)
    validate_raw_config(normalized)
    image_type = str(normalized["image_type"]).upper()
    image_defaults = IMAGE_TYPE_DEFAULTS[image_type]

    return V1SimulationConfig(
        image_resolution=normalized["image_resolution"],
        tile_size=normalized["tile_size"],
        link_bandwidth_gbps=float(link_bandwidth_gbps),
        prefill_inter_stage_transfer_mb=float(normalized["prefill_inter_stage_transfer_mb"]),
        decode_inter_stage_transfer_kb=float(normalized["decode_inter_stage_transfer_kb"]),
        flops_per_sample=float(normalized["flops_per_sample"]),
        peak_vram_gb=float(normalized["peak_vram_gb"]),
        model_name=str(normalized["model_name"]),
        model_params=str(normalized["model_params"]),
        active_parameter_count=float(normalized["active_parameter_count"]),
        resident_parameter_count=float(normalized["resident_parameter_count"]),
        image_type=image_type,
        num_images=int(normalized["num_images"]),
        decode_tokens=int(normalized["decode_tokens"]),
        channels=int(image_defaults["channels"]),
        bytes_per_pixel=int(image_defaults["bytes_per_pixel"]),
        big_star_peak_pflops=float(normalized["big_star_peak_pflops"]),
        single_star_compute_utilization=float(normalized["single_star_compute_utilization"]),
        prefill_compute_utilization=float(normalized["prefill_compute_utilization"]),
        prefill_memory_utilization=float(normalized["prefill_memory_utilization"]),
        decode_compute_utilization=float(normalized["decode_compute_utilization"]),
        decode_memory_utilization=float(normalized["decode_memory_utilization"]),
        single_node_memory_bandwidth_bytes_per_sec=float(normalized["single_node_memory_bandwidth_bytes_per_sec"]),
        prefill_memory_bytes_per_patch=float(normalized["prefill_memory_bytes_per_patch"]),
        decode_flops_per_token=float(normalized["decode_flops_per_token"]),
        decode_memory_bytes_per_token=float(normalized["decode_memory_bytes_per_token"]),
        llm_num_hidden_layers=int(normalized["llm_num_hidden_layers"]),
        llm_hidden_size=int(normalized["llm_hidden_size"]),
        llm_num_attention_heads=int(normalized["llm_num_attention_heads"]),
        llm_num_key_value_heads=int(normalized["llm_num_key_value_heads"]),
        vision_patch_size=int(normalized["vision_patch_size"]),
        vision_spatial_merge_size=int(normalized["vision_spatial_merge_size"]),
        inter_sat_latency_target_ms=float(normalized["inter_sat_latency_target_ms"]),
        peak_power_limit_kw=float(normalized["peak_power_limit_kw"]),
        single_star_compute_payload_power_w=float(normalized["single_star_compute_payload_power_w"]),
        stage_split_ratio=float(normalized["stage_split_ratio"]),
        fixed_sync_overhead_ms=float(normalized["fixed_sync_overhead_ms"]),
        inter_sat_distance_km=float(normalized["inter_sat_distance_km"]),
        activation_load_store_ratio=float(normalized.get("activation_load_store_ratio", 1.0)),
        local_mem_latency_ns=float(normalized.get("local_mem_latency_ns", 0.0)),
    )


def dump_config_dict(config: V1SimulationConfig) -> Dict[str, Any]:
    return {
        "image_resolution": config.image_resolution,
        "tile_size": config.tile_size,
        "image_type": config.image_type,
        "model_name": config.model_name,
        "model_params": config.model_params,
        "active_parameter_count": config.active_parameter_count,
        "resident_parameter_count": config.resident_parameter_count,
        "link_bandwidth_gbps": config.link_bandwidth_gbps,
        "prefill_inter_stage_transfer_mb": config.prefill_inter_stage_transfer_mb,
        "decode_inter_stage_transfer_kb": config.decode_inter_stage_transfer_kb,
        "flops_per_sample": config.flops_per_sample,
        "peak_vram_gb": config.peak_vram_gb,
        "num_images": config.num_images,
        "decode_tokens": config.decode_tokens,
        "channels": config.channels,
        "bytes_per_pixel": config.bytes_per_pixel,
        "big_star_peak_pflops": config.big_star_peak_pflops,
        "single_star_compute_utilization": config.single_star_compute_utilization,
        "prefill_compute_utilization": config.prefill_compute_utilization,
        "prefill_memory_utilization": config.prefill_memory_utilization,
        "decode_compute_utilization": config.decode_compute_utilization,
        "decode_memory_utilization": config.decode_memory_utilization,
        "single_node_memory_bandwidth_bytes_per_sec": config.single_node_memory_bandwidth_bytes_per_sec,
        "prefill_memory_bytes_per_patch": config.prefill_memory_bytes_per_patch,
        "decode_flops_per_token": config.decode_flops_per_token,
        "decode_memory_bytes_per_token": config.decode_memory_bytes_per_token,
        "llm_num_hidden_layers": config.llm_num_hidden_layers,
        "llm_hidden_size": config.llm_hidden_size,
        "llm_num_attention_heads": config.llm_num_attention_heads,
        "llm_num_key_value_heads": config.llm_num_key_value_heads,
        "vision_patch_size": config.vision_patch_size,
        "vision_spatial_merge_size": config.vision_spatial_merge_size,
        "inter_sat_latency_target_ms": config.inter_sat_latency_target_ms,
        "peak_power_limit_kw": config.peak_power_limit_kw,
        "single_star_compute_payload_power_w": config.single_star_compute_payload_power_w,
        "stage_split_ratio": config.stage_split_ratio,
        "fixed_sync_overhead_ms": config.fixed_sync_overhead_ms,
        "inter_sat_distance_km": config.inter_sat_distance_km,
        "activation_load_store_ratio": config.activation_load_store_ratio,
        "local_mem_latency_ns": config.local_mem_latency_ns,
    }
