from __future__ import annotations

import unittest

from scsp.metrics import build_simulation_metrics


class TestMetrics(unittest.TestCase):
    def test_effective_compute_and_latency_metric(self) -> None:
        metrics = build_simulation_metrics(
            total_samples=2,
            total_latency_s=4.0,
            stage0_transfer_s=0.1,
            inter_stage_transfer_s=0.2,
            stage1_compute_s=1.0,
            stage2_compute_s=1.5,
            flops_per_sample=100.0,
            big_star_peak_pflops=2.0,
            bottleneck_stage="bigstar1_stage",
        )
        self.assertAlmostEqual(metrics.effective_compute_flops, 50.0, places=8)
        self.assertAlmostEqual(metrics.total_latency_s, 4.0, places=8)
        self.assertEqual(metrics.bottleneck_stage, "bigstar1_stage")
        self.assertAlmostEqual(metrics.prefill_peak_memory_gb, 0.0, places=8)
        self.assertAlmostEqual(metrics.single_star_peak_memory_gb, 0.0, places=8)

    def test_prefill_peak_memory_metric_fields(self) -> None:
        metrics = build_simulation_metrics(
            total_samples=1,
            total_latency_s=1.0,
            stage0_transfer_s=0.0,
            inter_stage_transfer_s=0.0,
            stage1_compute_s=0.2,
            stage2_compute_s=0.3,
            flops_per_sample=10.0,
            big_star_peak_pflops=1.0,
            bottleneck_stage="stage1",
            prefill_peak_memory_bytes=110e9,
            prefill_weight_memory_bytes=72e9,
            prefill_kv_memory_bytes=10e9,
            prefill_activation_peak_memory_bytes=20e9,
            prefill_workspace_memory_bytes=8e9,
            single_star_peak_memory_bytes=150e9,
        )
        self.assertAlmostEqual(metrics.prefill_peak_memory_gb, 110.0, places=8)
        self.assertAlmostEqual(metrics.single_star_peak_memory_gb, 150.0, places=8)
        self.assertAlmostEqual(metrics.prefill_weight_memory_bytes, 72e9, places=2)
        self.assertAlmostEqual(metrics.prefill_workspace_memory_bytes, 8e9, places=2)


if __name__ == "__main__":
    unittest.main()
