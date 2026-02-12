#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p9.1 smoketest] FAIL: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    from harding.kernel_v1 import HardingKernelV1

    k = HardingKernelV1("server/scenarios")
    r = k.handle("load_scenario", {"name": "mini_gc_1942.json"})
    if not r.get("ok"):
        return fail(f"load failed: {r}")

    # Spam attacks to drive fatigue/readiness/supply down and strength attrition
    for _ in range(8):
        r = k.handle("orders.submit", {"kind": "attack", "unit_id": "US-1MAR", "eta_hours": 6, "intent": "grind"})
        if not r.get("ok"):
            return fail(f"submit failed: {r}")
        k.handle("clock.step", {"dt_hours": 6})
        # one more step to deliver intel report (8.9)
        out = k.handle("clock.step", {"dt_hours": 6})
        if not out.get("ok"):
            return fail(f"step failed: {out}")

        camp = out.get("campaign", {})
        if camp.get("status") == "loss":
            print("[p9.1 smoketest] PASS (early loss triggered)")
            return 0

    # If still not loss, fail
    last = k.handle("campaign.status", {}) if hasattr(k, "handle") else {}
    return fail(f"expected early loss, got: {out.get('campaign')}")

if __name__ == "__main__":
    raise SystemExit(main())
