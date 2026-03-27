from __future__ import annotations

import json
from pathlib import Path

from tools.bai_warlab.baselines.baseline_manager import compare_to_baseline, load_baseline, save_baseline
from tools.bai_warlab.models import BatchResult, RunResult, SeedPolicy, SuiteResult
from tools.bai_warlab.reports.regression_report import render_regression_report
from tools.bai_warlab.runners.batch_run import summarize_runs


def _synthetic_run(
    *,
    scenario: str,
    doctrine: str,
    personality: str,
    tuning: str,
    seed: int,
    result_value: str,
    vp_margin: float,
    casualty_ratio: float,
    objective_hold_duration: float,
    low_supply_turns: float,
    suite_job_id: str = "",
) -> RunResult:
    summary = {
        "execution_status": "completed",
        "terminal_status": "scenario_complete",
        "hours_elapsed": 8,
        "steps_completed": 3,
        "ai_side": "ALLIED",
        "result": result_value,
    }
    if suite_job_id:
        summary["suite_job_id"] = suite_job_id
    return RunResult(
        ok=True,
        command="run",
        scenario=scenario,
        scenario_dir="scenarios",
        doctrine=doctrine,
        personality=personality,
        tuning=tuning,
        seed=seed,
        max_steps=3,
        dt_hours=0,
        variant_label=f"{suite_job_id}:trial_001" if suite_job_id else "",
        summary=summary,
        metrics={
            "outcome": {
                "available": True,
                "win_loss_draw_allied": result_value,
                "vp_margin_allied": vp_margin,
            },
            "behavior": {
                "available": True,
                "casualty_ratio_allied": casualty_ratio,
                "objective_hold_turns_allied": objective_hold_duration,
            },
            "logistics": {
                "available": True,
                "low_supply_turns_allied": low_supply_turns,
            },
        },
    )


def _batch_result(*, scenario: str, doctrine: str, personality: str, tuning: str, runs: list[RunResult]) -> BatchResult:
    return BatchResult(
        ok=True,
        command="batch",
        scenario=scenario,
        scenario_dir="scenarios",
        doctrine=doctrine,
        personality=personality,
        tuning=tuning,
        seed_policy=SeedPolicy(
            kind="scheduled",
            seeds=[run.seed for run in runs],
            base_seed=runs[0].seed if runs else 0,
            count=len(runs),
        ),
        runs=runs,
        aggregate=summarize_runs(runs),
    )


def _suite_result(*, runs: list[RunResult]) -> SuiteResult:
    jobs = [
        {
            "id": "job_alpha",
            "scenario": "mini_gc_1942",
            "evaluation_goal": "tempo",
            "seed_policy": {"count": 1, "seeds": [runs[0].seed]},
            "aggregate": {"ok_runs": 1, "failed_runs": 0},
        },
        {
            "id": "job_bravo",
            "scenario": "gc_1942_historical",
            "evaluation_goal": "stability",
            "seed_policy": {"count": 1, "seeds": [runs[1].seed]},
            "aggregate": {"ok_runs": 1, "failed_runs": 0},
        },
    ]
    aggregate = summarize_runs(runs)
    return SuiteResult(
        ok=True,
        command="suite",
        suite_name="core_regression",
        runs=runs,
        jobs=jobs,
        aggregate=aggregate,
        suite_summary={
            "job_count": 2,
            "ok_jobs": 2,
            "failed_jobs": 0,
            "scheduled_runs": 2,
            "completed_runs": aggregate.ok_runs,
            "failed_runs": aggregate.failed_runs,
            "partial_failures": False,
        },
    )


