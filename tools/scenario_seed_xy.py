#!/usr/bin/env python3
"""
scenario_seed_xy.py
- Adds x/y coordinates to units in scenario JSON files if missing.
- Deterministic layout so units don't stack at (0,0).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

SCEN_DIR = Path("scenarios")

# Simple deterministic placement:
# - BLUE units: left half
# - RED units: right half
# - Spread in rows
BLUE_START_X = 3
RED_START_X  = 18
START_Y      = 4
COLS_PER_SIDE = 6   # how many columns to use per side
ROW_STEP = 1
COL_STEP = 1

def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p: Path, obj: Dict[str, Any]) -> None:
    p.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")

def ensure_units_list(scn: Dict[str, Any]) -> List[Dict[str, Any]]:
    units = scn.get("units")
    if not isinstance(units, list):
        raise SystemExit(f"{scn.get('name','(unknown)')}: scenario missing 'units' list")
    out: List[Dict[str, Any]] = []
    for u in units:
        if not isinstance(u, dict):
            raise SystemExit("Scenario has non-dict unit entry")
        out.append(u)
    return out

def seed_side(units: List[Dict[str, Any]], side: str, start_x: int) -> int:
    # preserve existing coords if present
    idx = 0
    for u in units:
        if str(u.get("side", "")).lower() != side:
            continue
        has_xy = isinstance(u.get("x"), int) and isinstance(u.get("y"), int)
        if has_xy:
            idx += 1
            continue

        col = idx % COLS_PER_SIDE
        row = idx // COLS_PER_SIDE
        u["x"] = start_x + col * COL_STEP
        u["y"] = START_Y + row * ROW_STEP
        idx += 1
    return idx

def main() -> int:
    if not SCEN_DIR.exists():
        print(f"no scenarios/ directory found at {SCEN_DIR.resolve()}")
        return 2

    changed = 0
    for p in sorted(SCEN_DIR.glob("*.json")):
        scn = load_json(p)
        units = ensure_units_list(scn)

        # count missing coords before
        before_missing = sum(
            1 for u in units
            if not (isinstance(u.get("x"), int) and isinstance(u.get("y"), int))
        )

        seed_side(units, "blue", BLUE_START_X)
        seed_side(units, "red",  RED_START_X)

        after_missing = sum(
            1 for u in units
            if not (isinstance(u.get("x"), int) and isinstance(u.get("y"), int))
        )

        if after_missing != before_missing:
            # Some units might not be blue/red; give them a neutral spread too
            idx = 0
            for u in units:
                if isinstance(u.get("x"), int) and isinstance(u.get("y"), int):
                    continue
                u["x"] = 10 + (idx % 6)
                u["y"] = 2 + (idx // 6)
                idx += 1

        # determine if we changed anything
        final_missing = sum(
            1 for u in units
            if not (isinstance(u.get("x"), int) and isinstance(u.get("y"), int))
        )
        if final_missing != 0:
            print(f"[WARN] {p.name}: still missing coords for {final_missing} units")
        # We treat as changed if we reduced missing count at all
        if before_missing > final_missing:
            save_json(p, scn)
            changed += 1
            print(f"[OK] {p.name}: seeded coords (missing {before_missing} -> {final_missing})")
        else:
            print(f"[SKIP] {p.name}: already has coords")

    print(f"\nDone. Updated {changed} scenario file(s).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
