from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main
from tools.bai_warlab.models import BatchResult, RunResult, SuiteCase
from tools.bai_warlab.presets.benchmark_suites import load_benchmark_suite_definition, list_suite_names
from tools.bai_warlab.runners.batch_run import summarize_runs
from tools.bai_warlab.runners.suite_run import execute_suite_run


def _successful_run(case: SuiteCase, seed: int, variant_label: str) -> RunResult:
    return RunResult(
        ok=True,
        command="run",
        scenario=case.scenario,
        scenario_dir=case.scenario_dir,
        doctrine=case.doctrine,
        personality=case.personality,
        tuning=case.tuning,
        seed=seed,
        max_steps=2,
        dt_hours=0,
        variant_label=variant_label,
        summary={
            "execution_status": "completed",
            "terminal_status": "scenario_complete",
            "hours_elapsed": 8,
            "steps_completed": 2,
            "ai_side": "ALLIED",
            "scenario_outcome": "allied_victory",
            "winning_side": "ALLIED",
            "result": "win",
        },
        metrics={
            "outcome": {"available": True, "vp_margin_allied": 1.0, "win_loss_draw_allied": "win"},
            "behavior": {"available": True, "allied_casualties": 3, "axis_casualties": 4, "casualty_ratio_allied": 1.333},
            "logistics": {"available": True, "low_supply_turns_allied": 1},
        },
    )


def test_execute_suite_run_batches_jobs_and_survives_job_failure(monkeypatch):
    cases = [
        SuiteCase(
            id="job_alpha",
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=41,
            runs=2,
            evaluation_goal="tempo",
            metric_focus=["vp_margin"],
            metric_thresholds={"vp_margin": 1.0},
        ),
        SuiteCase(
            id="job_bravo",
            scenario="gc_1942_historical",
            scenario_dir="scenarios",
            doctrine="korea_un_combined_arms",
            personality="historical",
            tuning="default",
            seed=51,
            runs=2,
            evaluation_goal="stability",
            metric_focus=["objective_hold_duration"],
            metric_thresholds={"objective_hold_duration": 1.0},
        ),
    ]

    def fake_load_benchmark_suite_definition(name: str):
        assert name == "core_regression"
        return {
            "name": "core_regression",
            "description": "Synthetic suite definition",
            "evaluation_notes": ["Synthetic evaluation note."],
            "source_path": "/tmp/core_regression.yaml",
            "cases": cases,
        }

    def fake_execute_batch_run(*, scenario, scenario_dir, doctrine, personality, tuning, seed_policy, loader, max_steps=None, dt_hours=None, stop_on_terminal=True):
        matching = next(case for case in cases if case.scenario == scenario and case.doctrine == doctrine)
        if matching.id == "job_bravo":
            raise RuntimeError("synthetic suite fault")
        runs = [
            _successful_run(matching, seed, f"trial_{index:03d}")
            for index, seed in enumerate(seed_policy.seeds, start=1)
        ]
        return BatchResult(
            ok=True,
            command="batch",
            scenario=scenario,
            scenario_dir=scenario_dir,
            doctrine=doctrine,
            personality=personality,
            tuning=tuning,
            seed_policy=seed_policy,
            runs=runs,
            aggregate=summarize_runs(runs),
        )

    monkeypatch.setattr("tools.bai_warlab.runners.suite_run.load_benchmark_suite_definition", fake_load_benchmark_suite_definition)
    monkeypatch.setattr("tools.bai_warlab.runners.suite_run.execute_batch_run", fake_execute_batch_run)

    result = execute_suite_run(
        suite_name="core_regression",
        loader=object(),
        max_steps=2,
    )

    assert result.ok is True
    assert result.suite_name == "core_regression"
    assert result.suite_summary["job_count"] == 2
    assert result.suite_summary["description"] == "Synthetic suite definition"
    assert result.suite_summary["evaluation_notes"] == ["Synthetic evaluation note."]
    assert result.suite_summary["ok_jobs"] == 1
    assert result.suite_summary["failed_jobs"] == 1
    assert result.suite_summary["scheduled_runs"] == 4
    assert result.aggregate.total_runs == 3
    assert result.aggregate.ok_runs == 2
    assert result.aggregate.failed_runs == 1
    assert result.aggregate.success_rate == 0.667
    assert result.aggregate.result_counts == {"win": 2}
    assert result.jobs[0]["id"] == "job_alpha"
    assert result.jobs[1]["id"] == "job_bravo"
    assert result.jobs[0]["metric_focus"] == ["vp_margin"]
    assert result.jobs[1]["metric_thresholds"] == {"objective_hold_duration": 1.0}
    assert result.jobs[1]["aggregate"]["failure_count"] == 1
    assert result.jobs[0]["aggregate"]["success_rate"] == 1.0
    assert result.jobs[0]["aggregate"]["victory_proxy"]["result_counts"] == {"win": 2}
    assert result.runs[0].variant_label.startswith("job_alpha:")
    assert result.runs[-1].variant_label.startswith("job_bravo:")
    assert "Partial failure" in result.warnings[0]
    assert "job_bravo" in result.warnings[1]


