from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.models import ManifestRecord, RunResult, to_plain
from tools.bai_warlab.report_io import run_result_to_row, write_json, write_report_txt, write_results_csv
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
    assert csv_rows[0]["summary_execution_status"] == "not_executed"
    assert "Execution Status: not_executed" in report_text
    assert "foundation build" in report_text
