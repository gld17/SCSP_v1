from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scsp.experiment import JsonlExperimentStore, reproduce_experiment, run_experiment


class TestExperimentManagement(unittest.TestCase):
    def _minimal_config(self) -> dict:
        return {
            "image_resolution": "1024x1024",
            "tile_size": "512x512",
            "image_type": "RGB",
            "link_bandwidth_gbps": [10, 50, 100],
            "prefill_inter_stage_transfer_mb": 2.2,
            "decode_inter_stage_transfer_kb": 2200.0,
            "flops_per_sample": 4e12,
            "peak_vram_gb": 120,
        }

    def test_record_persist_and_reproduce(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "runs"
            store_path = root / "records.jsonl"

            first = run_experiment(
                raw_config=self._minimal_config(),
                output_root=output_root,
                store_path=store_path,
                experiment_name="unit-test",
                template_name="bandwidth_sensitivity",
            )
            self.assertEqual(first["record"]["status"], "success")
            self.assertTrue(store_path.exists())
            summary = first["record"]["result_summary"]
            self.assertIn("best_decode_latency_s_per_token", summary)
            self.assertIn("best_decode_bottleneck", summary)
            self.assertIn("best_decode_effective_compute_pflops", summary)

            records = JsonlExperimentStore(store_path).list_records()
            self.assertGreaterEqual(len(records), 1)

            repro = reproduce_experiment(
                experiment_id=first["record"]["experiment_id"],
                output_root=output_root,
                store_path=store_path,
            )
            self.assertIn("reproduced_experiment_id", repro)


if __name__ == "__main__":
    unittest.main()
