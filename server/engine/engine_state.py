"""
Engine state snapshot for MWE.

Phase 8.1: Provide a JSON-serializable view of the current game state
that can be used by the bridge / UI.

We do NOT change any engine behavior here; this is a pure "view layer"
over existing objects.
"""

from __future__ import annotations
from typing import Dict, Any, List

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState
from engine.core.map_model import GameMap, MapTile, Terrain


def _time_to_dict(t: GameTime) -> Dict[str, Any]:
    return {
        "day": t.day,
        "phase": t.phase,
        # If weather attribute exists, include it; otherwise use "Unknown"
        "weather": getattr(t, "weather", "Unknown"),
    }


def _tile_to_dict(tile: MapTile) -> Dict[str, Any]:
    return {
        "id": tile.id,
        "terrain": tile.terrain.value if isinstance(tile.terrain, Terrain) else str(tile.terrain),
        "base_move_cost": tile.base_move_cost,
        "is_port": tile.is_port,
        "is_airfield": tile.is_airfield,
    }


def _unit_to_dict(u: UnitState) -> Dict[str, Any]:
    return {
        "id": u.id,
        "name": u.name,
        "side": u.side.value,
        "unit_type": u.unit_type.value,
        "location_id": u.location_id,
        "strength": u.strength,
        "fatigue": u.fatigue,
        "morale": u.morale,
        "supply": u.supply,
        "readiness": u.readiness,
        "hq_unit_id": u.hq_unit_id,
        # Optional / future fields can be added here without breaking JSON
    }


def build_engine_state(
    scenario_id: str,
    scenario_meta: Dict[str, Any],
    time: GameTime,
    game_map: GameMap,
    units: UnitRepository,
    logs: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Build a JSON-serializable snapshot of the current game state.

    This is the canonical structure that the bridge/UI will see.
    """
    logs = logs or []

    # Map
    map_data = {
        "tiles": [_tile_to_dict(t) for t in game_map.tiles.values()]
    }

    # Units
    unit_data = [_unit_to_dict(u) for u in units.all_units()]

    # Scenario-facing metadata (only copy what we care about)
    scenario_view = {
        "id": scenario_meta.get("id", scenario_id),
        "name": scenario_meta.get("name", ""),
        "description": scenario_meta.get("description", ""),
        "weather": scenario_meta.get("weather", "Unknown"),
        "supply_sources": scenario_meta.get("supply_sources", []),
        "objectives": scenario_meta.get("objectives", []),
    }

    state: Dict[str, Any] = {
        "scenario": scenario_view,
        "game": {
            "time": _time_to_dict(time),
            # "turn": could be same as "day" for now; we keep it explicit
            "turn": time.day,
        },
        "map": map_data,
        "units": unit_data,
        "logs": list(logs),
    }

    return state
