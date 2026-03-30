from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.models import ManifestRecord, RunResult, to_plain
from tools.bai_warlab.report_io import (
    RESULTS_CSV_COLUMNS,
    run_result_to_row,
    summarize_core_metric_rows,
    summarize_outcome_rows,
    write_json,
    write_report_txt,
    write_results_csv,
)
from tools.bai_warlab.reports.summary_report import render_report


def test_bai_warlab_models_serialize_cleanly():
    result = RunResult(
        ok=True,
        command="run",
        scenario="foundation_smoke.json",
        scenario_dir="synthetic_scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed=7,
        max_steps=2,
        dt_hours=0,
        summary={"execution_status": "not_executed"},
        metrics={"outcome": {"available": False}},
    )
    payload = to_plain(result)
    assert payload["scenario"] == "foundation_smoke.json"
    assert payload["summary"]["execution_status"] == "not_executed"


def test_bai_warlab_results_csv_row_uses_stable_columns_and_blank_optional_metrics():
    result = RunResult(
        ok=False,
        command="run",
        scenario="foundation_smoke.json",
        scenario_dir="synthetic_scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed=7,
        max_steps=2,
        dt_hours=0,
        error="synthetic failure",
        summary={
            "execution_status": "failed",
            "terminal_status": "runtime_error",
            "scenario_outcome": "error",
            "ai_side": "ALLIED",
        },
        metrics={"outcome": {"available": False}},
    )

    row = run_result_to_row(result)

    assert row["scenario"] == "foundation_smoke.json"
    assert row["result"] == "error"
    assert row["vp_margin"] is None
    assert row["allied_casualties"] is None
    assert row["axis_casualties"] is None
    assert row["casualty_ratio"] is None
    assert row["objective_hold_duration"] is None
    assert row["line_collapse_rate"] is None
    assert row["low_supply_turns"] is None
    assert row["failure_flag"] is True
    assert row["failure_message"] == "synthetic failure"
    for column in RESULTS_CSV_COLUMNS:
        assert column in row


def test_bai_warlab_row_summaries_capture_spread_and_outcomes():
    rows = [
        {"result": "win", "scenario_outcome": "allied_victory", "winning_side": "ALLIED", "ai_side": "ALLIED", "vp_margin": 4, "allied_casualties": 3, "hours_elapsed": 8},
        {"result": "draw", "scenario_outcome": "draw", "winning_side": "", "ai_side": "ALLIED", "vp_margin": 1, "allied_casualties": 5, "hours_elapsed": 10},
        {"result": "loss", "scenario_outcome": "axis_victory", "winning_side": "AXIS", "ai_side": "ALLIED", "vp_margin": -2, "allied_casualties": 7, "hours_elapsed": 12},
    ]

    metrics = summarize_core_metric_rows(rows)
    outcomes = summarize_outcome_rows(rows)

    assert metrics["vp_margin"]["mean"] == 1.0
    assert metrics["vp_margin"]["median"] == 1.0
    assert metrics["vp_margin"]["spread"] == 6.0
    assert metrics["vp_margin"]["stddev"] == 2.449
    assert metrics["allied_casualties"]["mean"] == 5.0
    assert outcomes["result_counts"] == {"draw": 1, "loss": 1, "win": 1}
    assert outcomes["scenario_outcome_counts"] == {"allied_victory": 1, "axis_victory": 1, "draw": 1}
    assert outcomes["winning_side_counts"] == {"ALLIED": 1, "AXIS": 1, "DRAW": 1}
    assert outcomes["non_loss_rate"] == 0.667


def test_bai_warlab_report_writers_emit_stable_artifacts(tmp_path: Path):
    result = RunResult(
        ok=True,
        command="run",
        scenario="foundation_smoke.json",
        scenario_dir="synthetic_scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed=7,
        max_steps=2,
        dt_hours=0,
        warnings=["Engine execution is not integrated in the BAI War Lab foundation build."],
        summary={
            "execution_status": "not_executed",
            "terminal_status": "not_executed",
            "configured_max_steps": 2,
            "configured_dt_hours": 0,
            "steps_completed": 0,
            "hours_elapsed": 0,
        },
        metrics={"outcome": {"available": False, "reason": "engine_execution_not_integrated"}},
    )
    manifest = ManifestRecord(
        bai_version="0.1.0",
        command="run",
        generated_at="2026-03-25T00:00:00+00:00",
        scenario="foundation_smoke.json",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed_policy={"kind": "explicit", "seeds": [7]},
        command_line="run --scenario foundation_smoke.json",
        output_dir=str(tmp_path),
    )

    summary_path = write_json(tmp_path / "summary.json", result)
    manifest_path = write_json(tmp_path / "manifest.json", manifest)
    csv_path = write_results_csv(tmp_path / "results.csv", [run_result_to_row(result)])
    txt_path = write_report_txt(tmp_path / "report.txt", render_report(result))

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    csv_rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    report_text = txt_path.read_text(encoding="utf-8")

    assert summary_payload["summary"]["execution_status"] == "not_executed"
    assert manifest_payload["seed_policy"]["seeds"] == [7]
    assert csv_rows[0]["execution_status"] == "not_executed"
    assert csv_rows[0]["failure_flag"] == "False"
    assert csv_rows[0]["vp_margin"] == ""
    assert "Execution Status: not_executed" in report_text
    assert "foundation build" in report_text
