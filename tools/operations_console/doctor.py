from __future__ import annotations

import argparse
import importlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List

from .konsole_integration import command_registry_path, load_command_registry, resolve_working_directory
from .models import ConsoleResult
from .process_control import probe_bridge, resolve_bridge_endpoint
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
    import_fn: Callable[[str], object] = importlib.import_module,
) -> DoctorResult:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    checks = [
        _bridge_uri_format_check(bridge_uri),
        _required_paths_check(root),
        _artifact_directory_check(default_artifacts_dir(root)),
        _bridge_reachability_check(bridge_uri, bridge_probe=bridge_probe),
        _tooling_commands_check(which_fn),
        _konsole_check(which_fn),
        _command_registry_check(root),
        _python_modules_check(import_fn),
    ]
    logs: List[str] = []
    for check in checks:
        verb = "passed" if check.status == "pass" else ("warned" if check.status == "warn" else "failed")
        logs.append(f"doctor check {verb}: {check.label}")
        logs.append(f"{check.label}: {check.summary}")
        logs.extend(check.details)
    pass_count = sum(1 for check in checks if check.status == "pass")
    warn_count = sum(1 for check in checks if check.status == "warn")
    fail_count = sum(1 for check in checks if check.status in {"fail", "error"})
    logs.append(f"doctor summary: {pass_count} pass, {warn_count} warn, {fail_count} fail")
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
    import_fn: Callable[[str], object] = importlib.import_module,
) -> ConsoleResult:
    result = run_doctor(
        bridge_uri=bridge_uri,
        repo_root_path=repo_root_path,
        which_fn=which_fn,
        bridge_probe=bridge_probe,
        import_fn=import_fn,
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
    summary_line = next((line for line in result.logs if line.startswith("doctor summary: ")), "")
    if summary_line:
        lines.append(summary_line)
    return "\n".join(lines)


def _bridge_uri_format_check(bridge_uri: str) -> DoctorCheckResult:
    raw_uri = str(bridge_uri or DEFAULT_BRIDGE_URI).strip() or DEFAULT_BRIDGE_URI
    try:
        endpoint = resolve_bridge_endpoint(raw_uri)
    except Exception as exc:
        return DoctorCheckResult(
            check_id="bridge_uri_format",
            label="Bridge URI",
            status="fail",
            summary=f"Bridge URI is invalid: {raw_uri}",
            details=[str(exc)],
        )
    return DoctorCheckResult(
        check_id="bridge_uri_format",
        label="Bridge URI",
        status="pass",
        summary=f"Bridge URI parsed successfully: {endpoint.uri}",
    )


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
    existed_before = artifacts_dir.exists() and artifacts_dir.is_dir()
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe_path = artifacts_dir / ".doctor-write-check"
        probe_path.write_text("ok\n", encoding="utf-8")
        probe_path.unlink()
    except OSError as exc:
        return DoctorCheckResult(
            check_id="artifact_directory",
            label="Artifact Directory",
            status="fail",
            summary=f"Artifact directory is not writable: {artifacts_dir}",
            details=[str(exc)],
        )
    return DoctorCheckResult(
        check_id="artifact_directory",
        label="Artifact Directory",
        status="pass",
        summary=f"Artifact directory writable: {artifacts_dir}",
        details=[] if existed_before else [f"created artifact directory: {artifacts_dir}"],
    )


def _tooling_commands_check(which_fn: Callable[[str], str | None]) -> DoctorCheckResult:
    required = ["git", "python", "pytest", "node", "npm"]
    missing_required = [name for name in required if not which_fn(name)]
    details = [f"available command: {name} -> {which_fn(name)}" for name in required if which_fn(name)]
    if missing_required:
        details.extend(f"missing required command: {name}" for name in missing_required)
        return DoctorCheckResult(
            check_id="tooling_commands",
            label="Tooling Commands",
            status="fail",
            summary="Required commands are missing from PATH.",
            details=details,
        )
    return DoctorCheckResult(
        check_id="tooling_commands",
        label="Tooling Commands",
        status="pass",
        summary="Required commands are available on PATH.",
        details=details,
    )


def _konsole_check(which_fn: Callable[[str], str | None]) -> DoctorCheckResult:
    konsole_path = which_fn("konsole")
    if konsole_path:
        return DoctorCheckResult(
            check_id="konsole_availability",
            label="Konsole Availability",
            status="pass",
            summary=f"Konsole available on PATH: {konsole_path}",
        )
    return DoctorCheckResult(
        check_id="konsole_availability",
        label="Konsole Availability",
        status="warn",
        summary="Konsole is not available on PATH.",
        details=["Konsole-backed utility actions will be unavailable until konsole is installed."],
    )


def _command_registry_check(root: Path) -> DoctorCheckResult:
    source_path = command_registry_path(root)
    details: List[str] = []
    try:
        catalog = load_command_registry(source_path)
    except Exception as exc:
        return DoctorCheckResult(
            check_id="command_registry",
            label="Command Registry",
            status="fail",
            summary="Command registry could not be loaded.",
            details=[str(exc)],
        )

    details.append(f"loaded command registry: {source_path}")
    details.append(f"allowlisted commands: {len(catalog.commands)}")
    missing_required: List[str] = []
    for directory_id in ["repo_root", "ui_dir", "bridge_dir", "artifacts_dir"]:
        try:
            resolved = resolve_working_directory(directory_id, catalog=catalog, repo_root_path=root)
            details.append(f"resolved directory: {directory_id} -> {resolved}")
        except Exception as exc:
            missing_required.append(f"{directory_id}: {exc}")

    optional_gaps: List[str] = []
    if catalog.get_directory("logs_dir") is not None:
        try:
            resolved = resolve_working_directory("logs_dir", catalog=catalog, repo_root_path=root)
            details.append(f"resolved directory: logs_dir -> {resolved}")
        except Exception as exc:
            optional_gaps.append(f"logs_dir: {exc}")

    if missing_required:
        details.extend(missing_required)
        details.extend(optional_gaps)
        return DoctorCheckResult(
            check_id="command_registry",
            label="Command Registry",
            status="fail",
            summary="Required command registry directories did not resolve.",
            details=details,
        )
    if optional_gaps:
        details.extend(optional_gaps)
        return DoctorCheckResult(
            check_id="command_registry",
            label="Command Registry",
            status="warn",
            summary="Command registry resolved with optional gaps.",
            details=details,
        )
    return DoctorCheckResult(
        check_id="command_registry",
        label="Command Registry",
        status="pass",
        summary="Command registry entries resolved.",
        details=details,
    )


def _python_modules_check(import_fn: Callable[[str], object]) -> DoctorCheckResult:
    required = ["json", "tkinter"]
    optional = ["websockets"]
    details: List[str] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []
    for module_name in required:
        try:
            import_fn(module_name)
        except Exception as exc:
            missing_required.append(module_name)
            details.append(f"missing required module: {module_name} ({exc})")
        else:
            details.append(f"imported module: {module_name}")
    for module_name in optional:
        try:
            import_fn(module_name)
        except Exception as exc:
            missing_optional.append(module_name)
            details.append(f"missing optional module: {module_name} ({exc})")
        else:
            details.append(f"imported module: {module_name}")
    if missing_required:
        return DoctorCheckResult(
            check_id="python_modules",
            label="Python Modules",
            status="fail",
            summary="Required Python modules are unavailable.",
            details=details,
        )
    if missing_optional:
        return DoctorCheckResult(
            check_id="python_modules",
            label="Python Modules",
            status="warn",
            summary="Required Python modules are available, but optional modules are missing.",
            details=details,
        )
    return DoctorCheckResult(
        check_id="python_modules",
        label="Python Modules",
        status="pass",
        summary="Required Python modules are available.",
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
