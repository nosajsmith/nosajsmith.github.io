#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Dict, Any

from engine.engine_api import EngineAPI


def die(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def must_have(d: Dict[str, Any], k: str) -> None:
    if k not in d:
        die(f"missing key '{k}' in {d}")


def main() -> None:
    api = EngineAPI()
    api.load_scenario("mini_gc_1942")

    unit_id = "US-1MAR"

    if not hasattr(api, "get_unit_state"):
        die("EngineAPI missing get_unit_state(unit_id)")
    if not hasattr(api, "apply_order_effect"):
        die("EngineAPI missing apply_order_effect(kind, unit_id, intent='')")

    before = api.get_unit_state(unit_id)
    if not isinstance(before, dict):
        die("get_unit_state did not return a dict")

    for k in ("fatigue", "readiness", "morale", "supply"):
        must_have(before, k)

    api.apply_order_effect("attack", unit_id, intent="smoketest")

    after = api.get_unit_state(unit_id)
    for k in ("fatigue", "readiness", "morale", "supply"):
        must_have(after, k)

    if after["fatigue"] <= before["fatigue"]:
        die(f"expected fatigue to increase on attack: {before['fatigue']} -> {after['fatigue']}")
    if after["readiness"] >= before["readiness"]:
        die(f"expected readiness to decrease on attack: {before['readiness']} -> {after['readiness']}")

    for k in ("fatigue", "readiness", "morale", "supply"):
        v = int(after[k])
        if not (0 <= v <= 100):
            die(f"expected {k} clamped 0..100, got {k}={v}")

    print("PASS: Phase 8.5 order effects stub")
    print(f"  unit={unit_id}")
    print(f"  fatigue:   {before['fatigue']} -> {after['fatigue']}")
    print(f"  readiness: {before['readiness']} -> {after['readiness']}")
    print(f"  morale:    {before['morale']} -> {after['morale']}")
    print(f"  supply:    {before['supply']} -> {after['supply']}")


if __name__ == "__main__":
    main()
