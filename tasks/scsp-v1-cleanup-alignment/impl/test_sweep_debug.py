#!/usr/bin/env python3
import json
import requests

BASE = "http://127.0.0.1:8000"

def test_sweep():
    config = {
        "model_name": "Qwen2.5-VL-3B",
        "link_bandwidth_gbps": [10, 50, 100],
        "big_star_peak_pflops": 10.0,
        "local_mem_bw_gbps": 3350.0,
        "mixed_precision": False,
        "dp": 1, "tp": 2, "pp": 1,
    }
    r = requests.post(f"{BASE}/api/simulations/sweep", json={"config": config, "bandwidths_gbps": [10, 50]}, timeout=120)
    print(f"3. /api/simulations/sweep: {r.status_code}")
    data = r.json()
    print(f"   keys={list(data.keys())}")
    print(f"   data={json.dumps(data, indent=2)[:800]}")

test_sweep()