def test_core_regression_suite_definition_is_korea_focused():
    assert "core_regression" in list_suite_names()

    suite = load_benchmark_suite_definition("core_regression")
    job_ids = [case.id for case in suite["cases"]]

    assert suite["name"] == "core_regression"
    assert "Core Korea regression suite" in suite["description"]
    assert len(suite["evaluation_notes"]) >= 2
    assert job_ids == [
        "korea_defense_benchmark",
        "korea_offensive_tempo_benchmark",
        "bad_attack_avoidance_benchmark",
        "reserve_discipline_benchmark",
    ]
    for case in suite["cases"]:
        assert case.metric_focus
        assert case.metric_thresholds
        assert case.notes


def test_bai_warlab_suite_cli_outputs(tmp_path: Path, capsys):
    suite_dir = tmp_path / "suite"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "suite",
            "core_regression",
            "--runs",
            "1",
            "--max-steps",
            "2",
            "--output-dir",
            str(suite_dir),
        ]
    )

    assert exit_code == 0

    summary_payload = json.loads((suite_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((suite_dir / "manifest.json").read_text(encoding="utf-8"))
    report_text = (suite_dir / "report.txt").read_text(encoding="utf-8")
    csv_rows = list(csv.DictReader((suite_dir / "results.csv").open(encoding="utf-8")))
    stdout = capsys.readouterr().out

    assert summary_payload["command"] == "suite"
    assert summary_payload["suite_name"] == "core_regression"
    assert summary_payload["suite_summary"]["job_count"] == 4
    assert len(summary_payload["jobs"]) == 4
    assert "evaluation_notes" in summary_payload["suite_summary"]
    assert manifest_payload["command"] == "suite"
    assert manifest_payload["seed_policy"]["kind"] == "suite_preset"
    assert manifest_payload["seed_policy"]["jobs"]["korea_defense_benchmark"]["seeds"] == [101]
    assert manifest_payload["extra"]["profile_records"]["doctrine"]["korea_defense_benchmark"]["selector"] == "korea_un_combined_arms"
    assert "Suite Report" in report_text
    assert "[evaluation_notes]" in report_text
    assert "[suite_jobs]" in report_text
    assert "[core_metrics]" in report_text
    assert "[victory_proxy]" in report_text
    assert "korea_defense_benchmark" in report_text
    assert "metric_focus:" in report_text
    assert "thresholds:" in report_text
    assert len(csv_rows) == 4
    assert "BAI War Lab — Suite Summary" in stdout
    assert "Suite: core_regression" in stdout
    assert "Success rate:" in stdout
    assert f"Artifacts: {suite_dir}" in stdout
