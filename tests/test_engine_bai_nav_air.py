from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from engine.ai import (
    BAIController,
    OperationCandidate,
    StrategicDirective,
    build_runtime_behavior_profile,
    plan_nav_air_support,
)
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.time_system import GameTime
from engine.core.unit_model import Posture, Side, UnitRepository, UnitState, UnitType


def _game_map() -> GameMap:
    game_map = GameMap()
    lunga = MapTile(tile_id="LUNGA", name="Lunga", terrain=Terrain.PLAINS, is_airfield=True)
    harbor = MapTile(tile_id="HARBOR", name="Harbor", terrain=Terrain.COAST)
    harbor.is_port = True
    enemy_port = MapTile(tile_id="ENEMY_PORT", name="Enemy Port", terrain=Terrain.COAST)
    enemy_port.is_port = True
    sea = MapTile(tile_id="SEA", name="Sea Lane", terrain=Terrain.OCEAN)
    ridge = MapTile(tile_id="RIDGE", name="Ridge", terrain=Terrain.MOUNTAIN)
    for tile in (lunga, harbor, enemy_port, sea, ridge):
        game_map.add_tile(tile)
    return game_map


def _directive(posture: str, objective: str) -> StrategicDirective:
    return StrategicDirective(
        directive_id=f"axis_{posture.lower()}_{objective.lower()}",
        side="AXIS",
        posture=posture,
        main_objective=objective,
        metadata={"reserve_fraction": 0.25},
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


def test_bai_nav_air_stub_prioritizes_cap_and_convoy_escort_under_threat():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=2,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-AIR",
                name="11th Air Flotilla",
                side=Side.AXIS,
                unit_type=UnitType.AIR,
                strength=90,
                fatigue=5,
                morale=70,
                supply=90,
                readiness=85,
                location_id="RIDGE",
                posture=Posture.HOLD,
            ),
            UnitState(
                id="AX-TF",
                name="Cruiser Task Force",
                side=Side.AXIS,
                unit_type=UnitType.NAVAL,
                strength=120,
                fatigue=10,
                morale=70,
                supply=85,
                readiness=80,
                location_id="SEA",
                posture=Posture.HOLD,
            ),
            UnitState(
                id="AX-GARRISON",
                name="Harbor Garrison",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=70,
                fatigue=10,
                morale=65,
                supply=75,
                readiness=60,
                location_id="LUNGA",
                posture=Posture.DEFEND,
            ),
        ],
        enemy_units=[
            UnitState(
                id="AL-RAIDERS",
                name="Raider Group",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=65,
                fatigue=10,
                morale=60,
                supply=70,
                readiness=60,
                location_id="LUNGA",
                posture=Posture.ATTACK,
            )
        ],
        objectives=[{"location_id": "LUNGA", "side": "AXIS", "value": 85}],
        supply_sources=[{"location_id": "HARBOR", "side": "AXIS", "daily_supply": 95}],
        known_locations=["LUNGA", "HARBOR", "ENEMY_PORT", "SEA", "RIDGE"],
    )

    plan = plan_nav_air_support(
        snapshot,
        _directive("DEFENSIVE", "LUNGA"),
        _operation("hold_line", "LUNGA", "DEFENSIVE"),
        build_runtime_behavior_profile(),
    )

    assert len(plan.orders) == 2

    air_intent = next(intent for intent in plan.intents if intent.unit_id == "AX-AIR")
    naval_intent = next(intent for intent in plan.intents if intent.unit_id == "AX-TF")

    assert air_intent.metadata["decision_type"] == "cap"
    assert air_intent.target_location_id == "LUNGA"
    assert air_intent.posture == "DEFEND"

    assert naval_intent.metadata["decision_type"] == "escort"
    assert naval_intent.target_location_id == "HARBOR"
    assert naval_intent.posture == "DEFEND"
    assert all(order["posture"] != "ATTACK" for order in plan.orders)


def test_bai_nav_air_stub_strikes_exposed_high_value_targets_when_safe():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=3,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-AIR",
                name="Carrier Air Group",
                side=Side.AXIS,
                unit_type=UnitType.AIR,
                strength=105,
                fatigue=5,
                morale=75,
                supply=90,
                readiness=90,
                location_id="SEA",
                posture=Posture.HOLD,
            )
        ],
        enemy_units=[
            UnitState(
                id="AL-PORT",
                name="Port Defense Battalion",
                side=Side.ALLIED,
                unit_type=UnitType.INFANTRY,
                strength=40,
                fatigue=15,
                morale=55,
                supply=55,
                readiness=50,
                location_id="ENEMY_PORT",
                posture=Posture.DEFEND,
            )
        ],
        objectives=[{"location_id": "ENEMY_PORT", "side": "ALLIED", "value": 120}],
        supply_sources=[{"location_id": "ENEMY_PORT", "side": "ALLIED", "daily_supply": 35}],
        known_locations=["LUNGA", "HARBOR", "ENEMY_PORT", "SEA", "RIDGE"],
    )

    plan = plan_nav_air_support(
        snapshot,
        _directive("OFFENSIVE", "ENEMY_PORT"),
        _operation("attack_objective", "ENEMY_PORT", "OFFENSIVE"),
        build_runtime_behavior_profile({"axis": {"aggression": 0.9, "risk_tolerance": 0.9}}),
    )

    assert len(plan.orders) == 1
    assert plan.orders[0]["unit_id"] == "AX-AIR"
    assert plan.orders[0]["target"] == "ENEMY_PORT"
    assert plan.orders[0]["posture"] == "ATTACK"
    assert plan.intents[0].metadata["decision_type"] == "air_strike"


