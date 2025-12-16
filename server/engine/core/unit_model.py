from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any, List


class Side(str, Enum):
    ALLIED = "ALLIED"
    AXIS = "AXIS"


class UnitType(str, Enum):
    INFANTRY = "INFANTRY"
    ARMOR = "ARMOR"
    ARTILLERY = "ARTILLERY"
    HQ = "HQ"
    NAVAL = "NAVAL"
    AIR = "AIR"

    # Alias to kill the "ARMORED" bunker forever
    ARMORED = "ARMOR"


class Posture(str, Enum):
    HOLD = "HOLD"
    ATTACK = "ATTACK"
    DEFEND = "DEFEND"
    MOVE = "MOVE"


@dataclass
class UnitState:
    id: str
    name: str
    side: Side
    unit_type: UnitType
    strength: int = 100
    fatigue: int = 0
    morale: int = 50
    supply: int = 50
    readiness: int = 50
    location_id: str = ""
    posture: Posture = Posture.HOLD
    hq_unit_id: Optional[str] = None


class UnitRepository:
    """
    IMPORTANT:
    - __init__ takes NO args (matches the error you hit)
    - use add() to load units
    """
    def __init__(self) -> None:
        self.units: Dict[str, UnitState] = {}

    def add(self, unit: UnitState) -> None:
        self.units[unit.id] = unit

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self.units.get(unit_id)

    def all(self) -> List[UnitState]:
        return list(self.units.values())

    def to_list(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for u in self.units.values():
            out.append(
                {
                    "id": u.id,
                    "name": u.name,
                    "side": u.side.value,
                    "unit_type": u.unit_type.value,
                    "strength": u.strength,
                    "fatigue": u.fatigue,
                    "morale": u.morale,
                    "supply": u.supply,
                    "readiness": u.readiness,
                    "location_id": u.location_id,
                    "posture": u.posture.value,
                    "hq_unit_id": u.hq_unit_id,
                }
            )
        return out
