"""
G-7 Reinforcements Staff Section

Spawns new units based on scenario metadata:
- 'reinforcements' list in the scenario JSON.
"""

from __future__ import annotations
from typing import List, Dict, Any

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, UnitType
from engine.staff.base_staff import StaffSection


class G7Reinforcements(StaffSection):
    def __init__(
        self,
        units: UnitRepository,
        reinforcements_meta: List[Dict[str, Any]],
    ) -> None:
        super().__init__("G-7 Reinforcements", units)
        self._reinforcements = reinforcements_meta[:]
        self._spawned_ids = set()
        self.last_log: List[str] = []

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_log.clear()
        for r in self._reinforcements:
            rid = r.get("id")
            arrival_day = int(r.get("arrival_day", 0))
            if not rid or rid in self._spawned_ids:
                continue
            if t.day < arrival_day:
                continue

            if self.units.get(rid) is not None:
                # Already present for some reason
                self._spawned_ids.add(rid)
                continue

            # Spawn the reinforcement
            unit = UnitState(
                id=r["id"],
                name=r["name"],
                side=Side(r["side"]),
                unit_type=UnitType(r["unit_type"]),
                strength=r.get("strength", 100),
                fatigue=r.get("fatigue", 0),
                morale=r.get("morale", 50),
                supply=r.get("supply", 100),
                readiness=r.get("readiness", 50),
                location_id=r.get("entry_location_id", "UNKNOWN"),
                hq_unit_id=r.get("hq_unit_id"),
            )
            self.units.add(unit)
            self._spawned_ids.add(rid)

            self.last_log.append(
                f"G-7: Day {t.day} – Reinforcement arrived: {unit.id} "
                f"({unit.name}) at {unit.location_id}"
            )
