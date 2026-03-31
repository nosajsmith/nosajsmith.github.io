from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


DEFAULT_BRIDGE_URI = "ws://127.0.0.1:8766"


@dataclass(frozen=True)
class CommandRegistryDirectory:
    entry_id: str
    label: str
    path: str
    create_if_missing: bool = False


@dataclass(frozen=True)
class AllowlistedCommand:
    command_id: str
    label: str
    provider: str
    directory_id: str
    argv: List[str] = field(default_factory=list)
    keep_open: bool = True


@dataclass(frozen=True)
class CommandRegistryCatalog:
    version: int
    directories: List[CommandRegistryDirectory] = field(default_factory=list)
    commands: List[AllowlistedCommand] = field(default_factory=list)
    source_path: str = ""

    def get_directory(self, entry_id: str) -> CommandRegistryDirectory | None:
        target = str(entry_id or "").strip()
        for entry in self.directories:
            if entry.entry_id == target:
                return entry
        return None

    def get_command(self, command_id: str) -> AllowlistedCommand | None:
        target = str(command_id or "").strip()
        for entry in self.commands:
            if entry.command_id == target:
                return entry
        return None

    def command_ids(self) -> List[str]:
        return [entry.command_id for entry in self.commands]


@dataclass(frozen=True)
class KonsoleLaunchSpec:
    label: str
    cwd: str
    argv: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    keep_open: bool = True
    new_tab: bool = False
    command_id: str = ""


@dataclass(frozen=True)
class KonsoleIntegrationResult:
    ok: bool
    status: str
    summary: str
    logs: List[str] = field(default_factory=list)
    command: List[str] = field(default_factory=list)
    workdir: str = ""
    command_id: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def command_registry_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "command_registry.yaml"


def load_command_registry(path: Path | None = None) -> CommandRegistryCatalog:
    source_path = Path(path) if path is not None else command_registry_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Command registry must be a top-level object.")
    version = payload.get("version")
    if not isinstance(version, int):
        raise RuntimeError("Command registry must expose an integer version.")

    directory_rows = payload.get("directories")
    command_rows = payload.get("commands")
    if not isinstance(directory_rows, list):
        raise RuntimeError("Command registry must expose a directories list.")
    if not isinstance(command_rows, list):
        raise RuntimeError("Command registry must expose a commands list.")

    directories: List[CommandRegistryDirectory] = []
    commands: List[AllowlistedCommand] = []
    seen_directory_ids: set[str] = set()
    seen_command_ids: set[str] = set()

    for index, row in enumerate(directory_rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"directories[{index}] must be an object.")
        entry = CommandRegistryDirectory(
            entry_id=_required_text(row.get("id"), f"directories[{index}].id"),
            label=_required_text(row.get("label"), f"directories[{index}].label"),
            path=str(row.get("path") or "").strip(),
            create_if_missing=bool(row.get("create_if_missing")),
        )
        if entry.entry_id in seen_directory_ids:
            raise RuntimeError(f"Duplicate directory id: {entry.entry_id}")
        seen_directory_ids.add(entry.entry_id)
        directories.append(entry)

    for index, row in enumerate(command_rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"commands[{index}] must be an object.")
        command = AllowlistedCommand(
            command_id=_required_text(row.get("id"), f"commands[{index}].id"),
            label=_required_text(row.get("label"), f"commands[{index}].label"),
            provider=_required_text(row.get("provider"), f"commands[{index}].provider"),
            directory_id=_required_text(row.get("directory"), f"commands[{index}].directory"),
            argv=_text_list(row.get("argv"), field_name=f"commands[{index}].argv"),
            keep_open=bool(row.get("keep_open", True)),
        )
        if command.command_id in seen_command_ids:
            raise RuntimeError(f"Duplicate command id: {command.command_id}")
        if command.directory_id not in seen_directory_ids:
            raise RuntimeError(f"commands[{index}].directory references unknown directory: {command.directory_id}")
        seen_command_ids.add(command.command_id)
        commands.append(command)

    return CommandRegistryCatalog(
        version=version,
        directories=directories,
        commands=commands,
        source_path=str(source_path),
    )


def detect_konsole(which_fn: Callable[[str], str | None] = shutil.which) -> str | None:
    path = which_fn("konsole")
    return str(path).strip() if path else None


