from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from engine.ai import BAIController, assess_defensive_situation, build_runtime_behavior_profile, plan_ground_tactical
from engine.ai.bai_models import OperationCandidate, StrategicDirective
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.time_system import GameTime
from engine.core.unit_model import Posture, Side, UnitRepository, UnitState, UnitType


def _game_map() -> GameMap:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="FRONT", name="Front", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="BASE", name="Base", terrain=Terrain.URBAN))
    game_map.add_tile(MapTile(tile_id="RIDGE", name="Ridge", terrain=Terrain.MOUNTAIN))
    game_map.add_tile(MapTile(tile_id="BREACH", name="Breach", terrain=Terrain.PLAINS))
    return game_map


def _directive(posture: str, objective: str, reserve_fraction: float = 0.35) -> StrategicDirective:
    return StrategicDirective(
        directive_id=f"axis_{posture.lower()}_{objective.lower()}",
        side="AXIS",
        posture=posture,
        main_objective=objective,
        metadata={"reserve_fraction": reserve_fraction},
    )


def _operation(operation_type: str, objective: str, posture: str) -> OperationCandidate:
    return OperationCandidate(
        operation_id=f"axis_{operation_type}_{objective.lower()}",
        name=f"{operation_type}::{objective}",
        operation_type=operation_type,
        posture=posture,
        target_objective=objective,
        selected=True,
    )


@dataclass
class DummyEngineState:
    time: GameTime
    game_map: GameMap
    units: UnitRepository
    meta: dict


def test_bai_defense_pack_shortens_exposed_line_and_defends_key_terrain():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=3,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-SCREEN",
                name="Forward Screen",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=70,
                fatigue=35,
                morale=55,
                supply=55,
                readiness=60,
                location_id="FRONT",
                posture=Posture.DEFEND,
            ),
            UnitState(
                id="AX-ANCHOR",
                name="Base Garrison",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=105,
                fatigue=10,
                morale=70,
                supply=80,
                readiness=78,
                location_id="BASE",
                posture=Posture.DEFEND,
            ),
        ],
        enemy_units=[
            UnitState(
                id="AL-PRESS",
                name="Pressure Group",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=125,
                fatigue=10,
                morale=65,
                supply=75,
                readiness=70,
                location_id="FRONT",
                posture=Posture.ATTACK,
            )
        ],
        objectives=[{"location_id": "BASE", "side": "AXIS", "value": 80}],
        known_locations=["FRONT", "BASE", "RIDGE", "BREACH"],
    )
    directive = _directive("DEFENSIVE", "BASE")
    operation = _operation("hold_line", "BASE", "DEFENSIVE")
    runtime_profile = build_runtime_behavior_profile()

    assessment = assess_defensive_situation(
        snapshot,
        directive,
        operation,
        runtime_profile,
        {
            "FRONT": {
                "location_id": "FRONT",
                "game_map": snapshot.game_map,
                "friendly_strength": 70.0,
                "enemy_strength": 125.0,
                "friendly_objective_value": 0.0,
                "enemy_objective_value": 0.0,
                "objective_value": 0.0,
                "terrain_value": 1.0,
                "control": None,
            },
            "BASE": {
                "location_id": "BASE",
                "game_map": snapshot.game_map,
                "friendly_strength": 105.0,
                "enemy_strength": 0.0,
                "friendly_objective_value": 80.0,
                "enemy_objective_value": 0.0,
                "objective_value": 80.0,
                "terrain_value": 1.5,
                "control": "AXIS",
            },
            "RIDGE": {
                "location_id": "RIDGE",
                "game_map": snapshot.game_map,
                "friendly_strength": 0.0,
                "enemy_strength": 0.0,
                "friendly_objective_value": 0.0,
                "enemy_objective_value": 0.0,
                "objective_value": 0.0,
                "terrain_value": 1.4,
                "control": None,
            },
            "BREACH": {
                "location_id": "BREACH",
                "game_map": snapshot.game_map,
                "friendly_strength": 0.0,
                "enemy_strength": 0.0,
                "friendly_objective_value": 0.0,
                "enemy_objective_value": 0.0,
                "objective_value": 0.0,
                "terrain_value": 1.0,
                "control": None,
            },
        },
    )

    assert assessment.active is True
    assert assessment.fallback_anchor == "BASE"
    assert assessment.collapse_risk in {"MEDIUM", "HIGH"}
    assert "BASE" in assessment.key_terrain_locations

    plan = plan_ground_tactical(snapshot, directive, operation, runtime_profile)
    screen_intent = next(intent for intent in plan.intents if intent.unit_id == "AX-SCREEN")
    anchor_intent = next(intent for intent in plan.intents if intent.unit_id == "AX-ANCHOR")

    assert screen_intent.target_location_id == "BASE"
    assert screen_intent.metadata["decision_type"] == "shorten_line"
    assert anchor_intent.target_location_id == "BASE"
    assert anchor_intent.metadata["decision_type"] == "defend_key_terrain"
    assert plan.metadata["defense_assessment"]["fallback_anchor"] == "BASE"


