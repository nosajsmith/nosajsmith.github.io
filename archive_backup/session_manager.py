# session_manager.py — create timestamped session dirs for headless runs
from __future__ import annotations
from pathlib import Path
from datetime import datetime

class SessionManager:
    def __init__(self, base_dir: str = "runs"):
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def new_session_dir(self, tag: str = "") -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"session_{stamp}{('_' + tag) if tag else ''}"
        d = self.base / name
        d.mkdir(parents=True, exist_ok=True)
        return d
