#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[p9.5 smoketest] FAIL: {msg}", file=sys.stderr)
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

    hud = k.handle("campaign.status", {})
    if not hud.get("ok"):
        return fail(f"campaign.status failed: {hud}")

    required = [
        "time_now",
        "campaign_status",
        "score_by_side",
        "objective_state",
        "pressure_reasons",
        "staff_load",
        "pending_reports",
    ]
    for kf in required:
        if kf not in hud:
            return fail(f"missing field '{kf}' in hud: {hud}")

    print("[p9.5 smoketest] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
