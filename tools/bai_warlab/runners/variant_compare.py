from __future__ import annotations

from typing import Any, Dict, Iterable, List

from ..config_loader import ConfigLoader
from ..models import RunRequest, RunResult, VariantCompareResult, VariantSpec
from ..report_io import run_result_to_row
from ..reports.first_divergence import find_first_divergence
from .single_run import execute_single_run


def _coerce_variant_spec(value: VariantSpec | Dict[str, Any]) -> VariantSpec:
    if isinstance(value, VariantSpec):
        return value
    payload = dict(value or {})
    return VariantSpec(
        variant_id=str(payload.get("variant_id") or payload.get("id") or payload.get("label") or "").strip(),
        label=str(payload.get("label") or payload.get("name") or payload.get("variant_id") or "").strip(),
        doctrine=str(payload.get("doctrine") or "").strip(),
        personality=str(payload.get("personality") or "").strip(),
        tuning=str(payload.get("tuning") or "").strip(),
        axis_overrides=dict(payload.get("axis_overrides") or {}),
        run_overrides=dict(payload.get("run_overrides") or {}),
    )


def _variant_label(spec: VariantSpec) -> str:
    return spec.label or spec.variant_id or f"{spec.doctrine}/{spec.personality}/{spec.tuning}"


def _failed_variant_run(spec: VariantSpec, scenario: str, scenario_dir: str, seed: int, error: Exception | str) -> RunResult:
    message = str(error)
    return RunResult(
        ok=False,
        command="run",
        scenario=scenario,
        scenario_dir=scenario_dir,
        doctrine=spec.doctrine,
        personality=spec.personality,
        tuning=spec.tuning,
        seed=int(seed),
        max_steps=0,
        dt_hours=0,
        variant_label=_variant_label(spec),
        variant_id=spec.variant_id,
        variant_name=_variant_label(spec),
        error=message,
        warnings=["Variant compare captured a trial failure and continued."],
        summary={
            "execution_status": "failed",
            "terminal_status": "variant_compare_exception",
            "result": "error",
        },
        metrics={"outcome": {"available": False, "reason": "variant_compare_exception"}},
        resolved_profile={
            "variant_id": spec.variant_id,
            "variant_name": _variant_label(spec),
            "doctrine": spec.doctrine,
            "personality": spec.personality,
            "tuning": spec.tuning,
            "config_provenance": {
                "axis_overrides": dict(spec.axis_overrides or {}),
                "run_overrides": dict(spec.run_overrides or {}),
            },
        },
    )


def _variant_summary(run: RunResult) -> Dict[str, Any]:
    row = run_result_to_row(run)
    pressure = dict((run.metrics or {}).get("pressure_visibility", {}) or {})
    objective = dict((run.metrics or {}).get("objective_visibility", {}) or {})
    return {
        "variant_id": run.variant_id or row.get("variant_id") or run.variant_label,
        "variant_name": run.variant_name or row.get("variant_name") or run.variant_label,
        "doctrine": run.doctrine,
        "personality": run.personality,
        "tuning": run.tuning,
        "ok": run.ok,
        "result": row.get("result"),
        "final_score": {
            "allied": row.get("final_score_allied"),
            "axis": row.get("final_score_axis"),
            "margin_allied": row.get("final_score_margin"),
        },
        "pressure_summary": {
            "peak": row.get("pressure_peak_score"),
            "final": row.get("final_pressure_score"),
            "summary_lines": list(pressure.get("summary_lines") or []),
        },
        "objective_summary": {
            "secured": row.get("objectives_secured"),
            "changes": row.get("objective_change_count"),
            "summary_lines": list(objective.get("summary_lines") or []),
        },
        "manifest_path": run.manifest_path,
        "artifacts": list(run.artifacts or []),
    }


