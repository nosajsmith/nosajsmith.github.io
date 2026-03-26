from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List

from ..config_loader import ConfigLoader
from ..models import AggregateSummary, BatchResult, CompareResult, RunRequest, RunResult, SeedPolicy, SuiteCase, SuiteResult
from .single_run import execute_single_run


BENCHMARK_SUITES: Dict[str, List[SuiteCase]] = {
    "korea_core_v1": [
        SuiteCase(
            id="mini_baseline",
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="offense_focus",
            seed=101,
        ),
        SuiteCase(
            id="historical_pressure",
            scenario="gc_1942_historical",
            scenario_dir="scenarios",
            doctrine="korea_un_combined_arms",
            personality="historical",
            tuning="default",
            seed=202,
        ),
        SuiteCase(
            id="adaptive_return",
            scenario="mini_gc_1942",
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


__all__ = [
    "BENCHMARK_SUITES",
    "execute_batch_run",
    "execute_compare_run",
    "execute_single_run",
    "execute_suite_run",
    "list_suite_names",
    "resolve_seed_policy",
]
