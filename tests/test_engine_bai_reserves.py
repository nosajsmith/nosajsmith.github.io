from __future__ import annotations

from types import SimpleNamespace

from engine.ai import OperationCandidate, ReservePlan, StrategicDirective, build_runtime_behavior_profile, plan_reserves
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import Posture, Side, UnitState, UnitType


def _game_map() -> GameMap:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="LINE", name="Line", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="OBJ", name="Objective", terrain=Terrain.URBAN))
    game_map.add_tile(MapTile(tile_id="BREACH", name="Breach", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="RESERVE", name="Reserve", terrain=Terrain.MOUNTAIN))
    return game_map


def _directive(posture: str, objective: str, reserve_fraction: float = 0.4) -> StrategicDirective:
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


def _unit(unit_id: str, location_id: str, strength: int = 100, readiness: int = 70, supply: int = 80) -> UnitState:
    return UnitState(
        id=unit_id,
        name=unit_id,
        side=Side.AXIS,
        unit_type=UnitType.INFANTRY,
        strength=strength,
        fatigue=10,
        morale=65,
        supply=supply,
        readiness=readiness,
        location_id=location_id,
        posture=Posture.HOLD,
    )


def _enemy(unit_id: str, location_id: str, strength: int = 100, readiness: int = 65, supply: int = 75) -> UnitState:
    return UnitState(
        id=unit_id,
        name=unit_id,
        side=Side.ALLIED,
        unit_type=UnitType.INFANTRY,
        strength=strength,
        fatigue=10,
        morale=65,
        supply=supply,
        readiness=readiness,
        location_id=location_id,
        posture=Posture.DEFEND,
    )


def test_bai_reserve_logic_holds_configured_fraction_by_default():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=3,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            _unit("AX-1", "LINE", readiness=85),
            _unit("AX-2", "LINE", readiness=80),
            _unit("AX-3", "RESERVE", readiness=75),
            _unit("AX-4", "RESERVE", readiness=70),
        ],
        enemy_units=[_enemy("AL-1", "OBJ", strength=70)],
        objectives=[
            {"location_id": "LINE", "side": "AXIS", "value": 40},
            {"location_id": "OBJ", "side": "ALLIED", "value": 75},
        ],
        known_locations=["LINE", "OBJ", "BREACH", "RESERVE"],
    )

    plan = plan_reserves(
        snapshot,
        _directive("CONTAIN", "OBJ", reserve_fraction=0.5),
        _operation("hold_line", "OBJ", "CONTAIN"),
        build_runtime_behavior_profile(),
    )

    assert isinstance(plan, ReservePlan)
    assert plan.target_fraction == 0.5
    assert plan.target_count == 2
    assert plan.held_count == 2
    assert plan.committed_reserve_ids == []
    assert plan.commitment_state == "HOLDING_RESERVE"
    assert "target reserve fraction of 0.50" in plan.rationale


def test_bai_reserve_logic_commits_for_critical_objective():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=4,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            _unit("AX-1", "OBJ", strength=90, readiness=82),
            _unit("AX-2", "LINE", strength=100, readiness=78),
            _unit("AX-3", "RESERVE", strength=105, readiness=88),
            _unit("AX-4", "RESERVE", strength=95, readiness=76),
        ],
        enemy_units=[_enemy("AL-1", "OBJ", strength=115), _enemy("AL-2", "OBJ", strength=30)],
        objectives=[{"location_id": "OBJ", "side": "AXIS", "value": 90}],
        known_locations=["LINE", "OBJ", "BREACH", "RESERVE"],
    )

    plan = plan_reserves(
        snapshot,
        _directive("DEFENSIVE", "OBJ", reserve_fraction=0.5),
        _operation("hold_line", "OBJ", "DEFENSIVE"),
        build_runtime_behavior_profile(),
    )

    assert plan.triggers["objective_critical"] is True
    assert plan.commitment_state == "CRITICAL_OBJECTIVE_COMMIT"
    assert len(plan.committed_reserve_ids) == 1
    assert plan.held_count == 1
    assert "critical" in plan.rationale.lower()


def test_bai_reserve_logic_commits_when_line_is_collapsing():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=5,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            _unit("AX-1", "LINE", strength=60, readiness=70),
            _unit("AX-2", "RESERVE", strength=100, readiness=86),
            _unit("AX-3", "RESERVE", strength=95, readiness=81),
            _unit("AX-4", "OBJ", strength=80, readiness=74),
        ],
        enemy_units=[
            _enemy("AL-1", "LINE", strength=120),
            _enemy("AL-2", "OBJ", strength=110),
        ],
        objectives=[
            {"location_id": "LINE", "side": "AXIS", "value": 50},
            {"location_id": "OBJ", "side": "AXIS", "value": 70},
        ],
        known_locations=["LINE", "OBJ", "BREACH", "RESERVE"],
    )

    plan = plan_reserves(
        snapshot,
        _directive("DEFENSIVE", "OBJ", reserve_fraction=0.5),
        _operation("reinforce_sector", "OBJ", "DEFENSIVE"),
        build_runtime_behavior_profile(),
    )

    assert plan.triggers["line_collapsing"] is True
    assert plan.commitment_state == "EMERGENCY_COMMIT"
    assert len(plan.committed_reserve_ids) >= 1
    assert plan.held_count < plan.target_count
    assert "line collapse" in plan.rationale.lower()


def test_bai_reserve_logic_commits_for_favorable_counterattack_window():
    snapshot = SimpleNamespace(
        side="AXIS",
        day=6,
        phase="day",
        game_map=_game_map(),
        friendly_units=[
            _unit("AX-1", "BREACH", strength=120, readiness=80, supply=82),
            _unit("AX-2", "RESERVE", strength=110, readiness=88, supply=85),
            _unit("AX-3", "RESERVE", strength=100, readiness=83, supply=80),
            _unit("AX-4", "LINE", strength=90, readiness=70, supply=75),
        ],
        enemy_units=[_enemy("AL-1", "BREACH", strength=140), _enemy("AL-2", "LINE", strength=60)],
        objectives=[{"location_id": "BREACH", "side": "AXIS", "value": 45}],
        known_locations=["LINE", "OBJ", "BREACH", "RESERVE"],
    )

    plan = plan_reserves(
        snapshot,
        _directive("CONTAIN", "BREACH", reserve_fraction=0.5),
        _operation("counterattack_local_breach", "BREACH", "CONTAIN"),
        build_runtime_behavior_profile(),
    )

    assert plan.triggers["counterattack_window"] is True
    assert plan.commitment_state == "COUNTERATTACK_COMMIT"
    assert len(plan.committed_reserve_ids) == 1
    assert "counterattack window" in plan.rationale.lower()
