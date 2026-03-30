#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import sys
from itertools import zip_longest
from pathlib import Path
from typing import Any, Dict, List

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from tools.bai_warlab import BAI_WARLAB_VERSION
from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.manifest import build_manifest_record, write_manifest
from tools.bai_warlab.models import ManifestRecord, RunRequest, SeedPolicy
from tools.bai_warlab.presets.benchmark_suites import list_suite_names, load_benchmark_suite
from tools.bai_warlab.report_io import (
    default_output_dir,
    ensure_output_dir,
    run_result_to_row,
    stable_hash,
    summarize_core_metric_rows,
    write_json,
    write_report_txt,
    write_results_csv,
)
from tools.bai_warlab.reports.summary_report import render_report
from tools.bai_warlab.runners import execute_batch_run, execute_compare_run, execute_single_run, execute_suite_run, resolve_seed_policy


def _command_line(argv: List[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _write_bundle(*, output_dir: Path, summary_obj: Any, manifest: ManifestRecord, rows: List[Dict[str, Any]], text_report: str) -> None:
    write_json(output_dir / "summary.json", summary_obj)
    write_results_csv(output_dir / "results.csv", rows)
    write_report_txt(output_dir / "report.txt", text_report)
    write_manifest(output_dir / "manifest.json", manifest)


def _seed_policy_record(seed_policy: SeedPolicy) -> Dict[str, Any]:
    return {
        "kind": seed_policy.kind,
        "seeds": list(seed_policy.seeds),
        "base_seed": seed_policy.base_seed,
        "count": seed_policy.count,
    }


def _print_console_metric_summary(rows: List[Dict[str, Any]]) -> None:
    metrics = summarize_core_metric_rows(rows)
    for payload in metrics.values():
        print(
            f"{payload['label']}: "
            f"mean={payload['mean']} min={payload['min']} max={payload['max']} sd={payload.get('stddev', 0.0)} n={payload['count']}"
        )


def _format_counts(counts: Dict[str, Any]) -> str:
    mapping = dict(counts or {})
    if not mapping:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in mapping.items())


def _print_batch_console_summary(result: Any, output_dir: Path) -> None:
    aggregate = getattr(result, "aggregate", None)
    rows = [
        run_result_to_row(run)
        for run in list(getattr(result, "runs", []) or [])
        if getattr(run, "ok", False)
    ]

    print("BAI War Lab — Batch Summary")
    print(f"Scenario: {result.scenario}")
    print(f"Doctrine: {result.doctrine}")
    print(f"Personality: {result.personality}")
    print(f"Tuning: {result.tuning}")
    print(f"Seeds: {', '.join(str(seed) for seed in result.seed_policy.seeds)}")
    if aggregate is not None:
        print(f"Runs: {aggregate.total_runs} | OK: {aggregate.ok_runs} | Failed: {aggregate.failure_count}")
        print(f"Success rate: {aggregate.success_rate}")
        if aggregate.victory_proxy.get("available"):
            print(
                "Results: "
                f"{_format_counts(aggregate.result_counts)} | Non-loss rate: {aggregate.victory_proxy.get('non_loss_rate')}"
            )
            print(f"Scenario outcomes: {_format_counts(aggregate.scenario_outcome_counts)}")
    _print_console_metric_summary(rows)
    if result.warnings:
        print(f"Warnings: {result.warnings[0]}")
    print(f"Artifacts: {output_dir}")


def _print_suite_console_summary(result: Any, output_dir: Path) -> None:
    aggregate = getattr(result, "aggregate", None)
    rows = [
        run_result_to_row(run)
        for run in list(getattr(result, "runs", []) or [])
        if getattr(run, "ok", False)
    ]

    print("BAI War Lab — Suite Summary")
    print(f"Suite: {result.suite_name}")
    if aggregate is not None:
        print(f"Runs: {aggregate.total_runs} | OK: {aggregate.ok_runs} | Failed: {aggregate.failure_count}")
        print(f"Success rate: {aggregate.success_rate}")
        if aggregate.victory_proxy.get("available"):
            print(
                "Results: "
                f"{_format_counts(aggregate.result_counts)} | Non-loss rate: {aggregate.victory_proxy.get('non_loss_rate')}"
            )
            print(f"Scenario outcomes: {_format_counts(aggregate.scenario_outcome_counts)}")
    _print_console_metric_summary(rows)
    if result.warnings:
        print(f"Warnings: {result.warnings[0]}")
    print(f"Artifacts: {output_dir}")


def _compare_variant_config(args: argparse.Namespace) -> tuple[Dict[str, str], Dict[str, str]]:
    shared = {
        "doctrine": getattr(args, "doctrine", None),
        "personality": getattr(args, "personality", None),
        "tuning": getattr(args, "tuning", None),
    }
    left = {
        key: getattr(args, f"left_{key}") or value
        for key, value in shared.items()
    }
    right = {
        key: getattr(args, f"right_{key}") or value
        for key, value in shared.items()
    }

    missing = sorted(key for key in shared if not left.get(key) or not right.get(key))
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(
            "Compare requires selectors for doctrine, personality, and tuning. "
            f"Provide shared defaults or left/right overrides for: {missing_text}."
        )
    if left == right:
        raise ValueError("Compare variants must differ in at least one of doctrine, personality, or tuning.")
    return left, right


def _compare_rows(result: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for left_run, right_run in zip_longest(result.left_runs, result.right_runs):
        if left_run is not None:
            rows.append(run_result_to_row(left_run))
        if right_run is not None:
            rows.append(run_result_to_row(right_run))
    return rows


def _suite_seed_policy_record(cases: List[Any], runs_override: int | None = None) -> Dict[str, Any]:
    return {
        "kind": "suite_preset",
        "jobs": {
            case.id: _seed_policy_record(resolve_seed_policy(count=int(runs_override or case.runs or 1), seed_start=case.seed))
            for case in cases
        },
    }


def _run_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    result = execute_single_run(
        RunRequest(
            scenario=args.scenario,
            scenario_dir=args.scenario_dir,
            doctrine=args.doctrine,
            personality=args.personality,
            tuning=args.tuning,
            seed=int(args.seed),
            max_steps=args.max_steps,
            dt_hours=args.dt_hours,
            stop_on_terminal=not args.no_stop_on_terminal,
        ),
        loader,
    )
    output_dir = ensure_output_dir(default_output_dir("run", [args.scenario, args.doctrine, args.personality, args.tuning, f"seed-{args.seed:04d}"], args.output_dir))
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="run",
        output_dir=output_dir,
        scenario=args.scenario,
        doctrine=args.doctrine,
        personality=args.personality,
        tuning=args.tuning,
        seed_policy={"kind": "explicit", "seeds": [int(args.seed)]},
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=[run_result_to_row(result)], text_report=render_report(result))
    print(output_dir)
    return 0 if result.ok else 1


def _batch_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    seed_policy = resolve_seed_policy(count=args.runs, seed_start=args.seed)
    result = execute_batch_run(
        scenario=args.scenario,
        scenario_dir=args.scenario_dir,
        doctrine=args.doctrine,
        personality=args.personality,
        tuning=args.tuning,
        seed_policy=seed_policy,
        loader=loader,
        max_steps=args.max_steps,
        dt_hours=args.dt_hours,
        stop_on_terminal=not args.no_stop_on_terminal,
    )
    base_seed = seed_policy.base_seed if seed_policy.base_seed is not None else 0
    output_dir = ensure_output_dir(
        default_output_dir(
            "batch",
            [args.scenario, args.doctrine, args.personality, args.tuning, f"runs-{args.runs:03d}", f"seed-{base_seed:04d}"],
            args.output_dir,
        )
    )
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="batch",
        output_dir=output_dir,
        scenario=args.scenario,
        doctrine=args.doctrine,
        personality=args.personality,
        tuning=args.tuning,
        seed_policy=_seed_policy_record(seed_policy),
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    rows = [run_result_to_row(run) for run in result.runs]
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=rows, text_report=render_report(result))
    _print_batch_console_summary(result, output_dir)
    return 0 if result.ok else 1


