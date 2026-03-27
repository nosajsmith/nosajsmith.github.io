from __future__ import annotations

from typing import Any


def _joined(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _signed_text(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.3f}"


def _overall_status(comparison: Any) -> str:
    regressed = list(comparison.get("regressed", []) or [])
    improved = list(comparison.get("improved", []) or [])
    if regressed and improved:
        return "mixed"
    if regressed:
        return "regressed"
    if improved:
        return "improved"
    if list(comparison.get("neutral", []) or []):
        return "neutral"
    return "inconclusive"


def _largest_by_category(metrics: dict[str, Any], category: str) -> tuple[str, Any] | None:
    candidates = []
    for metric_name, payload in metrics.items():
        if payload.get("category") != category:
            continue
        delta = payload.get("delta")
        if delta is None:
            continue
        candidates.append((metric_name, payload, abs(float(delta))))
    if not candidates:
        return None
    metric_name, payload, _ = max(candidates, key=lambda item: item[2])
    return metric_name, payload


def render_regression_report(comparison: Any | None) -> str:
    if not comparison:
        return "No regression comparison requested."
    metrics = dict(comparison.get("metrics", {}) or {})
    overall = _overall_status(comparison)
    best_improvement = _largest_by_category(metrics, "improved")
    worst_regression = _largest_by_category(metrics, "regressed")
    lines = [
        "BAI War Lab — Baseline Comparison",
        f"Baseline: {comparison.get('baseline_name') or 'unnamed'}",
        f"Baseline Command: {comparison.get('baseline_command') or 'unknown'}",
        f"Current Command: {comparison.get('current_command') or 'unknown'}",
        "",
        "[decision]",
        f"Result: {overall}",
        f"Improved: {_joined(list(comparison.get('improved', []) or []))}",
        f"Regressed: {_joined(list(comparison.get('regressed', []) or []))}",
        f"Neutral: {_joined(list(comparison.get('neutral', []) or []))}",
        f"Unavailable: {_joined(list(comparison.get('unavailable', []) or []))}",
    ]
    lines.extend(["", "[callouts]"])
    if best_improvement:
        lines.append(
            "  "
            f"Best improvement: {best_improvement[1].get('label', best_improvement[0])} "
            f"({_signed_text(best_improvement[1].get('delta'))})"
        )
    else:
        lines.append("  Best improvement: none")
    if worst_regression:
        lines.append(
            "  "
            f"Worst regression: {worst_regression[1].get('label', worst_regression[0])} "
            f"({_signed_text(worst_regression[1].get('delta'))})"
        )
    else:
        lines.append("  Worst regression: none")
    if metrics:
        lines.extend(["", "[metrics]"])
        for metric_name, payload in metrics.items():
            lines.append(
                "  "
                f"{metric_name}: status={payload.get('category')} "
                f"baseline={payload.get('baseline')} "
                f"current={payload.get('current')} "
                f"delta={_signed_text(payload.get('delta'))} "
                f"threshold={payload.get('threshold')}"
            )
    regressed = list(comparison.get("regressed", []) or [])
    if regressed:
        lines.extend(["", "[regression_warnings]"])
        for metric_name in regressed:
            payload = metrics.get(metric_name, {})
            lines.append(
                "  "
                f"{payload.get('label', metric_name)} regressed by {_signed_text(payload.get('delta'))} "
                f"against threshold {payload.get('threshold')}"
            )
    if comparison.get("job_comparisons"):
        lines.extend(["", "[job_comparisons]"])
        for job_id, payload in comparison["job_comparisons"].items():
            lines.append(
                "  "
                f"{job_id}: scenario={payload.get('scenario')} "
                f"goal={payload.get('evaluation_goal') or '-'} "
                f"improved={_joined(list(payload.get('improved', []) or []))} "
                f"regressed={_joined(list(payload.get('regressed', []) or []))}"
            )
    return "\n".join(lines)
