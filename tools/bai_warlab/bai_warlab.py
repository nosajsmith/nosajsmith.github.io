#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from tools.bai_warlab import BAI_WARLAB_VERSION
from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.manifest import build_manifest_record, write_manifest
from tools.bai_warlab.models import ManifestRecord, RunRequest, to_plain
from tools.bai_warlab.report_io import default_output_dir, ensure_output_dir, run_result_to_row, write_json, write_report_txt, write_results_csv
from tools.bai_warlab.reports.regression_report import render_regression_report
from tools.bai_warlab.reports.summary_report import render_report
from tools.bai_warlab.runners import execute_batch_run, execute_compare_run, execute_single_run, execute_suite_run, list_suite_names, resolve_seed_policy


def _command_line(argv: List[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _write_bundle(*, output_dir: Path, summary_obj: Any, manifest: ManifestRecord, rows: List[Dict[str, Any]], text_report: str) -> None:
    write_json(output_dir / "summary.json", summary_obj)
    write_results_csv(output_dir / "results.csv", rows)
    write_report_txt(output_dir / "report.txt", text_report)
    write_manifest(output_dir / "manifest.json", manifest)


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
    seeds = [int(part.strip()) for part in args.seeds.split(",") if part.strip()] if args.seeds else None
    seed_policy = resolve_seed_policy(count=args.count, seed_start=args.seed_start, seeds=seeds)
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
    output_dir = ensure_output_dir(default_output_dir("batch", [args.scenario, args.doctrine, args.personality, args.tuning], args.output_dir))
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="batch",
        output_dir=output_dir,
        scenario=args.scenario,
        doctrine=args.doctrine,
        personality=args.personality,
        tuning=args.tuning,
        seed_policy=to_plain(seed_policy),
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=[run_result_to_row(run) for run in result.runs], text_report=render_report(result))
    print(output_dir)
    return 0 if result.ok else 1


def _compare_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    seeds = [int(part.strip()) for part in args.seeds.split(",") if part.strip()] if args.seeds else None
    seed_policy = resolve_seed_policy(count=args.count, seed_start=args.seed_start, seeds=seeds)
    result = execute_compare_run(
        scenario=args.scenario,
        scenario_dir=args.scenario_dir,
        left={"doctrine": args.left_doctrine, "personality": args.left_personality, "tuning": args.left_tuning},
        right={"doctrine": args.right_doctrine, "personality": args.right_personality, "tuning": args.right_tuning},
        seed_policy=seed_policy,
        loader=loader,
        max_steps=args.max_steps,
        dt_hours=args.dt_hours,
        stop_on_terminal=not args.no_stop_on_terminal,
    )
    output_dir = ensure_output_dir(default_output_dir("compare", [args.scenario, args.left_doctrine, "vs", args.right_doctrine], args.output_dir))
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="compare",
        output_dir=output_dir,
        scenario=args.scenario,
        doctrine={"left": args.left_doctrine, "right": args.right_doctrine},
        personality={"left": args.left_personality, "right": args.right_personality},
        tuning={"left": args.left_tuning, "right": args.right_tuning},
        seed_policy=to_plain(seed_policy),
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    rows = [run_result_to_row(run) for run in result.left_runs + result.right_runs]
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=rows, text_report=render_report(result))
    print(output_dir)
    return 0 if result.ok else 1


def _suite_command(args: argparse.Namespace, loader: ConfigLoader, command_line: str, command_argv: List[str]) -> int:
    result = execute_suite_run(suite_name=args.suite_name, loader=loader)
    output_dir = ensure_output_dir(default_output_dir("suite", [args.suite_name], args.output_dir))
    result.output_dir = str(output_dir)
    manifest = build_manifest_record(
        command="suite",
        output_dir=output_dir,
        scenario=[run.scenario for run in result.runs],
        doctrine=[run.doctrine for run in result.runs],
        personality=[run.personality for run in result.runs],
        tuning=[run.tuning for run in result.runs],
        seed_policy={"kind": "suite", "seeds": [run.seed for run in result.runs]},
        command_line=command_line,
        command_argv=command_argv,
        config_root=args.config_root,
        loader=loader,
        result=result,
    )
    _write_bundle(output_dir=output_dir, summary_obj=result, manifest=manifest, rows=[run_result_to_row(run) for run in result.runs], text_report=render_report(result))
    print(output_dir)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BAI War Lab — headless BALCK AI tuning and benchmarking tool.")
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

    batch_parser = subparsers.add_parser("batch", help="Execute one config over multiple seeds.")
    add_common(batch_parser)
    batch_parser.add_argument("--doctrine", required=True)
    batch_parser.add_argument("--personality", required=True)
    batch_parser.add_argument("--tuning", required=True)
    batch_parser.add_argument("--count", type=int, default=4)
    batch_parser.add_argument("--seed-start", type=int, default=0)
    batch_parser.add_argument("--seeds", default=None)

    compare_parser = subparsers.add_parser("compare", help="Compare two doctrine/personality/tuning variants over shared seeds.")
    add_common(compare_parser)
    compare_parser.add_argument("--left-doctrine", required=True)
    compare_parser.add_argument("--left-personality", required=True)
    compare_parser.add_argument("--left-tuning", required=True)
    compare_parser.add_argument("--right-doctrine", required=True)
    compare_parser.add_argument("--right-personality", required=True)
    compare_parser.add_argument("--right-tuning", required=True)
    compare_parser.add_argument("--count", type=int, default=4)
    compare_parser.add_argument("--seed-start", type=int, default=0)
    compare_parser.add_argument("--seeds", default=None)

    suite_parser = subparsers.add_parser("suite", help="Execute a named benchmark suite.")
    suite_parser.add_argument("suite_name", choices=list_suite_names())
    suite_parser.add_argument("--config-root", default="configs/ai", help=argparse.SUPPRESS)
    suite_parser.add_argument("--output-dir", default=None)
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    command_argv = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(command_argv)
    loader = ConfigLoader(args.config_root)
    command_line = _command_line(command_argv)

    if args.command == "run":
        return _run_command(args, loader, command_line, command_argv)
    if args.command == "batch":
        return _batch_command(args, loader, command_line, command_argv)
    if args.command == "compare":
        return _compare_command(args, loader, command_line, command_argv)
    if args.command == "suite":
        return _suite_command(args, loader, command_line, command_argv)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
