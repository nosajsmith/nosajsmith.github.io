"""
G-4 Logistics

Handles:
- Daily supply consumption based on posture
- Supply replenishment from scenario supply sources
"""

from __future__ import annotations
from typing import List, Dict, Any

from engine.staff.base_staff import StaffSection
from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Posture, Side


class G4Logistics(StaffSection):
    def __init__(self, units: UnitRepository, supply_sources: List[Dict[str, Any]]):
        super().__init__("G-4 Logistics", units)
        self.supply_sources: List[Dict[str, Any]] = supply_sources or []
        self.last_log: List[str] = []

    # We run logistics at end of each day
    def on_day_end(self, t: GameTime) -> None:
        self.last_log.clear()
        self._apply_consumption(t)
        self._apply_supply_sources(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        # Not used for now
        return

    # ------------------------------------------------------------------ internals

    def _apply_consumption(self, t: GameTime) -> None:
        """
        Basic supply consumption per unit, influenced by posture.
        """
        for u in self.units.all_units():
            consumption = 1  # base

            if u.posture == Posture.ATTACK:
                consumption += 2
            elif u.posture == Posture.MOVE:
                consumption += 1
            elif u.posture == Posture.DEFEND:
                consumption += 1
            elif u.posture in (Posture.REST, Posture.REFIT):
                # resting / refitting uses almost no additional supply
                consumption += 0

            before = u.supply
            u.supply = max(0, u.supply - consumption)
            self.last_log.append(
                f"G-4: {u.id} consumed {consumption}, supply {before}->{u.supply}"
            )

    def _apply_supply_sources(self, t: GameTime) -> None:
        """
        Apply scenario supply sources to units sitting on those locations.
        Simple model:
        - Each source has a daily_supply value
        - It is split evenly between all friendly units in that hex
        - Supply capped at 100
        - Small positive effect on fatigue/readiness
        """
        for src in self.supply_sources:
            loc_id = src.get("location_id")
            side_str = src.get("side")
            daily_supply = int(src.get("daily_supply", 0))

            if not loc_id or not side_str or daily_supply <= 0:
                continue

            side = Side(side_str)
            units_here = [
                u
                for u in self.units.all_units()
                if u.location_id == loc_id and u.side == side
            ]
            if not units_here:
                continue

            per_unit = max(1, daily_supply // len(units_here))

            for u in units_here:
                before_sup = u.supply
                u.supply = min(100, u.supply + per_unit)

                # Simple restorative effect from being in a supplied hex
                if u.fatigue > 0:
                    u.fatigue = max(0, u.fatigue - 2)
                u.readiness = min(100, u.readiness + 2)

                self.last_log.append(
                    f"G-4: {u.id} resupplied +{per_unit} at {loc_id}, "
                    f"supply {before_sup}->{u.supply}"
                )