def test_baseline_manager_saves_loads_and_classifies_metrics(tmp_path: Path):
    baseline = _batch_result(
        scenario="mini_gc_1942",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        runs=[
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=11,
                result_value="win",
                vp_margin=2.0,
                casualty_ratio=1.0,
                objective_hold_duration=3.0,
                low_supply_turns=2.0,
            ),
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=12,
                result_value="win",
                vp_margin=2.0,
                casualty_ratio=1.0,
                objective_hold_duration=3.0,
                low_supply_turns=2.0,
            ),
        ],
    )
    baseline_path = save_baseline(
        name="tempo_anchor",
        result=baseline,
        root=tmp_path,
        metric_thresholds={
            "vp_margin": 0.25,
            "casualty_ratio": 0.1,
            "low_supply_turns": 0.25,
        },
    )

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    loaded = load_baseline("tempo_anchor", root=tmp_path)

    assert payload["schema_version"] == 1
    assert payload["baseline_name"] == "tempo_anchor"
    assert payload["snapshot"]["metrics"]["vp_margin"] == 2.0
    assert loaded["thresholds"]["casualty_ratio"]["threshold"] == 0.1

    current = _batch_result(
        scenario="mini_gc_1942",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        runs=[
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=21,
                result_value="win",
                vp_margin=3.0,
                casualty_ratio=1.05,
                objective_hold_duration=3.0,
                low_supply_turns=3.0,
            ),
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=22,
                result_value="win",
                vp_margin=3.0,
                casualty_ratio=1.05,
                objective_hold_duration=3.0,
                low_supply_turns=3.0,
            ),
        ],
    )

    comparison = compare_to_baseline(result=current, baseline=loaded)

    assert comparison["metrics"]["vp_margin"]["category"] == "improved"
    assert comparison["metrics"]["casualty_ratio"]["category"] == "neutral"
    assert comparison["metrics"]["low_supply_turns"]["category"] == "regressed"
    assert comparison["improved"] == ["vp_margin"]
    assert comparison["regressed"] == ["low_supply_turns"]
    assert comparison["neutral"] == ["casualty_ratio", "failure_rate", "objective_hold_duration", "result_score"]

    report_text = render_regression_report(comparison)
    assert "Baseline: tempo_anchor" in report_text
    assert "Result: mixed" in report_text
    assert "Improved: vp_margin" in report_text
    assert "Regressed: low_supply_turns" in report_text
    assert "Best improvement: VP margin (+1.000)" in report_text
    assert "Worst regression: Low supply turns (+1.000)" in report_text
    assert "[regression_warnings]" in report_text
    assert "Low supply turns regressed by +1.000 against threshold 0.25" in report_text


def test_suite_baseline_comparison_includes_job_breakdown(tmp_path: Path):
    baseline = _suite_result(
        runs=[
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=31,
                result_value="draw",
                vp_margin=1.0,
                casualty_ratio=1.0,
                objective_hold_duration=2.0,
                low_supply_turns=3.0,
                suite_job_id="job_alpha",
            ),
            _synthetic_run(
                scenario="gc_1942_historical",
                doctrine="korea_un_combined_arms",
                personality="historical",
                tuning="default",
                seed=41,
                result_value="win",
                vp_margin=2.0,
                casualty_ratio=1.1,
                objective_hold_duration=4.0,
                low_supply_turns=1.0,
                suite_job_id="job_bravo",
            ),
        ]
    )
    saved = save_baseline(name="core_regression_anchor", result=baseline, root=tmp_path)

    current = _suite_result(
        runs=[
            _synthetic_run(
                scenario="mini_gc_1942",
                doctrine="korea_nkpa_shock",
                personality="aggressive",
                tuning="default",
                seed=32,
                result_value="win",
                vp_margin=2.0,
                casualty_ratio=1.0,
                objective_hold_duration=3.0,
                low_supply_turns=2.0,
                suite_job_id="job_alpha",
            ),
            _synthetic_run(
                scenario="gc_1942_historical",
                doctrine="korea_un_combined_arms",
                personality="historical",
                tuning="default",
                seed=42,
                result_value="win",
                vp_margin=2.0,
                casualty_ratio=1.1,
                objective_hold_duration=4.0,
                low_supply_turns=3.0,
                suite_job_id="job_bravo",
            ),
        ]
    )

    comparison = compare_to_baseline(
        result=current,
        baseline=saved,
        metric_thresholds={"vp_margin": 0.25, "low_supply_turns": 0.25},
    )

    assert "job_comparisons" in comparison
    assert comparison["job_comparisons"]["job_alpha"]["improved"] == [
        "low_supply_turns",
        "objective_hold_duration",
        "result_score",
        "vp_margin",
    ]
    assert comparison["job_comparisons"]["job_bravo"]["regressed"] == ["low_supply_turns"]

    report_text = render_regression_report(comparison)
    assert "[job_comparisons]" in report_text
    assert "job_alpha: scenario=mini_gc_1942" in report_text
    assert "job_bravo: scenario=gc_1942_historical" in report_text
