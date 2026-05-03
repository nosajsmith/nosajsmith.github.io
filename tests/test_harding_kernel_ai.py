from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from server.harding.kernel_v1 import HardingKernelV1


def test_build_ai_decision_state_exposes_narrow_snapshot() -> None:
    kernel = HardingKernelV1("scenarios")
    kernel.scenario = {"units": [{"id": "JP-35BDE", "side": "AXIS"}], "objectives": []}
    kernel.objective_state = {"AXIS:TULAGI": True}
    kernel.politics = SimpleNamespace(
        scoring=SimpleNamespace(score_by_side={"AXIS": 3, "ALLIED": 1})
    )

    state = kernel._build_ai_decision_state()

    assert state == {
        "scenario": {"units": [{"id": "JP-35BDE", "side": "AXIS"}], "objectives": []},
        "objective_state": {"AXIS:TULAGI": True},
        "objective_status": {},
        "objective_pressure": {
            "semantics": "supply_aware_objective_pressure_v1",
            "radius": 1,
            "supply_thresholds": {
                "critical_below": 10,
                "adequate_at_or_above": 30,
                "low_supply_factor": 0.5,
            },
            "affects_scoring": False,
            "by_objective": {},
            "total_pressure_score": 0.0,
            "reasons": [],
        },
        "score_by_side": {"AXIS": 3, "ALLIED": 1},
    }


def test_ai_gate_state_reports_blocking_reason() -> None:
    kernel = HardingKernelV1("scenarios")
    kernel.ai_enabled = True
    kernel.ai_last_submit_hour = 4
    kernel.ai_min_interval_hours = 6

    gate = kernel._ai_gate_state(now=6)

    assert gate["enabled"] is True
    assert gate["cadence_ok"] is False
    assert gate["pending_ok"] is True
    assert gate["staff_overloaded"] is False
    assert gate["should_act"] is False


def test_unknown_ai_kind_is_ignored_safely() -> None:
    kernel = HardingKernelV1("scenarios")
    kernel.scenario = {"units": [], "objectives": []}
    kernel.ai_enabled = True
    kernel.ai = SimpleNamespace(
        decide_orders=lambda state, now: [
            {"kind": "feint", "unit_id": "JP-X", "eta_hours": 6, "intent": "test"}
        ]
    )

    result = kernel.handle("clock.step", {"dt_hours": 6})

    assert result["ok"] is True
    assert result["ai_submitted"] == []
    assert kernel.event_queue.pending() == []


def test_load_scenario_keeps_current_authored_scenarios_loadable() -> None:
    scenario_dir = Path(__file__).resolve().parents[1] / "server" / "scenarios"
    kernel = HardingKernelV1(str(scenario_dir))

    result = kernel.handle("load_scenario", {"scenario_name": "inchon_mvp.json"})

    assert result["ok"] is True
    assert result["loaded"] == "inchon_mvp.json"
    assert "ALLIED:SEOUL" in result["objective_state"]
