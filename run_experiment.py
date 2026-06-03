#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from scsp.experiment import reproduce_experiment, run_batch_experiments, run_experiment


def _load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_json_list(path: str) -> List[Dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Batch config file must be a JSON list")
    return raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCSP experiment management workflow")
    parser.add_argument("--config", help="Path to single experiment config JSON")
    parser.add_argument("--batch-configs", help="Path to batch config list JSON")
    parser.add_argument("--template", choices=["single_point", "bandwidth_sensitivity"])
    parser.add_argument("--output-root", default="experiments/runs")
    parser.add_argument("--store", default="experiments/records.jsonl")
    parser.add_argument("--name", help="Optional experiment name")
    parser.add_argument("--reproduce", help="Experiment ID to reproduce")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.reproduce:
        result = reproduce_experiment(
            experiment_id=args.reproduce,
            output_root=args.output_root,
            store_path=args.store,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.batch_configs:
        raw_configs = _load_json_list(args.batch_configs)
        result = run_batch_experiments(
            raw_configs=raw_configs,
            output_root=args.output_root,
            store_path=args.store,
            template_name=args.template,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.config:
        raw_config = _load_json(args.config)
        result = run_experiment(
            raw_config=raw_config,
            output_root=args.output_root,
            store_path=args.store,
            experiment_name=args.name,
            template_name=args.template,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    raise ValueError("One of --config, --batch-configs, or --reproduce must be provided")


if __name__ == "__main__":
    main()
