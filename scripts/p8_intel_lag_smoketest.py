#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p8.9 smoketest] FAIL: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    try:
        from harding.kernel_v1 import HardingKernelV1
    except Exception as e:
        return fail(f"import HardingKernelV1 failed: {e}")

    k = HardingKernelV1("server/scenarios")

    r = k.handle("load_scenario", {"name": "mini_gc_1942.json"})
    if not r.get("ok"):
        return fail(f"load_scenario failed: {r}")

    # submit a player order that resolves in 6 hours
    r = k.handle("orders.submit", {"kind": "attack", "unit_id": "US-1MAR", "eta_hours": 6, "intent": "smoke"})
    if not r.get("ok"):
        return fail(f"orders.submit failed: {r}")

    # Step 6h: order resolves now, but report should NOT arrive yet (delay=6h)
    r1 = k.handle("clock.step", {"dt_hours": 6})
    if not r1.get("ok"):
        return fail(f"clock.step(6) failed: {r1}")
    reports1 = r1.get("reports", [])
    if not isinstance(reports1, list):
        return fail(f"expected reports list, got: {reports1}")
    if len(reports1) != 0:
        return fail(f"expected 0 reports after first step, got: {reports1}")

    # Step another 6h: report should arrive now
    r2 = k.handle("clock.step", {"dt_hours": 6})
    if not r2.get("ok"):
        return fail(f"clock.step(6) failed: {r2}")
    reports2 = r2.get("reports", [])
    if not isinstance(reports2, list) or len(reports2) < 1:
        return fail(f"expected >=1 report after delay window, got: {reports2}")

    print("[p8.9 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
