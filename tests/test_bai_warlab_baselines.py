from __future__ import annotations

from pathlib import Path

from tools.bai_warlab.baselines.baseline_manager import compare_to_baseline, load_baseline, save_baseline
from tools.bai_warlab.models import BatchResult, RunResult, SeedPolicy
from tools.bai_warlab.reports.regression_report import render_regression_report
from tools.bai_warlab.runners.batch_run import summarize_runs


def _run(seed: int, *, vp_margin: float, low_supply_turns: float) -> RunResult:
    return RunResult(
        ok=True,
        command="run",
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed=seed,
        max_steps=2,
        dt_hours=0,
        summary={
            "execution_status": "completed",
            "terminal_status": "scenario_complete",
            "ai_side": "ALLIED",
            "result": "win",
            "steps_completed": 2,
            "hours_elapsed": 6,
        },
        metrics={
            "outcome": {"available": True, "win_loss_draw_allied": "win", "vp_margin_allied": vp_margin},
            "behavior": {"available": True, "casualty_ratio_allied": 1.1, "objective_hold_turns_allied": 3.0},
            "logistics": {"available": True, "low_supply_turns_allied": low_supply_turns},
        },
    )


def _batch_result(runs: list[RunResult]) -> BatchResult:
    return BatchResult(
        ok=True,
        command="batch",
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed_policy=SeedPolicy(kind="scheduled", seeds=[run.seed for run in runs], base_seed=runs[0].seed, count=len(runs)),
        runs=runs,
        aggregate=summarize_runs(runs),
    )


def test_bai_warlab_baseline_manager_smoke(tmp_path: Path):
    baseline_result = _batch_result([_run(41, vp_margin=2.0, low_supply_turns=2.0)])
    current_result = _batch_result([_run(51, vp_margin=3.0, low_supply_turns=3.0)])

    saved_path = save_baseline(
        name="smoke_anchor",
        result=baseline_result,
        root=tmp_path,
        metric_thresholds={"vp_margin": 0.25, "low_supply_turns": 0.25},
    )
    loaded = load_baseline("smoke_anchor", root=tmp_path)
    comparison = compare_to_baseline(result=current_result, baseline=loaded)
    report_text = render_regression_report(comparison)

    assert saved_path.exists()
    assert loaded["baseline_name"] == "smoke_anchor"
    assert comparison["metrics"]["vp_margin"]["category"] == "improved"
    assert comparison["metrics"]["low_supply_turns"]["category"] == "regressed"
    assert "Baseline Comparison" in report_text
    assert "[regression_warnings]" in report_text
    assert "Low supply turns regressed" in report_text
