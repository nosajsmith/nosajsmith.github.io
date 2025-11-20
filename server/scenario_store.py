"""
scenario_store.py — load, save, list Scenario JSON files.
"""

from __future__ import annotations
import json, os, glob
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple

DEFAULT_SCENARIO_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "scenarios")
)

@dataclass
class Unit:
    id: str
    name: str
    type: str
    strength: int
    fatigue: int
    hq: str
    pos: Tuple[int, int]

@dataclass
class Scenario:
    name: str
    metadata: Dict[str, Any]
    blue_units: List[Unit]
    red_units: List[Unit]
    objectives: List[Tuple[int, int]]
    start_turn: int

# ---------------------------------------------------------------------

def _ensure_dir(path: str):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def list_scenarios(scen_dir: str | None = None) -> List[str]:
    p = scen_dir or DEFAULT_SCENARIO_DIR
    _ensure_dir(p)
    return sorted([os.path.basename(f) for f in glob.glob(os.path.join(p, "*.json"))])

def read_scenario(name: str, scen_dir: str | None = None) -> Scenario:
    p = scen_dir or DEFAULT_SCENARIO_DIR
    _ensure_dir(p)
    fp = os.path.join(p, name if name.endswith(".json") else f"{name}.json")
    with open(fp, "r", encoding="utf-8") as f:
        raw = json.load(f)

    def _u(u: Dict[str, Any]) -> Unit:
        pos = tuple(u.get("pos", [0, 0]))
        return Unit(
            id=str(u.get("id")),
            name=str(u.get("name")),
            type=str(u.get("type")),
            strength=int(u.get("strength", 100)),
            fatigue=int(u.get("fatigue", 0)),
            hq=str(u.get("hq", "")),
            pos=(int(pos[0]), int(pos[1])),
        )

    return Scenario(
        name=str(raw.get("name", os.path.splitext(os.path.basename(fp))[0])),
        metadata=dict(raw.get("metadata", {})),
        blue_units=[_u(u) for u in raw.get("blue_units", [])],
        red_units=[_u(u) for u in raw.get("red_units", [])],
        objectives=[tuple(map(int, o)) for o in raw.get("objectives", [])],
        start_turn=int(raw.get("start_turn", 1)),
    )

def write_scenario(scn: Scenario, filename: str | None = None, scen_dir: str | None = None) -> str:
    p = scen_dir or DEFAULT_SCENARIO_DIR
    _ensure_dir(p)
    fname = filename or f"{scn.name}.json"
    if not fname.endswith(".json"):
        fname += ".json"

    data = {
        "name": scn.name,
        "metadata": scn.metadata,
        "blue_units": [asdict(u) for u in scn.blue_units],
        "red_units": [asdict(u) for u in scn.red_units],
        "objectives": scn.objectives,
        "start_turn": scn.start_turn,
    }
    out_path = os.path.join(p, fname)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out_path
