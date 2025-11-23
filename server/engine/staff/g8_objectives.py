"""
G-8 Objectives & Victory

Tracks:
- Control of objective locations
- Victory points (VP) awarded when objectives are secured
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

from engine.staff.base_staff import StaffSection
from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side


class G8Objectives(StaffSection):
    def __init__(
        self,
        units: UnitRepository,
        objectives: List[Dict[str, Any]],
    ):
        super().__init__("G-8 Objectives", units)
        self.objectives: List[Dict[str, Any]] = objectives or []
        self.control_by_loc: Dict[str, Optional[Side]] = {}
        self.vp: Dict[Side, int] = {
            Side.ALLIED: 0,
            Side.AXIS: 0,
        }
        self.events: List[str] = []

    # We evaluate objectives at end of each day
    def on_day_end(self, t: GameTime) -> None:
        self._update_objectives(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        return

    # ------------------------------------------------------------------ helpers

    def _determine_control_for_location(self, loc_id: str) -> Optional[Side]:
        """
        Determine which side (if any) clearly controls a location:
        - If only Allied units present: Allied
        - If only Axis units present: Axis
        - If both or none: None (contested or empty)
        """
        allied_present = False
        axis_present = False

        for u in self.units.all_units():
            if u.location_id != loc_id:
                continue
            if u.side == Side.ALLIED:
                allied_present = True
            elif u.side == Side.AXIS:
                axis_present = True

        if allied_present and not axis_present:
            return Side.ALLIED
        if axis_present and not allied_present:
            return Side.AXIS
        return None

    def _update_objectives(self, t: GameTime) -> None:
        """
        For each objective:
        - Check who controls the hex
        - If control changes and matches the objective side, award VP once
        """
        for obj in self.objectives:
            loc_id = obj.get("location_id")
            side_str = obj.get("side")
            if not loc_id or not side_str:
                continue

            desired_side = Side(side_str)

            previous_control = self.control_by_loc.get(loc_id)
            current_control = self._determine_control_for_location(loc_id)

            if previous_control == current_control:
                # no change in control state
                continue

            # Update stored control
            self.control_by_loc[loc_id] = current_control

            # Award VP only when the desired side takes control
            if current_control == desired_side:
                value = int(obj.get("value", 0))
                desc = obj.get("description", "")
                self.vp[desired_side] = self.vp.get(desired_side, 0) + value
                self.events.append(
                    f"Day {t.day}: {current_control.name} secured objective "
                    f"{loc_id} (+{value} VP). {desc}"
                )
            else:
                # Could log loss/contested, but no VP change for now
                if previous_control is not None and current_control is None:
                    self.events.append(
                        f"Day {t.day}: Objective {loc_id} has become contested/empty."
                    )
                elif previous_control is not None and current_control is not None:
                    # switched control away from desired side (if that mattered)
                    self.events.append(
                        f"Day {t.day}: Control of {loc_id} changed from "
                        f"{previous_control.name} to {current_control.name}."
                    )
