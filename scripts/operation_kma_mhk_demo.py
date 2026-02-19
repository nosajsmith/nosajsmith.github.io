#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    from harding.kernel_v1 import HardingKernelV1

    k = HardingKernelV1("server/scenarios")

    r = k.handle("load_scenario", {"name": "mini_gc_1942.json"})
    if not r.get("ok"):
        print("FAIL: load_scenario", r)
        return 2

    k.handle("ai.enable", {"enabled": True})

    print("=== Operation KMA MHK (Deterministic Demo) ===")
    print("Scenario: mini_gc_1942 | Tick=6h | IntelLag=6h | AI=ON")
    print("------------------------------------------------")

    # Run up to 96 hours (or until campaign ends)
    for _ in range(16):
        out = k.handle("clock.step", {"dt_hours": 6})
        if not out.get("ok"):
            print("FAIL: clock.step", out)
            return 2

        camp = out.get("campaign", {})
        scoring = (camp.get("scoring") or {}).get("score_by_side", {})
        obj = getattr(k, "objective_state", {}) or {}
        pressure = (camp.get("pressure") or {}).get("reasons", [])

        t = out.get("time")
        allied = int(scoring.get("ALLIED", 0))
        axis = int(scoring.get("AXIS", 0))
        lunga = 1 if obj.get("ALLIED:LUNGA") else 0
        tulagi = 1 if obj.get("AXIS:TULAGI") else 0
        staff = int(out.get("staff_load", 0))
        reps = len(out.get("reports", []) or [])
        status = camp.get("status", "ongoing")

        pr = ""
        if pressure:
            pr = f" Pressure:{pressure[0]}"

        print(f"T={t:>3}h  Score A:{allied:<3} X:{axis:<3}  Obj LUNGA:{lunga} TULAGI:{tulagi}  Staff:{staff}  Reports:{reps}  Status:{status}{pr}")

        if status != "ongoing":
            print("------------------------------------------------")
            print(f"CAMPAIGN RESULT: {status.upper()}")
            if pressure:
                print(f"Reason: {pressure[0]}")
            return 0

    print("------------------------------------------------")
    print("CAMPAIGN RESULT: TIMEBOX END (no terminal state)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
