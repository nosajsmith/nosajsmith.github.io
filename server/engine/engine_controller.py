"""
engine_controller.py
Safe wrapper around EngineAPI for Bridge / UI
Phase 8 — supports structured logging.
"""

from __future__ import annotations
from typing import Any, Dict

from engine.engine_api import EngineAPI


class EngineController:
    """
    Provides try/except safe versions of EngineAPI functions.
    Suitable for Bridge communication.
    """

    def __init__(self, debug: bool = False):
        self.api = EngineAPI()
        self.debug = debug

    # -----------------------------------------
    def _wrap(self, fn, *args, **kwargs) -> Dict[str, Any]:
        try:
            result = fn(*args, **kwargs)
            return {"ok": True, "payload": result}
        except Exception as e:
            if self.debug:
                raise
            return {"ok": False, "error": str(e)}

    # -----------------------------------------
    def load_scenario(self, scenario_id: str):
        return self._wrap(self.api.load_scenario, scenario_id)

    def start_game(self):
        return self._wrap(self.api.start_game)

    def apply_player_action(self, action: Dict[str, Any]):
        return self._wrap(self.api.apply_player_action, action)

    def process_turn(self):
        return self._wrap(self.api.process_turn)
