from __future__ import annotations

import unittest

from scsp.config import build_simulation_config
from scsp.simulator import run_v1_simulation


def _raw_base() -> dict:
    return {
        "image_resolution": "1024x1024",
        "tile_size": "512x512",
        "image_type": "RGB",
        "link_bandwidth_gbps": 100,
        "prefill_inter_stage_transfer_mb": 5.24288,
        "decode_inter_stage_transfer_kb": 5242.88,
        "flops_per_sample": 5.0e13,
        "peak_vram_gb": 120,
        "num_images": 1,
        "big_star_peak_pflops": 10.0,
        "single_star_compute_utilization": 0.5,
        "single_node_memory_bandwidth_bytes_per_sec": 3.0e12,
        "prefill_memory_bytes_per_patch": 5.0e10,
        "decode_flops_per_token": 1.435e11,
        "decode_memory_bytes_per_token": 1.0e8,
        "inter_sat_distance_km": 10,
    }


class TestSimulatorDecodeMetrics(unittest.TestCase):
    def test_legacy_inter_stage_transfer_mb_maps_to_prefill_and_decode(self) -> None:
        raw = _raw_base()
        del raw["prefill_inter_stage_transfer_mb"]
        del raw["decode_inter_stage_transfer_kb"]
        raw["inter_stage_transfer_mb"] = 1.0
        cfg = build_simulation_config(raw, 100)
        self.assertEqual(cfg.prefill_inter_stage_transfer_mb, 1.0)
        self.assertEqual(cfg.decode_inter_stage_transfer_kb, 1000.0)

    def test_decode_energy_efficiency_matches_power_and_latency(self) -> None:
        raw = _raw_base()
        raw["single_star_compute_payload_power_w"] = 10_000.0
        cfg = build_simulation_config(raw, 100)
        metrics = run_v1_simulation(cfg)
        expected = 1.0 / (
            raw["single_star_compute_payload_power_w"] * metrics.decode_latency_s_per_token
        )
        self.assertAlmostEqual(
            metrics.decode_energy_efficiency_tokens_per_j,
            expected,
            places=12,
        )

    def test_prefill_decode_utilization_are_independent(self) -> None:
        raw = _raw_base()
        raw.update(
            {
                "prefill_compute_utilization": 0.9,
                "prefill_memory_utilization": 0.9,
                "decode_compute_utilization": 0.1,
                "decode_memory_utilization": 0.4,
                "decode_flops_per_token": 1.0e12,
                "decode_memory_bytes_per_token": 1.0e9,
            }
        )
        cfg = build_simulation_config(raw, 100)
        metrics = run_v1_simulation(cfg)

        # prefill_compute_time_s = max(stage1, stage2)，默认 stage_split_ratio=0.5 时每级算量各为总 flops 的一半
        expected_prefill_compute = (raw["flops_per_sample"] * 0.5) / (
            raw["big_star_peak_pflops"] * 1e15 * raw["prefill_compute_utilization"]
        )
        expected_decode_compute = raw["decode_flops_per_token"] / (
            raw["big_star_peak_pflops"] * 1e15 * raw["decode_compute_utilization"]
        )
        self.assertAlmostEqual(metrics.prefill_compute_time_s, expected_prefill_compute, places=12)
        # Under two-star pipeline, single-star decode compute component uses the slower stage.
        self.assertAlmostEqual(
            metrics.decode_compute_latency_s_per_token, expected_decode_compute * 0.5, places=12
        )
        self.assertGreater(metrics.decode_memory_latency_s_per_token, 0.0)
        self.assertIn(metrics.prefill_bottleneck, ("compute", "memory"))
        self.assertIn(metrics.decode_bottleneck, ("compute", "memory"))

    def test_decode_compute_bound(self) -> None:
        raw = _raw_base()
        raw["decode_flops_per_token"] = 5.0e12
        raw["decode_memory_bytes_per_token"] = 1.0e7
        cfg = build_simulation_config(raw, 100)
        metrics = run_v1_simulation(cfg)
        self.assertGreater(
            metrics.decode_compute_latency_s_per_token,
            metrics.decode_memory_latency_s_per_token,
        )
        self.assertEqual(metrics.decode_bottleneck, "compute")
        # Full decode path includes stage1 + inter-stage transfer + stage2,
        # so it should be larger than single-star compute component.
        self.assertGreater(
            metrics.decode_latency_s_per_token,
            metrics.decode_compute_latency_s_per_token,
        )

    def test_decode_memory_bound(self) -> None:
        raw = _raw_base()
        raw["decode_flops_per_token"] = 1.0e9
        raw["decode_memory_bytes_per_token"] = 1.0e11
        cfg = build_simulation_config(raw, 100)
        metrics = run_v1_simulation(cfg)
        self.assertGreater(
            metrics.decode_memory_latency_s_per_token,
            metrics.decode_compute_latency_s_per_token,
        )
        self.assertEqual(metrics.decode_bottleneck, "memory")
        # Full decode path includes stage1 + inter-stage transfer + stage2,
        # so it should be larger than single-star memory component.
        self.assertGreater(
            metrics.decode_latency_s_per_token,
            metrics.decode_memory_latency_s_per_token,
        )

    def test_prefill_peak_memory_scales_with_tile_size(self) -> None:
        raw_small = _raw_base()
        raw_small["tile_size"] = "256x256"
        small_cfg = build_simulation_config(raw_small, 100)
        small_metrics = run_v1_simulation(small_cfg)

        raw_large = _raw_base()
        raw_large["tile_size"] = "1024x1024"
        large_cfg = build_simulation_config(raw_large, 100)
        large_metrics = run_v1_simulation(large_cfg)

        self.assertGreater(
            large_metrics.prefill_peak_memory_gb,
            small_metrics.prefill_peak_memory_gb,
        )

    def test_prefill_peak_memory_is_single_star_peak_under_pipeline(self) -> None:
        raw_balanced = _raw_base()
        raw_balanced["stage_split_ratio"] = 0.5
        balanced_cfg = build_simulation_config(raw_balanced, 100)
        balanced_metrics = run_v1_simulation(balanced_cfg)

        raw_skewed = _raw_base()
        raw_skewed["stage_split_ratio"] = 0.9
        skewed_cfg = build_simulation_config(raw_skewed, 100)
        skewed_metrics = run_v1_simulation(skewed_cfg)

        # If we report single-star peak under pipeline split, skewed partition
        # should increase the max per-star memory footprint.
        self.assertGreater(
            skewed_metrics.prefill_peak_memory_gb,
            balanced_metrics.prefill_peak_memory_gb,
        )

    def test_prefill_peak_memory_not_driven_by_decode_total_memory_traffic(self) -> None:
        raw_a = _raw_base()
        raw_a["decode_memory_bytes_per_token"] = 1.0e8
        cfg_a = build_simulation_config(raw_a, 100)
        m_a = run_v1_simulation(cfg_a)

        raw_b = _raw_base()
        raw_b["decode_memory_bytes_per_token"] = 5.0e10
        cfg_b = build_simulation_config(raw_b, 100)
        m_b = run_v1_simulation(cfg_b)

        # Prefill peak memory should be based on KV-write occupancy from model
        # structure, not decode total memory traffic parameter.
        self.assertAlmostEqual(m_a.prefill_peak_memory_gb, m_b.prefill_peak_memory_gb, places=6)

    def test_decode_total_latency_is_per_token_times_decode_tokens(self) -> None:
        raw = _raw_base()
        raw["decode_tokens"] = 50
        m = run_v1_simulation(build_simulation_config(raw, 100))
        self.assertAlmostEqual(
            m.decode_total_latency_s,
            m.decode_latency_s_per_token * 50.0,
            places=12,
        )

    def test_decode_tokens_scales_total_inference_time(self) -> None:
        raw = _raw_base()
        raw_one = dict(raw)
        raw_one["decode_tokens"] = 1
        raw_many = dict(raw)
        raw_many["decode_tokens"] = 100
        m1 = run_v1_simulation(build_simulation_config(raw_one, 100))
        m100 = run_v1_simulation(build_simulation_config(raw_many, 100))
        delta = m100.total_inference_time_s - m1.total_inference_time_s
        self.assertAlmostEqual(delta, 99.0 * m1.decode_latency_s_per_token, places=9)

    def test_single_star_peak_memory_covers_prefill_and_decode(self) -> None:
        m = run_v1_simulation(build_simulation_config(_raw_base(), 100))
        self.assertGreaterEqual(m.single_star_peak_memory_gb, m.prefill_peak_memory_gb)

    def test_single_star_peak_memory_grows_with_decode_tokens(self) -> None:
        # decode 激活仅按当前 token 计；本用例通过 KV 随 decode_tokens 变长验证单星峰值仍随序列增长
        raw_lo = dict(_raw_base())
        raw_lo["decode_tokens"] = 1
        raw_lo["prefill_memory_bytes_per_patch"] = 1.0e8
        raw_lo["decode_memory_bytes_per_token"] = 2.0e9
        raw_hi = dict(_raw_base())
        raw_hi["decode_tokens"] = 800
        raw_hi["prefill_memory_bytes_per_patch"] = 1.0e8
        raw_hi["decode_memory_bytes_per_token"] = 2.0e9
        m_lo = run_v1_simulation(build_simulation_config(raw_lo, 100))
        m_hi = run_v1_simulation(build_simulation_config(raw_hi, 100))
        self.assertGreater(m_hi.single_star_peak_memory_gb, m_lo.single_star_peak_memory_gb)


if __name__ == "__main__":
    unittest.main()
