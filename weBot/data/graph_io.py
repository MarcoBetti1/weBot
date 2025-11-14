"""Graph data export utilities."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Mapping

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..workflows.follower_graph import FollowerGraphResult


def export_edges_to_csv(edges: Dict[str, Iterable[str]], filename: str = "follower_graph.csv", *, directory: Path | None = None) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["source", "target"])
        for follower, followed_users in edges.items():
            for followed in followed_users:
                writer.writerow([follower, followed])
    return path


def export_follower_graph_json(
    result: "FollowerGraphResult" | Mapping[str, Any],
    filename: str = "follower_graph.json",
    *,
    directory: Path | None = None,
    indent: int = 2,
) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename

    if hasattr(result, "to_dict"):
        payload = result.to_dict()  # type: ignore[attr-defined]
    else:
        payload = dict(result)

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=indent), encoding="utf-8")
    return path
