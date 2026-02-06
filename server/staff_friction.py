from __future__ import annotations
from dataclasses import dataclass

@dataclass
class StaffModel:
    """
    Phase 8 HARDING: delay-only staff friction.
    staff_capacity: how many concurrent "work items" HQ can handle before delays spike.
    load: current work items queued/active.
    """
    staff_capacity: int = 4
    load: int = 0

    def estimate_latency_hours(self, base_hours: int) -> int:
        """
        Returns added delay due to staff overload.
        Simple model:
          - under capacity: 0 extra
          - over capacity: +2 hours per overload step
        """
        overload = max(0, self.load - self.staff_capacity)
        extra = overload * 2
        return base_hours + extra

    def on_order_submitted(self) -> None:
        self.load += 1

    def on_time_advanced(self, dt_hours: int) -> None:
        """
        Bleed off staff load slowly as time passes.
        This is intentionally coarse for v1.
        """
        # Every 6 hours, reduce load by 1 (floor), but not below 0.
        steps = dt_hours // 6
        if steps > 0:
            self.load = max(0, self.load - steps)
