from __future__ import annotations

from types import SimpleNamespace

from engine.ai import OrderValidationContext, validate_orders
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import Posture, Side, UnitState, UnitType


def _snapshot() -> SimpleNamespace:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="LUNGA", name="Lunga", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="TULAGI", name="Tulagi", terrain=Terrain.JUNGLE))
    game_map.add_tile(MapTile(tile_id="BASE", name="Base", terrain=Terrain.URBAN))
    return SimpleNamespace(
        side="AXIS",
        game_map=game_map,
        friendly_units=[
            UnitState(
                id="AX-1",
                name="Axis One",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=100,
                fatigue=5,
                morale=70,
                supply=80,
                readiness=85,
                location_id="LUNGA",
                posture=Posture.DEFEND,
            ),
            UnitState(
                id="AX-2",
                name="Axis Two",
                side=Side.AXIS,
                unit_type=UnitType.INFANTRY,
                strength=90,
                fatigue=10,
                morale=65,
                supply=75,
                readiness=70,
                location_id="BASE",
                posture=Posture.HOLD,
            ),
        ],
        known_locations=["LUNGA", "TULAGI", "BASE"],
    )


def test_bai_validator_filters_empty_unknown_and_impossible_orders():
    context = OrderValidationContext.from_snapshot(_snapshot())
    result = validate_orders(
        [
            {},
            {"type": "move", "unit_id": "AL-1", "target": "LUNGA", "posture": "ATTACK"},
            {"type": "move", "unit_id": "AX-1", "target": "UNKNOWN", "posture": "ATTACK"},
            {"type": "bombard", "unit_id": "AX-1", "target": "LUNGA", "posture": "ATTACK"},
            {"type": "move", "unit_id": "AX-1", "target": "TULAGI", "posture": "BROKEN"},
        ],
        context,
    )

    assert result.orders == [{"type": "move", "unit_id": "AX-1", "target": "TULAGI", "posture": "HOLD"}]
    codes = {item["code"] for item in result.diagnostics}
    assert {"order.empty_action", "order.unknown_or_wrong_side_unit", "order.unknown_target", "order.unsupported_type", "order.invalid_posture"} <= codes


def test_bai_validator_drops_duplicate_conflicts_and_generates_fallback_when_needed():
    context = OrderValidationContext.from_snapshot(_snapshot())

    duplicate_result = validate_orders(
        [
            {"type": "move", "unit_id": "AX-1", "target": "TULAGI", "posture": "MOVE"},
            {"type": "move", "unit_id": "AX-1", "target": "TULAGI", "posture": "MOVE"},
            {"type": "move", "unit_id": "AX-1", "target": "BASE", "posture": "DEFEND"},
        ],
        context,
    )

    assert duplicate_result.orders == [{"type": "move", "unit_id": "AX-1", "target": "TULAGI", "posture": "MOVE"}]
    duplicate_codes = [item["code"] for item in duplicate_result.diagnostics]
    assert "order.duplicate_redundant" in duplicate_codes
    assert "order.conflicting_duplicate" in duplicate_codes

    fallback_result = validate_orders([{}, {"unit_id": "AX-1", "target": "NOPE"}], context)

    assert fallback_result.orders == [{"type": "move", "unit_id": "AX-1", "target": "LUNGA", "posture": "HOLD"}]
    assert any(item["code"] == "order.fallback_hold_generated" for item in fallback_result.diagnostics)
