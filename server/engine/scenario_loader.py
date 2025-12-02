"""
Scenario loader for MWE.

Responsibilities:
- Load scenario JSON from server/scenarios/<id>.json
- Build:
  - GameTime (start day/phase)
  - GameMap  (tiles/terrain/features)
  - UnitRepository (starting OOB)
  - meta dictionary (name, description, weather, supply, objectives, reinforcements, etc.)

The JSON format it expects (simplified example):

{
  "id": "mini_gc_1942",
  "name": "Mini Guadalcanal 1942",
  "description": "Tiny test scenario for MWE engine skeleton.",
  "start_day": 1,
  "weather": "Clear",

  "map": {
    "tiles": [
      {
        "id": "LUNGA",
        "terrain": "JUNGLE",
        "base_move_cost": 1,
        "is_port": true,
        "is_airfield": true
      },
      {
        "id": "TULAGI",
        "terrain": "JUNGLE",
        "base_move_cost": 1,
        "is_port": true,
        "is_airfield": false
      }
    ]
  },

  "units": [
    {
      "id": "US-1MAR",
      "name": "1st Marine Division",
      "side": "Allied",
      "unit_type": "Division",
      "location_id": "LUNGA",
      "strength": 100,
      "fatigue": 10,
      "morale": 70,
      "supply": 80,
      "readiness": 60,
      "hq_unit_id": null
    }
  ],

  "supply_sources": [
    {
      "location_id": "LUNGA",
      "side": "Allied",
      "daily_supply": 10
    }
  ],

  "objectives": [
    {
      "location_id": "LUNGA",
      "side": "Allied",
      "value": 50,
      "description": "Secure and hold the beachhead and airfield."
    }
  ],

  "reinforcements": [
    {
      "id": "US-2MAR",
      "name": "2nd Marine Regiment (Reinf)",
      "side": "Allied",
      "unit_type": "Regiment",
      "arrival_day": 3,
      "entry_location_id": "LUNGA",
      "strength": 80,
      "fatigue": 0,
      "morale": 65,
      "supply": 90,
      "readiness": 70,
      "hq_unit_id": null
    }
  ]
}
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any, Tuple

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.unit_model import UnitRepository, UnitState, Side, UnitType


# --------------------------------------------------------------------------- paths


def _scenarios_dir() -> str:
    """
    Returns absolute path to the scenarios directory: server/scenarios
    starting from this file's location.
    """
    engine_dir = os.path.dirname(os.path.abspath(__file__))  # ...\server\engine
    scenarios_dir = os.path.join(engine_dir, "..", "scenarios")
    return os.path.abspath(scenarios_dir)


def _scenario_path(scenario_id: str) -> str:
    """
    Path to the JSON file backing a scenario.
    """
    return os.path.join(_scenarios_dir(), f"{scenario_id}.json")


# --------------------------------------------------------------------------- helpers


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_time(data: Dict[str, Any]) -> GameTime:
    """
    Build the starting GameTime from scenario data.
    Currently we use a simple day counter.
    """
    start_day = int(data.get("start_day", 1))
    phase = data.get("start_phase", "day")
    # We let TimeSystem/WeatherEngine handle daily weather changes; scenario
    # just seeds initial weather in meta.
    return GameTime(day=start_day, phase=phase, weather=data.get("weather", "Clear"))


def _build_map(map_data: Dict[str, Any]) -> GameMap:
    """
    Build a GameMap from JSON map data.
    Expects: { "tiles": [ { id, terrain, base_move_cost, is_port, is_airfield }, ... ] }
    """
    tiles_dict: Dict[str, MapTile] = {}

    for t in map_data.get("tiles", []):
        tile_id = t.get("id")
        if not tile_id:
            continue

        terrain_str = str(t.get("terrain", "PLAINS")).upper()
        try:
            terrain = Terrain[terrain_str]
        except KeyError:
            # Fallback: try by value, then PLAINS
            try:
                terrain = Terrain(terrain_str.title())
            except Exception:
                terrain = Terrain.PLAINS

        base_move_cost = int(t.get("base_move_cost", 1))
        is_port = bool(t.get("is_port", False))
        is_airfield = bool(t.get("is_airfield", False))

        tile = MapTile(
            id=tile_id,
            terrain=terrain,
            base_move_cost=base_move_cost,
            is_port=is_port,
            is_airfield=is_airfield,
        )
        tiles_dict[tile_id] = tile

    return GameMap(tiles=tiles_dict)


def _build_units(data: Dict[str, Any]) -> UnitRepository:
    """
    Build starting UnitRepository from scenario data.

    We only create initial on-map units here. Reinforcements are kept in
    data["reinforcements"] and handled by G-7.
    """
    repo = UnitRepository()

    for u in data.get("units", []):
        uid = u.get("id")
        if not uid:
            continue

        # Side: support values like "Allied", "Axis"
        side_str = u.get("side", "Allied")
        try:
            side = Side(side_str)
        except Exception:
            # Fallback to ALLIED if unknown
            side = Side.ALLIED

        # Unit type: values like "Division", "Brigade", "Regiment"
        ut_str = u.get("unit_type", "Division")
        try:
            unit_type = UnitType(ut_str)
        except Exception:
            # Try enum by name (e.g. "DIVISION") if needed
            try:
                unit_type = UnitType[ut_str.upper()]
            except Exception:
                unit_type = UnitType.DIVISION

        state = UnitState(
            id=uid,
            name=u.get("name", uid),
            side=side,
            unit_type=unit_type,
            location_id=u.get("location_id", ""),
            strength=int(u.get("strength", 100)),
            fatigue=int(u.get("fatigue", 0)),
            morale=int(u.get("morale", 50)),
            supply=int(u.get("supply", 50)),
            readiness=int(u.get("readiness", 50)),
            hq_unit_id=u.get("hq_unit_id"),
        )

        repo.add_unit(state)

    return repo


# --------------------------------------------------------------------------- main API


def load_scenario(scenario_id: str) -> Tuple[GameTime, GameMap, UnitRepository, Dict[str, Any]]:
    """
    Load a scenario by ID and return:

      (start_time, game_map, units, meta)

    where:
      - start_time: GameTime
      - game_map:  GameMap
      - units:     UnitRepository
      - meta:      dict with at least:
          {
            "id": str,
            "name": str,
            "description": str,
            "weather": str,
            "supply_sources": [...],
            "objectives": [...],
            "reinforcements": [...],
            ...
          }
    """
    path = _scenario_path(scenario_id)
    data = _load_json(path)

    # Start time
    start_time = _build_time(data)

    # Map
    map_data = data.get("map", {})
    game_map = _build_map(map_data)

    # Units (starting OOB)
    units = _build_units(data)

    # Meta: keep full scenario data, but ensure key fields exist
    meta: Dict[str, Any] = dict(data)
    meta.setdefault("id", scenario_id)
    meta.setdefault("name", "")
    meta.setdefault("description", "")
    meta.setdefault("weather", data.get("weather", "Clear"))
    meta.setdefault("supply_sources", data.get("supply_sources", []))
    meta.setdefault("objectives", data.get("objectives", []))
    meta.setdefault("reinforcements", data.get("reinforcements", []))

    return start_time, game_map, units, meta
