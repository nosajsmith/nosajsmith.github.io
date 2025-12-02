"""
EngineAPI - Phase 8.2

Unified interface the bridge/UI can call into.

Provides:
- load_scenario(name)
- start_game()
- process_turn()
- apply_player_action(action)
- get_game_state()
- get_map_data()
- get_unit_data()
- get_logs()
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

from engine.core.time_system import TimeSystem, GameTime
from engine.core.unit_model import Side, Posture, UnitRepository
from engine.core.map_model import GameMap
from engine.scenario_loader import load_scenario
from engine.engine_state import build_engine_state

# Staff sections
from engine.staff.g1_personnel import G1Personnel
from engine.staff.g2_intel import G2Intelligence
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans
from engine.staff.g6_signals import G6Signals
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives


class EngineAPI:
    """
    High-level controller for the MWE engine.

    The bridge / UI should ONLY talk to this class, not directly to
    staff sections or core modules.
    """

    def __init__(self) -> None:
        # Core state
        self.scenario_id: Optional[str] = None
        self.meta: Dict[str, Any] = {}
        self.map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None
        self.ts: Optional[TimeSystem] = None

        # Staff
        self.g1: Optional[G1Personnel] = None
        self.g2: Optional[G2Intelligence] = None
        self.g3: Optional[G3Operations] = None
        self.g4: Optional[G4Logistics] = None
        self.g5: Optional[G5Plans] = None
        self.g6: Optional[G6Signals] = None
        self.g7: Optional[G7Reinforcements] = None
        self.g8: Optional[G8Objectives] = None

        # Logs for last processed turn
        self.turn_logs: List[str] = []

    # ------------------------------------------------------------------ helpers

    def _ensure_ready(self) -> None:
        if not (self.scenario_id and self.ts and self.map and self.units):
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario() first.")

    # ------------------------------------------------------------------ public API

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Load the given scenario and construct TimeSystem + staff.

        Returns scenario metadata suitable for a bridge to show in UI.
        """
        self.scenario_id = scenario_id

        start_time, game_map, units, meta = load_scenario(scenario_id)

        self.meta = dict(meta)
        self.map = game_map
        self.units = units

        # Time system
        self.ts = TimeSystem()
        self.ts.time.day = start_time.day
        self.ts.time.phase = start_time.phase
        self.ts.set_initial_weather(meta.get("weather", "Clear"))

        # Staff initialization
        self.g1 = G1Personnel(units)
        self.g2 = G2Intelligence(units, enemy_side=Side.AXIS)
        self.g3 = G3Operations(units, game_map)
        self.g4 = G4Logistics(units, meta.get("supply_sources", []))
        self.g5 = G5Plans(
            units,
            game_map,
            g3=self.g3,
            mode="advisor",
            personality="macarthur",
        )
        self.g6 = G6Signals(units, self.g3)
        self.g7 = G7Reinforcements(units, meta.get("reinforcements", []))
        self.g8 = G8Objectives(units, meta.get("objectives", []))

        # Register with time system
        self.ts.register_listener("g1", self.g1)
        self.ts.register_listener("g2", self.g2)
        self.ts.register_listener("g5", self.g5)
        self.ts.register_listener("g6", self.g6)
        self.ts.register_listener("g7", self.g7)
        self.ts.register_listener("g3", self.g3)
        self.ts.register_listener("g4", self.g4)
        self.ts.register_listener("g8", self.g8)

        # Clear logs
        self.turn_logs = []

        # Return minimal metadata for UI / bridge
        return {
            "id": meta.get("id", scenario_id),
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
            "start_day": start_time.day,
            "weather": meta.get("weather", "Unknown"),
            "objectives": meta.get("objectives", []),
            "supply_sources": meta.get("supply_sources", []),
        }

    def start_game(self) -> Dict[str, Any]:
        """
        Start game and return initial EngineState snapshot.
        (In this simple model, load_scenario() has already prepared everything.)
        """
        self._ensure_ready()
        self.turn_logs = []
        # You could add a "Day 0" planning/log layer here if desired
        return self.get_game_state()

    def process_turn(self) -> Dict[str, Any]:
        """
        Advance one full turn (day) and return updated EngineState snapshot.
        """
        self._ensure_ready()
        self.turn_logs = []

        # Advance one day in the time system
        self.ts.advance_one_day()

        # Collect logs from staff modules for this turn
        self._collect_turn_logs()

        # Return updated state
        return self.get_game_state()

    def apply_player_action(self, action: Dict[str, Any]) -> None:
        """
        Apply a player action.

        For now we support:
        {
            "type": "move",
            "unit_id": "US-1MAR",
            "target": "TULAGI",
            "posture": "ATTACK"  # or "MOVE", "DEFEND", "REST", etc.
        }

        This uses G-6 to issue delayed movement orders.
        """
        self._ensure_ready()
        if not self.g6:
            return

        action_type = action.get("type")
        if action_type == "move":
            unit_id = action.get("unit_id")
            target = action.get("target")
            posture_str = action.get("posture", "MOVE").upper()

            try:
                posture = Posture[posture_str]
            except KeyError:
                posture = Posture.MOVE

            if unit_id and target:
                self.g6.issue_delayed_move_order(
                    unit_id,
                    target,
                    posture,
                    t=self.ts.time,
                    via_hq_id=None,
                    notes="Player-issued move",
                )
                # We don't advance time here. The order will be delivered
                # on a subsequent process_turn() call.
        else:
            # Other action types (air missions, naval, etc.) can be added later
            pass

    def get_game_state(self) -> Dict[str, Any]:
        """
        Build and return the current EngineState snapshot.
        """
        self._ensure_ready()
        return build_engine_state(
            self.scenario_id or "",
            self.meta,
            self.ts.time,
            self.map,
            self.units,
            logs=self.turn_logs,
        )

    def get_map_data(self) -> Dict[str, Any]:
        """
        Return just the map part of the state.
        """
        state = self.get_game_state()
        return state.get("map", {})

    def get_unit_data(self) -> List[Dict[str, Any]]:
        """
        Return just the units list.
        """
        state = self.get_game_state()
        return state.get("units", [])

    def get_logs(self) -> List[str]:
        """
        Return logs for the last processed turn.
        """
        return list(self.turn_logs)

    # ------------------------------------------------------------------ logging

    def _collect_turn_logs(self) -> None:
        """
        Collect logs from staff sections and push them into a unified string list.
        Later we may upgrade these to structured dicts.
        """
        # G-5 briefing
        if self.g5 and self.g5.last_briefing:
            self.turn_logs.append("[G-5] BRIEFING:")
            self.turn_logs.extend(
                f"[G-5] {line}" for line in self.g5.last_briefing.splitlines()
            )

        # G-3 battles
        if self.g3 and self.g3.last_battles:
            for br in self.g3.last_battles:
                self.turn_logs.append(f"[G-3] {br.summary}")
                for rnd in br.rounds:
                    self.turn_logs.append(
                        f"[G-3]   Round {rnd.round_index}: "
                        f"Allied loss {rnd.allied_loss}, "
                        f"Axis loss {rnd.axis_loss} ({rnd.notes})"
                    )

        # G-4 logistics
        if self.g4 and getattr(self.g4, "last_log", None):
            for line in self.g4.last_log:
                self.turn_logs.append(f"[G-4] {line}")

        # G-6 signals
        if self.g6 and getattr(self.g6, "last_log", None):
            for line in self.g6.last_log:
                self.turn_logs.append(f"[G-6] {line}")

        # G-7 reinforcements
        if self.g7 and getattr(self.g7, "arrived_log", None):
            for line in self.g7.arrived_log:
                self.turn_logs.append(f"[G-7] {line}")

        # G-8 objective events
        if self.g8 and getattr(self.g8, "events", None):
            for ev in self.g8.events:
                self.turn_logs.append(f"[G-8] {ev}")
