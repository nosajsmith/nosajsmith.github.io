"""
Unit model for MWE engine.

Defines:
- Side (Allied/Axis)
- UnitType (Infantry, Armored, HQ, etc.)
- Posture (MOVE, ATTACK, DEFEND, REST, REFIT)

- UnitState dataclass
- UnitRepository container with lookup helpers and JSON serializer
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Side(Enum):
    ALLIED = "Allied"
    AXIS = "Axis"


class UnitType(Enum):
    INFANTRY = "INFANTRY"
    ARMORED = "ARMORED"
    SUPPORT = "SUPPORT"
    HQ = "HQ"
    NAVAL = "NAVAL"
    AIR = "AIR"

    @classmethod
    def _missing_(cls, value):
        """
        Be forgiving about how unit types are written in JSON:
        accept "Infantry", "INF", "INFANTRY", etc.
        """
        if isinstance(value, str):
            v = value.upper()

            # Common short/alt forms
            aliases = {
                "INF": "INFANTRY",
                "ARMOUR": "ARMORED",
                "ARMOR": "ARMORED",
            }

            if v in aliases:
                return cls[aliases[v]]

            # Accept using the member name directly (INFANTRY, ARMORED, etc.)
            if v in cls.__members__:
                return cls[v]

        raise ValueError(f"{value!r} is not a valid UnitType")


class Posture(Enum):
    MOVE = "MOVE"
    ATTACK = "ATTACK"
    DEFEND = "DEFEND"
    REST = "REST"
    REFIT = "REFIT"


# ---------------------------------------------------------------------------
# UnitState
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

    # Optional link to higher HQ (used by some staff / scenario logic)
    hq_unit_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class UnitRepository:
    """
    Stores all units in the scenario. Provides lookups and serializers.
    """

    def __init__(self) -> None:
        self._units: Dict[str, UnitState] = {}

    # Basic ops --------------------------------------------------------------

    def add(self, u: UnitState) -> None:
        self._units[u.id] = u

    def remove(self, unit_id: str) -> None:
        if unit_id in self._units:
            del self._units[unit_id]

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self._units.get(unit_id)

    def all_units(self) -> List[UnitState]:
        return list(self._units.values())

    # EngineAPI / JSON serialization ----------------------------------------

    def to_dict(self) -> Dict[str, dict]:
        """
        JSON-safe snapshot of all units, keyed by unit id.
        """
        out: Dict[str, dict] = {}
        for u in self._units.values():
            out[u.id] = {
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
                "posture": u.posture.name,
                "hq_unit_id": u.hq_unit_id,
            }
        return out
