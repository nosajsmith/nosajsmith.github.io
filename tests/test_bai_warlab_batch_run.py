from __future__ import annotations

import json
from pathlib import Path
import csv

from tools.bai_warlab.bai_warlab import main as bai_warlab_main
from tools.bai_warlab.models import RunResult
from tools.bai_warlab.report_io import RESULTS_CSV_COLUMNS
from tools.bai_warlab.runners.batch_run import execute_batch_run
from tools.bai_warlab.seed_policy import resolve_seed_policy, schedule_seeds


def test_seed_policy_schedules_deterministic_batch_seeds():
    assert schedule_seeds(runs=4, base_seed=11) == [11, 12, 13, 14]
    policy = resolve_seed_policy(count=4, seed_start=11)
    assert policy.kind == "scheduled"
    assert policy.base_seed == 11
    assert policy.count == 4
    assert policy.seeds == [11, 12, 13, 14]


def test_execute_batch_run_aggregates_and_continues_on_partial_failure(monkeypatch):
    def fake_single_run(request, loader):
        if request.seed == 22:
            raise RuntimeError("synthetic batch fault")
        return RunResult(
            ok=True,
            command="run",
            scenario=request.scenario,
            scenario_dir=request.scenario_dir,
            doctrine=request.doctrine,
            personality=request.personality,
            tuning=request.tuning,
            seed=request.seed,
            max_steps=int(request.max_steps or 0),
            dt_hours=int(request.dt_hours or 0),
            variant_label=request.variant_label,
            summary={
                "execution_status": "completed",
                "terminal_status": "scenario_complete",
                "hours_elapsed": request.seed,
                "steps_completed": 4,
                "ai_side": "ALLIED",
                "scenario_outcome": "allied_victory" if request.seed >= 23 else "draw",
                "winning_side": "ALLIED" if request.seed >= 23 else "",
                "result": "win" if request.seed >= 23 else "draw",
            },
            metrics={
                "outcome": {
                    "available": True,
                    "vp_margin_allied": request.seed - 20,
                    "win_loss_draw_allied": "win" if request.seed >= 23 else "draw",
                },
                "behavior": {
                    "available": True,
                    "allied_casualties": request.seed,
                    "axis_casualties": request.seed + 3,
                    "casualty_ratio_allied": round((request.seed + 3) / request.seed, 3),
                    "objective_hold_turns_allied": request.seed - 19,
                    "line_collapse_rate_allied": 0.25,
                },
                "logistics": {
                    "available": True,
                    "low_supply_turns_allied": request.seed - 21,
                },
            },
        )

    monkeypatch.setattr("tools.bai_warlab.runners.batch_run.execute_single_run", fake_single_run)

    policy = resolve_seed_policy(count=4, seed_start=21)
    result = execute_batch_run(
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed_policy=policy,
        loader=object(),
        max_steps=2,
    )

    assert result.ok is True
    assert [run.seed for run in result.runs] == [21, 22, 23, 24]
    assert result.aggregate.total_runs == 4
    assert result.aggregate.ok_runs == 3
    assert result.aggregate.failed_runs == 1
    assert result.aggregate.failure_count == 1
    assert result.aggregate.partial_failures is True
    assert result.aggregate.success_rate == 0.75
    assert result.aggregate.status_counts["scenario_complete"] == 3
    assert result.aggregate.status_counts["batch_run_exception"] == 1
    assert result.aggregate.result_counts == {"draw": 1, "win": 2}
    assert result.aggregate.scenario_outcome_counts == {"allied_victory": 2, "draw": 1}
    assert result.aggregate.winning_side_counts == {"ALLIED": 2, "DRAW": 1}
    assert result.aggregate.victory_proxy["non_loss_rate"] == 1.0
    assert result.aggregate.victory_proxy["mean_result_score"] == 0.833
    assert result.aggregate.mean_summary["hours_elapsed"] == 22.667
    assert result.aggregate.min_summary["hours_elapsed"] == 21.0
    assert result.aggregate.max_summary["hours_elapsed"] == 24.0
    assert result.aggregate.mean_metrics["outcome.vp_margin_allied"] == 2.667
    assert result.aggregate.core_metrics["vp_margin"]["stddev"] == 1.247
    assert result.aggregate.core_metrics["allied_casualties"]["median"] == 23.0
    assert result.aggregate.core_metrics["low_supply_turns"]["spread"] == 3.0
    assert result.aggregate.averages["summary"]["hours_elapsed"] == 22.667
    assert "Partial failure" in result.warnings[0]


def test_bai_warlab_batch_cli_outputs(tmp_path: Path, capsys):
    batch_dir = tmp_path / "batch"

    assert bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "batch",
            "--scenario",
            "mini_gc_1942",
            "--scenario-dir",
            "scenarios",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "aggressive",
            "--tuning",
            "default",
            "--runs",
            "3",
            "--seed",
            "5",
            "--max-steps",
            "2",
            "--output-dir",
            str(batch_dir),
        ]
    ) == 0

    summary_payload = json.loads((batch_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    report_text = (batch_dir / "report.txt").read_text(encoding="utf-8")
    csv_rows = list(csv.DictReader((batch_dir / "results.csv").open(encoding="utf-8")))
    stdout = capsys.readouterr().out

    assert summary_payload["command"] == "batch"
    assert summary_payload["aggregate"]["total_runs"] == 3
    assert summary_payload["aggregate"]["failure_count"] == 0
    assert summary_payload["aggregate"]["success_rate"] == 1.0
    assert summary_payload["aggregate"]["core_metrics"]["vp_margin"]["stddev"] >= 0.0
    assert summary_payload["aggregate"]["victory_proxy"]["available"] is True
    assert summary_payload["aggregate"]["mean_summary"]
    assert summary_payload["aggregate"]["min_summary"]
    assert summary_payload["aggregate"]["max_summary"]
    assert manifest_payload["seed_policy"]["kind"] == "scheduled"
    assert manifest_payload["seed_policy"]["base_seed"] == 5
    assert manifest_payload["seed_policy"]["count"] == 3
    assert manifest_payload["seed_policy"]["seeds"] == [5, 6, 7]
    assert "Batch Report" in report_text
    assert "Failure Count: 0" in report_text
    assert "[aggregate_summary]" in report_text
    assert "[core_metrics]" in report_text
    assert "[victory_proxy]" in report_text
    assert len(csv_rows) == 3
    assert "BAI War Lab — Batch Summary" in stdout
    assert "Runs: 3 | OK: 3 | Failed: 0" in stdout
    assert "Success rate:" in stdout
    assert "Results:" in stdout
    assert f"Artifacts: {batch_dir}" in stdout
    for column in [
        "scenario",
        "doctrine",
        "personality",
        "tuning",
        "seed",
        "result",
        "vp_margin",
        "allied_casualties",
        "axis_casualties",
        "casualty_ratio",
        "objective_hold_duration",
        "low_supply_turns",
        "failure_flag",
        "failure_message",
    ]:
        assert column in RESULTS_CSV_COLUMNS
        assert column in csv_rows[0]
