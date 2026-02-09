#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p8.6 smoketest] FAIL: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    try:
        from bridge_handshake_itest import BridgeShell
    except Exception as e:
        return fail(f"import BridgeShell failed: {e}")

    shell = BridgeShell("server/scenarios")

    r = shell.handle("load_scenario", {"name": "mini_gc_1942.json"})
    if not r.get("ok"):
        return fail(f"load_scenario failed: {r}")

    r = shell.handle("ai.enable", {"enabled": True})
    if not r.get("ok") or not r.get("ai_enabled"):
        return fail(f"ai.enable failed: {r}")

    r1 = shell.handle("clock.step", {"dt_hours": 6})
    if not r1.get("ok"):
        return fail(f"clock.step(6) failed: {r1}")

    ai_sub = r1.get("ai_submitted", [])
    if not isinstance(ai_sub, list) or len(ai_sub) < 1:
        return fail(f"expected ai_submitted >= 1, got: {ai_sub}")

    r2 = shell.handle("clock.step", {"dt_hours": 6})
    if not r2.get("ok"):
        return fail(f"clock.step(resolve) failed: {r2}")

    resolved = r2.get("resolved", [])
    if not isinstance(resolved, list):
        return fail(f"expected resolved list, got: {resolved}")

    has_ai = any(isinstance(ev, dict) and ev.get("issuer") == "ai" for ev in resolved)
    if not has_ai:
        return fail(f"expected at least one resolved AI event, got: {resolved}")

    print("[p8.6 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
