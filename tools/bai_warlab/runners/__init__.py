from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List

from ..config_loader import ConfigLoader
from ..models import AggregateSummary, BatchResult, CompareResult, RunRequest, RunResult, SeedPolicy, SuiteCase, SuiteResult


FOUNDATION_WARNING = "Engine execution is not integrated in the BAI War Lab foundation build."

BENCHMARK_SUITES: Dict[str, List[SuiteCase]] = {
    "korea_core_v1": [
        SuiteCase(
            id="coastal_probe",
            scenario="korea_coastal_probe.json",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="offense_focus",
            seed=101,
        ),
        SuiteCase(
            id="river_defense",
            scenario="korea_river_defense.json",
            scenario_dir="scenarios",
            doctrine="korea_un_combined_arms",
            personality="historical",
            tuning="defense_focus",
            seed=202,
        ),
        SuiteCase(
            id="infiltration_push",
            scenario="korea_infiltration_push.json",
            scenario_dir="scenarios",
            doctrine="korea_chinese_mass_infiltration",
            personality="adaptive",
            tuning="default",
            seed=303,
        ),
    ]
}


def list_suite_names() -> List[str]:
    return sorted(BENCHMARK_SUITES.keys())


def resolve_seed_policy(*, count: int | None = None, seed_start: int = 0, seeds: Iterable[int] | None = None) -> SeedPolicy:
    if seeds is not None:
        seed_list = [int(value) for value in seeds]
        return SeedPolicy(kind="explicit", seeds=seed_list, count=len(seed_list))
    use_count = int(count or 1)
    seed_list = [int(seed_start) + index for index in range(use_count)]
    return SeedPolicy(kind="range", seeds=seed_list, base_seed=int(seed_start), count=use_count)


def _resolved_max_steps(request: RunRequest, merged_run: Dict[str, Any]) -> int:
    if request.max_steps is not None:
        return int(request.max_steps)
    if "max_steps" in merged_run:
        return int(merged_run["max_steps"])
    return 0


def _resolved_dt_hours(request: RunRequest, merged_run: Dict[str, Any]) -> int:
    if request.dt_hours is not None:
        return int(request.dt_hours)
    if "dt_hours" in merged_run:
        return int(merged_run["dt_hours"])
    return 0


def execute_single_run(request: RunRequest, loader: ConfigLoader) -> RunResult:
    try:
        resolved = loader.resolve_profiles(request.doctrine, request.personality, request.tuning)
    except Exception as exc:
        return RunResult(
            ok=False,
            command="run",
            scenario=request.scenario,
            scenario_dir=request.scenario_dir,
            doctrine=request.doctrine,
            personality=request.personality,
            tuning=request.tuning,
            seed=int(request.seed),
            max_steps=int(request.max_steps or 0),
            dt_hours=int(request.dt_hours or 0),
            variant_label=request.variant_label,
            error=str(exc),
            warnings=["Configuration resolution failed."],
            summary={
                "ok": False,
                "execution_status": "failed",
                "result": "error",
                "terminal_status": "config_error",
                "hours_elapsed": 0,
                "steps_completed": 0,
                "configured_max_steps": int(request.max_steps or 0),
                "configured_dt_hours": int(request.dt_hours or 0),
                "max_steps_exhausted": False,
            },
            metrics={},
        )

    max_steps = _resolved_max_steps(request, resolved.merged_run)
    dt_hours = _resolved_dt_hours(request, resolved.merged_run)
    warnings = list(resolved.warnings)
    warnings.append(FOUNDATION_WARNING)

    run_options = dict(resolved.merged_run)
    run_options.update(
        {
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "stop_on_terminal": bool(request.stop_on_terminal),
            "execution_mode": "foundation_stub",
        }
    )

    return RunResult(
        ok=True,
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
        warnings=warnings,
        applied_axis=dict(resolved.merged_axis),
        run_options=run_options,
        summary={
            "ok": True,
            "execution_status": "not_executed",
            "result": "not_executed",
            "terminal_status": "not_executed",
            "hours_elapsed": 0,
            "steps_completed": 0,
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "max_steps_exhausted": False,
        },
        metrics={
            "outcome": {
                "available": False,
                "reason": "engine_execution_not_integrated",
            }
        },
    )


