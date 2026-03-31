from __future__ import annotations

from engine.engine_api import EngineAPI
from engine.core.time_system import GameTime
from engine.core.unit_model import Posture, Side, UnitRepository, UnitState, UnitType
from server.engine.staff.g8_objectives import G8Objectives


def _units_for_objectives() -> UnitRepository:
    repo = UnitRepository()
    repo.add(
        UnitState(
            id="US-1MAR",
            name="1st Marines",
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
    )
    repo.add(
        UnitState(
            id="JP-35BDE",
            name="35th Brigade",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=90,
            fatigue=5,
            morale=65,
            supply=70,
            readiness=55,
            location_id="TULAGI",
            posture=Posture.DEFEND,
        )
    )
    return repo


def test_objective_contest_rules_hold_contested_locations_neutral() -> None:
    units = _units_for_objectives()
    units.add(
        UnitState(
            id="JP-2DIV",
            name="2nd Division",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=75,
            fatigue=8,
            morale=62,
            supply=68,
            readiness=57,
            location_id="LUNGA",
            posture=Posture.ATTACK,
        )
    )
    objectives = G8Objectives(
        units,
        [{"location_id": "LUNGA", "side": "ALLIED", "value": 50, "description": "Hold Lunga."}],
    )

    objectives.on_day_end(GameTime(day=1, phase="day"))

    assert objectives.control_by_loc.get("LUNGA") is None
    assert objectives.vp[Side.ALLIED] == 0
    assert objectives.vp[Side.AXIS] == 0


def test_objective_control_and_scoring_award_once_per_capture() -> None:
    units = _units_for_objectives()
    objectives = G8Objectives(
        units,
        [{"location_id": "LUNGA", "side": "ALLIED", "value": 50, "description": "Hold Lunga."}],
    )

    objectives.on_day_end(GameTime(day=1, phase="day"))
    objectives.on_day_end(GameTime(day=2, phase="day"))

    assert objectives.control_by_loc["LUNGA"] == Side.ALLIED
    assert objectives.vp[Side.ALLIED] == 50
    assert objectives.vp[Side.AXIS] == 0
    assert len(objectives.events) == 1


def test_engine_api_move_action_uses_current_movement_semantics_v1() -> None:
    api = EngineAPI()
    api.load_scenario("mini_gc_1942")

    accepted = api.apply_player_action(
        {"type": "move", "unit_id": "US-1MAR", "target": "TULAGI", "posture": "ATTACK"}
    )
    rejected = api.apply_player_action(
        {"type": "move", "unit_id": "US-1MAR", "target": "NOPE", "posture": "MOVE"}
    )

    unit = api.units.get("US-1MAR")

    assert accepted["status"] == "ok"
    assert rejected["status"] == "error"
    assert unit is not None
    assert unit.location_id == "TULAGI"
    assert unit.posture == Posture.ATTACK


def test_engine_api_loads_server_scenario_directory_fallback() -> None:
    api = EngineAPI()

    meta = api.load_scenario("gc_1942_historical")

    assert meta["id"] == "gc_1942_historical"
    assert meta["name"] == "Guadalcanal 1942 (Historical Skeleton)"
