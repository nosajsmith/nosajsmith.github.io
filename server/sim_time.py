from __future__ import annotations

class SimTime:
    """
    Phase 8 HARDING: forward-only simulation clock.
    Units: hours since scenario start.
    """
    def __init__(self) -> None:
        self._hours: int = 0

    def now(self) -> int:
        return self._hours

    def advance(self, dt_hours: int) -> int:
        if not isinstance(dt_hours, int):
            raise ValueError("dt_hours must be int")
        if dt_hours <= 0:
            raise ValueError("dt_hours must be > 0")
        self._hours += dt_hours
        return self._hours

    def reset(self) -> None:
        self._hours = 0
