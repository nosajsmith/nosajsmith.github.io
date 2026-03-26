from __future__ import annotations

from pathlib import Path


BAI_WARLAB_VERSION = "0.1.0"
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
CONFIG_ROOT = PROJECT_ROOT / "configs" / "ai"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "bai_warlab"

