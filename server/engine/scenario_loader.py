"""
Scenario loading for MWE.

Loads JSON scenario files from server/scenarios.
"""

from __future__ import annotations
import os
import json
from typing import Tuple, Dict, Any

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, UnitType
from engine.core.map_model import GameMap, MapTile, Terrain


def _scenario_dir() -> str:
    """
    Returns the absolute path to server/scenarios.
    """
    engine_dir = os.path.dirname(os.path.abspath(__file__))  # ...\server\engine
    scenarios_dir = os.path.join(engine_dir, "..", "scenarios")
    return os.path.abspath(scenarios_dir)


def _scenario_path(scenario_id: str) -> str:
    """
    Map a scenario ID to a JSON file path.
    e.g. 'mini_gc_1942' -> server/scenarios/mini_gc_1942.json
    """
    return os.path.join(_scenario_dir(), f"{scenario_id}.json")


def load_scenario(
    scenario_id: str,
) -> Tuple[GameTime, GameMap, UnitRepository, Dict[str, Any]]:
    """
    Load a scenario by ID and return:
    - starting GameTime
    - GameMap
    - UnitRepository
    - metadata dict (id, name, description)
    """
    path = _scenario_path(scenario_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scenario file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Time ---------------------------------------------------------------
    start_day = int(data.get("start_day", 1))
    game_time = GameTime(day=start_day, phase="day")

    # --- Map ----------------------------------------------------------------
    game_map = GameMap()
    for t in data.get("map", {}).get("tiles", []):
        tile = MapTile(
            id=t["id"],
            terrain=Terrain(t["terrain"]),
            base_move_cost=t.get("base_move_cost", 1),
            is_port=t.get("is_port", False),
            is_airfield=t.get("is_airfield", False),
        )
        game_map.add_tile(tile)

    # --- Units --------------------------------------------------------------
    units = UnitRepository()
    for u in data.get("units", []):
        unit = UnitState(
            id=u["id"],
            name=u["name"],
            side=Side(u["side"]),
            unit_type=UnitType(u["unit_type"]),
            strength=u.get("strength", 100),
            fatigue=u.get("fatigue", 0),
            morale=u.get("morale", 50),
            supply=u.get("supply", 100),
            readiness=u.get("readiness", 50),
            location_id=u.get("location_id", "UNKNOWN"),
            hq_unit_id=u.get("hq_unit_id"),
        )
        units.add(unit)

    metadata = {
        "id": data.get("id", scenario_id),
        "name": data.get("name", ""),
        "description": data.get("description", ""),
    }

    return game_time, game_map, units, metadata