def _compare_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    left, right = _compare_variant_config(args)
    seed_policy = resolve_seed_policy(count=args.runs, seed_start=args.seed)
    result = execute_compare_run(
        scenario=args.scenario,
        scenario_dir=args.scenario_dir,
        left=left,
        right=right,
        seed_policy=seed_policy,
        loader=loader,
        max_steps=args.max_steps,
        dt_hours=args.dt_hours,
        stop_on_terminal=not args.no_stop_on_terminal,
    )
    base_seed = seed_policy.base_seed if seed_policy.base_seed is not None else 0
    variant_key = stable_hash(
        [
            args.scenario,
            left["doctrine"],
            left["personality"],
            left["tuning"],
            right["doctrine"],
            right["personality"],
            right["tuning"],
            args.runs,
            base_seed,
        ]
    )
    output_dir = ensure_output_dir(
        default_output_dir(
            "compare",
            [args.scenario, f"runs-{args.runs:03d}", f"seed-{base_seed:04d}", variant_key],
            args.output_dir,
        )
    )
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="compare",
        output_dir=output_dir,
        scenario=args.scenario,
        doctrine={"left": left["doctrine"], "right": right["doctrine"]},
        personality={"left": left["personality"], "right": right["personality"]},
        tuning={"left": left["tuning"], "right": right["tuning"]},
        seed_policy=_seed_policy_record(seed_policy),
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    _write_bundle(
        output_dir=output_dir,
        summary_obj=result,
        manifest=manifest,
        rows=_compare_rows(result),
        text_report=render_report(result),
    )
    print(output_dir)
    return 0 if result.ok else 1


