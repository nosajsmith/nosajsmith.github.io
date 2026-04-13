from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..config_loader import ConfigLoader
from ..manifest import build_manifest_record, write_manifest
from ..models import RunRequest, RunResult, SweepResult, VariantSpec
from ..report_io import (
    ensure_output_dir,
    run_result_to_row,
    slugify,
    write_json,
    write_report_txt,
    write_results_csv,
)
from ..reports.batch_dashboard import build_batch_dashboard_payload, dashboard_row_for_run, render_batch_dashboard_markdown
from ..reports.summary_report import render_report
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


def _failed_run(spec: VariantSpec, scenario: str, scenario_dir: str, seed: int, error: Exception | str) -> RunResult:
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
        variant_id=spec.variant_id or _variant_label(spec),
        variant_name=_variant_label(spec),
        error=message,
        warnings=["Sweep runner captured a trial failure and continued."],
        summary={
            "execution_status": "failed",
            "terminal_status": "sweep_exception",
            "result": "error",
        },
        metrics={"outcome": {"available": False, "reason": "sweep_exception"}},
        resolved_profile={
            "variant_id": spec.variant_id or _variant_label(spec),
            "variant_name": _variant_label(spec),
            "doctrine": spec.doctrine,
            "personality": spec.personality,
            "tuning": spec.tuning,
        },
    )


def _write_run_bundle(run: RunResult, run_dir: Path, loader: ConfigLoader) -> RunResult:
    ensure_output_dir(run_dir)
    run.output_dir = str(run_dir.resolve())
    summary_path = write_json(run_dir / "summary.json", run)
    write_results_csv(run_dir / "results.csv", [run_result_to_row(run)])
    write_report_txt(run_dir / "report.txt", render_report(run))
    manifest = build_manifest_record(
        command="run",
        output_dir=run_dir,
        scenario=run.scenario,
        doctrine=run.doctrine,
        personality=run.personality,
        tuning=run.tuning,
        seed_policy={"kind": "explicit", "seeds": [int(run.seed)]},
        command_line=f"sweep scenario={run.scenario} variant={run.variant_id or run.variant_label} seed={run.seed}",
        command_argv=["sweep", "--scenario", run.scenario, "--variant", run.variant_id or run.variant_label, "--seed", str(run.seed)],
        config_root=loader.config_root,
        loader=loader,
        result=run,
    )
    manifest_path = write_manifest(run_dir / "manifest.json", manifest)
    run.manifest_path = str(manifest_path.resolve())
    run.artifacts = [
        str(summary_path.resolve()),
        str((run_dir / "results.csv").resolve()),
        str((run_dir / "report.txt").resolve()),
        str(manifest_path.resolve()),
    ]
    return run


def execute_sweep(
    *,
    scenarios: Iterable[str],
    scenario_dir: str,
    variants: Iterable[VariantSpec | Dict[str, Any]],
    loader: ConfigLoader,
    seed: int = 0,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
    output_dir: str | Path | None = None,
) -> SweepResult:
    scenario_list = [str(item) for item in scenarios if str(item).strip()]
    specs = [_coerce_variant_spec(item) for item in variants]
    runs: List[RunResult] = []
    matrix: List[Dict[str, Any]] = []
    warnings: List[str] = []
    output_root = ensure_output_dir(output_dir) if output_dir else None

    for scenario in scenario_list:
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
                run = _failed_run(spec, scenario, scenario_dir, int(seed), exc)

            if output_root is not None:
                run_dir = output_root / slugify(scenario) / slugify(run.variant_id or run.variant_label or _variant_label(spec)) / f"seed-{int(seed):04d}"
                run = _write_run_bundle(run, run_dir, loader)
            runs.append(run)
            matrix.append(dashboard_row_for_run(run))
            if not run.ok:
                warnings.append(f"{scenario} / {_variant_label(spec)} failed: {run.error or run.summary.get('terminal_status', 'unknown')}")

    aggregate = {
        "total_runs": len(runs),
        "ok_runs": sum(1 for run in runs if run.ok),
        "failed_runs": sum(1 for run in runs if not run.ok),
        "scenario_count": len(scenario_list),
        "variant_count": len(specs),
    }
    dashboard = build_batch_dashboard_payload(runs)
    if output_root is not None:
        dashboard_json = write_json(output_root / "dashboard.json", dashboard)
        dashboard_md = write_report_txt(output_root / "dashboard.md", render_batch_dashboard_markdown(dashboard))
        dashboard["artifacts"] = {
            "dashboard_json": str(dashboard_json.resolve()),
            "dashboard_md": str(dashboard_md.resolve()),
        }

    return SweepResult(
        ok=aggregate["ok_runs"] > 0,
        command="sweep",
        scenario_dir=scenario_dir,
        scenarios=scenario_list,
        variants=specs,
        runs=runs,
        matrix=matrix,
        aggregate=aggregate,
        dashboard=dashboard,
        warnings=warnings,
        output_dir=str(output_root.resolve()) if output_root is not None else "",
    )


__all__ = ["execute_sweep"]
