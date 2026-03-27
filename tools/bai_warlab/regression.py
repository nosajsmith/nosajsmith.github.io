from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from .report_io import run_result_to_row


DEFAULT_REGRESSION_RULES: Dict[str, Dict[str, Any]] = {
    "result_score": {"label": "Result score", "higher_is_better": True, "threshold": 0.05},
    "vp_margin": {"label": "VP margin", "higher_is_better": True, "threshold": 0.5},
    "casualty_ratio": {"label": "Casualty ratio", "higher_is_better": True, "threshold": 0.05},
    "objective_hold_duration": {"label": "Objective hold duration", "higher_is_better": True, "threshold": 0.5},
    "line_collapse_rate": {"label": "Line collapse rate", "higher_is_better": False, "threshold": 0.05},
    "low_supply_turns": {"label": "Low supply turns", "higher_is_better": False, "threshold": 0.5},
    "failure_rate": {"label": "Failure rate", "higher_is_better": False, "threshold": 0.02},
}


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _mean(values: Iterable[float]) -> float | None:
    series = list(values)
    if not series:
        return None
    return round(sum(series) / len(series), 3)


def _result_score(value: Any) -> float | None:
    normalized = str(value or "").strip().lower()
    if normalized == "win":
        return 1.0
    if normalized == "draw":
        return 0.5
    if normalized == "loss":
        return 0.0
    return None


def _runs_for_result(result: Any) -> List[Any]:
    if hasattr(result, "runs"):
        return list(getattr(result, "runs", []) or [])
    if hasattr(result, "summary") and hasattr(result, "scenario"):
        return [result]
    return []


def _metric_values(rows: List[Dict[str, Any]], metric_name: str) -> List[float]:
    if metric_name == "result_score":
        return [score for score in (_result_score(row.get("result")) for row in rows) if score is not None]
    if metric_name == "failure_rate":
        return [1.0 if row.get("failure_flag") else 0.0 for row in rows]
    return [value for value in (_to_float(row.get(metric_name)) for row in rows) if value is not None]


def _job_id_for_run(run: Any) -> str:
    summary = dict(getattr(run, "summary", {}) or {})
    job_id = str(summary.get("suite_job_id") or "").strip()
    if job_id:
        return job_id
    variant = str(getattr(run, "variant_label", "") or "")
    if ":" in variant:
        return variant.split(":", 1)[0]
    return ""


def resolve_regression_rules(metric_thresholds: Mapping[str, Any] | None = None) -> Dict[str, Dict[str, Any]]:
    rules = {name: dict(spec) for name, spec in DEFAULT_REGRESSION_RULES.items()}
    for name, override in dict(metric_thresholds or {}).items():
        rule = dict(rules.get(name, {"label": name.replace("_", " ").title(), "higher_is_better": True, "threshold": 0.0}))
        if isinstance(override, Mapping):
            if "label" in override:
                rule["label"] = str(override["label"])
            if "higher_is_better" in override:
                rule["higher_is_better"] = bool(override["higher_is_better"])
            if "threshold" in override:
                rule["threshold"] = float(override["threshold"])
        else:
            rule["threshold"] = float(override)
        rules[name] = rule
    return rules


def build_metric_snapshot(result: Any) -> Dict[str, Any]:
    runs = _runs_for_result(result)
    rows = [run_result_to_row(run) for run in runs]
    ok_runs = sum(1 for row in rows if bool(row.get("ok")))
    failed_runs = len(rows) - ok_runs
    metrics = {
        metric_name: _mean(_metric_values(rows, metric_name))
        for metric_name in DEFAULT_REGRESSION_RULES
    }

    snapshot: Dict[str, Any] = {
        "command": getattr(result, "command", "run"),
        "run_count": len(rows),
        "ok_runs": ok_runs,
        "failed_runs": failed_runs,
        "metrics": metrics,
    }

    if getattr(result, "command", "") == "suite":
        jobs = list(getattr(result, "jobs", []) or [])
        job_snapshots: Dict[str, Any] = {}
        for job in jobs:
            job_id = str(job.get("id") or "")
            if not job_id:
                continue
            job_runs = [run for run in runs if _job_id_for_run(run) == job_id]
            job_rows = [run_result_to_row(run) for run in job_runs]
            job_snapshots[job_id] = {
                "id": job_id,
                "scenario": job.get("scenario"),
                "evaluation_goal": job.get("evaluation_goal"),
                "run_count": len(job_rows),
                "ok_runs": sum(1 for row in job_rows if bool(row.get("ok"))),
                "failed_runs": sum(1 for row in job_rows if not bool(row.get("ok"))),
                "metrics": {
                    metric_name: _mean(_metric_values(job_rows, metric_name))
                    for metric_name in DEFAULT_REGRESSION_RULES
                },
            }
        snapshot["jobs"] = job_snapshots

    return snapshot


