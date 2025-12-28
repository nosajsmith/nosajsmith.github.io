from __future__ import annotations

import inspect
from typing import Any, Optional

# Import your staff sections
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans


class StaffManager:
    """
    Single entrypoint for staff hooks so EngineAPI can call staff without caring
    about individual file/class quirks.

    Contract we WANT:
      - on_day_start(self, time)
      - run_daily_cycle(self, time)
      - on_day_end(self, time) [optional]

    This wrapper is defensive: if a staff method currently takes 0 args, it still runs.
    (But you should standardize signatures after this works.)
    """

    def __init__(self, api: Any):
        # Keep reference to API if staff needs it (map/units/logs/etc).
        self.api = api

        # Instantiate staff sections
        self.g3 = G3Operations(api)
        self.g4 = G4Logistics(api)
        self.g5 = G5Plans(api)

    # -----------------------------
    # Hook calling helpers
    # -----------------------------
    def _call_hook(self, obj: Any, hook_name: str, time: Any) -> None:
        fn = getattr(obj, hook_name, None)
        if fn is None:
            return

        # Be defensive about signature mismatch during refactors.
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())

            # Bound method signatures usually have (time) only (self is already bound).
            # If it expects 0 params, call without time.
            if len(params) == 0:
                fn()
            else:
                fn(time)
        except TypeError:
            # Last-resort compatibility
            try:
                fn(time)
            except TypeError:
                fn()

    # -----------------------------
    # Public orchestration
    # -----------------------------
    def on_day_start(self, time: Any) -> None:
        self._call_hook(self.g3, "on_day_start", time)
        self._call_hook(self.g4, "on_day_start", time)
        self._call_hook(self.g5, "on_day_start", time)

    def run_daily_cycle(self, time: Any) -> None:
        self._call_hook(self.g3, "run_daily_cycle", time)
        self._call_hook(self.g4, "run_daily_cycle", time)
        self._call_hook(self.g5, "run_daily_cycle", time)

    def on_day_end(self, time: Any) -> None:
        self._call_hook(self.g3, "on_day_end", time)
        self._call_hook(self.g4, "on_day_end", time)
        self._call_hook(self.g5, "on_day_end", time)
