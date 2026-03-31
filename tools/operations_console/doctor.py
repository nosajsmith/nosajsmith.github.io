from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List

from .models import ConsoleResult
from .process_control import probe_bridge
from .runner_utils import make_result, roll_up_statuses


DEFAULT_BRIDGE_URI = "ws://127.0.0.1:8766"


@dataclass(frozen=True)
class DoctorCheckResult:
    check_id: str
    label: str
    status: str
    summary: str
    details: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DoctorResult:
    status: str
    summary: str
    checks: List[DoctorCheckResult] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_artifacts_dir(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "operations_console"


def run_doctor(
    *,
    bridge_uri: str = DEFAULT_BRIDGE_URI,
    repo_root_path: Path | None = None,
    which_fn: Callable[[str], str | None] = shutil.which,
    bridge_probe: Callable[[str], bool] = probe_bridge,
) -> DoctorResult:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    checks = [
        _bridge_reachability_check(bridge_uri, bridge_probe=bridge_probe),
        _required_paths_check(root),
        _artifact_directory_check(default_artifacts_dir(root)),
        _basic_commands_check(which_fn),
    ]
    logs: List[str] = []
    for check in checks:
        logs.append(f"{check.label}: {check.status.upper()} - {check.summary}")
        logs.extend(check.details)
    status = roll_up_statuses(check.status for check in checks)
    summary = f"mwe doctor completed with status {status.upper()}."
    return DoctorResult(status=status, summary=summary, checks=checks, logs=logs)


def run_doctor_console_result(
    *,
    bridge_uri: str = DEFAULT_BRIDGE_URI,
    scenario_name: str = "",
    repo_root_path: Path | None = None,
    which_fn: Callable[[str], str | None] = shutil.which,
    bridge_probe: Callable[[str], bool] = probe_bridge,
) -> ConsoleResult:
    result = run_doctor(
        bridge_uri=bridge_uri,
        repo_root_path=repo_root_path,
        which_fn=which_fn,
        bridge_probe=bridge_probe,
    )
    subresults = [
        make_result(
            name=check.label,
            status=check.status,
            summary=check.summary,
            details=check.details,
            errors=[check.summary] if check.status in {"fail", "error"} else [],
            scenario_name=scenario_name,
        )
        for check in result.checks
    ]
    return make_result(
        name="Utilities / mwe doctor",
        status=result.status,
        summary=result.summary,
        details=result.logs,
        scenario_name=scenario_name,
        subresults=subresults,
    )


def format_doctor_text(result: DoctorResult) -> str:
    lines = [result.summary]
    for check in result.checks:
        lines.append(f"- {check.label}: {check.status.upper()} - {check.summary}")
        lines.extend(f"  {line}" for line in check.details)
    return "\n".join(lines)


def _bridge_reachability_check(
    bridge_uri: str,
    *,
    bridge_probe: Callable[[str], bool],
) -> DoctorCheckResult:
    uri = str(bridge_uri or DEFAULT_BRIDGE_URI).strip() or DEFAULT_BRIDGE_URI
    reachable = bool(bridge_probe(uri))
    if reachable:
        return DoctorCheckResult(
            check_id="bridge_reachability",
            label="Bridge Reachability",
            status="pass",
            summary=f"Bridge reachable at {uri}.",
        )
    return DoctorCheckResult(
        check_id="bridge_reachability",
        label="Bridge Reachability",
        status="warn",
        summary=f"Bridge not reachable at {uri}.",
        details=["Start the bridge from the console or verify the configured websocket endpoint."],
    )


def _required_paths_check(root: Path) -> DoctorCheckResult:
    required = [
        root,
        root / "server" / "mwe_bridge_p8_ws15.py",
        root / "ui",
        root / "ui" / "package.json",
        root / "scenarios",
        root / "tools" / "operations_console",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if not missing:
        return DoctorCheckResult(
            check_id="required_paths",
            label="Required Paths",
            status="pass",
            summary="Required repo paths are present.",
        )
    return DoctorCheckResult(
        check_id="required_paths",
        label="Required Paths",
        status="fail",
        summary="Required repo paths are missing.",
        details=[f"missing: {path}" for path in missing],
    )


def _artifact_directory_check(artifacts_dir: Path) -> DoctorCheckResult:
    if artifacts_dir.exists() and artifacts_dir.is_dir():
        return DoctorCheckResult(
            check_id="artifact_directory",
            label="Artifact Directory",
            status="pass",
            summary=f"Artifact directory exists: {artifacts_dir}",
        )
    return DoctorCheckResult(
        check_id="artifact_directory",
        label="Artifact Directory",
        status="warn",
        summary=f"Artifact directory is missing: {artifacts_dir}",
        details=["The directory will be created automatically on the next report, incident, or manifest export."],
    )


def _basic_commands_check(which_fn: Callable[[str], str | None]) -> DoctorCheckResult:
    required = ["git", "python", "pytest", "node", "npm"]
    optional = ["konsole"]
    missing_required = [name for name in required if not which_fn(name)]
    missing_optional = [name for name in optional if not which_fn(name)]
    available = [name for name in [*required, *optional] if which_fn(name)]
    details = [f"available: {', '.join(available)}"] if available else []
    if missing_required:
        details.extend(f"missing required command: {name}" for name in missing_required)
        if missing_optional:
            details.extend(f"missing optional command: {name}" for name in missing_optional)
        return DoctorCheckResult(
            check_id="basic_commands",
            label="Basic Commands",
            status="fail",
            summary="Required commands are missing from PATH.",
            details=details,
        )
    if missing_optional:
        details.extend(f"missing optional command: {name}" for name in missing_optional)
        return DoctorCheckResult(
            check_id="basic_commands",
            label="Basic Commands",
            status="warn",
            summary="Required commands are available, but optional commands are missing.",
            details=details,
        )
    return DoctorCheckResult(
        check_id="basic_commands",
        label="Basic Commands",
        status="pass",
        summary="Required commands are available on PATH.",
        details=details,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run lightweight MWE environment sanity checks.")
    parser.add_argument("--bridge-uri", default=DEFAULT_BRIDGE_URI)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_doctor(bridge_uri=args.bridge_uri)
    print(format_doctor_text(result))
    return 0 if result.status in {"pass", "warn"} else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
