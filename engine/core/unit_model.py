from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


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


class Posture(str, Enum):
    HOLD = "HOLD"
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

    fatigue: int = 0
    morale: int = 50
    supply: int = 100
    readiness: int = 50

    location_id: str = ""
    posture: Posture = Posture.HOLD

    # Optional command relationship (used by scenario_loader / future command rules)
    hq_unit_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Enums -> values for JSON friendliness
        d["side"] = self.side.value
        d["unit_type"] = self.unit_type.value
        d["posture"] = self.posture.value
        return d


class UnitRepository:
    """
    Minimal, stable repository interface used across staff sections.

    Required by staff:
      - all_units()
      - get(id)
      - add(unit)
      - to_list()
    """

    def __init__(self) -> None:
        self._by_id: Dict[str, UnitState] = {}

    def add(self, u: UnitState) -> None:
        self._by_id[u.id] = u

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self._by_id.get(unit_id)

    def remove(self, unit_id: str) -> None:
        if unit_id in self._by_id:
            del self._by_id[unit_id]

    def all_units(self) -> List[UnitState]:
        return list(self._by_id.values())

    def to_list(self) -> List[Dict[str, Any]]:
        return [u.to_dict() for u in self.all_units()]

    @staticmethod
    def from_units(units: List[UnitState]) -> "UnitRepository":
        repo = UnitRepository()
        for u in units:
            repo.add(u)
        return repo
