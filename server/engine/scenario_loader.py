"""
Scenario loader for MWE.

Reads JSON scenarios from:
  ...\server\rules\scenarios\<id>.json

Exposes:
  load_scenario(scenario_id) -> (start_time, game_map, units_repo, meta)
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Tuple, List

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import (
    UnitState,
    UnitRepository,
    Side,
    UnitType,
    Posture,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _rules_dir() -> str:
    """
    Returns the absolute path to ...\server\rules
    (assuming this file is at ...\server\engine\scenario_loader.py)
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))  # ...\server\engine
    server_dir = os.path.dirname(this_dir)                 # ...\server
    rules_dir = os.path.join(server_dir, "rules")
    return os.path.abspath(rules_dir)


def _scenario_path(scenario_id: str) -> str:
    """
    Build the path to a scenario JSON file.

    Assumes:
      ...\server\rules\scenarios\<id>.json
    """
    rules_dir = _rules_dir()
    scenarios_dir = os.path.join(rules_dir, "scenarios")
    return os.path.join(scenarios_dir, f"{scenario_id}.json")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _build_time(data: Dict[str, Any]) -> GameTime:
    """
    Build initial GameTime from scenario data.

    GameTime(...) currently expects:
      day: int
      phase: str  (we'll just start at "day")
      weather: str
    """
    start_day = int(data.get("start_day", 1))
    weather = data.get("weather", "Clear")
    # NOTE: GameTime does NOT take a 'turn' keyword; just (day, phase, weather).
    return GameTime(day=start_day, phase="day", weather=weather)


def _build_map(data: Dict[str, Any]) -> GameMap:
    """
    Build a GameMap from the scenario's location definitions.

    Expected JSON shape (simplified):

      "locations": {
        "LUNGA": {
          "name": "Lunga Beachhead",
          "terrain": "PLAINS",
          "is_port": true,
          "is_airfield": true,
          "base_move_cost": 1
        },
        "TULAGI": {
          "name": "Tulagi",
          "terrain": "JUNGLE"
        }
      }
    """
    tiles: Dict[str, MapTile] = {}

    loc_defs: Dict[str, Any] = data.get("locations", {})
    for tile_id, tdef in loc_defs.items():
        terrain_str = str(tdef.get("terrain", "PLAINS")).upper()
        try:
            terrain = Terrain[terrain_str]
        except KeyError:
            terrain = Terrain.PLAINS

        tile = MapTile(
            tile_id=tile_id,  # <-- IMPORTANT: matches MapTile dataclass
            name=tdef.get("name", tile_id),
            terrain=terrain,
            is_port=bool(tdef.get("is_port", False)),
            is_airfield=bool(tdef.get("is_airfield", False)),
            base_move_cost=int(tdef.get("base_move_cost", 1)),
        )
        tiles[tile_id] = tile

    return GameMap(tiles=tiles)


def _build_units(data: Dict[str, Any]) -> UnitRepository:
    """
    Build UnitRepository from scenario data.

    Expected JSON shape (simplified):

      "units": [
        {
          "id": "US-1MAR",
          "name": "1st Marine Division",
          "side": "ALLIED",
          "unit_type": "INFANTRY",
          "strength": 100,
          "fatigue": 10,
          "morale": 70,
          "supply": 80,
          "readiness": 60,
          "location_id": "LUNGA",
          "posture": "DEFEND",
          "hq_unit_id": null
        }
      ]
    """
    repo = UnitRepository()   # <-- no arguments

    for udef in data.get("units", []):
        side_str = udef.get("side", "ALLIED")
        unit_type_str = udef.get("unit_type", "INFANTRY")
        posture_str = udef.get("posture", "DEFEND")

        try:
            side = Side(side_str)
        except ValueError:
            side = Side.ALLIED

        try:
            unit_type = UnitType(unit_type_str)
        except ValueError:
            unit_type = UnitType.INFANTRY

        try:
            posture = Posture(posture_str)
        except ValueError:
            posture = Posture.DEFEND

        u = UnitState(
            id=udef["id"],
            name=udef.get("name", udef["id"]),
            side=side,
            unit_type=unit_type,
            strength=int(udef.get("strength", 100)),
            fatigue=int(udef.get("fatigue", 0)),
            morale=int(udef.get("morale", 50)),
            supply=int(udef.get("supply", 100)),
            readiness=int(udef.get("readiness", 50)),
            location_id=udef.get("location_id", ""),
            posture=posture,
            hq_unit_id=udef.get("hq_unit_id"),
        )
        repo.add(u)

    return repo

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_scenario(scenario_id: str) -> Tuple[GameTime, GameMap, UnitRepository, Dict[str, Any]]:
    """
    High-level loader used by EngineAPI.

    Returns:
      (start_time, game_map, units_repo, meta)

    meta is a small dict the UI/bridge can use as scenario metadata.
    """
    path = _scenario_path(scenario_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scenario JSON not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    start_time = _build_time(data)
    game_map = _build_map(data)
    units_repo = _build_units(data)

    meta: Dict[str, Any] = {
        "id": data.get("id", scenario_id),
        "name": data.get("name", scenario_id),
        "description": data.get("description", ""),
        "start_day": data.get("start_day", 1),
        "weather": data.get("weather", "Clear"),
        # Pass through for G-4 / G-7 / G-8:
        "objectives": data.get("objectives", []),
        "supply_sources": data.get("supply_sources", []),
        "reinforcements": data.get("reinforcements", []),
    }

    return start_time, game_map, units_repo, meta
