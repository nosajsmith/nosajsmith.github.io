from __future__ import annotations

import json

from tools.operations_console.app import OperationsConsoleApp
from tools.operations_console.divergence_finder import (
    FirstDivergence,
    compare_result_to_baseline_divergence,
    find_first_divergence,
    find_first_divergence_in_artifact_paths,
)
from tools.operations_console.registry import build_default_registry
from tools.operations_console.report_export import export_result_text, report_dict
from tools.operations_console.runner_utils import make_result, run_registry_entry
from tools.operations_console.baselines import save_baseline


def test_find_first_divergence_identifies_replay_log_difference(tmp_path) -> None:
    replay_a = tmp_path / "replay-a.json"
    replay_b = tmp_path / "replay-b.json"
    replay_a.write_text(
        json.dumps(
            {
                "initial_game": {"scenario": "inchon_mvp"},
                "final_game": {"scenario": "inchon_mvp", "time": {"day": 1, "phase": "DAY"}},
                "initial_units": [],
                "final_units": [],
                "logs": [
                    {"turn": 1, "phase": "LOAD", "src": "ENGINE", "message": "Loaded scenario"},
                    {"turn": 1, "phase": "DAY", "src": "G4", "message": "Supply intact"},
                ],
            }
        ),
        encoding="utf-8",
    )
    replay_b.write_text(
        json.dumps(
            {
                "initial_game": {"scenario": "inchon_mvp"},
                "final_game": {"scenario": "inchon_mvp", "time": {"day": 1, "phase": "DAY"}},
                "initial_units": [],
                "final_units": [],
                "logs": [
                    {"turn": 1, "phase": "LOAD", "src": "ENGINE", "message": "Loaded scenario"},
                    {"turn": 1, "phase": "DAY", "src": "G4", "message": "Supply disrupted"},
                ],
            }
        ),
        encoding="utf-8",
    )

    divergence = find_first_divergence(replay_a, replay_b)

    assert divergence.comparable is True
    assert divergence.identical is False
    assert divergence.comparison_kind == "replay"
    assert divergence.field_path == "logs[1].message"
    assert divergence.step == "log 2"
    assert divergence.phase == "DAY"
    assert divergence.tick == 1
    assert divergence.scenario_name == "inchon_mvp"
    assert str(replay_a) in divergence.artifact_paths
    assert str(replay_b) in divergence.artifact_paths


def test_find_first_divergence_identifies_first_report_step_difference() -> None:
    report_a = {
        "name": "ORL / Core Validation Suite",
        "status": "pass",
        "summary": "all green",
        "scenario_name": "inchon_mvp",
        "subresults": [
            {"name": "ORL / Smoke Suite", "status": "pass", "summary": "smoke ok", "subresults": []},
            {"name": "ORL / Snapshot Smoke", "status": "pass", "summary": "snapshot ok", "subresults": []},
        ],
    }
    report_b = {
        "name": "ORL / Core Validation Suite",
        "status": "fail",
        "summary": "snapshot failed",
        "scenario_name": "inchon_mvp",
        "subresults": [
            {"name": "ORL / Smoke Suite", "status": "pass", "summary": "smoke ok", "subresults": []},
            {"name": "ORL / Snapshot Smoke", "status": "fail", "summary": "snapshot bad", "subresults": []},
        ],
    }

    divergence = find_first_divergence(report_a, report_b)

    assert divergence.comparable is True
    assert divergence.identical is False
    assert divergence.comparison_kind == "report"
    assert divergence.step == "ORL / Snapshot Smoke"
    assert divergence.field_path == "status"
    assert divergence.scenario_name == "inchon_mvp"


def test_find_first_divergence_identifies_snapshot_unit_difference(tmp_path) -> None:
    snapshot_a = tmp_path / "snapshot-a.json"
    snapshot_b = tmp_path / "snapshot-b.json"
    payload_a = {
        "scenario_id": "inchon_mvp",
        "time": {"day": 2, "phase": "NIGHT"},
        "meta": {"name": "Inchon Demo Vertical Slice"},
        "units": [{"id": "US-1MAR", "supply": 80, "location_id": "SEOUL"}],
    }
    payload_b = {
        "scenario_id": "inchon_mvp",
        "time": {"day": 2, "phase": "NIGHT"},
        "meta": {"name": "Inchon Demo Vertical Slice"},
        "units": [{"id": "US-1MAR", "supply": 65, "location_id": "SEOUL"}],
    }
    snapshot_a.write_text(json.dumps(payload_a), encoding="utf-8")
    snapshot_b.write_text(json.dumps(payload_b), encoding="utf-8")

    divergence = find_first_divergence(snapshot_a, snapshot_b)

    assert divergence.comparable is True
    assert divergence.identical is False
    assert divergence.comparison_kind == "snapshot"
    assert divergence.field_path == "units[0].supply"
    assert divergence.phase == "NIGHT"
    assert divergence.tick == 2


