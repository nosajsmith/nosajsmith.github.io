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


def test_bai_warlab_korea_doctrine_pack_loads_with_distinct_values():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    un_doc = loader.load_doctrine("korea_un_combined_arms")
    chinese_doc = loader.load_doctrine("korea_chinese_mass_infiltration")
    nkpa_doc = loader.load_doctrine("korea_nkpa_shock")

    assert un_doc.metadata["doctrine_id"] == "korea_un_combined_arms"
    assert chinese_doc.metadata["doctrine_id"] == "korea_chinese_mass_infiltration"
    assert nkpa_doc.metadata["doctrine_id"] == "korea_nkpa_shock"

    assert un_doc.axis["logistics_emphasis"] != chinese_doc.axis["logistics_emphasis"]
    assert chinese_doc.axis["infiltration_bias"] != nkpa_doc.axis["infiltration_bias"]
    assert nkpa_doc.axis["breakthrough_focus"] != un_doc.axis["breakthrough_focus"]
    assert {un_doc.metadata["doctrine_kind"], chinese_doc.metadata["doctrine_kind"], nkpa_doc.metadata["doctrine_kind"]} == {
        "combined_arms",
        "infiltration",
        "shock",
    }


def test_bai_warlab_personality_pack_loads_with_distinct_values():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    historical = loader.load_personality("historical")
    aggressive = loader.load_personality("aggressive")
    cautious = loader.load_personality("cautious")
    adaptive = loader.load_personality("adaptive")

    assert historical.metadata["personality_id"] == "historical"
    assert aggressive.metadata["personality_id"] == "aggressive"
    assert cautious.metadata["personality_id"] == "cautious"
    assert adaptive.metadata["personality_id"] == "adaptive"

    assert aggressive.axis["aggression"] > historical.axis["aggression"] > cautious.axis["aggression"]
    assert cautious.axis["reserve_preservation_bias"] > aggressive.axis["reserve_preservation_bias"]
    assert adaptive.axis["adaptation_rate"] > historical.axis["adaptation_rate"]
    assert {
        historical.metadata["style"],
        aggressive.metadata["style"],
        cautious.metadata["style"],
        adaptive.metadata["style"],
    } == {
        "baseline_historical",
        "exploitative",
        "force_preservation",
        "situational",
    }


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
