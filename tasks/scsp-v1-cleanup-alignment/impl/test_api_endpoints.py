#!/usr/bin/env python3
import json
import requests
import sys

BASE = "http://127.0.0.1:8000"

def test_health():
    r = requests.get(f"{BASE}/api/health", timeout=5)
    print(f"1. /api/health: {r.status_code} -> {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_single_simulation():
    with open('/share/guolidong-nfs/SeeSpace/SCSP_v1/configs/model_registry.json') as f:
        registry = json.load(f)
    model = registry["Qwen2.5-VL-3B"]
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
    r = requests.post(f"{BASE}/api/simulations/single", json={"config": config, "bandwidth_gbps": 50}, timeout=60)
    print(f"2. /api/simulations/single: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   mode={data.get('mode')}, total_latency_s={data.get('metrics',{}).get('total_latency_s')}")
        assert data["mode"] == "single"
        assert data["metrics"]["total_latency_s"] > 0
    else:
        print(f"   ERROR: {r.text[:500]}")

def test_sweep_simulation():
    config = {
        "model_name": "Qwen2.5-VL-3B",
        "link_bandwidth_gbps": [10, 50, 100],
        "big_star_peak_pflops": 10.0,
        "local_mem_bw_gbps": 3350.0,
        "mixed_precision": False,
        "dp": 1,
        "tp": 2,
        "pp": 1,
    }
    r = requests.post(f"{BASE}/api/simulations/sweep", json={"config": config, "bandwidths_gbps": [10, 50]}, timeout=120)
    print(f"3. /api/simulations/sweep: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   mode={data.get('mode')}, results_count={len(data.get('results',[]))}")
        assert data["mode"] == "sweep"
        assert len(data["results"]) > 0
    else:
        print(f"   ERROR: {r.text[:500]}")

def test_run_experiment():
    config = {
        "model_name": "Qwen2.5-VL-3B",
        "link_bandwidth_gbps": [10, 50],
        "image_resolution": "512x512",
        "tile_size": "256x256",
        "image_type": "RGB",
        "prefill_inter_stage_transfer_mb": 2.2,
        "decode_inter_stage_transfer_kb": 2200.0,
        "flops_per_sample": 4e12,
        "peak_vram_gb": 120,
    }
    r = requests.post(f"{BASE}/api/experiments/run", json={
        "config": config,
        "experiment_name": "api-test-qwen3b",
        "template_name": "bandwidth_sensitivity",
    }, timeout=120)
    print(f"4. /api/experiments/run: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   status={data.get('record',{}).get('status')}, experiment_id={data.get('record',{}).get('experiment_id','')[:8]}")
        assert data["record"]["status"] == "success"
        return data["record"]["experiment_id"]
    else:
        print(f"   ERROR: {r.text[:500]}")
        return None

def test_list_experiments():
    r = requests.get(f"{BASE}/api/experiments", timeout=10)
    print(f"5. /api/experiments: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   count={data.get('count')}")
        assert data["count"] >= 0

def test_get_experiment(exp_id):
    r = requests.get(f"{BASE}/api/experiments/{exp_id}", timeout=10)
    print(f"6. /api/experiments/{exp_id[:8]}: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   status={data.get('status')}, name={data.get('experiment_name')}")

def test_reproduce_experiment(exp_id):
    r = requests.post(f"{BASE}/api/experiments/reproduce/{exp_id}", timeout=120)
    print(f"7. /api/experiments/reproduce/{exp_id[:8]}: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   reproduced_experiment_id={data.get('reproduced_experiment_id','')[:8]}")

if __name__ == "__main__":
    test_health()
    test_single_simulation()
    test_sweep_simulation()
    exp_id = test_run_experiment()
    test_list_experiments()
    if exp_id:
        test_get_experiment(exp_id)
        test_reproduce_experiment(exp_id)
    print("\n✅ API 验证完成")
