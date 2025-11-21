"""
G-4 Logistics Staff Section
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState
from engine.staff.base_staff import StaffSection   # <-- FIXED HERE


@dataclass
class SupplyStatus:
    unit_id: str
    supply_pct: int
    notes: str = ""


class G4Logistics(StaffSection):
    def __init__(self, units: UnitRepository) -> None:
        super().__init__("G-4 Logistics", units)
        self.last_report: Dict[str, SupplyStatus] = {}

    def run_daily_cycle(self, t: GameTime) -> None:
        for unit in self.units.all_units():
            self._update_unit_supply(unit)

    def on_day_end(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def _update_unit_supply(self, unit: UnitState) -> None:
        old_supply = unit.supply
        unit.supply = max(0, min(100, unit.supply - 1))

        self.last_report[unit.id] = SupplyStatus(
            unit_id=unit.id,
            supply_pct=unit.supply,
            notes=f"Supply changed from {old_supply} to {unit.supply}"
        )
