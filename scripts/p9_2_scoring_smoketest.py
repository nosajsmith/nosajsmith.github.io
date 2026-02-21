#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path


def fail(msg: str):
    print("[p9.2 smoketest] FAIL:", msg, file=sys.stderr)
    sys.exit(2)


def main():
    root = Path(__file__).resolve().parents[1]
    server_dir = root / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    from harding.kernel_v1 import HardingKernelV1

    k = HardingKernelV1("server/scenarios")
    k.handle("load_scenario", {"name": "mini_gc_1942.json"})

    # Flip objective manually to simulate hold
    k.objective_state["ALLIED:LUNGA"] = True

    r1 = k.handle("clock.step", {"dt_hours": 6})
    r2 = k.handle("clock.step", {"dt_hours": 6})

    s1 = r1["campaign"]["scoring"]["score_by_side"]["ALLIED"]
    s2 = r2["campaign"]["scoring"]["score_by_side"]["ALLIED"]

    if s2 <= s1:
        fail(f"Score did not increase: {s1} -> {s2}")

    print("[p9.2 smoketest] PASS")


if __name__ == "__main__":
    main()
