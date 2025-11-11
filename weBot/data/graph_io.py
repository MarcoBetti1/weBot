"""Graph data export utilities."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, Set


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
