from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Side(str, Enum):
    ALLIED = "ALLIED"
    AXIS = "AXIS"


class UnitType(str, Enum):
    INFANTRY = "INFANTRY"
    ARMORED = "ARMORED"
    HQ = "HQ"
    SUPPORT = "SUPPORT"
    NAVAL = "NAVAL"
    AIR = "AIR"


class Posture(str, Enum):
    MOVE = "MOVE"
    ATTACK = "ATTACK"
    DEFEND = "DEFEND"
    REST = "REST"
    REFIT = "REFIT"


@dataclass
class UnitState:
    id: str
    name: str
    side: Side
    unit_type: UnitType
    strength: int
    fatigue: int
    morale: int
    supply: int
    readiness: int
    location_id: str
    posture: Posture = Posture.DEFEND
    hq_unit_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "side": self.side.value,
            "unit_type": self.unit_type.value,
            "strength": self.strength,
            "fatigue": self.fatigue,
            "morale": self.morale,
            "supply": self.supply,
            "readiness": self.readiness,
            "location_id": self.location_id,
            "posture": self.posture.name,
            "hq_unit_id": self.hq_unit_id,
        }


class UnitRepository:
    def __init__(self) -> None:
        self._units: Dict[str, UnitState] = {}

    def add(self, unit: UnitState) -> None:
        self._units[unit.id] = unit

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self._units.get(unit_id)

    def remove(self, unit_id: str) -> None:
        self._units.pop(unit_id, None)

    def all_units(self) -> List[UnitState]:
        return list(self._units.values())

    def to_dict(self) -> Dict[str, Dict]:
        return {uid: u.to_dict() for uid, u in self._units.items()}
