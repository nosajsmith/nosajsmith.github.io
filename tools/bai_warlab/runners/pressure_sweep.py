from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..config_loader import ConfigLoader
from ..models import PressureSweepResult, RunRequest, RunResult
from ..reports.batch_dashboard import build_batch_dashboard_payload
from .single_run import execute_single_run


PRESSURE_SWEEP_FIELDS: Dict[str, str] = {
    "attack_supply_floor": "run",
    "attack_readiness_floor": "run",
    "rest_supply_floor": "run",
    "rest_fatigue_floor": "run",
    "caution_bias": "axis",
    "reserve_preservation_bias": "axis",
    "reserve_commitment": "axis",
    "risk_tolerance": "axis",
    "logistics_emphasis": "axis",
}


def _row_summary(run: RunResult) -> Dict[str, Any]:
    score = dict((run.metrics or {}).get("score_visibility", {}).get("final", {}) or {})
    pressure = dict((run.metrics or {}).get("pressure_visibility", {}).get("peak", {}) or {})
    objective = dict((run.metrics or {}).get("objective_visibility", {}) or {})
    return {
        "result": str((run.summary or {}).get("result") or ""),
        "score_margin_allied": score.get("score_margin_allied"),
        "pressure_peak_score": pressure.get("pressure_score"),
        "objective_change_count": len(list(objective.get("changes") or [])),
    }


def execute_pressure_sweep(
    *,
    scenario: str,
    scenario_dir: str,
    doctrine: str,
    personality: str,
    tuning: str,
    parameter: str,
    values: Iterable[Any],
    loader: ConfigLoader,
    seed: int = 0,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
) -> PressureSweepResult:
    if parameter not in PRESSURE_SWEEP_FIELDS:
        raise ValueError(
            f"Unsupported pressure sweep parameter: {parameter}. "
            f"Allowed: {', '.join(sorted(PRESSURE_SWEEP_FIELDS))}."
        )

    target = PRESSURE_SWEEP_FIELDS[parameter]
    value_list = list(values)
    runs: List[RunResult] = []
    warnings: List[str] = []

    for value in value_list:
        axis_overrides: Dict[str, Any] = {}
        run_overrides: Dict[str, Any] = {}
        if target == "axis":
            axis_overrides[parameter] = value
        else:
            run_overrides[parameter] = value
        run = execute_single_run(
            RunRequest(
                scenario=scenario,
                scenario_dir=scenario_dir,
                doctrine=doctrine,
                personality=personality,
                tuning=tuning,
                seed=int(seed),
                max_steps=max_steps,
                dt_hours=dt_hours,
                stop_on_terminal=stop_on_terminal,
                variant_label=f"{parameter}={value}",
                variant_id=f"{parameter}:{value}",
                variant_name=f"{parameter}={value}",
                axis_overrides=axis_overrides,
                run_overrides=run_overrides,
            ),
            loader,
        )
        runs.append(run)
        if not run.ok:
            warnings.append(f"{parameter}={value} failed: {run.error or run.summary.get('terminal_status', 'unknown')}")

    summaries = [_row_summary(run) for run in runs]
    baseline = summaries[0] if summaries else {}
    points: List[Dict[str, Any]] = []
    for value, run, summary in zip(value_list, runs, summaries):
        points.append(
            {
                "value": value,
                "ok": run.ok,
                **summary,
                "delta_vs_first": {
                    "score_margin_allied": None
                    if baseline.get("score_margin_allied") is None or summary.get("score_margin_allied") is None
                    else round(float(summary["score_margin_allied"]) - float(baseline["score_margin_allied"]), 3),
                    "pressure_peak_score": None
                    if baseline.get("pressure_peak_score") is None or summary.get("pressure_peak_score") is None
                    else round(float(summary["pressure_peak_score"]) - float(baseline["pressure_peak_score"]), 3),
                    "objective_change_count": None
                    if baseline.get("objective_change_count") is None or summary.get("objective_change_count") is None
                    else int(summary["objective_change_count"]) - int(baseline["objective_change_count"]),
                },
            }
        )

    score_points = [point for point in points if point.get("score_margin_allied") is not None]
    best_score = max(score_points, key=lambda item: float(item["score_margin_allied"]), default=None)
    pressure_points = [point for point in points if point.get("delta_vs_first", {}).get("pressure_peak_score") is not None]
    largest_pressure_delta = max(
        pressure_points,
        key=lambda item: abs(float(item["delta_vs_first"]["pressure_peak_score"])),
        default=None,
    )
    comparison = {
        "parameter": parameter,
        "target": target,
        "points": points,
        "best_score": {
            "value": best_score["value"],
            "score_margin_allied": best_score["score_margin_allied"],
        }
        if best_score
        else None,
        "largest_pressure_delta": {
            "value": largest_pressure_delta["value"],
            "delta_vs_first": largest_pressure_delta["delta_vs_first"]["pressure_peak_score"],
        }
        if largest_pressure_delta
        else None,
        "dashboard": build_batch_dashboard_payload(runs),
    }

    return PressureSweepResult(
        ok=any(run.ok for run in runs),
        command="pressure_sweep",
        scenario=scenario,
        scenario_dir=scenario_dir,
        parameter=parameter,
        values=value_list,
        doctrine=doctrine,
        personality=personality,
        tuning=tuning,
        runs=runs,
        comparison=comparison,
        warnings=warnings,
    )


__all__ = ["PRESSURE_SWEEP_FIELDS", "execute_pressure_sweep"]
