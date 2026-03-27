from __future__ import annotations

from engine.engine_api import EngineAPI
from tools.bai_warlab.ai_report_adapter import normalize_ai_report


def test_engine_api_process_turn_can_run_one_side_with_bai():
    api = EngineAPI(ai_enabled=True, ai_side="AXIS")
    api.load_scenario("mini_gc_1942")

    state = api.process_turn()

    assert state["game"]["ai"]["enabled"] is True
    assert state["game"]["ai"]["side"] == "AXIS"
    assert state["game"]["ai"]["last_orders"] >= 1
    assert state["bai_report"]

    normalized = normalize_ai_report(state)
    assert normalized["available"] is True
    assert normalized["posture"] in {"OFFENSIVE", "DEFENSIVE", "CONTAIN"}
    assert normalized["main_objective"] is not None
    assert normalized["chosen_operation"] is not None

    logs = api.get_logs()
    assert any(entry["src"] == "BAI" for entry in logs)


def test_engine_api_accepts_engine_config_handoff_for_bai():
    api = EngineAPI()
    api.load_scenario(
        "mini_gc_1942",
        engine_config={
            "ai_side": "AXIS",
            "run": {"time_budget_ms": 0, "fallback_posture": "DEFEND"},
            "profile_selection": {
                "doctrine": "korea_nkpa_shock",
                "personality": "aggressive",
                "tuning": "default",
            },
        },
    )

    state = api.process_turn()

    assert state["game"]["ai"]["enabled"] is True
    assert state["game"]["ai"]["engine_received_settings"] is True
    assert state["game"]["ai"]["profile_selection"] == {
        "doctrine": "korea_nkpa_shock",
        "personality": "aggressive",
        "tuning": "default",
    }
    assert state["game"]["ai"]["budget_exceeded"] is True
    assert state["bai_report"]["engine_received_settings"] is True
    assert "runtime_profile" in state["bai_report"]
    assert state["bai_report"]["runtime_profile"]["run"]["fallback_posture"] == "DEFEND"


def test_engine_api_still_functions_when_bai_disabled():
    api = EngineAPI(ai_enabled=False)
    api.load_scenario("mini_gc_1942")

    state = api.process_turn()

    assert state["game"]["ai"]["enabled"] is False
    assert state["game"]["scenario"] == "Mini Guadalcanal 1942"
    assert len(state["units"]) >= 2
    assert state["bai_report"] == {}