def _suite_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    cases = load_benchmark_suite(args.suite_name)
    result = execute_suite_run(
        suite_name=args.suite_name,
        loader=loader,
        max_steps=args.max_steps,
        dt_hours=args.dt_hours,
        stop_on_terminal=not args.no_stop_on_terminal,
        runs_override=args.runs,
    )
    output_dir = ensure_output_dir(
        default_output_dir(
            "suite",
            [args.suite_name, stable_hash(command_argv)],
            args.output_dir,
        )
    )
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="suite",
        output_dir=output_dir,
        scenario={case.id: case.scenario for case in cases},
        doctrine={case.id: case.doctrine for case in cases},
        personality={case.id: case.personality for case in cases},
        tuning={case.id: case.tuning for case in cases},
        seed_policy=_suite_seed_policy_record(cases, args.runs),
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    rows = [run_result_to_row(run) for run in result.runs]
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=rows, text_report=render_report(result))
    _print_suite_console_summary(result, output_dir)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BAI War Lab — headless BAI scenario harness.")
    parser.add_argument("--config-root", default="configs/ai", help="Config root containing doctrines/, personalities/, and tuning/.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(run_parser: argparse.ArgumentParser) -> None:
        run_parser.add_argument("--config-root", default="configs/ai", help=argparse.SUPPRESS)
        run_parser.add_argument("--scenario", required=True)
        run_parser.add_argument("--scenario-dir", default="scenarios")
        run_parser.add_argument("--max-steps", type=int, default=None)
        run_parser.add_argument("--dt-hours", type=int, default=None)
        run_parser.add_argument("--output-dir", default=None)
        run_parser.add_argument("--no-stop-on-terminal", action="store_true")

    run_parser = subparsers.add_parser("run", help="Execute one headless scenario run.")
    add_common(run_parser)
    run_parser.add_argument("--doctrine", required=True)
    run_parser.add_argument("--personality", required=True)
    run_parser.add_argument("--tuning", required=True)
    run_parser.add_argument("--seed", type=int, default=0)

    batch_parser = subparsers.add_parser("batch", help="Execute repeated headless scenario trials.")
    add_common(batch_parser)
    batch_parser.add_argument("--doctrine", required=True)
    batch_parser.add_argument("--personality", required=True)
    batch_parser.add_argument("--tuning", required=True)
    batch_parser.add_argument("--runs", type=int, required=True)
    batch_parser.add_argument("--seed", type=int, default=None, help="Optional base seed for deterministic batch scheduling.")

    compare_parser = subparsers.add_parser("compare", help="Execute paired A/B headless scenario trials.")
    add_common(compare_parser)
    compare_parser.add_argument("--doctrine", default=None)
    compare_parser.add_argument("--personality", default=None)
    compare_parser.add_argument("--tuning", default=None)
    compare_parser.add_argument("--left-doctrine", default=None)
    compare_parser.add_argument("--right-doctrine", default=None)
    compare_parser.add_argument("--left-personality", default=None)
    compare_parser.add_argument("--right-personality", default=None)
    compare_parser.add_argument("--left-tuning", default=None)
    compare_parser.add_argument("--right-tuning", default=None)
    compare_parser.add_argument("--runs", type=int, required=True)
    compare_parser.add_argument("--seed", type=int, default=None, help="Optional base seed for deterministic compare scheduling.")

    suite_parser = subparsers.add_parser("suite", help="Execute a named benchmark suite.")
    suite_parser.add_argument("--config-root", default="configs/ai", help=argparse.SUPPRESS)
    suite_parser.add_argument("suite_name", choices=list_suite_names())
    suite_parser.add_argument("--max-steps", type=int, default=None)
    suite_parser.add_argument("--dt-hours", type=int, default=None)
    suite_parser.add_argument("--runs", type=int, default=None, help="Optional override for runs per suite job.")
    suite_parser.add_argument("--output-dir", default=None)
    suite_parser.add_argument("--no-stop-on-terminal", action="store_true")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    command_argv = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(command_argv)
    loader = ConfigLoader(args.config_root)
    command_line = _command_line(command_argv)

    try:
        if args.command == "run":
            return _run_command(args, loader, command_line, command_argv)
        if args.command == "batch":
            return _batch_command(args, loader, command_line, command_argv)
        if args.command == "compare":
            return _compare_command(args, loader, command_line, command_argv)
        if args.command == "suite":
            return _suite_command(args, loader, command_line, command_argv)
    except ValueError as exc:
        parser.error(str(exc))
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
