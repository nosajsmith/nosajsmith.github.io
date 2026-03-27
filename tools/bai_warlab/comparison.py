from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .report_io import run_result_to_row


CORE_METRICS: Dict[str, Dict[str, Any]] = {
    "result_score": {"higher_is_better": True, "label": "Result score"},
    "vp_margin": {"higher_is_better": True, "label": "VP margin"},
    "casualty_ratio": {"higher_is_better": True, "label": "Casualty ratio"},
    "objective_hold_duration": {"higher_is_better": True, "label": "Objective hold duration"},
    "low_supply_turns": {"higher_is_better": False, "label": "Low supply turns"},
}


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _result_score(value: Any) -> float | None:
    normalized = str(value or "").strip().lower()
    if normalized == "win":
        return 1.0
    if normalized == "draw":
        return 0.5
    if normalized == "loss":
        return 0.0
    return None


def _comparison_row(run: Any) -> Dict[str, Any]:
    row = run_result_to_row(run)
    return {
        "seed": row.get("seed"),
        "ok": bool(row.get("ok")),
        "result": row.get("result"),
        "result_score": _result_score(row.get("result")),
        "vp_margin": _to_float(row.get("vp_margin")),
        "casualty_ratio": _to_float(row.get("casualty_ratio")),
        "objective_hold_duration": _to_float(row.get("objective_hold_duration")),
        "low_supply_turns": _to_float(row.get("low_supply_turns")),
        "failure_flag": bool(row.get("failure_flag")),
        "failure_message": row.get("failure_message") or "",
    }


def _mean(values: Iterable[float]) -> float | None:
    series = list(values)
    if not series:
        return None
    return round(sum(series) / len(series), 3)


def _metric_summary(metric_name: str, pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> Dict[str, Any]:
    spec = CORE_METRICS[metric_name]
    left_values = [left[metric_name] for left, right in pairs if left.get(metric_name) is not None and right.get(metric_name) is not None]
    right_values = [right[metric_name] for left, right in pairs if left.get(metric_name) is not None and right.get(metric_name) is not None]
    left_mean = _mean(left_values)
    right_mean = _mean(right_values)

    if left_mean is None or right_mean is None:
        return {
            "label": spec["label"],
            "available": False,
            "higher_is_better": bool(spec["higher_is_better"]),
            "left_mean": None,
            "right_mean": None,
            "delta_right_minus_left": None,
            "winner": "unavailable",
        }

    delta = round(right_mean - left_mean, 3)
    if abs(delta) < 1e-9:
        winner = "tie"
    elif spec["higher_is_better"]:
        winner = "right" if delta > 0 else "left"
    else:
        winner = "right" if delta < 0 else "left"

    return {
        "label": spec["label"],
        "available": True,
        "higher_is_better": bool(spec["higher_is_better"]),
        "left_mean": left_mean,
        "right_mean": right_mean,
        "delta_right_minus_left": delta,
        "winner": winner,
    }


def build_comparison(*, left_runs: List[Any], right_runs: List[Any], left_label: str, right_label: str) -> Dict[str, Any]:
    pair_rows = []
    successful_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    seed_mismatches = 0

    for left_run, right_run in zip(left_runs, right_runs):
        left_row = _comparison_row(left_run)
        right_row = _comparison_row(right_run)
        same_seed = left_row["seed"] == right_row["seed"]
        if not same_seed:
            seed_mismatches += 1
        pair_rows.append(
            {
                "seed_left": left_row["seed"],
                "seed_right": right_row["seed"],
                "same_seed": same_seed,
                "left_ok": left_row["ok"],
                "right_ok": right_row["ok"],
                "left_result": left_row["result"],
                "right_result": right_row["result"],
                "left_failure": left_row["failure_message"],
                "right_failure": right_row["failure_message"],
            }
        )
        if same_seed and left_row["ok"] and right_row["ok"]:
            successful_pairs.append((left_row, right_row))

    core_metrics = {
        metric_name: _metric_summary(metric_name, successful_pairs)
        for metric_name in CORE_METRICS
    }
    left_beats_right = sorted(name for name, payload in core_metrics.items() if payload.get("winner") == "left")
    right_beats_left = sorted(name for name, payload in core_metrics.items() if payload.get("winner") == "right")
    ties = sorted(name for name, payload in core_metrics.items() if payload.get("winner") == "tie")

    return {
        "left_label": left_label,
        "right_label": right_label,
        "scheduled_seed_count": max(len(left_runs), len(right_runs)),
        "paired_seed_count": len(successful_pairs),
        "partial_failures": len(successful_pairs) != max(len(left_runs), len(right_runs)),
        "seed_mismatch_count": seed_mismatches,
        "core_metrics": core_metrics,
        "core_metric_deltas": {
            name: payload.get("delta_right_minus_left")
            for name, payload in core_metrics.items()
        },
        "left_beats_right": left_beats_right,
        "right_beats_left": right_beats_left,
        "ties": ties,
        "pair_results": pair_rows,
    }


__all__ = ["CORE_METRICS", "build_comparison"]