def command_options(catalog: CommandRegistryCatalog | None = None) -> List[str]:
    registry = catalog or load_command_registry()
    return registry.command_ids()


def resolve_working_directory(
    directory_id: str,
    *,
    catalog: CommandRegistryCatalog | None = None,
    repo_root_path: Path | None = None,
) -> Path:
    registry = catalog or load_command_registry()
    entry = registry.get_directory(directory_id)
    if entry is None:
        raise RuntimeError(f"Unknown directory id: {directory_id}")
    if not entry.path:
        raise RuntimeError(f"{entry.entry_id} is not configured.")
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    resolved = (root / entry.path).resolve()
    if entry.create_if_missing:
        resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.exists() or not resolved.is_dir():
        raise RuntimeError(f"Directory not found: {resolved}")
    return resolved


def resolve_allowlisted_command(
    command_id: str,
    *,
    catalog: CommandRegistryCatalog | None = None,
    repo_root_path: Path | None = None,
    bridge_uri: str = DEFAULT_BRIDGE_URI,
) -> KonsoleLaunchSpec:
    registry = catalog or load_command_registry()
    command_entry = registry.get_command(command_id)
    if command_entry is None:
        raise RuntimeError(f"Selected allowlisted Konsole command is not configured: {command_id}")
    if command_entry.provider == "tail_latest_logs":
        raise RuntimeError("tail logs command unavailable because no canonical log path configured")
    cwd = resolve_working_directory(command_entry.directory_id, catalog=registry, repo_root_path=repo_root_path)

    if command_entry.provider == "directory":
        return KonsoleLaunchSpec(
            label=command_entry.label,
            cwd=str(cwd),
            keep_open=command_entry.keep_open,
            command_id=command_entry.command_id,
        )
    if command_entry.provider == "argv":
        if not command_entry.argv:
            raise RuntimeError(f"Allowlisted command {command_entry.command_id} does not declare argv.")
        return KonsoleLaunchSpec(
            label=command_entry.label,
            cwd=str(cwd),
            argv=list(command_entry.argv),
            keep_open=command_entry.keep_open,
            command_id=command_entry.command_id,
        )
    if command_entry.provider == "bridge_launch":
        from .process_control import resolve_bridge_launch_spec

        spec = resolve_bridge_launch_spec(repo_root_path=repo_root_path, bridge_uri=bridge_uri)
        return KonsoleLaunchSpec(
            label=command_entry.label,
            cwd=spec.cwd,
            argv=list(spec.command),
            env=dict(spec.env),
            keep_open=command_entry.keep_open,
            command_id=command_entry.command_id,
        )
    if command_entry.provider == "ui_launch":
        from .process_control import resolve_mwe_launch_spec

        spec = resolve_mwe_launch_spec(repo_root_path=repo_root_path, bridge_uri=bridge_uri)
        return KonsoleLaunchSpec(
            label=command_entry.label,
            cwd=spec.cwd,
            argv=list(spec.command),
            env=dict(spec.env),
            keep_open=command_entry.keep_open,
            command_id=command_entry.command_id,
        )
    raise RuntimeError(f"Unsupported allowlisted command provider: {command_entry.provider}")


def build_konsole_command(
    spec: KonsoleLaunchSpec,
    *,
    konsole_binary: str = "konsole",
    shell: str = "bash",
) -> List[str]:
    argv = [str(konsole_binary), "--workdir", str(spec.cwd)]
    if spec.new_tab:
        argv.append("--new-tab")
    if spec.argv:
        if spec.keep_open:
            argv.append("--hold")
        argv.extend(["-e", shell, "-lc", _shell_script(spec.argv, spec.env)])
    return argv


