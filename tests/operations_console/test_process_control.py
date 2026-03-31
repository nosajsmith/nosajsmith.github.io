from __future__ import annotations

import json
from pathlib import Path

from tools.operations_console.process_control import (
    ManagedProcessController,
    load_gui_action_matrix,
    resolve_bridge_endpoint,
    resolve_bridge_launch_spec,
    resolve_mwe_launch_spec,
    resolve_mwe_ui_url,
)


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = []
        self._returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self._returncode

    def terminate(self):
        self.terminated = True
        self._returncode = 0

    def kill(self):
        self.killed = True
        self._returncode = -9

    def wait(self, timeout=None):
        self._returncode = self._returncode if self._returncode is not None else 0
        return self._returncode


def test_resolve_bridge_launch_spec_uses_repo_canonical_bridge_path(tmp_path) -> None:
    bridge_path = tmp_path / "server" / "mwe_bridge_p8_ws15.py"
    bridge_path.parent.mkdir(parents=True)
    bridge_path.write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "scenarios").mkdir()

    spec = resolve_bridge_launch_spec(tmp_path)

    assert spec.command[:2] == ["python", str(bridge_path)]
    assert "--port" in spec.command
    assert spec.env["MWE_SCENARIO_DIR"] == str(tmp_path / "scenarios")


def test_resolve_bridge_launch_spec_uses_current_bridge_uri_host_and_port(tmp_path) -> None:
    bridge_path = tmp_path / "server" / "mwe_bridge_p8_ws15.py"
    bridge_path.parent.mkdir(parents=True)
    bridge_path.write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "scenarios").mkdir()

    spec = resolve_bridge_launch_spec(tmp_path, "ws://0.0.0.0:9100")

    assert spec.command == [
        "python",
        str(bridge_path),
        "--host",
        "0.0.0.0",
        "--port",
        "9100",
        "--health-port",
        "9105",
    ]


def test_resolve_mwe_launch_spec_uses_ui_dev_command(tmp_path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")

    spec = resolve_mwe_launch_spec(tmp_path)

    assert spec.cwd == str(ui_dir)
    assert spec.command == ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "4175"]
    assert spec.env["VITE_BRIDGE_URL"] == "ws://127.0.0.1:8766"
    assert spec.env["VITE_BRIDGE_HOST"] == "127.0.0.1"
    assert spec.env["VITE_BRIDGE_PORT"] == "8766"
    assert resolve_mwe_ui_url() == "http://127.0.0.1:4175"


def test_resolve_bridge_endpoint_normalizes_missing_scheme() -> None:
    endpoint = resolve_bridge_endpoint("localhost:9010")

    assert endpoint.uri == "ws://localhost:9010"
    assert endpoint.host == "localhost"
    assert endpoint.port == 9010
    assert endpoint.health_port == 9015


def test_launch_bridge_skips_duplicate_when_bridge_reachable() -> None:
    calls: list[list[str]] = []
    logs: list[str] = []

    def fake_popen(*args, **kwargs):
        calls.append(list(args[0]))
        return FakeProcess()

    controller = ManagedProcessController(
        repo_root_path=Path("/tmp/mwe"),
        log_sink=logs.append,
        popen_factory=fake_popen,
        bridge_probe=lambda _uri: True,
        stream_output=False,
    )

    result = controller.launch_bridge()

    assert result.status == "pass"
    assert calls == []
    assert any("bridge already running" in line for line in logs)


def test_launch_bridge_fails_if_spawned_process_never_becomes_reachable(tmp_path) -> None:
    bridge_path = tmp_path / "server" / "mwe_bridge_p8_ws15.py"
    bridge_path.parent.mkdir(parents=True)
    bridge_path.write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "scenarios").mkdir()

    calls: list[list[str]] = []

    def fake_popen(*args, **kwargs):
        calls.append(list(args[0]))
        return FakeProcess()

    controller = ManagedProcessController(
        repo_root_path=tmp_path,
        popen_factory=fake_popen,
        bridge_probe=lambda _uri: False,
        stream_output=False,
        sleep_fn=lambda _seconds: None,
        bridge_wait_timeout_s=0.2,
        bridge_wait_interval_s=0.1,
    )

    result = controller.launch_bridge()

    assert result.status == "fail"
    assert result.summary == "Bridge launched but did not become reachable."
    assert len(calls) == 1
    assert calls[0][0] == "python"
    assert any("did not become reachable" in line for line in result.logs)


def test_launch_mwe_starts_bridge_then_ui_when_bridge_is_down(tmp_path) -> None:
    bridge_path = tmp_path / "server" / "mwe_bridge_p8_ws15.py"
    bridge_path.parent.mkdir(parents=True)
    bridge_path.write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "scenarios").mkdir()
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")

    calls: list[list[str]] = []

    def fake_popen(*args, **kwargs):
        calls.append(list(args[0]))
        return FakeProcess()

    probe_results = iter([False, False, True, True])

    controller = ManagedProcessController(
        repo_root_path=tmp_path,
        popen_factory=fake_popen,
        bridge_probe=lambda _uri: next(probe_results),
        stream_output=False,
        sleep_fn=lambda _seconds: None,
        bridge_wait_timeout_s=0.2,
        bridge_wait_interval_s=0.1,
    )

    result = controller.launch_mwe()

    assert result.status == "pass"
    assert len(calls) == 2
    assert calls[0][0] == "python"
    assert calls[1][:3] == ["npm", "run", "dev"]
    assert any("ui url: http://127.0.0.1:4175" in line for line in result.logs)


def test_launch_mwe_fails_if_bridge_never_becomes_reachable(tmp_path) -> None:
    bridge_path = tmp_path / "server" / "mwe_bridge_p8_ws15.py"
    bridge_path.parent.mkdir(parents=True)
    bridge_path.write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "scenarios").mkdir()
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")

    calls: list[list[str]] = []

    def fake_popen(*args, **kwargs):
        calls.append(list(args[0]))
        return FakeProcess()

    controller = ManagedProcessController(
        repo_root_path=tmp_path,
        popen_factory=fake_popen,
        bridge_probe=lambda _uri: False,
        stream_output=False,
        sleep_fn=lambda _seconds: None,
        bridge_wait_timeout_s=0.2,
        bridge_wait_interval_s=0.1,
    )

    result = controller.launch_mwe()

    assert result.status == "fail"
    assert result.summary == "Bridge is required before launching MWE."
    assert len(calls) == 1
    assert calls[0][0] == "python"


def test_stop_managed_processes_only_terminates_managed() -> None:
    controller = ManagedProcessController(
        repo_root_path=Path("/tmp/mwe"),
        bridge_probe=lambda _uri: False,
        stream_output=False,
    )
    bridge_proc = FakeProcess()
    mwe_proc = FakeProcess()
    controller._managed["bridge"] = bridge_proc
    controller._managed["mwe"] = mwe_proc
    unrelated = FakeProcess()

    result = controller.stop_managed_processes()

    assert result.status == "pass"
    assert bridge_proc.terminated is True
    assert mwe_proc.terminated is True
    assert unrelated.terminated is False
    assert controller.managed_processes() == {}


def test_load_gui_action_matrix_parses_seed_file() -> None:
    payload = load_gui_action_matrix()

    ids = {row["id"] for row in payload["actions"]}
    assert "refresh-scenarios" in ids
    assert "run-bridge" in ids
    assert "run-mwe" in ids
