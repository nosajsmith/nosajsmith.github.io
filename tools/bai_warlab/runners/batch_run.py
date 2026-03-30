from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple

from ..config_loader import ConfigLoader
from ..models import AggregateSummary, BatchResult, RunRequest, RunResult, SeedPolicy
from ..report_io import run_result_to_row, summarize_core_metric_rows, summarize_outcome_rows
from .single_run import execute_single_run


def _flatten_numeric(mapping: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    flattened: Dict[str, float] = {}
    for key, value in mapping.items():
        field = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_numeric(value, field))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            flattened[field] = float(value)
    return flattened


def _aggregate_numeric(records: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    buckets: Dict[str, List[float]] = {}
    for record in records:
        for key, value in _flatten_numeric(record).items():
            buckets.setdefault(key, []).append(value)

    means = {key: round(sum(values) / len(values), 3) for key, values in buckets.items() if values}
    mins = {key: round(min(values), 3) for key, values in buckets.items() if values}
    maxes = {key: round(max(values), 3) for key, values in buckets.items() if values}
    return means, mins, maxes


def mean_summary(runs: List[RunResult]) -> Dict[str, Any]:
    means, _, _ = _aggregate_numeric([dict(run.summary or {}) for run in runs])
    return means


def summarize_runs(runs: List[RunResult]) -> AggregateSummary:
    successful = [run for run in runs if run.ok]
    successful_rows = [run_result_to_row(run) for run in successful]
    status_counts = Counter(str((run.summary or {}).get("terminal_status", "unknown")) for run in runs)
    mean_summary_values, min_summary_values, max_summary_values = _aggregate_numeric(
        [dict(run.summary or {}) for run in successful]
    )
    mean_metric_values, min_metric_values, max_metric_values = _aggregate_numeric(
        [dict(run.metrics or {}) for run in successful]
    )
    failure_count = len(runs) - len(successful)
    success_rate = round(len(successful) / len(runs), 3) if runs else 0.0
    core_metrics = summarize_core_metric_rows(successful_rows)
    victory_proxy = summarize_outcome_rows(successful_rows)

    return AggregateSummary(
        total_runs=len(runs),
        ok_runs=len(successful),
        failed_runs=failure_count,
        failure_count=failure_count,
        partial_failures=bool(successful) and failure_count > 0,
        success_rate=success_rate,
        status_counts=dict(status_counts),
        result_counts=dict(victory_proxy.get("result_counts", {}) or {}),
        scenario_outcome_counts=dict(victory_proxy.get("scenario_outcome_counts", {}) or {}),
        winning_side_counts=dict(victory_proxy.get("winning_side_counts", {}) or {}),
        core_metrics=core_metrics,
        victory_proxy=victory_proxy,
        mean_summary=mean_summary_values,
        min_summary=min_summary_values,
        max_summary=max_summary_values,
        mean_metrics=mean_metric_values,
        min_metrics=min_metric_values,
        max_metrics=max_metric_values,
        averages={"summary": mean_summary_values, "metrics": mean_metric_values},
        mins={"summary": min_summary_values, "metrics": min_metric_values},
        maxes={"summary": max_summary_values, "metrics": max_metric_values},
    )


def _failed_batch_run(request: RunRequest, error: Exception | str) -> RunResult:
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
        warnings=["Batch runner captured a trial failure and continued."],
        summary={
            "ok": False,
            "execution_status": "failed",
            "result": "error",
            "terminal_status": "batch_run_exception",
            "hours_elapsed": 0,
            "steps_completed": 0,
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "max_steps_exhausted": False,
        },
        metrics={"outcome": {"available": False, "reason": "batch_run_exception"}},
        ai_report={"available": False},
    )


def execute_batch_run(
    *,
    scenario: str,
    scenario_dir: str,
    doctrine: str,
    personality: str,
    tuning: str,
    seed_policy: SeedPolicy,
    loader: ConfigLoader,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
) -> BatchResult:
    runs: List[RunResult] = []
    warnings: List[str] = []

    for index, seed in enumerate(seed_policy.seeds, start=1):
        request = RunRequest(
            scenario=scenario,
            scenario_dir=scenario_dir,
            doctrine=doctrine,
            personality=personality,
            tuning=tuning,
            seed=int(seed),
            max_steps=max_steps,
            dt_hours=dt_hours,
            stop_on_terminal=stop_on_terminal,
            variant_label=f"trial_{index:03d}",
        )
        try:
            run = execute_single_run(request, loader)
        except Exception as exc:
            run = _failed_batch_run(request, exc)
        runs.append(run)
        if not run.ok:
            warnings.append(f"Seed {seed} failed: {run.error or run.summary.get('terminal_status', 'unknown')}")

    aggregate = summarize_runs(runs)
    if aggregate.partial_failures:
        warnings.insert(0, f"Partial failure: {aggregate.failure_count} of {aggregate.total_runs} runs failed.")

    return BatchResult(
        ok=aggregate.ok_runs > 0,
        command="batch",
        scenario=scenario,
        scenario_dir=scenario_dir,
        doctrine=doctrine,
        personality=personality,
        tuning=tuning,
        seed_policy=seed_policy,
        runs=runs,
        aggregate=aggregate,
        warnings=warnings,
    )


__all__ = ["execute_batch_run", "mean_summary", "summarize_runs"]
