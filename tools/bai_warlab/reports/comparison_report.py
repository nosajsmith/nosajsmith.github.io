from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _joined(items: Iterable[str]) -> str:
    values = [str(item) for item in items if str(item)]
    return ", ".join(values) if values else "none"


def _overall_outcome(comparison: Dict[str, Any]) -> Tuple[str, str]:
    left_wins = len(list(comparison.get("left_beats_right", []) or []))
    right_wins = len(list(comparison.get("right_beats_left", []) or []))
    paired = int(comparison.get("paired_seed_count") or 0)
    if paired <= 0:
        return "inconclusive", "No matched successful pairs."
    if left_wins > right_wins:
        return "left", f"A leads {left_wins} to {right_wins} on core metrics."
    if right_wins > left_wins:
        return "right", f"B leads {right_wins} to {left_wins} on core metrics."
    return "mixed", f"Split decision with {left_wins} metrics each and {len(list(comparison.get('ties', []) or []))} ties."


def _left_advantage(metric: Dict[str, Any]) -> float | None:
    delta = metric.get("delta_right_minus_left")
    if delta is None:
        return None
    value = float(delta)
    return -value if bool(metric.get("higher_is_better")) else value


def _signed_text(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.3f}"


def _metric_lines(core_metrics: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for metric_name, payload in core_metrics.items():
        winner = str(payload.get("winner") or "unavailable")
        edge = "A" if winner == "left" else "B" if winner == "right" else "tie" if winner == "tie" else "n/a"
        lines.append(
            "  "
            f"{payload.get('label')}: "
            f"A={payload.get('left_mean')} "
            f"B={payload.get('right_mean')} "
            f"delta(B-A)={_signed_text(payload.get('delta_right_minus_left'))} "
            f"edge={edge}"
        )
    return lines


def _best_and_worst_callouts(core_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    left_edges: List[Tuple[str, Dict[str, Any], float]] = []
    right_edges: List[Tuple[str, Dict[str, Any], float]] = []

    for metric_name, payload in core_metrics.items():
        left_edge = _left_advantage(payload)
        if left_edge is None:
            continue
        if left_edge > 0:
            left_edges.append((metric_name, payload, left_edge))
        elif left_edge < 0:
            right_edges.append((metric_name, payload, abs(left_edge)))

    left_best = max(left_edges, key=lambda item: item[2], default=None)
    right_best = max(right_edges, key=lambda item: item[2], default=None)

    largest_gap_candidates = left_edges + right_edges
    largest_gap = max(largest_gap_candidates, key=lambda item: item[2], default=None)

    return {
        "left_best": left_best,
        "right_best": right_best,
        "largest_gap": largest_gap,
    }


def _warning_lines(comparison: Dict[str, Any], core_metrics: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    if comparison.get("partial_failures"):
        lines.append(
            f"  Partial failures reduced matched pairs to {comparison.get('paired_seed_count', 0)} of {comparison.get('scheduled_seed_count', 0)}."
        )
    if comparison.get("seed_mismatch_count"):
        lines.append(f"  Seed mismatch count: {comparison.get('seed_mismatch_count')}")

    left_losses = list(comparison.get("right_beats_left", []) or [])
    right_losses = list(comparison.get("left_beats_right", []) or [])
    if left_losses:
        lines.append("  A regression risks:")
        for metric_name in left_losses:
            payload = core_metrics.get(metric_name, {})
            lines.append(f"    {payload.get('label', metric_name)} ({_signed_text(payload.get('delta_right_minus_left'))} B-A)")
    if right_losses:
        lines.append("  B regression risks:")
        for metric_name in right_losses:
            payload = core_metrics.get(metric_name, {})
            lines.append(f"    {payload.get('label', metric_name)} ({_signed_text(payload.get('delta_right_minus_left'))} B-A)")
    return lines


def render_comparison_report(result: Any) -> str:
    comparison = dict(getattr(result, "comparison", {}) or {})
    core_metrics = dict(comparison.get("core_metrics", {}) or {})
    outcome, rationale = _overall_outcome(comparison)
    callouts = _best_and_worst_callouts(core_metrics)

    outcome_text = {
        "left": "Winner: A",
        "right": "Winner: B",
        "mixed": "Result: Mixed",
        "inconclusive": "Result: Inconclusive",
    }.get(outcome, "Result: Mixed")

    lines = [
        "BAI War Lab — Compare Report",
        f"Scenario: {getattr(result, 'scenario', '')}",
        f"A Variant: {getattr(result, 'left_label', '')}",
        f"B Variant: {getattr(result, 'right_label', '')}",
        f"Seeds: {', '.join(str(seed) for seed in getattr(getattr(result, 'seed_policy', None), 'seeds', []) or [])}",
        "",
        "[decision]",
        outcome_text,
        f"Rationale: {rationale}",
        f"Matched successful pairs: {comparison.get('paired_seed_count', 0)} / {comparison.get('scheduled_seed_count', 0)}",
        f"A wins: {_joined(list(comparison.get('left_beats_right', []) or []))}",
        f"B wins: {_joined(list(comparison.get('right_beats_left', []) or []))}",
        f"Ties: {_joined(list(comparison.get('ties', []) or []))}",
    ]

    left_aggregate = dict(comparison.get("left_aggregate", {}) or {})
    right_aggregate = dict(comparison.get("right_aggregate", {}) or {})
    if left_aggregate or right_aggregate:
        lines.extend(["", "[side_by_side_summary]"])
        if left_aggregate:
            lines.append(
                "  "
                f"A: ok_runs={left_aggregate.get('ok_runs')} "
                f"failed_runs={left_aggregate.get('failed_runs')} "
                f"failure_count={left_aggregate.get('failure_count')}"
            )
        if right_aggregate:
            lines.append(
                "  "
                f"B: ok_runs={right_aggregate.get('ok_runs')} "
                f"failed_runs={right_aggregate.get('failed_runs')} "
                f"failure_count={right_aggregate.get('failure_count')}"
            )

    if core_metrics:
        lines.extend(["", "[key_deltas]"])
        lines.extend(_metric_lines(core_metrics))

    lines.extend(["", "[callouts]"])
    left_best = callouts.get("left_best")
    right_best = callouts.get("right_best")
    largest_gap = callouts.get("largest_gap")
    if left_best:
        lines.append(f"  Best A edge: {left_best[1].get('label')} ({_signed_text(left_best[1].get('delta_right_minus_left'))} B-A)")
    else:
        lines.append("  Best A edge: none")
    if right_best:
        lines.append(f"  Best B edge: {right_best[1].get('label')} ({_signed_text(right_best[1].get('delta_right_minus_left'))} B-A)")
    else:
        lines.append("  Best B edge: none")
    if largest_gap:
        winner = "A" if largest_gap == left_best else "B" if largest_gap == right_best else "mixed"
        lines.append(f"  Largest swing: {largest_gap[1].get('label')} ({winner})")

    warning_lines = _warning_lines(comparison, core_metrics)
    if warning_lines:
        lines.extend(["", "[regression_warnings]"])
        lines.extend(warning_lines)

    if getattr(result, "warnings", None):
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in list(getattr(result, "warnings", []) or []))
    return "\n".join(lines)

def render_variant_comparison_report(result: Any) -> str:
    comparison = dict(getattr(result, "comparison", {}) or {})
    variants = list(comparison.get("variants") or [])
    lines = [
        "BAI War Lab — Variant Comparison Report",
        f"Scenario: {getattr(result, 'scenario', '')}",
        f"Compared {len(variants)} variants on scenario {getattr(result, 'scenario', '')}.",
        "",
        "[variants]",
    ]
    for variant in variants:
        lines.append(
            "  "
            f"{variant.get('variant_name') or variant.get('variant_id')}: "
            f"score={dict(variant.get('final_score') or {}).get('margin_allied')} "
            f"pressure_peak={dict(variant.get('pressure_summary') or {}).get('peak')} "
            f"objectives_secured={dict(variant.get('objective_summary') or {}).get('secured')}"
        )
    if comparison.get("best_score"):
        lines.extend(["", f"best score: {comparison.get('best_score')}"])
    if comparison.get("largest_pressure_delta"):
        lines.append(f"largest pressure delta: {comparison.get('largest_pressure_delta')}")
    if comparison.get("first_objective_divergence"):
        lines.append(f"first objective divergence: {comparison.get('first_objective_divergence')}")
    if getattr(result, "warnings", None):
        lines.extend(["", "[warnings]"])
        lines.extend(f"  - {warning}" for warning in list(getattr(result, "warnings", []) or []))
    return "\n".join(lines)


__all__ = ["render_comparison_report", "render_variant_comparison_report"]