def _best_score(variant_summaries: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    available = [item for item in variant_summaries if item.get("ok") and item.get("final_score", {}).get("margin_allied") is not None]
    if not available:
        return None
    winner = max(available, key=lambda item: float(item["final_score"]["margin_allied"]))
    return {
        "variant_id": winner["variant_id"],
        "variant_name": winner["variant_name"],
        "score_margin_allied": winner["final_score"]["margin_allied"],
    }


def _largest_pressure_delta(variant_summaries: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    available = [item for item in variant_summaries if item.get("ok") and item.get("pressure_summary", {}).get("peak") is not None]
    if len(available) < 2:
        return None
    low = min(available, key=lambda item: float(item["pressure_summary"]["peak"]))
    high = max(available, key=lambda item: float(item["pressure_summary"]["peak"]))
    return {
        "from_variant_id": low["variant_id"],
        "to_variant_id": high["variant_id"],
        "delta": round(float(high["pressure_summary"]["peak"]) - float(low["pressure_summary"]["peak"]), 3),
        "low_peak": low["pressure_summary"]["peak"],
        "high_peak": high["pressure_summary"]["peak"],
    }


def _first_objective_divergence(runs: List[RunResult]) -> Dict[str, Any] | None:
    successful = [run for run in runs if run.ok]
    if len(successful) < 2:
        return None
    baseline = successful[0]
    candidates: List[Dict[str, Any]] = []
    for run in successful[1:]:
        divergence = find_first_divergence(baseline, run)
        if not divergence.get("comparable") or divergence.get("identical"):
            continue
        candidates.append(divergence)
    if not candidates:
        return None

    def _key(item: Dict[str, Any]) -> tuple[int, int, str]:
        day = int(item.get("day") if item.get("day") is not None else 10**9)
        tick = int(item.get("tick") if item.get("tick") is not None else 10**9)
        phase = "0" if str(item.get("phase")) == "objective" else "1"
        return (day, tick, phase)

    return min(candidates, key=_key)


def execute_variant_compare(
    *,
    scenario: str,
    scenario_dir: str,
    variants: Iterable[VariantSpec | Dict[str, Any]],
    loader: ConfigLoader,
    seed: int = 0,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
) -> VariantCompareResult:
    specs = [_coerce_variant_spec(item) for item in variants]
    runs: List[RunResult] = []
    warnings: List[str] = []

    for spec in specs:
        try:
            run = execute_single_run(
                RunRequest(
                    scenario=scenario,
                    scenario_dir=scenario_dir,
                    doctrine=spec.doctrine,
                    personality=spec.personality,
                    tuning=spec.tuning,
                    seed=int(seed),
                    max_steps=max_steps,
                    dt_hours=dt_hours,
                    stop_on_terminal=stop_on_terminal,
                    variant_label=_variant_label(spec),
                    variant_id=spec.variant_id or _variant_label(spec),
                    variant_name=_variant_label(spec),
                    axis_overrides=dict(spec.axis_overrides or {}),
                    run_overrides=dict(spec.run_overrides or {}),
                ),
                loader,
            )
        except Exception as exc:
            run = _failed_variant_run(spec, scenario, scenario_dir, int(seed), exc)
        runs.append(run)
        if not run.ok:
            warnings.append(f"{_variant_label(spec)} failed: {run.error or run.summary.get('terminal_status', 'unknown')}")

    variant_summaries = [_variant_summary(run) for run in runs]
    comparison = {
        "variant_count": len(specs),
        "variants": variant_summaries,
        "best_score": _best_score(variant_summaries),
        "largest_pressure_delta": _largest_pressure_delta(variant_summaries),
        "first_objective_divergence": _first_objective_divergence(runs),
    }
    if comparison["first_objective_divergence"] is None and len([run for run in runs if run.ok]) >= 2:
        warnings.append("No objective divergence found across successful variants.")

    return VariantCompareResult(
        ok=any(run.ok for run in runs),
        command="variant_compare",
        scenario=scenario,
        scenario_dir=scenario_dir,
        variants=specs,
        runs=runs,
        comparison=comparison,
        warnings=warnings,
    )


__all__ = ["execute_variant_compare"]
