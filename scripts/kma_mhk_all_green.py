#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, env=os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "server"

    # Core suite (adjust list as needed)
    tests = [
        ["python", "scripts/p8_intel_lag_smoketest.py"],
        ["python", "scripts/p9_1_make_it_hurt_smoketest.py"],
        ["python", "scripts/p9_2_scoring_smoketest.py"],
        ["python", "scripts/p9_3_objective_control_smoketest.py"],
        ["python", "scripts/p9_5_campaign_status_smoketest.py"],
        ["python", "scripts/p9_demo_stability_smoketest.py"],
    ]

    for t in tests:
        run(t)

    # Demo + report
    run(["python", "scripts/operation_kma_mhk_demo.py"])
    run(["python", "scripts/operation_kma_mhk_demo_report.py"])

    print("\nALL GREEN ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
