from __future__ import annotations

from typing import Any, Dict, List

from ..config_loader import ConfigLoader
from ..models import BatchResult, RunResult, SeedPolicy, SuiteCase, SuiteResult
from ..presets.benchmark_suites import load_benchmark_suite_definition
from ..seed_policy import resolve_seed_policy
from .batch_run import execute_batch_run, summarize_runs


def _suite_seed_policy(case: SuiteCase, runs_override: int | None = None) -> SeedPolicy:
    run_count = int(runs_override or case.runs or 1)
    return resolve_seed_policy(count=run_count, seed_start=case.seed)


def _failed_suite_job(
    case: SuiteCase,
    seed_policy: SeedPolicy,
    error: Exception | str,
    *,
    max_steps: int | None = None,
    dt_hours: int | None = None,
) -> BatchResult:
    message = str(error)
    max_steps = int(max_steps or case.max_steps or 0)
    dt_hours = int(dt_hours or case.dt_hours or 0)
    failed_run = RunResult(
        ok=False,
        command="run",
        scenario=case.scenario,
        scenario_dir=case.scenario_dir,
        doctrine=case.doctrine,
        personality=case.personality,
        tuning=case.tuning,
        seed=int(seed_policy.seeds[0]),
        max_steps=max_steps,
        dt_hours=dt_hours,
        variant_label=f"{case.id}:trial_001",
        error=message,
        warnings=["Suite runner captured a scenario job failure and continued."],
        summary={
            "ok": False,
            "execution_status": "failed",
            "result": "error",
            "terminal_status": "suite_job_exception",
            "hours_elapsed": 0,
            "steps_completed": 0,
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "max_steps_exhausted": False,
            "suite_job_id": case.id,
            "suite_goal": case.evaluation_goal,
        },
        metrics={"outcome": {"available": False, "reason": "suite_job_exception"}},
        ai_report={"available": False},
    )
    aggregate = summarize_runs([failed_run])
    return BatchResult(
        ok=False,
        command="batch",
        scenario=case.scenario,
        scenario_dir=case.scenario_dir,
        doctrine=case.doctrine,
        personality=case.personality,
        tuning=case.tuning,
        seed_policy=seed_policy,
        runs=[failed_run],
        aggregate=aggregate,
        warnings=[f"Suite job {case.id} failed before batch execution completed: {message}"],
    )


def _annotate_job_runs(*, suite_name: str, case: SuiteCase, batch_result: BatchResult) -> None:
    for run in batch_result.runs:
        suffix = run.variant_label or "trial"
        if not suffix.startswith(f"{case.id}:"):
            run.variant_label = f"{case.id}:{suffix}"
        summary = dict(run.summary or {})
        summary.setdefault("suite_name", suite_name)
        summary.setdefault("suite_job_id", case.id)
        if case.evaluation_goal:
            summary.setdefault("suite_goal", case.evaluation_goal)
        run.summary = summary


def _job_summary(case: SuiteCase, batch_result: BatchResult) -> Dict[str, Any]:
    aggregate = batch_result.aggregate
    return {
        "id": case.id,
        "scenario": case.scenario,
        "scenario_dir": case.scenario_dir,
        "doctrine": case.doctrine,
        "personality": case.personality,
        "tuning": case.tuning,
        "evaluation_goal": case.evaluation_goal,
        "notes": case.notes,
        "metric_focus": list(case.metric_focus),
        "metric_thresholds": dict(case.metric_thresholds),
        "seed_policy": {
            "kind": batch_result.seed_policy.kind,
            "seeds": list(batch_result.seed_policy.seeds),
            "base_seed": batch_result.seed_policy.base_seed,
            "count": batch_result.seed_policy.count,
        },
        "ok": batch_result.ok,
        "warning_count": len(batch_result.warnings),
        "aggregate": {
            "total_runs": aggregate.total_runs if aggregate else 0,
            "ok_runs": aggregate.ok_runs if aggregate else 0,
            "failed_runs": aggregate.failed_runs if aggregate else 0,
            "failure_count": aggregate.failure_count if aggregate else 0,
            "partial_failures": aggregate.partial_failures if aggregate else False,
            "status_counts": dict(aggregate.status_counts or {}) if aggregate else {},
            "mean_summary": dict(aggregate.mean_summary or {}) if aggregate else {},
            "mean_metrics": dict(aggregate.mean_metrics or {}) if aggregate else {},
        },
    }


def execute_suite_run(
    *,
    suite_name: str,
    loader: ConfigLoader,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
    runs_override: int | None = None,
) -> SuiteResult:
    suite_definition = load_benchmark_suite_definition(suite_name)
    cases = list(suite_definition["cases"])
    flattened_runs: List[RunResult] = []
    job_summaries: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for case in cases:
        seed_policy = _suite_seed_policy(case, runs_override)
        job_max_steps = case.max_steps or max_steps
        job_dt_hours = case.dt_hours or dt_hours
        try:
            batch_result = execute_batch_run(
                scenario=case.scenario,
                scenario_dir=case.scenario_dir,
                doctrine=case.doctrine,
                personality=case.personality,
                tuning=case.tuning,
                seed_policy=seed_policy,
                loader=loader,
                max_steps=job_max_steps,
                dt_hours=job_dt_hours,
                stop_on_terminal=stop_on_terminal,
            )
        except Exception as exc:
            batch_result = _failed_suite_job(case, seed_policy, exc, max_steps=job_max_steps, dt_hours=job_dt_hours)

        _annotate_job_runs(suite_name=suite_name, case=case, batch_result=batch_result)
        flattened_runs.extend(batch_result.runs)
        job_summaries.append(_job_summary(case, batch_result))

        aggregate = batch_result.aggregate
        if not batch_result.ok:
            warnings.append(f"Job {case.id} completed with no successful runs.")
        if aggregate and aggregate.failure_count:
            warnings.append(f"Job {case.id} reported {aggregate.failure_count} failed run(s).")

    aggregate = summarize_runs(flattened_runs)
    suite_summary = {
        "description": suite_definition.get("description", ""),
        "evaluation_notes": list(suite_definition.get("evaluation_notes", []) or []),
        "source_path": suite_definition.get("source_path", ""),
        "job_count": len(job_summaries),
        "ok_jobs": sum(1 for job in job_summaries if job.get("ok")),
        "failed_jobs": sum(1 for job in job_summaries if not job.get("ok")),
        "scheduled_runs": sum(int((job.get("seed_policy") or {}).get("count") or 0) for job in job_summaries),
        "completed_runs": aggregate.ok_runs,
        "failed_runs": aggregate.failed_runs,
        "partial_failures": any(
            bool((job.get("aggregate") or {}).get("failure_count")) or not bool(job.get("ok"))
            for job in job_summaries
        ),
    }
    if suite_summary["partial_failures"]:
        warnings.insert(
            0,
            f"Partial failure: suite {suite_name} completed with {suite_summary['failed_jobs']} failed job(s) and {aggregate.failure_count} failed run(s).",
        )

    return SuiteResult(
        ok=aggregate.ok_runs > 0,
        command="suite",
        suite_name=suite_name,
        runs=flattened_runs,
        jobs=job_summaries,
        aggregate=aggregate,
        suite_summary=suite_summary,
        warnings=warnings,
    )


__all__ = ["execute_suite_run"]
