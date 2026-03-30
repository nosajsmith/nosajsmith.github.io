from __future__ import annotations

from typing import Any, Dict, List

from ..report_io import run_result_to_row, summarize_core_metric_rows, summarize_outcome_rows
from .comparison_report import render_comparison_report


def _lines_for_metrics(metrics: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for category, payload in metrics.items():
        lines.append(f"[{category}]")
        for key, value in payload.items():
            lines.append(f"  {key}: {value}")
    return lines


def _joined(items: List[str]) -> str:
    return ", ".join(items) if items else "none"


def _count_lines(title: str, payload: Dict[str, Any]) -> List[str]:
    counts = dict(payload or {})
    if not counts:
        return [f"{title}: none"]
    return [f"{title}: {', '.join(f'{key}={value}' for key, value in counts.items())}"]


def _core_metric_lines(metrics: Dict[str, Dict[str, Any]]) -> List[str]:
    metrics = dict(metrics or {})
    if not metrics:
        return []
    lines = ["[core_metrics]"]
    for payload in metrics.values():
        lines.append(
            f"{payload['label']}: "
            f"mean={payload['mean']} median={payload.get('median', payload['mean'])} "
            f"min={payload['min']} max={payload['max']} spread={payload.get('spread', 0.0)} "
            f"sd={payload.get('stddev', 0.0)} n={payload['count']}"
        )
    return lines


def _victory_proxy_lines(payload: Dict[str, Any]) -> List[str]:
    proxy = dict(payload or {})
    if not proxy.get("available"):
        return []
    lines = ["[victory_proxy]"]
    lines.extend(_count_lines("AI sides", proxy.get("ai_side_counts") or {}))
    lines.extend(_count_lines("Results", proxy.get("result_counts") or {}))
    lines.extend(_count_lines("Scenario outcomes", proxy.get("scenario_outcome_counts") or {}))
    lines.extend(_count_lines("Winning sides", proxy.get("winning_side_counts") or {}))
    lines.append(f"Win rate: {proxy.get('win_rate')}")
    lines.append(f"Draw rate: {proxy.get('draw_rate')}")
    lines.append(f"Loss rate: {proxy.get('loss_rate')}")
    lines.append(f"Non-loss rate: {proxy.get('non_loss_rate')}")
    if proxy.get("mean_result_score") is not None:
        lines.append(f"Mean result score: {proxy.get('mean_result_score')}")
    return lines


def render_report(result: Any) -> str:
    command = getattr(result, "command", "run")
    if command == "run":
        return _render_run(result)
    if command == "batch":
        return _render_batch(result)
    if command == "compare":
        return _render_compare(result)
    if command == "suite":
        return _render_suite(result)
    return f"BAI War Lab report unavailable for command: {command}"


def _render_run(result: Any) -> str:
    summary = result.summary or {}
    ai_report = getattr(result, "ai_report", {}) or {}
    lines = [
        "BAI War Lab — Run Report",
        f"Scenario: {result.scenario}",
        f"Doctrine: {result.doctrine}",
        f"Personality: {result.personality}",
        f"Tuning: {result.tuning}",
        f"Seed: {result.seed}",
        f"Execution Status: {summary.get('execution_status', 'unknown')}",
        f"Terminal Status: {summary.get('terminal_status', 'unknown')}",
        f"Configured Max Steps: {summary.get('configured_max_steps', result.max_steps)}",
        f"Configured DT Hours: {summary.get('configured_dt_hours', result.dt_hours)}",
        f"Steps Completed: {summary.get('steps_completed', 0)}",
        f"Hours Elapsed: {summary.get('hours_elapsed', 0)}",
        "",
    ]
    if summary.get("scenario_outcome"):
        lines.extend(
            [
                f"Scenario Outcome: {summary.get('scenario_outcome')}",
                f"Winning Side: {summary.get('winning_side') or 'draw'}",
                "",
            ]
        )
    if result.metrics:
        lines.extend(_lines_for_metrics(result.metrics))
    if ai_report.get("available"):
        lines.extend(
            [
                "",
                "[ai_report]",
                f"  posture: {ai_report.get('posture')}",
                f"  main_objective: {ai_report.get('main_objective')}",
                f"  chosen_operation: {ai_report.get('chosen_operation')}",
                f"  reserve_level: {ai_report.get('reserve_level')}",
                f"  timing_breakdown: {ai_report.get('timing_breakdown')}",
            ]
        )
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    if result.error:
        lines.extend(["", f"Error: {result.error}"])
    return "\n".join(lines)


def _render_batch(result: Any) -> str:
    rows = [run_result_to_row(run) for run in list(getattr(result, "runs", []) or [])]
    successful_rows = [row for row in rows if row.get("ok")]
    lines = [
        "BAI War Lab — Batch Report",
        f"Scenario: {result.scenario}",
        f"Doctrine: {result.doctrine}",
        f"Personality: {result.personality}",
        f"Tuning: {result.tuning}",
        f"Seeds: {', '.join(str(seed) for seed in result.seed_policy.seeds)}",
        "",
    ]
    if result.aggregate is not None:
        lines.extend(
            [
                "[aggregate_summary]",
                f"Runs: {result.aggregate.total_runs}",
                f"OK Runs: {result.aggregate.ok_runs}",
                f"Failed Runs: {result.aggregate.failed_runs}",
                f"Failure Count: {result.aggregate.failure_count}",
                f"Success Rate: {result.aggregate.success_rate}",
            ]
        )
        core_metric_lines = _core_metric_lines(
            getattr(result.aggregate, "core_metrics", None) or summarize_core_metric_rows(successful_rows)
        )
        if core_metric_lines:
            lines.extend([""] + core_metric_lines)
        victory_proxy_lines = _victory_proxy_lines(
            getattr(result.aggregate, "victory_proxy", None) or summarize_outcome_rows(successful_rows)
        )
        if victory_proxy_lines:
            lines.extend([""] + victory_proxy_lines)
        if result.aggregate.partial_failures:
            lines.append("Partial failures: yes")
        lines.append("Status counts:")
        for key, value in result.aggregate.status_counts.items():
            lines.append(f"  {key}: {value}")
        if result.aggregate.averages:
            lines.extend(["", "[aggregate_averages]"])
            for section, payload in result.aggregate.averages.items():
                lines.append(f"  {section}:")
                for key, value in payload.items():
                    lines.append(f"    {key}: {value}")
        if result.aggregate.mins:
            lines.extend(["", "[aggregate_mins]"])
            for section, payload in result.aggregate.mins.items():
                lines.append(f"  {section}:")
                for key, value in payload.items():
                    lines.append(f"    {key}: {value}")
        if result.aggregate.maxes:
            lines.extend(["", "[aggregate_maxes]"])
            for section, payload in result.aggregate.maxes.items():
                lines.append(f"  {section}:")
                for key, value in payload.items():
                    lines.append(f"    {key}: {value}")
        if result.aggregate.mean_summary:
            lines.extend(["", "[summary_averages]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.mean_summary.items())
        if result.aggregate.min_summary:
            lines.extend(["", "[summary_mins]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.min_summary.items())
        if result.aggregate.max_summary:
            lines.extend(["", "[summary_maxes]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.max_summary.items())
        if result.aggregate.mean_metrics:
            lines.extend(["", "[metric_averages]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.mean_metrics.items())
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _render_compare(result: Any) -> str:
    return render_comparison_report(result)


def _render_suite(result: Any) -> str:
    suite_summary = dict(getattr(result, "suite_summary", {}) or {})
    jobs = list(getattr(result, "jobs", []) or [])
    rows = [run_result_to_row(run) for run in list(getattr(result, "runs", []) or [])]
    successful_rows = [row for row in rows if row.get("ok")]
    lines = [
        "BAI War Lab — Suite Report",
        f"Suite: {result.suite_name}",
        f"Jobs: {suite_summary.get('job_count', len(jobs))}",
        f"Flattened runs: {len(result.runs)}",
        "",
    ]
    if suite_summary:
        lines.extend(
            [
                "[suite_summary]",
                f"Description: {suite_summary.get('description') or '-'}",
                f"Scheduled runs: {suite_summary.get('scheduled_runs', 0)}",
                f"Completed runs: {suite_summary.get('completed_runs', 0)}",
                f"Failed runs: {suite_summary.get('failed_runs', 0)}",
                f"OK jobs: {suite_summary.get('ok_jobs', 0)}",
                f"Failed jobs: {suite_summary.get('failed_jobs', 0)}",
                f"Partial failures: {'yes' if suite_summary.get('partial_failures') else 'no'}",
            ]
        )
        evaluation_notes = list(suite_summary.get("evaluation_notes", []) or [])
        if evaluation_notes:
            lines.extend(["", "[evaluation_notes]"])
            lines.extend(f"  - {note}" for note in evaluation_notes)
    if result.aggregate is not None:
        lines.extend(
            [
                "",
                "[aggregate_summary]",
                f"Runs: {result.aggregate.total_runs}",
                f"OK: {result.aggregate.ok_runs}",
                f"Failed: {result.aggregate.failed_runs}",
                f"Failure Count: {result.aggregate.failure_count}",
                f"Success Rate: {result.aggregate.success_rate}",
            ]
        )
        core_metric_lines = _core_metric_lines(
            getattr(result.aggregate, "core_metrics", None) or summarize_core_metric_rows(successful_rows)
        )
        if core_metric_lines:
            lines.extend([""] + core_metric_lines)
        victory_proxy_lines = _victory_proxy_lines(
            getattr(result.aggregate, "victory_proxy", None) or summarize_outcome_rows(successful_rows)
        )
        if victory_proxy_lines:
            lines.extend([""] + victory_proxy_lines)
        if result.aggregate.mean_summary:
            lines.extend(["", "[summary_averages]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.mean_summary.items())
        if result.aggregate.mean_metrics:
            lines.extend(["", "[metric_averages]"])
            lines.extend(f"  {key}: {value}" for key, value in result.aggregate.mean_metrics.items())
    if jobs:
        lines.extend(["", "[suite_jobs]"])
        for job in jobs:
            aggregate = dict(job.get("aggregate", {}) or {})
            seed_policy = dict(job.get("seed_policy", {}) or {})
            lines.append(
                "  "
                f"{job.get('id')}: scenario={job.get('scenario')} "
                f"goal={job.get('evaluation_goal') or '-'} "
                f"runs={seed_policy.get('count', 0)} "
                f"ok={aggregate.get('ok_runs', 0)} "
                f"failed={aggregate.get('failed_runs', 0)}"
            )
            metric_focus = list(job.get("metric_focus", []) or [])
            metric_thresholds = dict(job.get("metric_thresholds", {}) or {})
            if metric_focus:
                lines.append(f"    metric_focus: {', '.join(metric_focus)}")
            if metric_thresholds:
                lines.append(f"    thresholds: {metric_thresholds}")
            if job.get("notes"):
                lines.append(f"    notes: {job.get('notes')}")
            if aggregate.get("mean_metrics"):
                lines.append(f"    mean_metrics: {aggregate.get('mean_metrics')}")
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)
