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

    # Step 1: AI should submit at least one order
    r1 = shell.handle("clock.step", {"dt_hours": 6})
    if not r1.get("ok"):
        return fail(f"clock.step(step1) failed: {r1}")

    ai_submitted = r1.get("ai_submitted", [])
    if not isinstance(ai_submitted, list) or len(ai_submitted) < 1:
        return fail(f"expected ai_submitted >=1 on step1, got: {ai_submitted}")

    # Step 2: AI order resolves internally, but intel lag may delay report visibility
    r2 = shell.handle("clock.step", {"dt_hours": 6})
    if not r2.get("ok"):
        return fail(f"clock.step(step2) failed: {r2}")

    # Step 3: reports should arrive (default report_delay_hours=6)
    r3 = shell.handle("clock.step", {"dt_hours": 6})
    if not r3.get("ok"):
        return fail(f"clock.step(step3) failed: {r3}")

    reports = r3.get("reports", [])
    if not isinstance(reports, list) or len(reports) < 1:
        return fail(f"expected >=1 report after delay window, got: {reports}")

    has_ai = False
    for rep in reports:
        if isinstance(rep, dict):
            ev = rep.get("event")
            if isinstance(ev, dict) and ev.get("issuer") == "ai":
                has_ai = True
                break

    if not has_ai:
        return fail(f"expected AI event in reports, got: {reports}")

    print("[p8.6 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
