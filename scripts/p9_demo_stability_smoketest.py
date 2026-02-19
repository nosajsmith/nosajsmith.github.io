#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(f"[demo smoketest] FAIL: {msg}", file=sys.stderr)
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
        return fail(f"load_scenario failed: {r}")

    k.handle("ai.enable", {"enabled": True})

    status = "ongoing"
    for _ in range(20):  # up to 120h
        out = k.handle("clock.step", {"dt_hours": 6})
        if not out.get("ok"):
            return fail(f"clock.step failed: {out}")
        camp = out.get("campaign", {})
        status = camp.get("status", "ongoing")
        if status in ("win", "loss"):
            print("[demo smoketest] PASS")
            return 0

    return fail(f"campaign did not terminate, last status={status}")


if __name__ == "__main__":
    raise SystemExit(main())
