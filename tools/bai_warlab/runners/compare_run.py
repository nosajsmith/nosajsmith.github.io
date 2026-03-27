from __future__ import annotations

from typing import Dict, List

from ..comparison import build_comparison
from ..config_loader import ConfigLoader
from ..models import CompareResult, RunRequest, RunResult, SeedPolicy
from .batch_run import summarize_runs
from .single_run import execute_single_run


def _failed_compare_run(request: RunRequest, error: Exception | str) -> RunResult:
    message = str(error)
    max_steps = int(request.max_steps or 0)
    dt_hours = int(request.dt_hours or 0)
    return RunResult(
        ok=False,
        command="run",
        scenario=request.scenario,
        scenario_dir=request.scenario_dir,
        doctrine=request.doctrine,
        personality=request.personality,
        tuning=request.tuning,
        seed=int(request.seed),
        max_steps=max_steps,
        dt_hours=dt_hours,
        variant_label=request.variant_label,
        error=message,
        warnings=["Compare runner captured a trial failure and continued."],
        summary={
            "ok": False,
            "execution_status": "failed",
            "result": "error",
            "terminal_status": "compare_run_exception",
            "hours_elapsed": 0,
            "steps_completed": 0,
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "max_steps_exhausted": False,
        },
        metrics={"outcome": {"available": False, "reason": "compare_run_exception"}},
        ai_report={"available": False},
    )


def _variant_label(config: Dict[str, str]) -> str:
    return f"{config['doctrine']} / {config['personality']} / {config['tuning']}"


def execute_compare_run(
    *,
    scenario: str,
    scenario_dir: str,
    left: Dict[str, str],
    right: Dict[str, str],
    seed_policy: SeedPolicy,
    loader: ConfigLoader,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
) -> CompareResult:
    left_runs: List[RunResult] = []
    right_runs: List[RunResult] = []
    warnings: List[str] = []

    for seed in seed_policy.seeds:
        left_request = RunRequest(
            scenario=scenario,
            scenario_dir=scenario_dir,
            doctrine=left["doctrine"],
            personality=left["personality"],
            tuning=left["tuning"],
            seed=int(seed),
            max_steps=max_steps,
            dt_hours=dt_hours,
            stop_on_terminal=stop_on_terminal,
            variant_label="left",
        )
        right_request = RunRequest(
            scenario=scenario,
            scenario_dir=scenario_dir,
            doctrine=right["doctrine"],
            personality=right["personality"],
            tuning=right["tuning"],
            seed=int(seed),
            max_steps=max_steps,
            dt_hours=dt_hours,
            stop_on_terminal=stop_on_terminal,
            variant_label="right",
        )

        try:
            left_run = execute_single_run(left_request, loader)
        except Exception as exc:
            left_run = _failed_compare_run(left_request, exc)

        try:
            right_run = execute_single_run(right_request, loader)
        except Exception as exc:
            right_run = _failed_compare_run(right_request, exc)

        left_runs.append(left_run)
        right_runs.append(right_run)
        if not left_run.ok or not right_run.ok:
            warnings.append(
                f"Seed {seed}: left_ok={left_run.ok} right_ok={right_run.ok}"
            )

    left_label = _variant_label(left)
    right_label = _variant_label(right)
    comparison = build_comparison(
        left_runs=left_runs,
        right_runs=right_runs,
        left_label=left_label,
        right_label=right_label,
    )
    left_aggregate = summarize_runs(left_runs)
    right_aggregate = summarize_runs(right_runs)
    comparison["left_aggregate"] = {
        "ok_runs": left_aggregate.ok_runs,
        "failed_runs": left_aggregate.failed_runs,
        "failure_count": left_aggregate.failure_count,
        "mean_summary": left_aggregate.mean_summary,
    }
    comparison["right_aggregate"] = {
        "ok_runs": right_aggregate.ok_runs,
        "failed_runs": right_aggregate.failed_runs,
        "failure_count": right_aggregate.failure_count,
        "mean_summary": right_aggregate.mean_summary,
    }

    if comparison.get("partial_failures"):
        warnings.insert(0, f"Partial failure: matched comparison completed for {comparison['paired_seed_count']} of {comparison['scheduled_seed_count']} seeds.")
    if comparison.get("seed_mismatch_count"):
        warnings.append(f"Seed mismatch detected in {comparison['seed_mismatch_count']} pair(s).")

    return CompareResult(
        ok=bool(comparison.get("paired_seed_count")),
        command="compare",
        scenario=scenario,
        scenario_dir=scenario_dir,
        seed_policy=seed_policy,
        left_label=left_label,
        right_label=right_label,
        left_runs=left_runs,
        right_runs=right_runs,
        comparison=comparison,
        warnings=warnings,
    )


__all__ = ["execute_compare_run"]
