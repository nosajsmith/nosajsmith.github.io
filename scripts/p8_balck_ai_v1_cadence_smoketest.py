#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p8.7 smoketest] FAIL: {msg}", file=sys.stderr)
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

    # Step 1: should submit
    r1 = shell.handle("clock.step", {"dt_hours": 6})
    if not r1.get("ok"):
        return fail(f"clock.step(6) failed: {r1}")
    s1 = r1.get("ai_submitted", [])
    if not isinstance(s1, list) or len(s1) < 1:
        return fail(f"expected ai_submitted >=1 on first tick, got: {s1}")

    # Step 2: cadence should block (no new submit)
    r2 = shell.handle("clock.step", {"dt_hours": 6})
    if not r2.get("ok"):
        return fail(f"clock.step(6) failed: {r2}")
    s2 = r2.get("ai_submitted", [])
    if not isinstance(s2, list):
        return fail(f"expected ai_submitted list, got: {s2}")
    if len(s2) != 0:
        return fail(f"expected 0 ai_submitted due to cadence, got: {s2}")

    # Step 3: cadence window opens again (should submit)
    r3 = shell.handle("clock.step", {"dt_hours": 6})
    if not r3.get("ok"):
        return fail(f"clock.step(6) failed: {r3}")
    s3 = r3.get("ai_submitted", [])
    if not isinstance(s3, list) or len(s3) < 1:
        return fail(f"expected ai_submitted >=1 after cadence window, got: {s3}")

    print("[p8.7 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