def _classify_metric(*, baseline_value: float | None, current_value: float | None, higher_is_better: bool, threshold: float) -> str:
    if baseline_value is None or current_value is None:
        return "unavailable"
    delta = round(current_value - baseline_value, 3)
    if abs(delta) <= float(threshold):
        return "neutral"
    if higher_is_better:
        return "improved" if delta > 0 else "regressed"
    return "improved" if delta < 0 else "regressed"


def compare_metric_snapshots(
    *,
    baseline_snapshot: Mapping[str, Any],
    current_snapshot: Mapping[str, Any],
    metric_thresholds: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    rules = resolve_regression_rules(metric_thresholds)
    baseline_metrics = dict(baseline_snapshot.get("metrics", {}) or {})
    current_metrics = dict(current_snapshot.get("metrics", {}) or {})

    metrics: Dict[str, Dict[str, Any]] = {}
    improved: List[str] = []
    regressed: List[str] = []
    neutral: List[str] = []
    unavailable: List[str] = []

    for metric_name, rule in rules.items():
        baseline_value = _to_float(baseline_metrics.get(metric_name))
        current_value = _to_float(current_metrics.get(metric_name))
        threshold = float(rule.get("threshold", 0.0))
        category = _classify_metric(
            baseline_value=baseline_value,
            current_value=current_value,
            higher_is_better=bool(rule.get("higher_is_better", True)),
            threshold=threshold,
        )
        delta = None
        if baseline_value is not None and current_value is not None:
            delta = round(current_value - baseline_value, 3)
        relative_change = None
        if baseline_value not in (None, 0) and delta is not None:
            relative_change = round((delta / baseline_value) * 100.0, 3)
        metrics[metric_name] = {
            "label": rule.get("label", metric_name),
            "higher_is_better": bool(rule.get("higher_is_better", True)),
            "threshold": threshold,
            "baseline": baseline_value,
            "current": current_value,
            "delta": delta,
            "relative_change_pct": relative_change,
            "category": category,
            "regression_flag": category == "regressed",
        }
        if category == "improved":
            improved.append(metric_name)
        elif category == "regressed":
            regressed.append(metric_name)
        elif category == "neutral":
            neutral.append(metric_name)
        else:
            unavailable.append(metric_name)

    return {
        "metrics": metrics,
        "improved": sorted(improved),
        "regressed": sorted(regressed),
        "neutral": sorted(neutral),
        "unavailable": sorted(unavailable),
        "regression_flags": sorted(regressed),
    }


def compare_against_baseline(
    *,
    baseline_record: Mapping[str, Any],
    current_result: Any,
    metric_thresholds: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    baseline_snapshot = dict(baseline_record.get("snapshot", {}) or {})
    current_snapshot = build_metric_snapshot(current_result)
    merged_thresholds = dict(baseline_record.get("thresholds", {}) or {})
    merged_thresholds.update(dict(metric_thresholds or {}))
    comparison = compare_metric_snapshots(
        baseline_snapshot=baseline_snapshot,
        current_snapshot=current_snapshot,
        metric_thresholds=merged_thresholds,
    )
    comparison.update(
        {
            "baseline_name": baseline_record.get("baseline_name"),
            "baseline_command": baseline_record.get("source", {}).get("command") if isinstance(baseline_record.get("source"), Mapping) else None,
            "current_command": getattr(current_result, "command", "run"),
            "thresholds": resolve_regression_rules(merged_thresholds),
            "baseline_snapshot": baseline_snapshot,
            "current_snapshot": current_snapshot,
        }
    )

    baseline_jobs = dict(baseline_snapshot.get("jobs", {}) or {})
    current_jobs = dict(current_snapshot.get("jobs", {}) or {})
    job_comparisons: Dict[str, Any] = {}
    for job_id in sorted(set(baseline_jobs) & set(current_jobs)):
        job_comparison = compare_metric_snapshots(
            baseline_snapshot=baseline_jobs[job_id],
            current_snapshot=current_jobs[job_id],
            metric_thresholds=merged_thresholds,
        )
        job_comparison.update(
            {
                "job_id": job_id,
                "scenario": current_jobs[job_id].get("scenario") or baseline_jobs[job_id].get("scenario"),
                "evaluation_goal": current_jobs[job_id].get("evaluation_goal") or baseline_jobs[job_id].get("evaluation_goal"),
            }
        )
        job_comparisons[job_id] = job_comparison
    if job_comparisons:
        comparison["job_comparisons"] = job_comparisons

    return comparison


__all__ = [
    "DEFAULT_REGRESSION_RULES",
    "build_metric_snapshot",
    "compare_against_baseline",
    "compare_metric_snapshots",
    "resolve_regression_rules",
]
