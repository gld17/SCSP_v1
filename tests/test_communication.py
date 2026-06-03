from __future__ import annotations

import unittest

from scsp.communication import LIGHT_SPEED_MPS, inter_stage_kb_to_data_mb, transfer_time_seconds


class TestCommunication(unittest.TestCase):
    def test_transfer_time_contains_propagation(self) -> None:
        latency = transfer_time_seconds(data_mb=0.0, bandwidth_gbps=10.0, distance_km=10.0)
        expected = 10_000.0 / LIGHT_SPEED_MPS
        self.assertAlmostEqual(latency, expected, places=12)

    def test_transfer_time_decreases_with_bandwidth(self) -> None:
        low_bw = transfer_time_seconds(data_mb=10.0, bandwidth_gbps=10.0, distance_km=10.0)
        high_bw = transfer_time_seconds(data_mb=10.0, bandwidth_gbps=100.0, distance_km=10.0)
        self.assertGreater(low_bw, high_bw)

    def test_inter_stage_kb_to_data_mb(self) -> None:
        self.assertAlmostEqual(inter_stage_kb_to_data_mb(1000.0), 1.0, places=12)
        self.assertAlmostEqual(inter_stage_kb_to_data_mb(5.72), 0.00572, places=12)


if __name__ == "__main__":
    unittest.main()
