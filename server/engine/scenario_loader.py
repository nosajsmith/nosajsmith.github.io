# engine/scenario_loader.py
from __future__ import annotations

import inspect
import json
import os
from typing import Any, Dict, List, Tuple

from .core.map_model import GameMap, MapTile, Terrain
from .core.time_system import GameTime
from .core.unit_model import UnitState, UnitRepository, Side, UnitType, Posture


def _rules_dir() -> str:
    """
    Returns absolute path to ...\\server\\rules (assuming this file is ...\\server\\engine\\scenario_loader.py)
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))  # ...\server\engine
    server_dir = os.path.dirname(this_dir)                 # ...\server
    return os.path.join(server_dir, "rules")


def _scenario_candidate_paths(scenario_id: str) -> List[str]:
    server_dir = os.path.dirname(_rules_dir())
    return [
        os.path.join(_rules_dir(), "scenarios", f"{scenario_id}.json"),
        os.path.join(server_dir, "scenarios", f"{scenario_id}.json"),
    ]


def _scenario_path(scenario_id: str) -> str:
    """
    Prefer canonical rules scenarios, but fall back to server/scenarios for
    older engine-ready fixtures that are still used by support tooling.
    """
    for path in _scenario_candidate_paths(scenario_id):
        if os.path.exists(path):
            return path
    searched = ", ".join(_scenario_candidate_paths(scenario_id))
    raise FileNotFoundError(f"Scenario not found for engine loader: {scenario_id} (searched: {searched})")


def _enum_value(enum_cls, raw: Any, *, default=None):
    """Best-effort enum coercion with safe fallback."""
    if raw is None:
        return default
    # already enum
    if isinstance(raw, enum_cls):
        return raw
    v = str(raw).strip()

    # Try exact
    try:
        return enum_cls(v)
    except Exception:
        pass

    # Try upper
    try:
        return enum_cls(v.upper())
    except Exception:
        return default


def _build_time(data: Dict[str, Any]) -> GameTime:
    start_day = int(data.get("start_day", 1))
    weather = str(data.get("weather", "Clear"))
    # Keep this aligned to your existing GameTime signature:
    # GameTime(day=..., phase=..., weather=...)
    return GameTime(day=start_day, phase="day", weather=weather)


def _build_map(data: Dict[str, Any]) -> GameMap:
    game_map = GameMap()

    raw_tiles = data.get("map", {}).get("tiles", {})
    # Support both dict and list formats
    if isinstance(raw_tiles, list):
        # list of {id/name/...}
        tiles_iter = []
        for t in raw_tiles:
            if not isinstance(t, dict):
                continue
            tile_id = t.get("tile_id") or t.get("id")
            if tile_id is None:
                continue
            tiles_iter.append((str(tile_id), t))
    else:
        tiles_iter = list(raw_tiles.items())

    for tile_id, tdef in tiles_iter:
        if not isinstance(tdef, dict):
            tdef = {}

        name = str(tdef.get("name", tile_id))
        terrain_raw = tdef.get("terrain", "CLEAR")
        terrain = Terrain.coerce(str(terrain_raw))

        # IMPORTANT: pass tile_id positionally to avoid "multiple values for tile_id"
        tile = MapTile(
            str(tile_id),
            name=name,
            terrain=terrain,
            base_move_cost=int(tdef.get("base_move_cost", 1)),
            defense_bonus=int(tdef.get("defense_bonus", 0)),
            supply_bonus=int(tdef.get("supply_bonus", 0)),
            is_port=bool(tdef.get("is_port", False)),
            is_airfield=bool(tdef.get("is_airfield", False)),
        )
        game_map.add_tile(tile)

    return game_map


def _repo_add(repo: Any, unit: UnitState) -> None:
    """
    Add a unit to whatever UnitRepository implementation is present.
    Supports several common shapes without assuming constructor args.
    """
    # common patterns
    if hasattr(repo, "add_unit"):
        repo.add_unit(unit)
        return
    if hasattr(repo, "add"):
        repo.add(unit)
        return
    # fallback: units dict
    if hasattr(repo, "units") and isinstance(getattr(repo, "units"), dict):
        repo.units[unit.id] = unit
        return
    if hasattr(repo, "_units") and isinstance(getattr(repo, "_units"), dict):
        repo._units[unit.id] = unit
        return

    raise TypeError("UnitRepository has no supported method to add units (expected add_unit/add/units dict).")


def _build_units(data: Dict[str, Any]) -> UnitRepository:
    units: List[UnitState] = []
    raw_units = data.get("units", [])
    if not isinstance(raw_units, list):
        raw_units = []

    for u in raw_units:
        if not isinstance(u, dict):
            continue

        side = _enum_value(Side, u.get("side"), default=Side.ALLIED)
        unit_type = _enum_value(UnitType, u.get("unit_type"), default=UnitType.INFANTRY)
        posture = _enum_value(Posture, u.get("posture"), default=Posture.DEFEND)

        unit = UnitState(
            id=str(u.get("id", "")),
            name=str(u.get("name", "")),
            side=side,
            unit_type=unit_type,
            strength=int(u.get("strength", 100)),
            fatigue=int(u.get("fatigue", 0)),
            morale=int(u.get("morale", 50)),
            supply=int(u.get("supply", 50)),
            readiness=int(u.get("readiness", 50)),
            location_id=str(u.get("location_id", "")),
            posture=posture,
            hq_unit_id=u.get("hq_unit_id"),
        )
        units.append(unit)

    # Create repo WITHOUT passing a list (avoids: UnitRepository.__init__ takes 1 positional argument)
    repo = UnitRepository()
    for unit in units:
        _repo_add(repo, unit)

    return repo


def _build_meta(data: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
    return {
        "id": scenario_id,
        "name": str(data.get("name", scenario_id)),
        "description": str(data.get("description", "")),
        "start_day": int(data.get("start_day", 1)),
        "weather": str(data.get("weather", "Clear")),
        "supply_sources": data.get("supply_sources", []),
        "objectives": data.get("objectives", []),
        "reinforcements": data.get("reinforcements", []),
        "ai": data.get("ai", {}),
    }


def load_scenario(scenario_id: str) -> Tuple[GameTime, GameMap, UnitRepository, Dict[str, Any]]:
    path = _scenario_path(scenario_id)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    start_time = _build_time(data)
    game_map = _build_map(data)
    units_repo = _build_units(data)
    meta = _build_meta(data, scenario_id)

    return start_time, game_map, units_repo, meta
