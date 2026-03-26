from __future__ import annotations

from pathlib import Path

import pytest

from tools.bai_warlab.config_loader import BAIWarLabConfigError, ConfigLoader
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.runners import execute_single_run


ROOT = Path(__file__).resolve().parents[1]


def test_bai_warlab_config_loader_merges_profiles():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    resolved = loader.resolve_profiles("korea_nkpa_shock", "aggressive", "offense_focus")
    assert resolved.doctrine.name == "korea_nkpa_shock"
    assert resolved.personality.name == "aggressive"
    assert resolved.tuning.name == "offense_focus"
    assert isinstance(resolved.merged_axis, dict)
    assert isinstance(resolved.merged_run, dict)


def test_bai_warlab_config_loader_missing_profile_is_clear():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    with pytest.raises(BAIWarLabConfigError) as excinfo:
        loader.resolve_profiles("missing_doctrine", "aggressive", "default")
    assert "Missing doctrines profile: missing_doctrine" in str(excinfo.value)


def test_bai_warlab_single_run_handles_missing_profile_gracefully():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="foundation_smoke.json",
            scenario_dir="synthetic_scenarios",
            doctrine="missing_doctrine",
            personality="aggressive",
            tuning="default",
            seed=1,
        ),
        loader,
    )
    assert result.ok is False
    assert result.error == "Missing doctrines profile: missing_doctrine"
    assert result.summary["terminal_status"] == "config_error"

