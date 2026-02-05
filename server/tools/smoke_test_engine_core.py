from __future__ import annotations

import os
import sys


def _add_server_root_to_path() -> None:
    # tools\ -> server\
    here = os.path.dirname(os.path.abspath(__file__))
    server_root = os.path.dirname(here)
    if server_root not in sys.path:
        sys.path.insert(0, server_root)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    _add_server_root_to_path()

    from engine_core import EngineCore  # noqa: E402
    from bridge_protocol import (  # noqa: E402
        CMD_LIST_SCENARIOS,
        CMD_PING,
    )

    core = EngineCore()

    ping = core.apply(CMD_PING, {})
    _require(isinstance(ping, dict) and ping.get("pong") is True, "ping failed")

    scenarios = core.apply(CMD_LIST_SCENARIOS, {})
    _require(isinstance(scenarios, dict), "list_scenarios failed")
    _require(isinstance(scenarios.get("scenarios"), list), "list_scenarios did not return list")

    missing_cmd = core.apply("", {})
    _require(missing_cmd.get("ok") is False, "missing cmd should return ok=false")
    _require(missing_cmd.get("error", {}).get("code") == "bad_request", "missing cmd error code")

    unknown = core.apply("totally_unknown", {})
    _require(unknown.get("ok") is False, "unknown cmd should return ok=false")
    _require(unknown.get("error", {}).get("code") == "unknown_cmd", "unknown cmd error code")
    _require(
        unknown.get("error", {}).get("details", {}).get("cmd") == "totally_unknown",
        "unknown cmd should include cmd value",
    )

    print("SMOKE TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
