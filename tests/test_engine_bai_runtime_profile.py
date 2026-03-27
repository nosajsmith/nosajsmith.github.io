from __future__ import annotations

from engine.ai.bai_doctrine import build_doctrine_profile
from engine.ai.bai_personality import apply_personality_overlay, build_runtime_behavior_profile


def test_bai_doctrine_profile_defaults_and_missing_fields_degrade_gracefully():
    empty_profile = build_doctrine_profile({})
    broken_profile = build_doctrine_profile(
        {
            "doctrine": {
                "axis": {
                    "aggression": "bad",
                    "logistics_emphasis": 0.82,
                    "reserve_commitment": None,
                },
                "run": {
                    "attack_supply_floor": "oops",
                    "fallback_posture": "invalid",
                },
            }
        }
    )

    assert empty_profile["axis"]["aggression"] == 0.5
    assert empty_profile["run"]["fallback_posture"] == "HOLD"
    assert "attack_supply_floor" in empty_profile["thresholds"]
    assert "objective_value" in empty_profile["weights"]

    assert broken_profile["axis"]["aggression"] == 0.5
    assert broken_profile["axis"]["logistics_emphasis"] == 0.82
    assert broken_profile["run"]["attack_supply_floor"] == 45
    assert broken_profile["run"]["fallback_posture"] == "HOLD"


def test_bai_personality_overlay_changes_effective_thresholds_and_weights():
    base = build_doctrine_profile(
        {
            "doctrine": {
                "axis": {
                    "aggression": 0.42,
                    "objective_discipline": 0.76,
                    "logistics_emphasis": 0.78,
                    "breakthrough_focus": 0.41,
                },
            }
        }
    )
    aggressive = apply_personality_overlay(
        base,
        {
            "personality": {
                "axis": {
                    "aggression": 0.9,
                    "caution_bias": 0.18,
                    "reserve_preservation_bias": 0.24,
                    "risk_tolerance": 0.88,
                }
            },
            "axis": {"breakthrough_focus": 0.91},
        },
    )
    cautious = build_runtime_behavior_profile(
        {
            "axis": {
                "aggression": 0.26,
                "caution_bias": 0.87,
                "reserve_preservation_bias": 0.83,
                "risk_tolerance": 0.22,
                "logistics_emphasis": 0.78,
                "objective_discipline": 0.76,
                "breakthrough_focus": 0.41,
            }
        }
    )

    assert aggressive["axis"]["aggression"] == 0.9
    assert aggressive["thresholds"]["attack_supply_floor"] < cautious["thresholds"]["attack_supply_floor"]
    assert aggressive["thresholds"]["attack_readiness_floor"] < cautious["thresholds"]["attack_readiness_floor"]
    assert aggressive["thresholds"]["reserve_target_fraction"] < cautious["thresholds"]["reserve_target_fraction"]
    assert aggressive["weights"]["enemy_objective"] > cautious["weights"]["enemy_objective"]
    assert aggressive["weights"]["risk_acceptance"] > cautious["weights"]["risk_acceptance"]
