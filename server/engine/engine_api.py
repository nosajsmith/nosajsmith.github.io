"""
High-level Engine API for bridge / UI.

Exposes a simple JSON-friendly interface:

- load_scenario(scenario_id) -> scenario metadata
- start_game()               -> initial game state
- apply_player_action(action_dict)
- process_turn()             -> updated state + logs
- get_game_state()           -> current state
- get_logs()                 -> last turn's logs
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

from engine.core.time_system import TimeSystem, GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, Posture
from engine.core.map_model import GameMap
from engine.scenario_loader import load_scenario

from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans
from engine.staff.g6_signals import G6Signals
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives


class EngineAPI:
    def __init__(self) -> None:
        # Core state
        self.units: Optional[UnitRepository] = None
        self.game_map: Optional[GameMap] = None
        self.fs: Optional[TimeSystem] = None  # time system (alias used elsewhere)
        self.scenario_meta: Dict[str, Any] = {}
        self.scenario_id: Optional[str] = None

        # Staff sections
        self.g3: Optional[G3Operations] = None
        self.g4: Optional[G4Logistics] = None
        self.g5: Optional[G5Plans] = None
        self.g6: Optional[G6Signals] = None
        self.g7: Optional[G7Reinforcements] = None
        self.g8: Optional[G8Objectives] = None

        # Last turn logs
        self._last_logs: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------- util

    def _ensure_ready(self) -> None:
        if self.units is None or self.fs is None or self.game_map is None:
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario() first.")

    def _current_time(self) -> GameTime:
        assert self.fs is not None
        return self.fs.get()

    # ----------------------------------------------------------------- loading

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Load scenario data and initialize core engine + staff sections.
        Returns a small JSON-friendly metadata dict for the UI.
        """
        self.scenario_id = scenario_id

        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.units = units_repo
        self.game_map = game_map

        start_day = start_time.day if hasattr(start_time, "day") else int(start_time)
        self.fs = TimeSystem(start_day=start_day)

        self.scenario_meta = meta or {}

        # Initialize staff in a consistent order
        self.g3 = G3Operations(self.units, self.game_map)
        self.g4 = G4Logistics(self.units, meta.get("supply_sources", []))
        self.g5 = G5Plans(
            self.units,
            self.game_map,
            g3=self.g3,
            mode="advisor",
            personality=self.scenario_meta.get("g5_personality", "macarthur"),
        )
        self.g6 = G6Signals(self.units, self.g3)
        self.g7 = G7Reinforcements(self.units, meta.get("reinforcements", []))
        self.g8 = G8Objectives(self.units, meta.get("objectives", []))

        self._last_logs = []

        # Minimal scenario header for UI
        return {
            "id": scenario_id,
            "name": meta.get("name", scenario_id),
            "description": meta.get("description", ""),
            "start_day": start_day,
            "weather": start_time.weather if hasattr(start_time, "weather") else meta.get("weather", "Unknown"),
        }

    # --------------------------------------------------------------- game state

    def get_game_state(self) -> Dict[str, Any]:
        """
        Return a JSON-serializable snapshot of the current game state.
        """
        self._ensure_ready()
        assert self.units is not None and self.fs is not None and self.game_map is not None

        t = self._current_time()

        # Game header
        game_info: Dict[str, Any] = {
            "time": {
                "day": t.day,
                "phase": t.phase,
                "weather": t.weather,
            },
            "scenario": self.scenario_meta.get("name", self.scenario_id or ""),
        }

        # Victory points (if G-8 present)
        if self.g8 is not None:
            game_info["vp"] = {
                "ALLIED": self.g8.vp.get(Side.ALLIED, 0),
                "AXIS": self.g8.vp.get(Side.AXIS, 0),
            }

        # Map data (minimal for now)
        map_tiles: Dict[str, Any] = {}
        if getattr(self.game_map, "tiles", None) is not None:
            for tile_id, tile in self.game_map.tiles.items():
                terrain_val = getattr(tile.terrain, "value", str(tile.terrain))
                map_tiles[tile_id] = {
                    "terrain": terrain_val,
                }

        # Units
        units_list: List[Dict[str, Any]] = []
        for u in self.units.all_units():
            side_val = getattr(u.side, "value", str(u.side))
            utype_val = getattr(getattr(u, "unit_type", None), "value", str(getattr(u, "unit_type", "")))
            posture_name = getattr(u.posture, "name", str(u.posture))
            units_list.append(
                {
                    "id": u.id,
                    "name": u.name,
                    "side": side_val,
                    "unit_type": utype_val,
                    "strength": u.strength,
                    "fatigue": u.fatigue,
                    "morale": u.morale,
                    "supply": u.supply,
                    "readiness": u.readiness,
                    "location_id": u.location_id,
                    "posture": posture_name,
                }
            )

        return {
            "game": game_info,
            "map": {"tiles": map_tiles},
            "units": units_list,
        }

    # -------------------------------------------------------------- public API

    def start_game(self) -> Dict[str, Any]:
        """
        For now, just return the initial state after loading.
        (No extra work beyond what load_scenario did.)
        """
        return self.get_game_state()

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a high-level player action (move, set_posture, etc.).
        """
        self._ensure_ready()
        assert self.g3 is not None and self.units is not None

        atype = action.get("type")

        if atype == "move":
            unit_id = action["unit_id"]
            target = action["target"]
            posture_str = action.get("posture", "MOVE")
            posture = getattr(Posture, posture_str.upper(), Posture.MOVE)

            t = self._current_time()
            # For now, send orders directly to G-3 (signals layer is optional later)
            self.g3.issue_move_order(unit_id, target, posture, t=t)
            return {"status": "ok"}

        if atype == "set_posture":
            unit_id = action["unit_id"]
            posture_str = action["posture"]
            posture = getattr(Posture, posture_str.upper(), Posture.MOVE)
            u = self.units.get(unit_id)
            if u is not None:
                u.posture = posture
                return {"status": "ok"}
            return {"status": "error", "error": f"Unknown unit_id {unit_id}"}

        return {"status": "error", "error": f"Unknown action type '{atype}'"}

    def process_turn(self) -> Dict[str, Any]:
        """
        Run a single day of the game, invoking staff sections in a fixed order,
        collect logs, advance time, and return the new state + logs.
        """
        self._ensure_ready()
        assert self.g3 and self.g4 and self.g5 and self.g6 and self.g7 and self.g8 and self.fs

        t = self._current_time()

        # Morning: new arrivals & planning
        self.g7.on_day_start(t)
        self.g5.on_day_start(t)
        self.g6.on_day_start(t)
        self.g3.on_day_start(t)

        # End of day: logistics & objectives
        self.g4.on_day_end(t)
        self.g8.on_day_end(t)

        # Collect logs for this day
        logs = self._collect_turn_logs(t)

        # Advance time to the next day
        self.fs.advance()

        state = self.get_game_state()
        return {
            "game": state["game"],
            "map": state["map"],
            "units": state["units"],
            "logs": logs,
        }

    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Return last turn's logs in packet form.
        """
        return list(self._last_logs)

    # --------------------------------------------------------- internal logging

    def _collect_turn_logs(self, t: GameTime) -> List[Dict[str, Any]]:
        """
        Build a list of structured log packets from staff sections.
        Each packet:
            { "src": "G-4", "turn": day, "phase": "day", "message": "..." }
        """
        packets: List[Dict[str, Any]] = []
        day = t.day
        phase = t.phase

        def add(src: str, msg_or_list: Any) -> None:
            if not msg_or_list:
                return
            if isinstance(msg_or_list, str):
                packets.append(
                    {"src": src, "turn": day, "phase": phase, "message": msg_or_list}
                )
            elif isinstance(msg_or_list, list):
                for m in msg_or_list:
                    if m:
                        packets.append(
                            {
                                "src": src,
                                "turn": day,
                                "phase": phase,
                                "message": str(m),
                            }
                        )

        # G-3 battles
        if self.g3 and self.g3.last_battles:
            for rep in self.g3.last_battles:
                add("G-3", rep.summary)
                for rnd in rep.rounds:
                    add(
                        "G-3",
                        f"Round {rnd.round_index}: Allied loss {rnd.allied_loss}, "
                        f"Axis loss {rnd.axis_loss} ({rnd.notes})",
                    )

        # G-4 logistics
        if self.g4:
            add("G-4", self.g4.last_log)

        # G-5 plans / briefing
        if self.g5 and self.g5.last_briefing:
            add("G-5", self.g5.last_briefing)

        # G-6 signals
        if self.g6:
            add("G-6", self.g6.last_log)

        # G-7 reinforcements
        if self.g7:
            add("G-7", self.g7.arrived_log)

        # G-8 objectives / victory
        if self.g8:
            add("G-8", self.g8.events)

        self._last_logs = packets
        return packets