def launch_konsole_directory(
    directory_id: str,
    *,
    label: str,
    catalog: CommandRegistryCatalog | None = None,
    repo_root_path: Path | None = None,
    which_fn: Callable[[str], str | None] = shutil.which,
    popen_factory: Callable[..., object] = subprocess.Popen,
    new_tab: bool = False,
) -> KonsoleIntegrationResult:
    registry = catalog or load_command_registry()
    konsole_path = detect_konsole(which_fn)
    logs: List[str] = []
    if not konsole_path:
        logs.append("konsole not found")
        return _result("fail", "Konsole is not installed or not found on PATH.", logs=logs)
    logs.append(f"konsole detected: {konsole_path}")
    logs.append(f"opening {label.lower()} terminal")
    try:
        cwd = resolve_working_directory(directory_id, catalog=registry, repo_root_path=repo_root_path)
    except Exception as exc:
        logs.append(str(exc))
        return _result("fail", f"Unable to open {label.lower()} terminal.", logs=logs)

    spec = KonsoleLaunchSpec(label=label, cwd=str(cwd), new_tab=new_tab)
    command = build_konsole_command(spec, konsole_binary=konsole_path)
    try:
        popen_factory(command)
    except OSError as exc:
        logs.append(str(exc))
        return _result("error", f"Failed to launch {label.lower()} terminal.", logs=logs, command=command, workdir=str(cwd))
    logs.append(f"opened {label.lower()} terminal")
    return _result("pass", f"{label} terminal opened.", logs=logs, command=command, workdir=str(cwd))


def launch_konsole_command(
    command_id: str,
    *,
    label: str,
    catalog: CommandRegistryCatalog | None = None,
    repo_root_path: Path | None = None,
    bridge_uri: str = DEFAULT_BRIDGE_URI,
    which_fn: Callable[[str], str | None] = shutil.which,
    popen_factory: Callable[..., object] = subprocess.Popen,
    new_tab: bool = False,
) -> KonsoleIntegrationResult:
    registry = catalog or load_command_registry()
    logs: List[str] = []
    konsole_path = detect_konsole(which_fn)
    if not konsole_path:
        logs.append("konsole not found")
        return _result("fail", "Konsole is not installed or not found on PATH.", logs=logs, command_id=command_id)
    logs.append(f"konsole detected: {konsole_path}")
    try:
        spec = resolve_allowlisted_command(
            command_id,
            catalog=registry,
            repo_root_path=repo_root_path,
            bridge_uri=bridge_uri,
        )
    except Exception as exc:
        message = str(exc)
        logs.append(message)
        status = "warn" if "unavailable" in message.lower() else "fail"
        return _result(status, f"{label} unavailable.", logs=logs, command_id=command_id)

    spec = KonsoleLaunchSpec(
        label=spec.label,
        cwd=spec.cwd,
        argv=spec.argv,
        env=spec.env,
        keep_open=spec.keep_open,
        new_tab=new_tab,
        command_id=spec.command_id,
    )
    command = build_konsole_command(spec, konsole_binary=konsole_path)
    logs.append(f"opening {label.lower()}")
    try:
        popen_factory(command)
    except OSError as exc:
        logs.append(str(exc))
        return _result("error", f"Failed to launch {label.lower()}.", logs=logs, command=command, workdir=spec.cwd, command_id=command_id)
    if command_id == "bridge_launch":
        logs.append("launched bridge terminal using allowlisted command")
    elif command_id == "ui_launch":
        logs.append("launched UI terminal using allowlisted command")
    else:
        logs.append(f"launched allowlisted command: {command_id}")
    logs.append(f"workdir: {spec.cwd}")
    logs.append(f"command: {' '.join(spec.argv)}")
    return _result(
        "pass",
        f"{label} launched.",
        logs=logs,
        command=command,
        workdir=spec.cwd,
        command_id=command_id,
    )


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse command registry: {path}") from exc


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{field_name} is required.")
    return text


def _text_list(value: object, *, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"{field_name} must be a list of strings.")
    items: List[str] = []
    for index, item in enumerate(value, start=1):
        text = str(item or "").strip()
        if not text:
            raise RuntimeError(f"{field_name}[{index}] must be a non-empty string.")
        items.append(text)
    return items


def _shell_script(argv: List[str], env: Dict[str, str]) -> str:
    exports = [f"export {key}={shlex.quote(str(value))}" for key, value in sorted(env.items())]
    command_text = " ".join(shlex.quote(str(item)) for item in argv)
    return "; ".join([*exports, command_text]) if exports else command_text


def _result(
    status: str,
    summary: str,
    *,
    logs: List[str] | None = None,
    command: List[str] | None = None,
    workdir: str = "",
    command_id: str = "",
) -> KonsoleIntegrationResult:
    return KonsoleIntegrationResult(
        ok=status not in {"fail", "error"},
        status=status,
        summary=summary,
        logs=list(logs or []),
        command=list(command or []),
        workdir=str(workdir or ""),
        command_id=str(command_id or ""),
    )
