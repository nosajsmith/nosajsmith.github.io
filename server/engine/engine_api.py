"""
engine_api.py
High-level engine interface for the MacArthur War Engine (MWE)
Phase 8 — includes unified structured logging.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

from engine.core.time_system import TimeSystem, GameTime
from engine.scenario_loader import load_scenario
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans
from engine.staff.g6_signals import G6Signals
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives


class EngineAPI:
    """
    Main engine API called by the bridge or UI.
    """

    def __init__(self):
        self.ts: Optional[TimeSystem] = None
        self.game_map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None
        self.meta: Dict[str, Any] = {}
        self.turn_logs: List[Dict[str, Any]] = []

        # Staff sections
        self.g3: Optional[G3Operations] = None
        self.g4: Optional[G4Logistics] = None
        self.g5: Optional[G5Plans] = None
        self.g6: Optional[G6Signals] = None
        self.g7: Optional[G7Reinforcements] = None
        self.g8: Optional[G8Objectives] = None

    # ------------------------------------------------------------------
    # Scenario loading
    # ------------------------------------------------------------------

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Loads scenario data and initializes:
          - time system
          - map
          - units
          - staff sections
        """

        start_time, game_map, units, meta = load_scenario(scenario_id)

        self.ts = TimeSystem(start_time)
        self.game_map = game_map
        self.units = units
        self.meta = meta

        # Build staff sections
        self.g3 = G3Operations(self.game_map, self.units)
        self.g4 = G4Logistics(self.units, meta.get("supply_sources", []))
        self.g5 = G5Plans(self.units, self.game_map)
        self.g6 = G6Signals(self.units)
        self.g7 = G7Reinforcements(self.units, meta.get("reinforcements", []))
        self.g8 = G8Objectives(self.units, meta.get("objectives", []))

        return {
            "status": "ok",
            "meta": meta,
        }

    # ------------------------------------------------------------------
    # Internal check
    # ------------------------------------------------------------------

    def _ensure_ready(self):
        if not (self.ts and self.game_map and self.units):
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario() first.")

    # ------------------------------------------------------------------
    # Start game
    # ------------------------------------------------------------------

    def start_game(self) -> Dict[str, Any]:
        self._ensure_ready()
        self.turn_logs = []
        return self.get_game_state()

    # ------------------------------------------------------------------
    # Apply a player action
    # ------------------------------------------------------------------

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_ready()

        # Movement request
        if action.get("type") == "move":
            uid = action.get("unit_id")
            tgt = action.get("target")
            posture = action.get("posture", "ATTACK")
            self.g3.issue_move_order(uid, tgt, posture)

        return {"status": "ok"}

    # ------------------------------------------------------------------
    # Process 1 turn of the game
    # ------------------------------------------------------------------

    def process_turn(self) -> Dict[str, Any]:
        self._ensure_ready()
        self.turn_logs = []

        # G-5 briefing (AI planning)
        self.g5.generate_briefing(self.ts.time)

        # G-7 reinforcements
        self.g7.check_reinforcements(self.ts.time)

        # G-4 logistics — supply update
        self.g4.process_day(self.ts.time)

        # G-3 combat / movement
        self.g3.process_operations(self.ts.time)
        battles = self.g3.last_battles

        # G-6 signals
        self.g6.collect(self.ts.time)

        # G-8 objectives
        self.g8.evaluate(self.ts.time)

        # Advance time
        self.ts.advance()

        # Build unified logs
        self._collect_turn_logs()

        return self.get_game_state()

    # ------------------------------------------------------------------
    # Unified structured logs
    # ------------------------------------------------------------------

    def _collect_turn_logs(self) -> None:
        """
        Produces log packets of the form:
        {
          "src": "G-3",
          "turn": 5,
          "phase": "day",
          "message": "...",
        }
        """

        turn = self.ts.time.day
        phase = self.ts.time.phase
        logs = []

        def add(src: str, msg: str):
            logs.append({
                "src": src,
                "turn": turn,
                "phase": phase,
                "message": msg,
            })

        # G-5 briefing
        if self.g5 and self.g5.last_briefing:
            add("G-5", "BRIEFING:")
            for line in self.g5.last_briefing.splitlines():
                add("G-5", line)

        # G-3 battles
        if self.g3 and self.g3.last_battles:
            for br in self.g3.last_battles:
                add("G-3", br.summary)
                for rnd in br.rounds:
                    add(
                        "G-3",
                        f"Round {rnd.round_index}: Allied {rnd.allied_loss}, "
                        f"Axis {rnd.axis_loss} ({rnd.notes})"
                    )

        # G-4 logistics
        if self.g4 and getattr(self.g4, "last_log", None):
            for line in self.g4.last_log:
                add("G-4", line)

        # G-6 signals
        if self.g6 and getattr(self.g6, "last_log", None):
            for line in self.g6.last_log:
                add("G-6", line)

        # G-7 reinforcements
        if self.g7 and getattr(self.g7, "arrived_log", None):
            for line in self.g7.arrived_log:
                add("G-7", line)

        # G-8 objectives
        if self.g8 and getattr(self.g8, "events", None):
            for ev in self.g8.events:
                add("G-8", ev)

        self.turn_logs = logs

    # ------------------------------------------------------------------
    # Data retrieval
    # ------------------------------------------------------------------

    def get_game_state(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "game": {
                "time": {
                    "day": self.ts.time.day,
                    "phase": self.ts.time.phase,
                    "weather": self.ts.time.weather,
                },
                "turn": self.ts.time.day,
            },
            "units": self.units.to_dict(),
            "map": self.game_map.to_dict() if hasattr(self.game_map, "to_dict") else {},
            "logs": self.turn_logs,
        }

    def get_logs(self):
        return self.turn_logs
