from __future__ import annotations

from typing import Any, Dict, List


def _lines_for_metrics(metrics: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for category, payload in metrics.items():
        lines.append(f"[{category}]")
        for key, value in payload.items():
            lines.append(f"  {key}: {value}")
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
    if result.metrics:
        lines.extend(_lines_for_metrics(result.metrics))
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    if result.error:
        lines.extend(["", f"Error: {result.error}"])
    return "\n".join(lines)


def _render_batch(result: Any) -> str:
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
        lines.append(f"Runs: {result.aggregate.total_runs} | OK: {result.aggregate.ok_runs} | Failed: {result.aggregate.failed_runs}")
        if result.aggregate.partial_failures:
            lines.append("Partial failures: yes")
        lines.append("Status counts:")
        for key, value in result.aggregate.status_counts.items():
            lines.append(f"  {key}: {value}")
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _render_compare(result: Any) -> str:
    lines = [
        "BAI War Lab — Compare Report",
        f"Scenario: {result.scenario}",
        f"Left: {result.left_label}",
        f"Right: {result.right_label}",
        f"Seeds: {', '.join(str(seed) for seed in result.seed_policy.seeds)}",
        "",
        "[comparison]",
    ]
    for key, value in result.comparison.items():
        lines.append(f"  {key}: {value}")
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _render_suite(result: Any) -> str:
    lines = [
        "BAI War Lab — Suite Report",
        f"Suite: {result.suite_name}",
        f"Cases: {len(result.runs)}",
        "",
    ]
    if result.aggregate is not None:
        lines.append(f"Runs: {result.aggregate.total_runs} | OK: {result.aggregate.ok_runs} | Failed: {result.aggregate.failed_runs}")
        if result.aggregate.partial_failures:
            lines.append("Partial failures: yes")
    if result.warnings:
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)