def _mean_summary(runs: List[RunResult]) -> Dict[str, Any]:
    numeric: Dict[str, List[float]] = {}
    for run in runs:
        for key, value in (run.summary or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric.setdefault(key, []).append(float(value))
    return {key: round(sum(values) / len(values), 3) for key, values in numeric.items() if values}


def _summarize_runs(runs: List[RunResult]) -> AggregateSummary:
    successful = [run for run in runs if run.ok]
    status_counts = Counter(str((run.summary or {}).get("terminal_status", "unknown")) for run in runs)
    return AggregateSummary(
        total_runs=len(runs),
        ok_runs=len(successful),
        failed_runs=len(runs) - len(successful),
        partial_failures=bool(successful) and len(successful) != len(runs),
        status_counts=dict(status_counts),
        mean_summary=_mean_summary(successful),
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
    runs = [
        execute_single_run(
            RunRequest(
                scenario=scenario,
                scenario_dir=scenario_dir,
                doctrine=doctrine,
                personality=personality,
                tuning=tuning,
                seed=seed,
                max_steps=max_steps,
                dt_hours=dt_hours,
                stop_on_terminal=stop_on_terminal,
            ),
            loader,
        )
        for seed in seed_policy.seeds
    ]
    aggregate = _summarize_runs(runs)
    warnings = []
    if aggregate.partial_failures:
        warnings.append(f"Partial failure: {aggregate.failed_runs} of {aggregate.total_runs} runs failed.")
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


def execute_compare_run(
    *,
    scenario: str,
    scenario_dir: str,
    left: Dict[str, str],
    right: Dict[str, str],
    seed_policy: SeedPolicy,
    loader: ConfigLoader,
    max_steps: int | None = None,
    dt_hours: int | None = None,
    stop_on_terminal: bool = True,
) -> CompareResult:
    left_runs: List[RunResult] = []
    right_runs: List[RunResult] = []
    warnings: List[str] = []
    for seed in seed_policy.seeds:
        left_run = execute_single_run(
            RunRequest(
                scenario=scenario,
                scenario_dir=scenario_dir,
                doctrine=left["doctrine"],
                personality=left["personality"],
                tuning=left["tuning"],
                seed=seed,
                max_steps=max_steps,
                dt_hours=dt_hours,
                stop_on_terminal=stop_on_terminal,
                variant_label="left",
            ),
            loader,
        )
        right_run = execute_single_run(
            RunRequest(
                scenario=scenario,
                scenario_dir=scenario_dir,
                doctrine=right["doctrine"],
                personality=right["personality"],
                tuning=right["tuning"],
                seed=seed,
                max_steps=max_steps,
                dt_hours=dt_hours,
                stop_on_terminal=stop_on_terminal,
                variant_label="right",
            ),
            loader,
        )
        left_runs.append(left_run)
        right_runs.append(right_run)
        if not (left_run.ok and right_run.ok):
            warnings.append(f"Seed {seed}: left_ok={left_run.ok} right_ok={right_run.ok}")

    paired = [(left_run, right_run) for left_run, right_run in zip(left_runs, right_runs) if left_run.ok and right_run.ok]
    left_mean = _mean_summary([left_run for left_run, _ in paired])
    right_mean = _mean_summary([right_run for _, right_run in paired])
    delta = {}
    for key in sorted(set(left_mean) & set(right_mean)):
        delta[key] = round(right_mean[key] - left_mean[key], 3)

    return CompareResult(
        ok=len(paired) > 0,
        command="compare",
        scenario=scenario,
        scenario_dir=scenario_dir,
        seed_policy=seed_policy,
        left_label=f"{left['doctrine']} / {left['personality']} / {left['tuning']}",
        right_label=f"{right['doctrine']} / {right['personality']} / {right['tuning']}",
        left_runs=left_runs,
        right_runs=right_runs,
        comparison={
            "paired_seed_count": len(paired),
            "partial_failures": len(paired) != len(seed_policy.seeds),
            "left_mean": left_mean,
            "right_mean": right_mean,
            "delta_right_minus_left": delta,
        },
        warnings=warnings,
    )


def execute_suite_run(*, suite_name: str, loader: ConfigLoader) -> SuiteResult:
    cases = BENCHMARK_SUITES.get(suite_name)
    if cases is None:
        raise KeyError(f"Unknown War Lab suite: {suite_name}")
    runs = [
        execute_single_run(
            RunRequest(
                scenario=case.scenario,
                scenario_dir=case.scenario_dir,
                doctrine=case.doctrine,
                personality=case.personality,
                tuning=case.tuning,
                seed=case.seed,
                max_steps=case.max_steps,
                dt_hours=case.dt_hours,
                variant_label=case.id,
            ),
            loader,
        )
        for case in cases
    ]
    aggregate = _summarize_runs(runs)
    warnings = []
    if aggregate.partial_failures:
        warnings.append(f"Partial failure: {aggregate.failed_runs} of {aggregate.total_runs} suite cases failed.")
    return SuiteResult(
        ok=aggregate.ok_runs > 0,
        command="suite",
        suite_name=suite_name,
        runs=runs,
        aggregate=aggregate,
        warnings=warnings,
    )

