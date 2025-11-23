"""
Simple save/load system for MWE.

We don't try to serialize every object; instead we:
- Remember which scenario we came from
- Save the current GameTime (day/phase)
- Save current unit state (strength, fatigue, morale, supply, readiness, location)
- On load, we reload the scenario, then override units and time.
"""

from __future__ import annotations
import os
import json
from typing import Dict, Any, Tuple

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository
from engine.scenario_loader import load_scenario


def _saves_dir() -> str:
    engine_dir = os.path.dirname(os.path.abspath(__file__))  # ...\server\engine
    saves_dir = os.path.join(engine_dir, "..", "saves")
    return os.path.abspath(saves_dir)


def save_game(
    save_name: str,
    t: GameTime,
    units: UnitRepository,
    meta: Dict[str, Any],
) -> str:
    """
    Save minimal game state as JSON.
    Returns the full path to the save file.
    """
    os.makedirs(_saves_dir(), exist_ok=True)
    path = os.path.join(_saves_dir(), f"{save_name}.json")

    units_data = []
    for u in units.all_units():
        units_data.append(
            {
                "id": u.id,
                "location_id": u.location_id,
                "strength": u.strength,
                "fatigue": u.fatigue,
                "morale": u.morale,
                "supply": u.supply,
                "readiness": u.readiness,
                "hq_unit_id": getattr(u, "hq_unit_id", None),
            }
        )

    data = {
        "scenario_id": meta.get("id", ""),
        "time": {"day": t.day, "phase": t.phase},
        "units": units_data,
        "meta": meta,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path


def load_game(save_name: str) -> Tuple[GameTime, Any, UnitRepository, Dict[str, Any]]:
    """
    Load a saved state.
    Returns (GameTime, GameMap, UnitRepository, metadata)
    """
    path = os.path.join(_saves_dir(), f"{save_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Save file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenario_id = data.get("scenario_id", "")
    if not scenario_id:
        raise ValueError("Save file missing 'scenario_id'.")

    # Load the base scenario again
    base_time, game_map, units, meta = load_scenario(scenario_id)

    # Override time from save
    time_data = data.get("time", {})
    game_time = GameTime(
        day=int(time_data.get("day", base_time.day)),
        phase=time_data.get("phase", base_time.phase),
    )

    # Override unit states from save
    saved_units = {u["id"]: u for u in data.get("units", [])}
    for u in units.all_units():
        su = saved_units.get(u.id)
        if not su:
            continue
        u.location_id = su.get("location_id", u.location_id)
        u.strength = su.get("strength", u.strength)
        u.fatigue = su.get("fatigue", u.fatigue)
        u.morale = su.get("morale", u.morale)
        u.supply = su.get("supply", u.supply)
        u.readiness = su.get("readiness", u.readiness)
        u.hq_unit_id = su.get("hq_unit_id", getattr(u, "hq_unit_id", None))

    # Merge meta
    saved_meta = data.get("meta", {})
    meta.update(saved_meta)

    return game_time, game_map, units, meta
