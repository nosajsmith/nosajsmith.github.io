from __future__ import annotations

from types import SimpleNamespace

from engine.ai import OperationCandidate, StrategicDirective, build_runtime_behavior_profile, plan_operational_layer
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import Posture, Side, UnitState, UnitType


def _build_game_map() -> GameMap:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="LUNGA", name="Lunga Point", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="TULAGI", name="Tulagi", terrain=Terrain.JUNGLE))
    game_map.add_tile(MapTile(tile_id="MANTANIKAU", name="Matanikau", terrain=Terrain.MOUNTAIN))
    return game_map


def _directive(posture: str = "CONTAIN") -> StrategicDirective:
    return StrategicDirective(
        directive_id="axis_strategic_day_2",
        side="AXIS",
        posture=posture,
        main_objective="TULAGI",
        notes=["Operational test directive."],
        metadata={
            "reserve_fraction": 0.4,
            "front_priority": "SCREEN::TULAGI",
            "theater_priority": "CONTAIN_AND_SHAPE",
        },
    )


def _stable_snapshot() -> SimpleNamespace:
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
        day=2,
        phase="day",
        game_map=_build_game_map(),
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=[
            {"location_id": "LUNGA", "side": "ALLIED", "value": 50},
            {"location_id": "TULAGI", "side": "ALLIED", "value": 100},
            {"location_id": "TULAGI", "side": "AXIS", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "MANTANIKAU"],
    )


def _stressed_snapshot() -> SimpleNamespace:
    friendly_units = [
        UnitState(
            id="JP-35BDE",
            name="35th Infantry Brigade",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=70,
            fatigue=60,
            morale=50,
            supply=35,
            readiness=50,
            location_id="TULAGI",
            posture=Posture.DEFEND,
        ),
        UnitState(
            id="JP-2DIV",
            name="2nd Division",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=82,
            fatigue=58,
            morale=58,
            supply=38,
            readiness=52,
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
            location_id="TULAGI",
            posture=Posture.ATTACK,
        )
    ]
    return SimpleNamespace(
        side="AXIS",
        day=4,
        phase="day",
        game_map=_build_game_map(),
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=[
            {"location_id": "TULAGI", "side": "AXIS", "value": 75},
            {"location_id": "LUNGA", "side": "ALLIED", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "MANTANIKAU"],
    )


def test_bai_operational_v1_generates_ranked_candidates_and_support_actions():
    plan = plan_operational_layer(_stable_snapshot(), _directive(), build_runtime_behavior_profile())

    assert isinstance(plan.primary_operation, OperationCandidate)
    assert 2 <= len(plan.candidates) <= 5
    assert sum(1 for candidate in plan.candidates if candidate.selected) == 1
    assert plan.primary_operation.selected is True
    assert plan.primary_operation.operation_id == plan.candidates[0].operation_id
    assert len(plan.support_actions) <= 2
    assert all(action["operation_id"] != plan.primary_operation.operation_id for action in plan.support_actions)
    assert plan.candidates[0].metadata["evaluation"]["dominant_reason"]


def test_bai_operational_v1_ranking_is_deterministic_for_same_inputs():
    snapshot = _stable_snapshot()
    directive = _directive()
    runtime_profile = build_runtime_behavior_profile()

    first = plan_operational_layer(snapshot, directive, runtime_profile)
    second = plan_operational_layer(snapshot, directive, runtime_profile)

    assert [candidate.to_dict() for candidate in first.candidates] == [candidate.to_dict() for candidate in second.candidates]
    assert first.primary_operation.to_dict() == second.primary_operation.to_dict()
    assert first.support_actions == second.support_actions
    assert first.primary_operation.metadata["evaluation"]["reasons"]


def test_bai_operational_v1_emits_withdraw_convoy_and_counterattack_when_pressure_demands_it():
    plan = plan_operational_layer(_stressed_snapshot(), _directive(posture="DEFENSIVE"), build_runtime_behavior_profile())

    operation_types = {candidate.operation_type for candidate in plan.candidates}

    assert 2 <= len(plan.candidates) <= 5
    assert "hold_line" in operation_types
    assert "withdraw_stronger_terrain" in operation_types
    assert "convoy_resupply" in operation_types
    assert "counterattack_local_breach" in operation_types
