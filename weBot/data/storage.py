"""Persistence helpers for exported data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_json(name: str, data: Any, *, directory: Path | None = None) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path
