from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main
from tools.bai_warlab.models import RunResult
from tools.bai_warlab.reports.summary_report import render_report
from tools.bai_warlab.runners.compare_run import execute_compare_run
from tools.bai_warlab.seed_policy import resolve_seed_policy


ROOT = Path(__file__).resolve().parents[1]


def _synthetic_run(request, *, result_value: str, vp_margin: float, casualty_ratio: float, objective_hold: float, low_supply_turns: float) -> RunResult:
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
            "hours_elapsed": 12,
            "steps_completed": 4,
            "ai_side": "ALLIED",
            "scenario_outcome": "draw",
            "result": result_value,
        },
        metrics={
            "outcome": {
                "available": True,
                "win_loss_draw_allied": result_value,
                "vp_margin_allied": vp_margin,
            },
            "behavior": {
                "available": True,
                "casualty_ratio_allied": casualty_ratio,
                "objective_hold_turns_allied": objective_hold,
            },
            "logistics": {
                "available": True,
                "low_supply_turns_allied": low_supply_turns,
            },
        },
    )


def test_execute_compare_run_uses_shared_seed_schedule_and_computes_metric_deltas(monkeypatch):
    def fake_single_run(request, loader):
        if request.variant_label == "left":
            return _synthetic_run(
                request,
                result_value="draw",
                vp_margin=request.seed - 30,
                casualty_ratio=1.5,
                objective_hold=2,
                low_supply_turns=5,
            )
        return _synthetic_run(
            request,
            result_value="win",
            vp_margin=request.seed - 28,
            casualty_ratio=1.0,
            objective_hold=4,
            low_supply_turns=3,
        )

    monkeypatch.setattr("tools.bai_warlab.runners.compare_run.execute_single_run", fake_single_run)

    result = execute_compare_run(
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        left={
            "doctrine": "korea_nkpa_shock",
            "personality": "aggressive",
            "tuning": "default",
        },
        right={
            "doctrine": "korea_un_combined_arms",
            "personality": "aggressive",
            "tuning": "default",
        },
        seed_policy=resolve_seed_policy(count=3, seed_start=31),
        loader=object(),
        max_steps=2,
    )

    assert result.ok is True
    assert [run.seed for run in result.left_runs] == [31, 32, 33]
    assert [run.seed for run in result.right_runs] == [31, 32, 33]
    assert result.comparison["paired_seed_count"] == 3
    assert result.comparison["seed_mismatch_count"] == 0
    assert result.comparison["left_beats_right"] == ["casualty_ratio"]
    assert result.comparison["right_beats_left"] == [
        "low_supply_turns",
        "objective_hold_duration",
        "result_score",
        "vp_margin",
    ]
    assert result.comparison["core_metrics"]["vp_margin"]["delta_right_minus_left"] == 2.0
    assert result.comparison["core_metrics"]["casualty_ratio"]["winner"] == "left"
    assert result.comparison["core_metrics"]["low_supply_turns"]["winner"] == "right"

    report_text = render_report(result)
    assert "Winner: B" in report_text
    assert "Rationale: B leads 4 to 1 on core metrics." in report_text
    assert "Result score: A=0.5 B=1.0 delta(B-A)=+0.500 edge=B" in report_text
    assert "Best A edge: Casualty ratio (-0.500 B-A)" in report_text
    assert "Best B edge: VP margin (+2.000 B-A)" in report_text
    assert "[regression_warnings]" in report_text
    assert "A regression risks:" in report_text
    assert "Result score (+0.500 B-A)" in report_text


def test_execute_compare_run_continues_on_partial_failure(monkeypatch):
    def fake_single_run(request, loader):
        if request.variant_label == "right" and request.seed == 42:
            raise RuntimeError("synthetic compare fault")
        return _synthetic_run(
            request,
            result_value="win",
            vp_margin=2,
            casualty_ratio=1.2,
            objective_hold=3,
            low_supply_turns=2,
        )

    monkeypatch.setattr("tools.bai_warlab.runners.compare_run.execute_single_run", fake_single_run)

    result = execute_compare_run(
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        left={
            "doctrine": "korea_nkpa_shock",
            "personality": "aggressive",
            "tuning": "default",
        },
        right={
            "doctrine": "korea_un_combined_arms",
            "personality": "aggressive",
            "tuning": "default",
        },
        seed_policy=resolve_seed_policy(count=3, seed_start=41),
        loader=object(),
        max_steps=2,
    )

    assert result.ok is True
    assert result.comparison["paired_seed_count"] == 2
    assert result.comparison["partial_failures"] is True
    assert result.comparison["pair_results"][1]["seed_left"] == 42
    assert result.comparison["pair_results"][1]["right_ok"] is False
    assert result.comparison["pair_results"][1]["right_failure"] == "synthetic compare fault"
    assert "Partial failure" in result.warnings[0]
    assert "Seed 42: left_ok=True right_ok=False" in result.warnings[1]


def test_bai_warlab_compare_cli_outputs(tmp_path: Path):
    compare_dir = tmp_path / "compare"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "compare",
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
            "--right-doctrine",
            "korea_un_combined_arms",
            "--runs",
            "2",
            "--seed",
            "9",
            "--max-steps",
            "2",
            "--output-dir",
            str(compare_dir),
        ]
    )

    assert exit_code == 0

    summary_payload = json.loads((compare_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((compare_dir / "manifest.json").read_text(encoding="utf-8"))
    report_text = (compare_dir / "report.txt").read_text(encoding="utf-8")
    csv_rows = list(csv.DictReader((compare_dir / "results.csv").open(encoding="utf-8")))

    assert summary_payload["command"] == "compare"
    assert summary_payload["comparison"]["paired_seed_count"] == 2
    assert "vp_margin" in summary_payload["comparison"]["core_metrics"]
    assert manifest_payload["seed_policy"]["seeds"] == [9, 10]
    assert manifest_payload["extra"]["profile_records"]["doctrine"]["left"]["selector"] == "korea_nkpa_shock"
    assert manifest_payload["extra"]["profile_records"]["doctrine"]["right"]["selector"] == "korea_un_combined_arms"
    assert "Compare Report" in report_text
    assert "[decision]" in report_text
    assert "[key_deltas]" in report_text
    assert "[callouts]" in report_text
    assert len(csv_rows) == 4
    assert {row["variant_label"] for row in csv_rows} == {"left", "right"}
