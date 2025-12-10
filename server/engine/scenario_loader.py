"""
Scenario loader for MWE.

Reads JSON scenarios from:  ...\server\rules\scenarios\<id>.json

Exposes one main function:

    load_scenario(scenario_id) -> (GameTime, GameMap, UnitRepository, meta)

`meta` is a small dict with scenario metadata + extra lists
(supply sources, objectives, reinforcements) that staff sections use.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, List, Tuple

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import UnitRepository, UnitState, Side, UnitType


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _rules_dir() -> str:
    """
    Returns the absolute path to ...\server\rules
    """
    here = os.path.dirname(os.path.abspath(__file__))     # ...\server\engine
    server_dir = os.path.dirname(here)                    # ...\server
    rules_dir = os.path.join(server_dir, "rules")         # ...\server\rules
    return os.path.abspath(rules_dir)


def _scenario_path(scenario_id: str) -> str:
    """
    Return full path to the scenario JSON file.
    Assumes: ...\server\rules\scenarios\<id>.json
    """
    rules = _rules_dir()
    scen_dir = os.path.join(rules, "scenarios")
    return os.path.join(scen_dir, f"{scenario_id}.json")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_time(data: Dict[str, Any]) -> GameTime:
    start_day = int(data.get("start_day", 1))
    weather = data.get("weather", "Clear")
    return GameTime(day=start_day, phase="day", weather=weather, turn=1)


def _build_map(data: Dict[str, Any]) -> GameMap:
    """
    Build GameMap from scenario JSON.

    Expected JSON layout:

      "tiles": [
        {
          "id": "LUNGA",
          "name": "Lunga",
          "terrain": "PLAINS",
          "neighbors": ["TULAGI"],
          "is_port": true,
          "is_airfield": true,
          "base_move_cost": 1
        },
        ...
      ]
    """
    tiles_list: List[Dict[str, Any]] = data.get("tiles", []) or []

    tiles: Dict[str, MapTile] = {}

    for tdef in tiles_list:
        tile_id = tdef.get("id")
        if not tile_id:
            continue

        name = tdef.get("name", tile_id)

        terrain_name = str(tdef.get("terrain", "PLAINS")).upper()
        try:
            terrain = Terrain[terrain_name]
        except KeyError:
            terrain = Terrain.PLAINS

        neighbors = list(tdef.get("neighbors", []))

        tile = MapTile(
            id=tile_id,
            name=name,
            terrain=terrain,
            neighbors=neighbors,
            is_port=bool(tdef.get("is_port", False)),
            is_airfield=bool(tdef.get("is_airfield", False)),
            base_move_cost=int(tdef.get("base_move_cost", 1)),
        )
        tiles[tile_id] = tile

    return GameMap(tiles=tiles)


def _build_units(data: Dict[str, Any]) -> UnitRepository:
    """
    Build UnitRepository from scenario JSON.

    Expected layout:

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
          "hq_unit_id": null
        },
        ...
      ]
    """
    units_list: List[Dict[str, Any]] = data.get("units", []) or []

    repo = UnitRepository()
    for udef in units_list:
        uid = udef.get("id")
        if not uid:
            continue

        name = udef.get("name", uid)

        side_str = udef.get("side", "ALLIED")
        unit_type_str = udef.get("unit_type", "INFANTRY")

        side = Side(side_str)
        unit_type = UnitType(unit_type_str)

        u = UnitState(
            id=uid,
            name=name,
            side=side,
            unit_type=unit_type,
            strength=int(udef.get("strength", 100)),
            fatigue=int(udef.get("fatigue", 0)),
            morale=int(udef.get("morale", 50)),
            supply=int(udef.get("supply", 100)),
            readiness=int(udef.get("readiness", 50)),
            location_id=udef.get("location_id", ""),
            hq_unit_id=udef.get("hq_unit_id"),
        )
        repo.add(u)

    return repo


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_scenario(scenario_id: str) -> Tuple[GameTime, GameMap, UnitRepository, Dict[str, Any]]:
    """
    Load a scenario and return:
      - start_time (GameTime)
      - game_map (GameMap)
      - units_repo (UnitRepository)
      - meta (dict with scenario summary + extras)
    """
    path = _scenario_path(scenario_id)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    start_time = _build_time(data)
    game_map = _build_map(data)
    units_repo = _build_units(data)

    meta: Dict[str, Any] = {
        "id": data.get("id", scenario_id),
        "name": data.get("name", scenario_id),
        "description": data.get("description", ""),
        "start_day": start_time.day,
        "weather": start_time.weather,
        # Extras used by staff sections:
        "supply_sources": data.get("supply_sources", []) or [],
        "objectives": data.get("objectives", []) or [],
        "reinforcements": data.get("reinforcements", []) or [],
    }

    return start_time, game_map, units_repo, meta
