from __future__ import annotations

from types import SimpleNamespace

from engine.ai import GroundTacticalPlan, OperationCandidate, StrategicDirective, build_runtime_behavior_profile, plan_ground_tactical
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import Posture, Side, UnitState, UnitType


def _game_map() -> GameMap:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="LUNGA", name="Lunga", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="TULAGI", name="Tulagi", terrain=Terrain.JUNGLE))
    game_map.add_tile(MapTile(tile_id="RIDGE", name="Ridge", terrain=Terrain.MOUNTAIN))
    game_map.add_tile(MapTile(tile_id="BASE", name="Base", terrain=Terrain.URBAN))
    return game_map


def _directive(posture: str, objective: str, reserve_fraction: float = 0.25) -> StrategicDirective:
    return StrategicDirective(
        directive_id="axis_strategic_day_3",
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


def test_bai_tactical_ground_v1_attacks_only_above_threshold_odds():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=3,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-STRONG",
                name="Strong Regiment",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=150,
                fatigue=5,
                morale=70,
                supply=85,
                readiness=80,
                location_id="LUNGA",
                posture=Posture.MOVE,
            ),
            UnitState(
                id="AX-WEAK",
                name="Weak Battalion",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=60,
                fatigue=10,
                morale=55,
                supply=70,
                readiness=55,
                location_id="RIDGE",
                posture=Posture.HOLD,
            ),
        ],
        enemy_units=[
            UnitState(
                id="AL-DEF",
                name="Allied Defenders",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=80,
                fatigue=10,
                morale=65,
                supply=80,
                readiness=65,
                location_id="TULAGI",
                posture=Posture.DEFEND,
            )
        ],
        objectives=[
            {"location_id": "TULAGI", "side": "ALLIED", "value": 100},
            {"location_id": "LUNGA", "side": "AXIS", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "RIDGE", "BASE"],
    )

    plan = plan_ground_tactical(
        snapshot,
        _directive("OFFENSIVE", "TULAGI"),
        _operation("attack_objective", "TULAGI", "OFFENSIVE"),
        build_runtime_behavior_profile(),
    )

    assert isinstance(plan, GroundTacticalPlan)
    attack_intents = [intent for intent in plan.intents if intent.posture == "ATTACK"]
    assert len(plan.orders) == 2
    assert len(attack_intents) == 1
    assert attack_intents[0].unit_id == "AX-STRONG"
    assert attack_intents[0].target_location_id == "TULAGI"
    assert all(intent.posture != "ATTACK" for intent in plan.intents if intent.unit_id == "AX-WEAK")


def test_bai_tactical_ground_v1_withdraws_from_exposed_salient_and_keeps_reserve():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=4,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-FWD",
                name="Forward Screen",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=65,
                fatigue=60,
                morale=50,
                supply=35,
                readiness=50,
                location_id="LUNGA",
                posture=Posture.DEFEND,
            ),
            UnitState(
                id="AX-RES",
                name="Reserve Regiment",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=110,
                fatigue=10,
                morale=70,
                supply=80,
                readiness=75,
                location_id="BASE",
                posture=Posture.HOLD,
            ),
        ],
        enemy_units=[
            UnitState(
                id="AL-PRESSURE",
                name="Enemy Pressure Group",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=130,
                fatigue=10,
                morale=70,
                supply=80,
                readiness=70,
                location_id="LUNGA",
                posture=Posture.ATTACK,
            )
        ],
        objectives=[
            {"location_id": "LUNGA", "side": "AXIS", "value": 40},
            {"location_id": "BASE", "side": "AXIS", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "RIDGE", "BASE"],
    )

    plan = plan_ground_tactical(
        snapshot,
        _directive("DEFENSIVE", "LUNGA", reserve_fraction=0.4),
        _operation("hold_line", "LUNGA", "DEFENSIVE"),
        build_runtime_behavior_profile(),
        reserve_ids=["AX-RES"],
    )

    forward_order = next(order for order in plan.orders if order["unit_id"] == "AX-FWD")
    reserve_order = next(order for order in plan.orders if order["unit_id"] == "AX-RES")

    assert forward_order["target"] == "BASE"
    assert forward_order["posture"] == "DEFEND"
    assert reserve_order["target"] == "BASE"
    assert reserve_order["posture"] in {"HOLD", "DEFEND"}
    assert any(intent.metadata["decision_type"] in {"withdraw", "shorten_line"} for intent in plan.intents if intent.unit_id == "AX-FWD")
    assert any(intent.metadata["reserve"] is True for intent in plan.intents if intent.unit_id == "AX-RES")


def test_bai_tactical_ground_v1_defends_valuable_ground_without_suicide_attack():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=5,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-GARRISON",
                name="Garrison",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=90,
                fatigue=15,
                morale=65,
                supply=75,
                readiness=60,
                location_id="TULAGI",
                posture=Posture.DEFEND,
            )
        ],
        enemy_units=[
            UnitState(
                id="AL-STACK",
                name="Allied Stack",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=140,
                fatigue=10,
                morale=70,
                supply=85,
                readiness=75,
                location_id="LUNGA",
                posture=Posture.DEFEND,
            )
        ],
        objectives=[
            {"location_id": "TULAGI", "side": "AXIS", "value": 75},
            {"location_id": "LUNGA", "side": "ALLIED", "value": 50},
        ],
        known_locations=["LUNGA", "TULAGI", "RIDGE", "BASE"],
    )

    plan = plan_ground_tactical(
        snapshot,
        _directive("DEFENSIVE", "TULAGI"),
        _operation("hold_line", "TULAGI", "DEFENSIVE"),
        build_runtime_behavior_profile(),
    )

    assert len(plan.orders) == 1
    assert plan.orders[0]["target"] == "TULAGI"
    assert plan.orders[0]["posture"] in {"DEFEND", "HOLD"}
    assert plan.intents[0].metadata["decision_type"] in {"hold_ground", "delay", "defend_key_terrain"}
    assert plan.intents[0].posture != "ATTACK"
