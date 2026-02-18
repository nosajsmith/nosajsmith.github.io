#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p9.4 smoketest] FAIL: {msg}", file=sys.stderr)
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

    # Enable AI
    r = k.handle("ai.enable", {"enabled": True})
    if not r.get("ok"):
        return fail(f"ai.enable failed: {r}")

    obj = k.objective_state
    if not isinstance(obj, dict):
        return fail(f"objective_state not dict: {obj}")

    # Step enough for AI to submit and resolve an order, then deliver intel reports
    # With intel lag, we need 3 steps: submit, resolve, report
    k.handle("clock.step", {"dt_hours": 6})
    k.handle("clock.step", {"dt_hours": 6})
    out = k.handle("clock.step", {"dt_hours": 6})
    if not out.get("ok"):
        return fail(f"clock.step failed: {out}")

    # Expect AXIS objective flipped True OR Allied objective flipped False
    tulagi = obj.get("AXIS:TULAGI", None)
    lunga = obj.get("ALLIED:LUNGA", None)

    if not (tulagi is True or longa_false(lunga)):
        return fail(f"expected objective contest change. obj={obj}")

    print("[p9.4 smoketest] PASS")
    return 0


def longa_false(v):
    return v is False


if __name__ == "__main__":
    raise SystemExit(main())
