from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, data: Dict | List[Dict]) -> None:
    ensure_parent_dir(path)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_csv(path: str | Path, rows: List[Dict]) -> None:
    if not rows:
        raise ValueError("rows is empty")
    ensure_parent_dir(path)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
