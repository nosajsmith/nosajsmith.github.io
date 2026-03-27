from __future__ import annotations

from engine.engine_api import EngineAPI
from tools.bai_warlab.ai_report_adapter import normalize_ai_report


def test_bai_first_playable_scenario_runs_headlessly_for_multiple_turns():
    api = EngineAPI(ai_enabled=True, ai_side="AXIS")
    api.load_scenario("mini_gc_1942")

    playable_turns = 4
    last_state = None
    seen_operations: list[str] = []

    for expected_day in range(2, 2 + playable_turns):
        state = api.process_turn()
        last_state = state
        report = state["bai_report"]
        normalized = normalize_ai_report(state)

        assert state["game"]["scenario"] == "Mini Guadalcanal 1942"
        assert state["game"]["time"]["day"] == expected_day
        assert state["game"]["ai"]["enabled"] is True
        assert state["game"]["ai"]["side"] == "AXIS"
        assert state["game"]["ai"]["last_orders"] >= 1

        assert report["report_version"] == "bai_report_v1"
        assert report["generated_order_count"] >= report["legal_order_count"] >= 1
        assert report["unit_orders"]
        assert report["summary_lines"]
        assert report["tactical_intents"]

        for order in report["unit_orders"]:
            assert order["unit_id"]
            assert order["action"] in {"attack", "hold", "move", "withdraw", "delay", "reserve"}
            assert order["target_location_id"] in {"LUNGA", "TULAGI"}
            assert order["priority"] >= 1

        assert normalized["available"] is True
        assert normalized["posture"] in {"OFFENSIVE", "DEFENSIVE", "CONTAIN"}
        assert normalized["main_objective"] in {"LUNGA", "TULAGI"}
        assert normalized["chosen_operation"] is not None
        assert normalized["reserve_level"] is not None
        assert normalized["timing_breakdown"]

        seen_operations.append(str(normalized["chosen_operation"]))

    assert last_state is not None
    assert any(unit["id"] == "JP-35BDE" for unit in last_state["units"])
    assert len(last_state["units"]) >= 3
    assert len(set(seen_operations)) <= 2

    logs = api.get_logs()
    assert sum(1 for entry in logs if entry["src"] == "BAI" and entry["phase"] == "turn") == playable_turns
    assert sum(1 for entry in logs if entry["src"] == "BAI" and entry["phase"] == "orders") >= playable_turns
