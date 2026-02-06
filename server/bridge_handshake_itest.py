"""
Simple JSON command-line "bridge" to talk to EngineAPI.

This simulates what the real UI bridge will do later.

Commands (JSON on a single line):

  {"cmd": "load_scenario", "args": {"id": "mini_gc_1942"}}
  {"cmd": "start_game"}
  {"cmd": "process_turn"}
  {"cmd": "apply_player_action", "args": {...}}
  {"cmd": "get_state"}
  {"cmd": "get_logs"}
  {"cmd": "clock.step", "args": {"dt_hours": 6}}
  {"cmd": "orders.submit", "args": {"kind":"attack","unit_id":"US-1MAR","eta_hours":12,"intent":"Probe"}}
  {"cmd": "orders.pending"}
  {"cmd": "quit"}
"""

from __future__ import annotations
import json
import sys
from typing import Any, Dict

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import server.*` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.engine_api import EngineAPI

# Phase 8 HARDING primitives
from server.sim_time import SimTime
from server.event_queue import EventQueue
from server.orders_v1 import make_order_event


class BridgeShell:
    def __init__(self) -> None:
        self.api = EngineAPI()
        self.loaded = False
        self.time = SimTime()
        self.q = EventQueue()

    def handle(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        cmd = packet.get("cmd")

        # Compat: accept either "args" (old bridge) or "payload" (protocol tests)
        args = packet.get("args")
        payload = packet.get("payload")
        if args is None and isinstance(payload, dict):
            args = payload
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return {"status": "error", "error": "args/payload must be an object"}

        try:
            if cmd == "ping":
                return {"status": "ok", "payload": {"pong": True}}

            if cmd == "help":
                return {
                    "status": "ok",
                    "commands": [
                        "ping",
                        "help",
                        "list_scenarios",
                        "load_scenario",
                        "start_game",
                        "process_turn",
                        "apply_player_action",
                        "get_state",
                        "get_logs",
                        "orders.submit",
                        "orders.pending",
                        "clock.step",
                        "quit",
                    ],
                    "note": 'Use either {"args": {...}} or {"payload": {...}}',
                }

            if cmd == "list_scenarios":
                # Minimal for now. We can wire to a real scenario store next.
                return {"status": "ok", "scenarios": ["mini_gc_1942"]}

            if cmd == "load_scenario":
                sid = args.get("id") or args.get("name") or "mini_gc_1942"
                meta = self.api.load_scenario(sid)
                self.loaded = True
                self.time.reset()
                self.q.clear()
                return {"status": "ok", "meta": meta}

            if cmd == "start_game":
                if not self.loaded:
                    return {"status": "error", "error": "No scenario loaded."}
                state = self.api.start_game()
                return {"status": "ok", "state": state}

            if cmd == "process_turn":
                self._ensure_loaded()
                state = self.api.process_turn()
                return {"status": "ok", "state": state}

            if cmd == "apply_player_action":
                self._ensure_loaded()
                result = self.api.apply_player_action(args)
                return {"status": "ok", "result": result}

            if cmd == "get_state":
                self._ensure_loaded()
                state = self.api.get_game_state()
                return {"status": "ok", "state": state}

            if cmd == "get_logs":
                self._ensure_loaded()
                logs = self.api.get_logs()
                return {"status": "ok", "logs": logs}

            # ---- Phase 8 HARDING: Orders as future events ----
            if cmd == "orders.submit":
                self._ensure_loaded()

                kind = args.get("kind")
                unit_id = args.get("unit_id")
                eta = args.get("eta_hours", 6)
                intent = args.get("intent", "")

                try:
                    eta = int(eta)
                except Exception:
                    return {"status": "error", "error": "eta_hours must be an int"}

                try:
                    ev = make_order_event(
                        kind=str(kind) if kind is not None else "",
                        unit_id=str(unit_id) if unit_id is not None else "",
                        issued_at=self.time.now(),
                        eta_hours=eta,
                        intent=str(intent) if intent is not None else "",
                    )
                except Exception as e:
                    return {"status": "error", "error": str(e)}

                scheduled = self.q.schedule(ev)
                return {"status": "ok", "payload": {"event": scheduled}}

            if cmd == "orders.pending":
                return {"status": "ok", "payload": {"pending": self.q.pending()}}

            # ---- Phase 8 HARDING: Time with teeth ----
            if cmd == "clock.step":
                dt = args.get("dt_hours", 6)
                try:
                    dt = int(dt)
                except Exception:
                    return {"status": "error", "error": "dt_hours must be an int"}

                if dt <= 0 or dt > 168:
                    return {"status": "error", "error": "dt_hours must be 1..168"}

                self.time.advance(dt)
                resolved = self.q.resolve_up_to(self.time.now())

                return {
                    "status": "ok",
                    "payload": {
                        "dt_hours": dt,
                        "sim_hours": self.time.now(),
                        "events": resolved,
                        "log": [
                            f"Executed {ev.get('type')} #{ev.get('id')} ({ev.get('kind','')}) for {ev.get('unit_id','')}"
                            for ev in resolved
                        ],
                    },
                }

            if cmd == "quit":
                return {"status": "ok", "bye": True}

            return {"status": "error", "error": f"Unknown cmd '{cmd}'"}

        except Exception as e:
            return {"status": "error", "error": repr(e)}

    def _ensure_loaded(self) -> None:
        if not self.loaded:
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario first.")


def main() -> None:
    shell = BridgeShell()
    print("Bridge handshake test. Enter JSON commands, or 'quit'.")
    print("Example:")
    print('  {"cmd": "load_scenario", "args": {"id": "mini_gc_1942"}}')

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            packet = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "error": f"Bad JSON: {e}"}))
            continue

        resp = shell.handle(packet)
        print(json.dumps(resp))

        if resp.get("bye"):
            break


if __name__ == "__main__":
    main()
