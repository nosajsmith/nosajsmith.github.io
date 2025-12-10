"""
EngineAPI – unified, bridge-friendly engine surface

Exposes:
    load_scenario(scenario_id)
    start_game()
    apply_player_action(action)
    process_turn()
    get_game_state()
    get_logs()
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository, UnitState, Side, Posture
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans
from engine.staff.g6_signals import G6Signals
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives
from engine.scenario_loader import load_scenario


class EngineAPI:
    """
    Thin façade over the core engine/state and staff sections.
    """

    def __init__(self) -> None:
        # Scenario / core state
        self.scenario_id: Optional[str] = None
        self.meta: Dict[str, Any] = {}
        self.time: Optional[GameTime] = None
        self.turn: int = 0

        self.game_map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None

        # Staff sections
        self.g3: Optional[G3Operations] = None
        self.g4: Optional[G4Logistics] = None
        self.g5: Optional[G5Plans] = None
        self.g6: Optional[G6Signals] = None
        self.g7: Optional[G7Reinforcements] = None
        self.g8: Optional[G8Objectives] = None

        # Unified log buffer (list of dicts)
        self._logs: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------- utils

    def _log(self, src: str, phase: str, message: str) -> None:
        """
        Append a structured log entry.
        """
        t = self.time.to_dict() if self.time else {"day": 0, "phase": "n/a", "weather": "n/a"}
        entry = {
            "src": src,
            "turn": self.turn,
            "phase": phase,
            "day": t.get("day", 0),
            "time": t,
            "message": message,
        }
        self._logs.append(entry)

    def _ensure_ready(self) -> None:
        if not (self.scenario_id and self.time and self.game_map and self.units):
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario() first.")

    def _staff_sections(self) -> List[Any]:
        return [
            s
            for s in [self.g3, self.g4, self.g5, self.g6, self.g7, self.g8]
            if s is not None
        ]

    # ----------------------------------------------------------------- public API

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Load scenario and wire up staff sections.

        Returns a small metadata dict suitable for UI display.
        """
        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.scenario_id = scenario_id
        self.time = start_time        # GameTime
        self.turn = 1

        self.game_map = game_map      # GameMap
        self.units = units_repo       # UnitRepository
        self.meta = meta or {}

        # Scenario extras
        supply_sources = self.meta.get("supply_sources", [])
        objectives = self.meta.get("objectives", [])
        reinforcements = self.meta.get("reinforcements", [])

        # Staff sections
        self.g3 = G3Operations(self.units, self.game_map)
        self.g4 = G4Logistics(self.units, supply_sources)
        self.g7 = G7Reinforcements(self.units, reinforcements)
        self.g8 = G8Objectives(self.units, objectives)
        self.g5 = G5Plans(self.units, self.game_map, g3=self.g3, mode="advisor", personality="macarthur")
        self.g6 = G6Signals(self.units, self.g3)

        # Reset logs
        self._logs.clear()
        self._log("ENGINE", "load", f"Loaded scenario {scenario_id}")

        # Return lightweight metadata for front-ends
        return {
            "id": self.meta.get("id", scenario_id),
            "name": self.meta.get("name", scenario_id),
            "description": self.meta.get("description", ""),
            "start_day": self.time.day,
            "weather": self.time.weather,
        }

    def start_game(self) -> Dict[str, Any]:
        """
        Start game but do NOT advance time yet.
        Just return initial snapshot.
        """
        self._ensure_ready()
        self._log("ENGINE", "start", f"Game started for scenario {self.scenario_id}")
        return self.get_game_state()

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle simple player actions.

        Currently supports:
        - type == "move":
            { "type": "move",
              "unit_id": "US-1MAR",
              "target": "TULAGI",
              "posture": "ATTACK" }
        """
        self._ensure_ready()

        a_type = action.get("type")
        if a_type != "move":
            msg = f"Unknown action type: {a_type}"
            self._log("ENGINE", "orders", msg)
            return {"status": "error", "message": msg}

        unit_id = action.get("unit_id")
        target = action.get("target")
        posture_raw = action.get("posture", "MOVE")

        if not unit_id or not target:
            msg = "move action requires 'unit_id' and 'target'"
            self._log("ENGINE", "orders", msg)
            return {"status": "error", "message": msg}

        unit = self.units.get(unit_id)
        if unit is None:
            msg = f"Unknown unit id: {unit_id}"
            self._log("ENGINE", "orders", msg)
            return {"status": "error", "message": msg}

        # Resolve posture enum
        if isinstance(posture_raw, Posture):
            posture = posture_raw
        else:
            try:
                posture = Posture[posture_raw.upper()]
            except Exception:
                posture = Posture.MOVE

        # For now, send orders straight to G-3 (no G-6 delay).
        if self.g3 is not None:
            self.g3.issue_move_order(unit_id, target, posture, t=self.time)

        self._log(
            "PLAYER",
            "orders",
            f"Order: {unit_id} -> {target}, posture={posture.name}"
        )
        return {"status": "ok"}

    def process_turn(self) -> Dict[str, Any]:
        """
        Process a single campaign day.

        Order:
        - Start-of-day hooks for current day (G-5 planning, G-7 arrivals, G-6 delivery, G-3 ops)
        - Per-day cycles (run_daily_cycle) for those that use it
        - End-of-day hooks (G-4 logistics, G-8 objectives)
        - Increment day and turn counter
        """
        self._ensure_ready()
        t = self.time

        # 1) Start-of-day for CURRENT day
        for s in self._staff_sections():
            if hasattr(s, "on_day_start"):
                s.on_day_start(t)

        # 2) Per-day cycles (ops, etc.)
        for s in self._staff_sections():
            if hasattr(s, "run_daily_cycle"):
                s.run_daily_cycle(t)

        # 3) End-of-day
        for s in self._staff_sections():
            if hasattr(s, "on_day_end"):
                s.on_day_end(t)

        # 4) Advance to next day (simple increment)
        current_day = self.time.day
        self.time.day += 1
        self.time.phase = "day"
        # Weather stays the same for now; rules can change it later.

        self.turn += 1
        self._log("ENGINE", "turn", f"Processed Day {current_day}; now Day {self.time.day}")

        return self.get_game_state()

    # ----------------------------------------------------------------- state / logs

    def get_game_state(self) -> Dict[str, Any]:
        """
        Return a JSON-serializable snapshot of the current game state.
        """
        self._ensure_ready()

        time_dict = self.time.to_dict()
        scenario_name = self.meta.get("name", self.scenario_id)

        # Victory points (if G-8 active)
        vp: Dict[str, int] = {}
        if self.g8 is not None:
            for side in (Side.ALLIED, Side.AXIS):
                vp[side.name] = self.g8.vp.get(side, 0)

        game_block = {
            "time": time_dict,
            "scenario": scenario_name,
            "vp": vp,
        }

        units_block = self.units.to_dict() if self.units is not None else []
        map_block = self.game_map.to_dict() if self.game_map is not None else {}

        return {
            "game": game_block,
            "units": units_block,
            "map": map_block,
        }

    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Return the cumulative log buffer.
        (Front-end/bridge can trim as needed.)
        """
        return list(self._logs)
