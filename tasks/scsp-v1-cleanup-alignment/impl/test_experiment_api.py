#!/usr/bin/env python3
import json
import requests

BASE = "http://127.0.0.1:8000"

def test_experiment_run():
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
    print("4. POST /api/experiments/run (timeout=300s)...")
    r = requests.post(f"{BASE}/api/experiments/run", json={
        "config": config,
        "experiment_name": "api-test-qwen3b-v1",
        "template_name": "bandwidth_sensitivity",
    }, timeout=300)
    print(f"   status={r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print(f"   record_status={data.get('record',{}).get('status')}")
        print(f"   experiment_id={data.get('record',{}).get('experiment_id','')[:16]}")
        return data["record"]["experiment_id"]
    else:
        print(f"   ERROR: {r.text[:500]}")
        return None

def test_list_experiments():
    print("5. GET /api/experiments (timeout=30s)...")
    r = requests.get(f"{BASE}/api/experiments", timeout=30)
    print(f"   status={r.status_code}")
    data = r.json()
    print(f"   count={data.get('count')}")
    return data.get("count", 0)

def test_get_experiment(exp_id):
    print(f"6. GET /api/experiments/{exp_id[:8]} (timeout=30s)...")
    r = requests.get(f"{BASE}/api/experiments/{exp_id}", timeout=30)
    print(f"   status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   name={data.get('experiment_name')}, status={data.get('status')}")

def test_reproduce_experiment(exp_id):
    print(f"7. POST /api/experiments/reproduce/{exp_id[:8]} (timeout=300s)...")
    r = requests.post(f"{BASE}/api/experiments/reproduce/{exp_id}", timeout=300)
    print(f"   status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   reproduced_id={data.get('reproduced_experiment_id','')[:16]}")

if __name__ == "__main__":
    exp_id = test_experiment_run()
    test_list_experiments()
    if exp_id:
        test_get_experiment(exp_id)
        test_reproduce_experiment(exp_id)
    print("\n✅ 实验管理 API 验证完成")
