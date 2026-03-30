from __future__ import annotations

import json
from pathlib import Path

from tools.operations_console.process_control import (
    ManagedProcessController,
    load_gui_action_matrix,
    resolve_bridge_launch_spec,
    resolve_mwe_launch_spec,
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


def test_resolve_mwe_launch_spec_uses_ui_dev_command(tmp_path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")

    spec = resolve_mwe_launch_spec(tmp_path)

    assert spec.cwd == str(ui_dir)
    assert spec.command == ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "4175"]


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

    controller = ManagedProcessController(
        repo_root_path=tmp_path,
        popen_factory=fake_popen,
        bridge_probe=lambda _uri: False,
        stream_output=False,
    )

    result = controller.launch_mwe()

    assert result.status == "pass"
    assert len(calls) == 2
    assert calls[0][0] == "python"
    assert calls[1][:3] == ["npm", "run", "dev"]


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
