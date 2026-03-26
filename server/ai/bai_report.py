from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.ai.bai_report import BAIReport, attach_bai_report, build_bai_report


__all__ = ["BAIReport", "attach_bai_report", "build_bai_report"]
