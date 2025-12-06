"""
Scenario loader for the MacArthur War Engine (MWE)

Phase 8 compatible – returns:
    start_time : GameTime
    game_map   : GameMap
    units      : UnitRepository
    meta       : dict
"""

from __future__ import annotations
import os
import json
from typing import Dict, Any

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import UnitRepository, UnitState, Side, UnitType


# -----------------------------------------------------------------------------
# Scenario Path Resolution – MULTI-PATH AUTO-DETECT
# -----------------------------------------------------------------------------


def _scenario_path(scenario_id: str) -> str:
    """
    Attempts to locate a scenario JSON file in several possible folders.
    Whichever is found first is returned.

    This makes the engine tolerant of folder layouts like:
        C:\MWE\server\scenarios\
        C:\MWE\scenarios\
        C:\MWE\server\rules\scenarios\
    """

    engine_dir = os.path.dirname(os.path.abspath(__file__))   # ...\server\engine
    server_dir = os.path.dirname(engine_dir)                  # ...\server
    root_dir = os.path.dirname(server_dir)                    # ...\MWE

    filename = f"{scenario_id}.json"

    candidates = [
        # 1) Your ACTUAL current location (from your dir output)
        os.path.join(server_dir, "scenarios", filename),
        # 2) Root-level scenarios folder
        os.path.join(root_dir, "scenarios", filename),
        # 3) Legacy rules/scenarios layout
        os.path.join(server_dir, "rules", "scenarios", filename),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    tried_str = "\n  ".join(candidates)
    raise FileNotFoundError(
        f"Scenario '{scenario_id}' could not be located.\n"
        f"Tried these paths:\n  {tried_str}"
    )


# -----------------------------------------------------------------------------
# BUILD GAME TIME
# -----------------------------------------------------------------------------


def _build_time(meta: Dict[str, Any]) -> GameTime:
    """
    Convert metadata into an initial GameTime object.
    """
    day = int(meta.get("start_day", 1))
    phase = meta.get("start_phase", "day")

    t = GameTime(day=day, phase=phase)

    # Only set if GameTime supports weather
    if hasattr(t, "weather"):
        t.weather = meta.get("weather", "Clear")

    return t


# -----------------------------------------------------------------------------
# BUILD MAP
# -----------------------------------------------------------------------------


def _build_map(data: Dict[str, Any]) -> GameMap:
    """
    Builds a GameMap from scenario JSON.

    Expected:
    {
      "map": {
        "tiles": [
          {
            "id": "LUNGA",
            "terrain": "JUNGLE",
            "base_move_cost": 1,
            "is_port": true,
            "is_airfield": true
          },
          ...
        ]
      }
    }
    """

    tiles: Dict[str, MapTile] = {}

    map_def = data.get("map", {})
    for tdef in map_def.get("tiles", []):
        tile_id = tdef["id"]

        terr_str = str(tdef.get("terrain", "PLAINS")).strip().upper()

        try:
            terrain = Terrain(terr_str)
        except Exception:
            terrain = Terrain.PLAINS

        tile = MapTile(
            tile_id=tile_id,
            terrain=terrain,
            base_move_cost=int(tdef.get("base_move_cost", 1)),
            is_port=bool(tdef.get("is_port", False)),
            is_airfield=bool(tdef.get("is_airfield", False)),
        )
        tiles[tile_id] = tile

    return GameMap(tiles=tiles)


# -----------------------------------------------------------------------------
# BUILD UNIT REPOSITORY
# -----------------------------------------------------------------------------


def _build_units(data: Dict[str, Any]) -> UnitRepository:
    """
    Converts scenario JSON unit definitions into a UnitRepository.
    """

    repo = UnitRepository()

    for udef in data.get("units", []):
        side = Side(udef.get("side"))
        unit_type = UnitType(udef.get("unit_type"))

        u = UnitState(
            id=udef["id"],
            name=udef.get("name", udef["id"]),
            side=side,
            unit_type=unit_type,
            location_id=udef.get("location_id", ""),
            strength=int(udef.get("strength", 100)),
            fatigue=int(udef.get("fatigue", 0)),
            morale=int(udef.get("morale", 50)),
            supply=int(udef.get("supply", 50)),
            readiness=int(udef.get("readiness", 50)),
            hq_unit_id=udef.get("hq_unit_id", None),
        )

        repo.add(u)

    return repo


# -----------------------------------------------------------------------------
# MAIN ENTRYPOINT
# -----------------------------------------------------------------------------


def load_scenario(scenario_id: str):
    """
    Load scenario metadata + map + units.

    Returns:
        start_time: GameTime
        game_map: GameMap
        units: UnitRepository
        meta: Dict (scenario metadata)
    """

    path = _scenario_path(scenario_id)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Metadata normalizing
    meta = dict(data.get("meta", {}))
    meta.setdefault("id", scenario_id)
    meta.setdefault("name", data.get("name", scenario_id))
    meta.setdefault("description", data.get("description", ""))

    # These may appear top-level or in meta
    for key in ("supply_sources", "objectives", "reinforcements"):
        if key in data and key not in meta:
            meta[key] = data[key]

    start_time = _build_time(meta)
    game_map = _build_map(data)
    units = _build_units(data)

    return start_time, game_map, units, meta
