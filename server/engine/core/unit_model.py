"""
Unit model for MWE.

Contains:
  - Enum Side (ALLIED / AXIS)
  - Enum UnitType
  - Enum Posture
  - UnitState dataclass
  - UnitRepository container
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Iterable
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

class Side(str, Enum):
    ALLIED = "ALLIED"
    AXIS = "AXIS"


class UnitType(str, Enum):
    INFANTRY = "INFANTRY"
    ARMOR = "ARMOR"
    AIR = "AIR"
    NAVAL = "NAVAL"


class Posture(str, Enum):
    ATTACK = "ATTACK"
    DEFEND = "DEFEND"
    MOVE = "MOVE"
    REST = "REST"
    REFIT = "REFIT"


# ---------------------------------------------------------------------------
# UNIT STATE
# ---------------------------------------------------------------------------

@dataclass
class UnitState:
    id: str
    name: str
    side: Side
    unit_type: UnitType

    strength: int = 100
    fatigue: int = 0
    morale: int = 50
    supply: int = 100
    readiness: int = 50

    location_id: str = ""
    posture: Posture = Posture.DEFEND

    hq_unit_id: Optional[str] = None


# ---------------------------------------------------------------------------
# UNIT REPOSITORY
# ---------------------------------------------------------------------------

class UnitRepository:
    """
    Stores UnitState objects and provides search helpers.
    THIS VERSION ACCEPTS NO CONSTRUCTOR ARGUMENTS.
    """

    def __init__(self) -> None:
        self.units: Dict[str, UnitState] = {}

    def add(self, unit: UnitState) -> None:
        self.units[unit.id] = unit

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self.units.get(unit_id)

    def all_units(self) -> Iterable[UnitState]:
        return self.units.values()

    # Used by EngineAPI.get_game_state()
    def to_dict(self) -> Dict[str, Dict]:
        return {
            uid: {
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
            for uid, u in self.units.items()
        }
