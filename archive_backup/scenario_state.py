# -*- coding: utf-8 -*-
"""
scenario_state.py
-----------------
Phase 5: Scenario model & sync utilities.
Defines simple data structures for Units, HQs, and Objectives with basic serialization.
"""

from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Any
import json

@dataclass
class Unit:
    id: str
    name: str
    type: str  # inf, arm, mech, eng, arty, air, navy
    strength: int
    fatigue: int
    pos: Tuple[int,int]  # hex coords
    hq: str

@dataclass
class HQ:
    id: str
    name: str
    tier: str  # green, regular, veteran, elite
    stance: str  # aggressive, balanced, cautious

@dataclass
class Scenario:
    id: str
    name: str
    units: List[Unit]
    hqs: List[HQ]
    objectives: List[Tuple[int,int]]

def serialize(s: Scenario) -> str:
    return json.dumps({
        "id": s.id,
        "name": s.name,
        "units": [asdict(u) for u in s.units],
        "hqs": [asdict(h) for h in s.hqs],
        "objectives": s.objectives,
    })

def deserialize(js: str) -> Scenario:
    data = json.loads(js)
    units = [Unit(**u) for u in data["units"]]
    hqs = [HQ(**h) for h in data["hqs"]]
    return Scenario(id=data["id"], name=data["name"], units=units, hqs=hqs, objectives=[tuple(o) for o in data["objectives"]])
