"""
G-7 Reinforcements

Handles:
- Reading reinforcements from scenario metadata
- Spawning units on the correct arrival day
- Logging reinforcement arrivals
"""

from __future__ import annotations
from typing import List, Dict, Any
from engine.staff.base_staff import StaffSection
from engine.core.time_system import GameTime
from engine.core.unit_model import UnitState, Side, UnitType, UnitRepository


class G7Reinforcements(StaffSection):
    def __init__(
        self,
        units: UnitRepository,
        scenario_reinforcements: List[Dict[str, Any]]
    ):
        super().__init__("G-7 Reinforcements", units)
        self.reinforcements = scenario_reinforcements  # loaded from scenario JSON
        self.arrived_log: List[str] = []
        self._already_arrived_ids: set = set()  # keep from spawning twice

    def on_day_start(self, t: GameTime) -> None:
        self._check_arrivals(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        return  # nothing else needed

    def _check_arrivals(self, t: GameTime) -> None:
        """Check if any reinforcements arrive today."""
        for r in self.reinforcements:
            unit_id = r["id"]

            if unit_id in self._already_arrived_ids:
                continue

            if r.get("arrival_day") == t.day:
                # Spawn the unit
                new_unit = UnitState(
                    id=r["id"],
                    name=r["name"],
                    side=Side(r["side"]),
                    unit_type=UnitType(r["unit_type"]),
                    strength=r["strength"],
                    fatigue=r.get("fatigue", 0),
                    morale=r.get("morale", 50),
                    supply=r.get("supply", 100),
                    readiness=r.get("readiness", 50),
                    location_id=r["entry_location_id"],
                )

                self.units.add(new_unit)
                self._already_arrived_ids.add(unit_id)

                msg = (
                    f"G-7 Reinforcements: {new_unit.id} ({new_unit.name}) "
                    f"arrived at {new_unit.location_id} on Day {t.day}"
                )
                self.arrived_log.append(msg)
