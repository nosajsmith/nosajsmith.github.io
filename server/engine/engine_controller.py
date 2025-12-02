"""
EngineController - Phase 8.3

Provides a *safe* wrapper around EngineAPI:

- No blocking loops (each call does a bounded amount of work)
- Exceptions are caught and converted into error responses
- Engine always returns a valid state packet or an explicit error packet

This is the layer the bridge should talk to in production.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

from engine.engine_api import EngineAPI


class EngineController:
    """
    High-level, fault-tolerant controller for the MWE engine.

    All public methods:
      - are single-step (no loops)
      - catch exceptions
      - return a dict with at least:
        { "status": "ok" | "error", ... }

    This keeps the bridge/UI simple and safe.
    """

    def __init__(self, debug: bool = False) -> None:
        self.api = EngineAPI()
        self.debug = debug
        self.last_error: Optional[str] = None

    # ------------------------------------------------------------------ helpers

    def _ok(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload.setdefault("status", "ok")
        return payload

    def _err(self, message: str) -> Dict[str, Any]:
        self.last_error = message
        return {
            "status": "error",
            "error": message,
        }

    # ------------------------------------------------------------------ public API

    def safe_load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Safely load a scenario.

        Returns:
          { "status": "ok", "scenario": { ... } }
        or
          { "status": "error", "error": "..." }
        """
        try:
            meta = self.api.load_scenario(scenario_id)
            return self._ok({
                "scenario": meta,
            })
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to load scenario '{scenario_id}': {e}")

    def safe_start_game(self) -> Dict[str, Any]:
        """
        Safely start the game and return initial state.

        Returns:
          { "status": "ok", "state": EngineState }
        or
          { "status": "error", "error": "..." }
        """
        try:
            state = self.api.start_game()
            return self._ok({
                "state": state,
            })
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to start game: {e}")

    def safe_process_turn(self) -> Dict[str, Any]:
        """
        Safely process one turn.

        Returns:
          { "status": "ok", "state": EngineState, "logs": [... ] }
        or
          { "status": "error", "error": "..." }

        NOTE: This function NEVER loops; it advances exactly one turn.
        """
        try:
            state = self.api.process_turn()
            logs = self.api.get_logs()
            return self._ok({
                "state": state,
                "logs": logs,
            })
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to process turn: {e}")

    def safe_apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely apply a player action.

        Returns:
          { "status": "ok" }
        or
          { "status": "error", "error": "..." }

        This call does *not* advance the turn. It simply queues orders
        (e.g., via G-6) to be processed on the next safe_process_turn().
        """
        try:
            self.api.apply_player_action(action)
            return self._ok({})
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to apply action: {e}")

    def safe_get_state(self) -> Dict[str, Any]:
        """
        Safely return the current engine state without advancing time.

        Returns:
          { "status": "ok", "state": EngineState }
        or
          { "status": "error", "error": "..." }
        """
        try:
            state = self.api.get_game_state()
            return self._ok({
                "state": state,
            })
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to get state: {e}")

    def safe_get_logs(self) -> Dict[str, Any]:
        """
        Safely return the last turn's logs.

        Returns:
          { "status": "ok", "logs": [...] }
        or
          { "status": "error", "error": "..." }
        """
        try:
            logs = self.api.get_logs()
            return self._ok({
                "logs": logs,
            })
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._err(f"Failed to get logs: {e}")