def test_bai_nav_air_stub_avoids_major_naval_suicide_routing():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=4,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            UnitState(
                id="AX-FLEET",
                name="Carrier Task Force",
                side=Side.AXIS,
                unit_type=UnitType.NAVAL,
                strength=120,
                fatigue=10,
                morale=75,
                supply=88,
                readiness=82,
                location_id="SEA",
                posture=Posture.HOLD,
            )
        ],
        enemy_units=[
            UnitState(
                id="AL-SCREEN",
                name="Heavy Naval Screen",
                side=Side.ALLIED,
                unit_type=UnitType.NAVAL,
                strength=180,
                fatigue=5,
                morale=75,
                supply=85,
                readiness=85,
                location_id="ENEMY_PORT",
                posture=Posture.DEFEND,
            )
        ],
        objectives=[{"location_id": "ENEMY_PORT", "side": "ALLIED", "value": 100}],
        supply_sources=[{"location_id": "HARBOR", "side": "AXIS", "daily_supply": 80}],
        known_locations=["LUNGA", "HARBOR", "ENEMY_PORT", "SEA", "RIDGE"],
    )

    plan = plan_nav_air_support(
        snapshot,
        _directive("OFFENSIVE", "ENEMY_PORT"),
        _operation("attack_objective", "ENEMY_PORT", "OFFENSIVE"),
        build_runtime_behavior_profile({"axis": {"aggression": 0.85}}),
    )

    assert len(plan.orders) == 1
    assert plan.orders[0]["unit_id"] == "AX-FLEET"
    assert plan.orders[0]["posture"] != "ATTACK"
    assert plan.intents[0].metadata["decision_type"] in {"escort", "safe_harbor"}
    assert plan.orders[0]["target"] == "HARBOR"


def test_bai_controller_includes_nav_air_support_orders_in_tactical_report():
    game_map = _game_map()
    units = UnitRepository()
    units.add(
        UnitState(
            id="AX-INF",
            name="2nd Division",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=95,
            fatigue=10,
            morale=65,
            supply=75,
            readiness=62,
            location_id="RIDGE",
            posture=Posture.DEFEND,
        )
    )
    units.add(
        UnitState(
            id="AX-AIR",
            name="11th Air Flotilla",
            side=Side.AXIS,
            unit_type=UnitType.AIR,
            strength=92,
            fatigue=5,
            morale=72,
            supply=90,
            readiness=88,
            location_id="LUNGA",
            posture=Posture.HOLD,
        )
    )
    units.add(
        UnitState(
            id="AX-TF",
            name="Cruiser Task Force",
            side=Side.AXIS,
            unit_type=UnitType.NAVAL,
            strength=115,
            fatigue=8,
            morale=70,
            supply=84,
            readiness=80,
            location_id="SEA",
            posture=Posture.HOLD,
        )
    )
    units.add(
        UnitState(
            id="AL-PORT",
            name="Port Defense Battalion",
            side=Side.ALLIED,
            unit_type=UnitType.INFANTRY,
            strength=45,
            fatigue=10,
            morale=60,
            supply=60,
            readiness=55,
            location_id="ENEMY_PORT",
            posture=Posture.DEFEND,
        )
    )

    state = DummyEngineState(
        time=GameTime(day=3, phase="day"),
        game_map=game_map,
        units=units,
        meta={
            "id": "support_test",
            "name": "Support Test",
            "objectives": [{"location_id": "ENEMY_PORT", "side": "ALLIED", "value": 120}],
            "supply_sources": [{"location_id": "HARBOR", "side": "AXIS", "daily_supply": 85}],
        },
    )

    result = BAIController().plan_turn(
        state,
        side="AXIS",
        engine_config={"axis": {"aggression": 0.9, "risk_tolerance": 0.85, "reserve_commitment": 0.2}},
    )

    ordered_units = {order["unit_id"] for order in result.orders}
    assert {"AX-INF", "AX-AIR", "AX-TF"} <= ordered_units

    support_intents = [
        intent
        for intent in result.report["bai_report"]["tactical_intents"]
        if intent["unit_id"] in {"AX-AIR", "AX-TF"}
    ]
    decision_types = {intent["metadata"]["decision_type"] for intent in support_intents}

    assert support_intents
    assert any(decision_type in {"cap", "air_strike", "air_loiter"} for decision_type in decision_types)
    assert any(decision_type in {"escort", "safe_harbor", "naval_strike", "naval_loiter"} for decision_type in decision_types)
