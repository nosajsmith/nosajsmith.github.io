#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p8.8 parity] FAIL: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    try:
        import asyncio
        from mwe_bridge_p8_ws15 import dispatch
    except Exception as e:
        return fail(f"import dispatch failed: {e}")

    async def run() -> int:
        scen_dir = "server/scenarios"

        r = await dispatch("load_scenario", {"name": "mini_gc_1942.json"}, scen_dir)
        if r.get("status") != "ok":
            return fail(f"load_scenario failed: {r}")

        r = await dispatch("ai.enable", {"enabled": True}, scen_dir)
        if r.get("status") != "ok":
            return fail(f"ai.enable failed: {r}")

        # Step 1: AI should submit at least one order
        r1 = await dispatch("clock.step", {"dt_hours": 6}, scen_dir)
        if r1.get("status") != "ok":
            return fail(f"clock.step(6) failed: {r1}")

        ai_sub = (r1.get("payload") or {}).get("ai_submitted", [])
        if not isinstance(ai_sub, list) or len(ai_sub) < 1:
            return fail(f"expected ai_submitted >=1, got: {ai_sub}")

        # Step 2: resolves internally, but intel lag delays report visibility
        r2 = await dispatch("clock.step", {"dt_hours": 6}, scen_dir)
        if r2.get("status") != "ok":
            return fail(f"clock.step(step2) failed: {r2}")

        # Step 3: report should arrive (default delay = 6h)
        r3 = await dispatch("clock.step", {"dt_hours": 6}, scen_dir)
        if r3.get("status") != "ok":
            return fail(f"clock.step(step3) failed: {r3}")

        reports = (r3.get("payload") or {}).get("reports", [])
        if not isinstance(reports, list) or len(reports) < 1:
            return fail(f"expected >=1 report, got: {reports}")

        has_ai = False
        for rep in reports:
            if isinstance(rep, dict):
                ev = rep.get("event")
                if isinstance(ev, dict) and ev.get("issuer") == "ai":
                    has_ai = True
                    break

        if not has_ai:
            return fail(f"expected AI event in reports, got: {reports}")

        print("[p8.8 parity] PASS")
        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