def test_bai_defense_pack_counterattacks_selectively_when_window_is_favorable():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=4,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-SPEAR",
                name="Counterattack Group",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=130,
                fatigue=10,
                morale=70,
                supply=85,
                readiness=82,
                location_id="BREACH",
                posture=Posture.DEFEND,
            ),
            UnitState(
                id="AX-RESERVE",
                name="Reserve Battalion",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=100,
                fatigue=8,
                morale=68,
                supply=80,
                readiness=78,
                location_id="RIDGE",
                posture=Posture.HOLD,
            ),
        ],
        enemy_units=[
            UnitState(
                id="AL-WEDGE",
                name="Enemy Wedge",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=90,
                fatigue=15,
                morale=55,
                supply=65,
                readiness=60,
                location_id="BREACH",
                posture=Posture.ATTACK,
            )
        ],
        objectives=[{"location_id": "BREACH", "side": "AXIS", "value": 60}],
        known_locations=["FRONT", "BASE", "RIDGE", "BREACH"],
    )

    plan = plan_ground_tactical(
        snapshot,
        _directive("DEFENSIVE", "BREACH"),
        _operation("counterattack_local_breach", "BREACH", "DEFENSIVE"),
        build_runtime_behavior_profile(),
    )

    spear_intent = next(intent for intent in plan.intents if intent.unit_id == "AX-SPEAR")

    assert spear_intent.posture == "ATTACK"
    assert spear_intent.metadata["decision_type"] == "counterattack"
    assert spear_intent.metadata["counterattack_window"] is True


def test_bai_controller_reports_defensive_assessment():
    game_map = _game_map()
    units = UnitRepository()
    units.add(
        UnitState(
            id="AX-SCREEN",
            name="Forward Screen",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=70,
            fatigue=35,
            morale=55,
            supply=55,
            readiness=60,
            location_id="FRONT",
            posture=Posture.DEFEND,
        )
    )
    units.add(
        UnitState(
            id="AX-ANCHOR",
            name="Base Garrison",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=105,
            fatigue=10,
            morale=70,
            supply=80,
            readiness=78,
            location_id="BASE",
            posture=Posture.DEFEND,
        )
    )
    units.add(
        UnitState(
            id="AL-PRESS",
            name="Pressure Group",
            side=Side.ALLIED,
            unit_type=UnitType.INFANTRY,
            strength=125,
            fatigue=10,
            morale=65,
            supply=75,
            readiness=70,
            location_id="FRONT",
            posture=Posture.ATTACK,
        )
    )
    state = DummyEngineState(
        time=GameTime(day=3, phase="day"),
        game_map=game_map,
        units=units,
        meta={"objectives": [{"location_id": "BASE", "side": "AXIS", "value": 80}]},
    )

    result = BAIController().plan_turn(
        state,
        side="AXIS",
        engine_config={
            "axis": {
                "aggression": 0.2,
                "caution_bias": 0.9,
                "reserve_preservation_bias": 0.8,
                "counterattack_bias": 0.55,
            }
        },
    )

    assessment = result.report["bai_report"]["defense_assessment"]
    decision_types = {
        intent["metadata"]["decision_type"]
        for intent in result.report["bai_report"]["tactical_intents"]
    }

    assert assessment["active"] is True
    assert assessment["fallback_anchor"] == "BASE"
    assert assessment["collapse_risk"] in {"MEDIUM", "HIGH"}
    assert "BASE" in assessment["key_terrain_locations"]
    assert {"shorten_line", "defend_key_terrain"} & decision_types
