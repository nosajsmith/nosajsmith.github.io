from __future__ import annotations

from pathlib import Path

from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.config_merge import apply_profile_overrides, merge_ai_config
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.runners import execute_pressure_sweep, execute_single_run


ROOT = Path(__file__).resolve().parents[1]


def test_bai_warlab_config_merge_infers_side_and_applies_defaults():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    resolved = loader.resolve_profiles("korea_nkpa_shock", "aggressive", "default")
    merged = merge_ai_config(resolved)

    assert merged["profile_selection"]["doctrine"] == "korea_nkpa_shock"
    assert merged["profile_selection"]["personality"] == "aggressive"
    assert merged["profile_selection"]["tuning"] == "default"
    assert merged["ai_side"] == "AXIS"
    assert merged["run"]["attack_supply_floor"] == 45
    assert merged["run"]["rest_fatigue_floor"] == 65
    assert "attack_supply_floor" in merged["defaults_applied"]["run"]


def test_bai_warlab_single_run_exposes_injected_settings_in_metadata():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=7,
            max_steps=2,
        ),
        loader,
    )

    assert result.ok is True
    assert result.run_options["engine_received_settings"] is True
    assert result.run_options["profile_selection"] == {
        "doctrine": "korea_nkpa_shock",
        "personality": "aggressive",
        "tuning": "default",
    }
    assert result.run_options["engine_config"]["ai_side"] == "AXIS"
    assert result.summary["ai_side"] == "AXIS"


def test_bai_warlab_config_merge_falls_back_cleanly_for_missing_optional_settings(tmp_path: Path):
    config_root = tmp_path / "configs"
    (config_root / "doctrines").mkdir(parents=True)
    (config_root / "personalities").mkdir(parents=True)
    (config_root / "tuning").mkdir(parents=True)

    (config_root / "doctrines" / "demo.yaml").write_text(
        "name: demo\naxis: {}\nrun: {}\nmetadata: {}\n",
        encoding="utf-8",
    )
    (config_root / "personalities" / "demo.yaml").write_text(
        "name: demo\naxis: {}\nrun: {}\nmetadata: {}\n",
        encoding="utf-8",
    )
    (config_root / "tuning" / "demo.yaml").write_text(
        "name: demo\naxis: {}\nrun: {}\nmetadata: {}\n",
        encoding="utf-8",
    )

    loader = ConfigLoader(config_root)
    resolved = loader.resolve_profiles("demo", "demo", "demo")
    merged = merge_ai_config(resolved)

    assert merged["ai_side"] == "ALLIED"
    assert merged["axis"]["aggression"] == 0.5
    assert merged["axis"]["breakthrough_focus"] == 0.5
    assert merged["run"]["attack_readiness_floor"] == 45
    assert merged["warnings"] == ["No explicit AI side configured; defaulting to ALLIED."]


def test_bai_warlab_runtime_overrides_apply_after_profile_merge():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    resolved = loader.resolve_profiles("korea_nkpa_shock", "aggressive", "default")
    overridden = apply_profile_overrides(
        resolved,
        axis_overrides={"caution_bias": 0.1},
        run_overrides={"attack_supply_floor": 60},
    )
    merged = merge_ai_config(overridden)

    assert merged["axis"]["caution_bias"] == 0.1
    assert merged["run"]["attack_supply_floor"] == 60
    assert "Applied runtime axis overrides." in overridden.warnings
    assert "Applied runtime run overrides." in overridden.warnings


def test_bai_warlab_pressure_sweep_uses_allowlisted_runtime_overrides():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_pressure_sweep(
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        parameter="attack_supply_floor",
        values=[35, 55],
        loader=loader,
        seed=7,
        max_steps=2,
    )

    assert result.ok is True
    assert result.parameter == "attack_supply_floor"
    assert len(result.runs) == 2
    assert result.runs[0].resolved_profile["config_provenance"]["run_overrides"]["attack_supply_floor"] == 35
    assert result.comparison["points"][1]["delta_vs_first"]["pressure_peak_score"] is not None