def test_compare_result_to_baseline_divergence_returns_first_metric_difference(tmp_path) -> None:
    baseline = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 8 unit(s).",
        scenario_name="demo",
        details=["Validated units: 8 total, 8 with basic identity/location fields"],
    )
    current = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 10 unit(s).",
        scenario_name="demo",
        details=["Validated units: 10 total, 10 with basic identity/location fields"],
    )
    baseline_path = save_baseline(baseline, baseline_dir_path=tmp_path / "baselines")

    divergence = compare_result_to_baseline_divergence(current, baseline_dir_path=tmp_path / "baselines")

    assert divergence.comparable is True
    assert divergence.identical is False
    assert divergence.comparison_kind == "baseline_metrics"
    assert divergence.field_path == "unit_count"
    assert divergence.scenario_name == "demo"
    assert baseline_path.as_posix() in divergence.artifact_paths


def test_find_first_divergence_in_artifact_paths_skips_incomparable_pairs(tmp_path) -> None:
    report_a = tmp_path / "report-a.json"
    replay = tmp_path / "replay.json"
    report_b = tmp_path / "report-b.json"
    report_a.write_text(
        json.dumps(
            {
                "name": "ORL / Smoke Suite",
                "status": "pass",
                "summary": "smoke ok",
                "scenario_name": "inchon_mvp",
                "subresults": [],
            }
        ),
        encoding="utf-8",
    )
    replay.write_text(
        json.dumps(
            {
                "initial_game": {"scenario": "inchon_mvp"},
                "final_game": {"scenario": "inchon_mvp", "time": {"day": 1, "phase": "DAY"}},
                "initial_units": [],
                "final_units": [],
                "logs": [],
            }
        ),
        encoding="utf-8",
    )
    report_b.write_text(
        json.dumps(
            {
                "name": "ORL / Smoke Suite",
                "status": "fail",
                "summary": "smoke bad",
                "scenario_name": "inchon_mvp",
                "subresults": [],
            }
        ),
        encoding="utf-8",
    )

    divergence = find_first_divergence_in_artifact_paths([report_a, replay, report_b])

    assert divergence is not None
    assert divergence.comparable is True
    assert divergence.identical is False
    assert divergence.comparison_kind == "report"
    assert divergence.field_path == "status"
    assert divergence.artifact_paths == [str(report_a), str(report_b)]


def test_app_registers_first_divergence_finder_action_and_reports_values(monkeypatch) -> None:
    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.registry = build_default_registry()
    app.last_result = make_result(
        name="ORL / Core Validation Suite",
        status="pass",
        summary="core ok",
        scenario_name="inchon_mvp",
    )

    app._register_divergence_action()
    action = app.registry.get_action("Utilities / First Divergence Finder")

    assert action is not None

    monkeypatch.setattr(
        "tools.operations_console.app.compare_result_to_baseline_divergence",
        lambda result: FirstDivergence(
            comparable=True,
            identical=False,
            comparison_kind="baseline_metrics",
            scenario_name="inchon_mvp",
            field_path="unit_count",
            artifact_paths=["/tmp/baselines/core.json", "/tmp/current/report.json"],
            left_value=14,
            right_value=12,
            message="unit_count diverged (scenario=inchon_mvp): 14 -> 12",
        ),
    )

    result = run_registry_entry(
        action,
        entry_lookup=app.registry.get,
    )

    assert result.status == "warn"
    assert result.adapter_method == "first_divergence_finder"
    assert result.summary == "First divergence found at unit_count."
    assert "comparing current result against saved baseline" in result.details
    assert "first divergence at field: unit_count" in result.details
    assert "baseline: 14" in result.details
    assert "current: 12" in result.details


def test_report_export_includes_first_divergence(tmp_path) -> None:
    baseline = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 8 unit(s).",
        scenario_name="demo",
        details=["Validated units: 8 total, 8 with basic identity/location fields"],
    )
    current = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 10 unit(s).",
        scenario_name="demo",
        details=["Validated units: 10 total, 10 with basic identity/location fields"],
    )
    save_baseline(baseline, baseline_dir_path=tmp_path / "baselines")

    payload = report_dict(current, baseline_dir_path=tmp_path / "baselines")
    text_path = export_result_text(current, tmp_path / "exports", baseline_dir_path=tmp_path / "baselines")
    text = text_path.read_text(encoding="utf-8")

    assert payload["first_divergence"] is not None
    assert payload["first_divergence"]["field_path"] == "unit_count"
    assert payload["first_divergence"]["comparison_kind"] == "baseline_metrics"
    assert "First Divergence:" in text
    assert "First Divergence Field: unit_count" in text
    assert "Baseline: 8" in text
    assert "Current: 10" in text
