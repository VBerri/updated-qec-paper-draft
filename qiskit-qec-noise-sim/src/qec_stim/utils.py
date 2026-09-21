from __future__ import annotations

from pathlib import Path


def ensure_project_dirs(root: str | Path = ".") -> None:
    root = Path(root)
    for rel in ["results", "figures", "logs", "docs"]:
        (root / rel).mkdir(parents=True, exist_ok=True)
