from __future__ import annotations
from dataclasses import dataclass

@dataclass
class StaffModelV1:
    """
    Phase 8 HARDING
    Delay-only staff friction model.

    staff_capacity:
        How many concurrent orders HQ can process without delay.

    load:
        Current active workload.
    """
    staff_capacity: int = 4
    load: int = 0

    def estimate_latency(self, base_eta_hours: int) -> int:
        """
        Returns effective ETA after staff friction.
        Simple rule:
          - under capacity: no delay
          - over capacity: +2h per overload slot
        """
        if base_eta_hours <= 0:
            raise ValueError("base_eta_hours must be > 0")

        overload = max(0, self.load - self.staff_capacity)
        return base_eta_hours + (overload * 2)

    def submit_order(self) -> None:
        """Called when an order is accepted."""
        self.load += 1

    def advance_time(self, dt_hours: int) -> None:
        """
        Bleed staff load over time.
        Every 6 hours reduces load by 1 (floor).
        """
        if dt_hours <= 0:
            return
        decay = dt_hours // 6
        if decay > 0:
            self.load = max(0, self.load - decay)
