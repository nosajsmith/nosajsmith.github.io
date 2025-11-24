# output_manager.py — centralize where files are written
from __future__ import annotations
from pathlib import Path

class OutputManager:
    def __init__(self, root: str = ".", base_dir: str = "runs"):
        self.root = Path(root).resolve()
        self.base = (self.root / base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def turn_dir(self, n: int) -> Path:
        d = self.base / f"turn_{n}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, n: int, name: str) -> Path:
        """Path inside runs/turn_<n>/name (auto-creates folder)."""
        return self.turn_dir(n) / name
