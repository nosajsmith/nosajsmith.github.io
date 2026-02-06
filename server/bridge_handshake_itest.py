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
  {"cmd": "quit"}

Usage:
    cd C:\\MWE\\server
    python bridge_handshake_test.py

Then type JSON commands, or pipe them from a file.
"""

from __future__ import annotations
import json
import sys
from typing import Any, Dict

from engine.engine_api import EngineAPI


class BridgeShell:
    def __init__(self) -> None:
        self.api = EngineAPI()
        self.loaded = False

    def handle(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        cmd = packet.get("cmd")
        args = packet.get("args") or {}

        try:
            if cmd == "load_scenario":
                sid = args.get("id", "mini_gc_1942")
                meta = self.api.load_scenario(sid)
                self.loaded = True
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
