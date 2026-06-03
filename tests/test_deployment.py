from __future__ import annotations

import unittest

from scsp.deployment import run_pipeline_schedule


class TestDeployment(unittest.TestCase):
    def test_pipeline_schedule_matches_expected_formula(self) -> None:
        result = run_pipeline_schedule(
            total_samples=3,
            stage0_transfer_s=1.0,
            stage1_compute_s=2.0,
            inter_stage_transfer_s=0.5,
            stage2_compute_s=1.5,
            sync_overhead_ms=0.0,
        )
        # stage1 total = 2.5, cycle=max(1.0,2.5,1.5)=2.5
        # warmup=1.0+2.5+1.5=5.0, makespan=5.0+(3-1)*2.5=10.0
        self.assertAlmostEqual(result["makespan_s"], 10.0, places=8)
        self.assertEqual(result["bottleneck"], "bigstar1_stage")


if __name__ == "__main__":
    unittest.main()
