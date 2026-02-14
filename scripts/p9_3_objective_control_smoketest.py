#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p9.3 smoketest] FAIL: {msg}", file=sys.stderr)
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

    # Initially objectives should be present and false
    obj = k.objective_state
    if not isinstance(obj, dict) or len(obj) == 0:
        return fail(f"expected objective_state dict, got: {obj}")

    # Submit an ALLIED attack; after resolution it should flip ALLIED:LUNGA True
    k.handle("orders.submit", {"kind":"attack","unit_id":"US-1MAR","eta_hours":6,"intent":"take"})
    k.handle("clock.step", {"dt_hours":6})   # resolves internally
    k.handle("clock.step", {"dt_hours":6})   # deliver report

    if obj.get("ALLIED:LUNGA") is not True:
        return fail(f"expected ALLIED:LUNGA True after attack, got: {obj}")

    # Score should increase on subsequent ticks because objective is held
    c1 = k.handle("clock.step", {"dt_hours":6}).get("campaign", {})
    s1 = (((c1.get("scoring") or {}).get("score_by_side") or {}).get("ALLIED", 0))
    c2 = k.handle("clock.step", {"dt_hours":6}).get("campaign", {})
    s2 = (((c2.get("scoring") or {}).get("score_by_side") or {}).get("ALLIED", 0))

    if int(s2) <= int(s1):
        return fail(f"expected score to increase with held objective: {s1} -> {s2}")

    print("[p9.3 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
