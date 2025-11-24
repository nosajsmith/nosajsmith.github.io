# scenario_loader.py — load units from scenario JSON (accepts "side")
import json
from game_state import Unit

def load_units_from_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    units = []
    for raw in data.get("units", []):
        unit_id = raw["unit_id"]
        name = raw.get("name", unit_id)
        position = raw.get("position", [0, 0])
        side = (raw.get("side") or "BLUE").upper()
        units.append(Unit(unit_id, name, position, side))
    return units
