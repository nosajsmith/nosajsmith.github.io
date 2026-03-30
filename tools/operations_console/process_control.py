from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.parse import urlparse

from .registry import DEFAULT_BRIDGE_URI


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def gui_action_matrix_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "gui_action_matrix.yaml"


def load_gui_action_matrix(path: Path | None = None) -> Dict[str, Any]:
    source_path = Path(path) if path is not None else gui_action_matrix_path()
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("GUI action matrix must be a top-level object.")
    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise RuntimeError("GUI action matrix must expose an actions list.")
    return payload


def probe_bridge(uri: str) -> bool:
    parsed = urlparse(str(uri or DEFAULT_BRIDGE_URI))
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or 8766)
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


@dataclass(frozen=True)
class ProcessLaunchSpec:
    name: str
    command: List[str]
    cwd: str
    env: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessControlResult:
    ok: bool
    status: str
    summary: str
    logs: List[str] = field(default_factory=list)
    command: List[str] = field(default_factory=list)


def resolve_bridge_launch_spec(repo_root_path: Path | None = None) -> ProcessLaunchSpec:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    bridge_path = root / "server" / "mwe_bridge_p8_ws15.py"
    if not bridge_path.exists():
        raise FileNotFoundError(f"Bridge entrypoint not found: {bridge_path}")
    return ProcessLaunchSpec(
        name="Bridge",
        command=[
            "python",
            str(bridge_path),
            "--host",
            "127.0.0.1",
            "--port",
            "8766",
            "--health-port",
            "8771",
        ],
        cwd=str(root),
        env={"MWE_SCENARIO_DIR": str(root / "scenarios")},
    )


def resolve_mwe_launch_spec(repo_root_path: Path | None = None) -> ProcessLaunchSpec:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    ui_dir = root / "ui"
    package_json_path = ui_dir / "package.json"
    if not package_json_path.exists():
        raise FileNotFoundError(f"UI package.json not found: {package_json_path}")
    payload = json.loads(package_json_path.read_text(encoding="utf-8"))
    scripts = payload.get("scripts")
    if not isinstance(scripts, dict) or not str(scripts.get("dev") or "").strip():
        raise RuntimeError("UI package.json does not expose a dev script.")
    return ProcessLaunchSpec(
        name="MWE",
        command=["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "4175"],
        cwd=str(ui_dir),
    )


class ManagedProcessController:
    def __init__(
        self,
        *,
        repo_root_path: Path | None = None,
        log_sink: Callable[[str], None] | None = None,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        bridge_probe: Callable[[str], bool] = probe_bridge,
        stream_output: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root_path) if repo_root_path is not None else repo_root()
        self.log_sink = log_sink or (lambda _message: None)
        self.popen_factory = popen_factory
        self.bridge_probe = bridge_probe
        self.stream_output = bool(stream_output)
        self._managed: Dict[str, Any] = {}

    def managed_processes(self) -> Dict[str, Any]:
        self._prune_finished()
        return dict(self._managed)

    def launch_bridge(self, bridge_uri: str = DEFAULT_BRIDGE_URI) -> ProcessControlResult:
        self._prune_finished()
        if self._is_running("bridge"):
            return self._result("pass", "Bridge already running (managed).", ["bridge already running"])
        if self.bridge_probe(bridge_uri):
            return self._result("pass", "Bridge already running.", ["bridge already running"])
        try:
            spec = resolve_bridge_launch_spec(self.repo_root)
        except Exception as exc:
            return self._result("error", "Unable to resolve bridge launch command.", [str(exc)])
        return self._launch("bridge", spec, "launched bridge process")

    def launch_mwe(self, bridge_uri: str = DEFAULT_BRIDGE_URI) -> ProcessControlResult:
        self._prune_finished()
        if self._is_running("mwe"):
            return self._result("pass", "MWE UI already running (managed).", ["mwe already running"])
        if not self.bridge_probe(bridge_uri) and not self._is_running("bridge"):
            bridge_result = self.launch_bridge(bridge_uri)
            if not bridge_result.ok and not self.bridge_probe(bridge_uri):
                return ProcessControlResult(
                    ok=False,
                    status="fail",
                    summary="Bridge is required before launching MWE.",
                    logs=list(bridge_result.logs),
                    command=list(bridge_result.command),
                )
        try:
            spec = resolve_mwe_launch_spec(self.repo_root)
        except Exception as exc:
            return self._result("error", "Unable to resolve MWE launch command.", [str(exc)])
        return self._launch("mwe", spec, "launched MWE UI process")

    def stop_managed_processes(self) -> ProcessControlResult:
        self._prune_finished()
        if not self._managed:
            return self._result("pass", "No managed processes were running.", ["no managed processes to stop"])

        logs: List[str] = []
        for key, proc in list(self._managed.items()):
            label = "Bridge" if key == "bridge" else "MWE"
            try:
                proc.terminate()
                wait_fn = getattr(proc, "wait", None)
                if callable(wait_fn):
                    try:
                        wait_fn(timeout=2.0)
                    except Exception:
                        kill_fn = getattr(proc, "kill", None)
                        if callable(kill_fn):
                            kill_fn()
                        wait_fn(timeout=2.0)
                logs.append(f"stopped managed process: {label}")
            finally:
                self._managed.pop(key, None)
        return self._result("pass", "Stopped managed processes.", logs)

    def _launch(self, key: str, spec: ProcessLaunchSpec, success_log: str) -> ProcessControlResult:
        try:
            proc = self.popen_factory(
                spec.command,
                cwd=spec.cwd,
                env={**os.environ, **spec.env},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            return self._result("error", f"Failed to launch {spec.name}.", [str(exc)], spec.command)

        self._managed[key] = proc
        if self.stream_output:
            self._start_stream_thread(spec.name, proc)
        return self._result("pass", f"{spec.name} launched.", [success_log], spec.command)

    def _start_stream_thread(self, label: str, proc: Any) -> None:
        stream = getattr(proc, "stdout", None)
        if stream is None:
            return

        def pump() -> None:
            try:
                for raw_line in stream:
                    text = str(raw_line or "").rstrip()
                    if text:
                        self.log_sink(f"[{label}] {text}")
            except Exception:
                return

        threading.Thread(target=pump, name=f"operations-console-{label.lower()}-log", daemon=True).start()

    def _prune_finished(self) -> None:
        for key, proc in list(self._managed.items()):
            poll_fn = getattr(proc, "poll", None)
            if callable(poll_fn) and poll_fn() is not None:
                self._managed.pop(key, None)

    def _is_running(self, key: str) -> bool:
        proc = self._managed.get(key)
        if proc is None:
            return False
        poll_fn = getattr(proc, "poll", None)
        return not callable(poll_fn) or poll_fn() is None

    def _result(
        self,
        status: str,
        summary: str,
        logs: List[str] | None = None,
        command: List[str] | None = None,
    ) -> ProcessControlResult:
        for line in logs or []:
            self.log_sink(line)
        return ProcessControlResult(
            ok=status not in {"fail", "error"},
            status=status,
            summary=summary,
            logs=list(logs or []),
            command=list(command or []),
        )
