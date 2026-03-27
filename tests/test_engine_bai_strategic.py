from __future__ import annotations

from types import SimpleNamespace

from engine.ai import StrategicDirective, StrategicMemory, build_runtime_behavior_profile, plan_strategic_directive
from engine.core.unit_model import Posture, Side, UnitState, UnitType


def _build_snapshot(day: int = 2) -> SimpleNamespace:
    friendly_units = [
        UnitState(
            id="JP-35BDE",
            name="35th Infantry Brigade",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=90,
            fatigue=5,
            morale=65,
            supply=70,
            readiness=55,
            location_id="TULAGI",
            posture=Posture.DEFEND,
        ),
        UnitState(
            id="JP-2DIV",
            name="2nd Division",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=80,
            fatigue=15,
            morale=60,
            supply=75,
            readiness=58,
            location_id="MANTANIKAU",
            posture=Posture.HOLD,
        ),
    ]
    enemy_units = [
        UnitState(
            id="US-1MAR",
            name="1st Marine Division",
            side=Side.ALLIED,
            unit_type=UnitType.INFANTRY,
            strength=100,
            fatigue=10,
            morale=70,
            supply=80,
            readiness=60,
            location_id="LUNGA",
            posture=Posture.DEFEND,
        )
    ]
    return SimpleNamespace(
        side="AXIS",
        day=day,
        phase="day",
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=[
            {"location_id": "LUNGA", "side": "ALLIED", "value": 50},
            {"location_id": "TULAGI", "side": "ALLIED", "value": 100},
            {"location_id": "TULAGI", "side": "AXIS", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "MANTANIKAU"],
    )


def test_bai_strategic_lite_produces_explainable_directive():
    directive, memory = plan_strategic_directive(_build_snapshot(), build_runtime_behavior_profile())

    assert isinstance(directive, StrategicDirective)
    assert isinstance(memory, StrategicMemory)
    assert directive.posture in {"OFFENSIVE", "DEFENSIVE", "CONTAIN"}
    assert directive.main_objective in {"LUNGA", "TULAGI"}
    assert directive.metadata["front_priority"].startswith(("MAIN_EFFORT::", "SCREEN::", "HOLD::"))
    assert directive.metadata["theater_priority"] in {"DECISIVE_ACTION", "THEATER_STABILIZATION", "CONTAIN_AND_SHAPE"}
    assert directive.metadata["reserve_fraction"] > 0
    assert "Objective rationale:" in directive.notes[1]
    assert directive.metadata["objective_explanation"]
    assert directive.metadata["candidate_scores"][0]["contain_reason"]


def test_bai_strategic_lite_keeps_directive_sticky_when_situation_is_stable():
    runtime_profile = build_runtime_behavior_profile()
    first_directive, memory = plan_strategic_directive(_build_snapshot(day=2), runtime_profile)
    second_directive, updated_memory = plan_strategic_directive(_build_snapshot(day=3), runtime_profile, memory)

    assert first_directive.posture == second_directive.posture
    assert first_directive.main_objective == second_directive.main_objective
    assert updated_memory.sticky_until_day >= 4
    assert "avoid posture whiplash" in " ".join(second_directive.notes).lower()
