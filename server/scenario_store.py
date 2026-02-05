from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SCENARIO_DIR = os.environ.get(
    "MWE_SCENARIO_DIR",
    str(Path(__file__).resolve().parent.parent / "scenarios")
)

def _scen_dir(scenario_dir: str | None = None) -> Path:
    base_dir = scenario_dir or DEFAULT_SCENARIO_DIR
    return Path(base_dir).resolve()

def list_scenarios(scenario_dir: str | None = None) -> List[str]:
    d = _scen_dir(scenario_dir)
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob("*.json") if p.is_file()])

def _safe_name(name: str) -> Optional[str]:
    if not name or "/" in name or "\\" in name:
        return None
    if not name.endswith(".json"):
        return None
    return name

def read_scenario(name: str, scenario_dir: str | None = None) -> Optional[Dict[str, Any]]:
    name = _safe_name(name)
    if not name:
        return None
    p = _scen_dir(scenario_dir) / name
    if not p.exists() or not p.is_file():
        return None
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return None
    # ensure units list exists
    if not isinstance(obj.get("units"), list):
        obj["units"] = []
    return obj

def write_scenario(name: str, obj: Dict[str, Any], scenario_dir: str | None = None) -> bool:
    name = _safe_name(name)
    if not name:
        return False
    p = _scen_dir(scenario_dir) / name
    if not p.exists() or not p.is_file():
        return False

    # atomic write
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(p)
    return True

def move_unit(name: str, unit_id: str, q: int, r: int) -> Optional[Dict[str, Any]]:
    scn = read_scenario(name)
    if not scn:
        return None

    units = scn.get("units", [])
    if not isinstance(units, list):
        scn["units"] = []
        units = scn["units"]

    changed = False
    for u in units:
        if not isinstance(u, dict):
            continue
        uid = str(u.get("unit_id") or u.get("id") or u.get("name") or "")
        if uid != str(unit_id):
            continue

        # canonical: position:[q,r]
        u["position"] = [int(q), int(r)]
        # legacy compat if you want
        u["x"] = int(q)
        u["y"] = int(r)

        changed = True
        break

    if not changed:
        return None

    if not write_scenario(name, scn):
        return None
    return scn
