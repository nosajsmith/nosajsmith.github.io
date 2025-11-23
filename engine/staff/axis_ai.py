"""
Simple Axis AI staff (early stub).

- If Axis and Allied units share a location and Axis unit is in
  decent condition, set posture to ATTACK.
- Otherwise, Axis units DEFEND by default.
"""

from __future__ import annotations
from typing import List

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, Posture
from engine.staff.base_staff import StaffSection


class AxisAI(StaffSection):
    def __init__(self, units: UnitRepository) -> None:
        super().__init__("Axis AI", units)
        self.last_log: List[str] = []

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_log.clear()

        axis_units = [u for u in self.units.all_units() if u.side == Side.AXIS]
        allied_units = [u for u in self.units.all_units() if u.side == Side.ALLIED]

        if not axis_units or not allied_units:
            return

        # Map Allied presence by location
        allied_locs = {u.location_id for u in allied_units}

        for u in axis_units:
            if u.location_id in allied_locs:
                # Contact! decide whether to attack
                if u.readiness > 30 and u.morale > 30 and u.fatigue < 90:
                    u.posture = Posture.ATTACK
                    self.last_log.append(
                        f"Axis AI: {u.id} at {u.location_id} switches to ATTACK (contact)."
                    )
                else:
                    u.posture = Posture.DEFEND
                    self.last_log.append(
                        f"Axis AI: {u.id} at {u.location_id} holds in DEFEND (too tired)."
                    )
            else:
                # No contact – default to DEFEND posture
                u.posture = Posture.DEFEND
