"""
scenario_store.py — Small, strict JSON scenario store.

Contract:
- list_scenarios() -> list[str] of filenames (e.g. "breakthrough.json")
- read_scenario(name) -> dict | None   (NEVER returns dataclass objects)
- write_scenario(name, data: dict) -> dict (written data)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


DEFAULT_SCENARIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")


# --- Optional dataclasses (kept for future, but store returns dicts) ---

@dataclass
class Unit:
    id: str
    name: str
    side: str = "BLUE"
    x: int = 0
    y: int = 0
    strength: int = 100


@dataclass
class Scenario:
    name: str
    units: List[Unit]
    meta: Dict[str, Any] | None = None


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _norm_filename(name: str) -> str:
    """
    Normalize scenario references:
    - strips directories
    - forces .json extension
    """
    base = os.path.basename(name.strip())
    if not base.endswith(".json"):
        base += ".json"
    return base


def _scenario_path(scenario_dir: str, name: str) -> str:
    return os.path.join(scenario_dir, _norm_filename(name))


def list_scenarios(scenario_dir: str = DEFAULT_SCENARIO_DIR) -> List[str]:
    _ensure_dir(scenario_dir)
    items: List[str] = []
    for fn in os.listdir(scenario_dir):
        if fn.lower().endswith(".json") and os.path.isfile(os.path.join(scenario_dir, fn)):
            items.append(fn)
    items.sort()
    return items


def read_scenario(name: str, scenario_dir: str = DEFAULT_SCENARIO_DIR) -> Optional[Dict[str, Any]]:
    _ensure_dir(scenario_dir)
    path = _scenario_path(scenario_dir, name)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        # Return a dict describing the parse issue instead of raising.
        return {
            "_invalid_json": True,
            "error": f"JSONDecodeError: {e}",
            "file": os.path.basename(path),
        }
    except Exception as e:
        return {
            "_read_error": True,
            "error": repr(e),
            "file": os.path.basename(path),
        }

    # Strict contract: scenario content MUST be a dict for the bridge.
    if not isinstance(data, dict):
        return None
    return data


def write_scenario(name: str, data: Dict[str, Any], scenario_dir: str = DEFAULT_SCENARIO_DIR) -> Dict[str, Any]:
    _ensure_dir(scenario_dir)
    path = _scenario_path(scenario_dir, name)

    if not isinstance(data, dict):
        raise TypeError(f"write_scenario expects dict, got {type(data)}")

    # Always ensure some minimal shape
    data.setdefault("name", os.path.splitext(_norm_filename(name))[0])
    data.setdefault("units", [])
    data.setdefault("meta", {})

    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, path)
    return data


# --- Helpers for future expansion (not used by the bridge today) ---

def scenario_to_dict(s: Scenario) -> Dict[str, Any]:
    d = asdict(s)
    return d


def unit_to_dict(u: Unit) -> Dict[str, Any]:
    return asdict(u)
