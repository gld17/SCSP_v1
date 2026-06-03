from pathlib import Path

from scsp.engine import run_simulation


def test_run_simulation_uses_astra_bridge_end_to_end() -> None:
    config = {
        "model_name": "Qwen2.5-VL-3B",
        "link_bandwidth_gbps": 50,
        "big_star_peak_pflops": 10.0,
        "local_mem_bw_gbps": 3350.0,
        "mixed_precision": False,
        "dp": 1,
        "tp": 2,
        "pp": 1,
    }

    result = run_simulation(config)

    assert result["mode"] == "single"
    assert result["metrics"]["total_latency_s"] > 0
    artifacts = result["artifacts"]
    stage_output_dir = Path(artifacts["stage_output_dir"])
    workload_base = Path(artifacts["workload_configuration"])
    comm_group = Path(artifacts["comm_group_configuration"])
    assert stage_output_dir.exists()
    assert Path(f"{workload_base}.0.et").exists()
    assert comm_group.exists()
    assert result["astra_sim_result"]
    assert result["unsupported_fields"]
