"""
Unit model for MWE.

Keeps track of:
- static info (name, side, type)
- dynamic state (strength, fatigue, supply, morale)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional


class Side(str, Enum):
    ALLIED = "Allied"
    AXIS = "Axis"      # or "Japan" later if you prefer


class UnitType(str, Enum):
    HQ = "HQ"
    INFANTRY = "Infantry"
    ARMORED = "Armored"
    NAVAL = "Naval"
    AIR = "Air"
    SUPPORT = "Support"


class Posture(str, Enum):
    REST = "Rest"
    DEFEND = "Defend"
    ATTACK = "Attack"
    MOVE = "Move"
    REFIT = "Refit"


@dataclass
class UnitState:
    id: str
    name: str
    side: Side
    unit_type: UnitType

    # Dynamic combat state
    strength: int = 100       # abstract combat power
    fatigue: int = 0          # 0–100
    morale: int = 50          # 0–100
    supply: int = 100         # 0–100 (% of needs met)
    readiness: int = 50       # 0–100

    posture: Posture = Posture.REST
    location_id: str = "UNKNOWN"   # link to map hex/area
    hq_unit_id: Optional[str] = None

    def is_combat_effective(self) -> bool:
        """Very rough first-pass rule."""
        return self.strength > 20 and self.supply > 30 and self.fatigue < 80


class UnitRepository:
    """
    Simple in-memory unit store.

    Later this can load/save from scenario files, DB, etc.
    """

    def __init__(self) -> None:
        self._units: Dict[str, UnitState] = {}

    # CRUD operations ---------------------------------------------------------

    def add(self, unit: UnitState) -> None:
        self._units[unit.id] = unit

    def get(self, unit_id: str) -> Optional[UnitState]:
        return self._units.get(unit_id)

    def all_units(self):
        return list(self._units.values())

    # Convenience helpers -----------------------------------------------------

    def by_side(self, side: Side):
        return [u for u in self._units.values() if u.side == side]

    def at_location(self, location_id: str):
        return [u for u in self._units.values() if u.location_id == location_id]
