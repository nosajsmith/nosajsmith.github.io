from __future__ import annotations

from tools.operations_console.konsole_integration import (
    AllowlistedCommand,
    CommandRegistryCatalog,
    CommandRegistryDirectory,
    KonsoleLaunchSpec,
    build_konsole_command,
    detect_konsole,
    launch_konsole_command,
    launch_konsole_directory,
    resolve_allowlisted_command,
    resolve_working_directory,
)
from tools.operations_console.process_control import ProcessLaunchSpec


def _catalog(tmp_path) -> CommandRegistryCatalog:
    return CommandRegistryCatalog(
        version=1,
        directories=[
            CommandRegistryDirectory(entry_id="repo_root", label="Repo Root", path="."),
            CommandRegistryDirectory(entry_id="artifacts_dir", label="Artifacts", path="artifacts/operations_console", create_if_missing=True),
            CommandRegistryDirectory(entry_id="logs_dir", label="Logs", path=""),
        ],
        commands=[
            AllowlistedCommand(
                command_id="repo_terminal",
                label="Open Repo Terminal",
                provider="directory",
                directory_id="repo_root",
            ),
            AllowlistedCommand(
                command_id="bridge_launch",
                label="Bridge Launch",
                provider="bridge_launch",
                directory_id="repo_root",
            ),
            AllowlistedCommand(
                command_id="artifacts_list",
                label="List Artifacts",
                provider="argv",
                directory_id="artifacts_dir",
                argv=["ls", "-lah"],
            ),
            AllowlistedCommand(
                command_id="tail_latest_logs",
                label="Tail Latest Logs",
                provider="tail_latest_logs",
                directory_id="logs_dir",
            ),
        ],
        source_path=str(tmp_path / "command_registry.yaml"),
    )


def test_detect_konsole_returns_path_from_which() -> None:
    assert detect_konsole(lambda name: "/usr/bin/konsole" if name == "konsole" else None) == "/usr/bin/konsole"


def test_build_konsole_command_uses_workdir_hold_and_bash_lc() -> None:
    spec = KonsoleLaunchSpec(
        label="Bridge Launch",
        cwd="/tmp/repo",
        argv=["python", "server/mwe_bridge_p8_ws15.py", "--port", "8766"],
        env={"MWE_SCENARIO_DIR": "/tmp/repo/scenarios"},
        keep_open=True,
        command_id="bridge_launch",
    )

    command = build_konsole_command(spec, konsole_binary="/usr/bin/konsole")

    assert command[:3] == ["/usr/bin/konsole", "--workdir", "/tmp/repo"]
    assert "--hold" in command
    assert "-e" in command
    assert "bash" in command
    assert "-lc" in command
    script = command[-1]
    assert "export MWE_SCENARIO_DIR=" in script
    assert "python server/mwe_bridge_p8_ws15.py --port 8766" in script


def test_resolve_working_directory_creates_configured_artifacts_dir(tmp_path) -> None:
    catalog = _catalog(tmp_path)

    resolved = resolve_working_directory("artifacts_dir", catalog=catalog, repo_root_path=tmp_path)

    assert resolved.exists()
    assert resolved.is_dir()
    assert resolved == (tmp_path / "artifacts" / "operations_console").resolve()


def test_resolve_allowlisted_command_uses_bridge_provider(monkeypatch, tmp_path) -> None:
    catalog = _catalog(tmp_path)
    fake_spec = ProcessLaunchSpec(
        name="Bridge",
        command=["python", "server/mwe_bridge_p8_ws15.py", "--host", "127.0.0.1", "--port", "8766"],
        cwd=str(tmp_path),
        env={"MWE_SCENARIO_DIR": str(tmp_path / "scenarios")},
    )
    monkeypatch.setattr("tools.operations_console.process_control.resolve_bridge_launch_spec", lambda **kwargs: fake_spec)

    spec = resolve_allowlisted_command(
        "bridge_launch",
        catalog=catalog,
        repo_root_path=tmp_path,
        bridge_uri="ws://127.0.0.1:8766",
    )

    assert spec.command_id == "bridge_launch"
    assert spec.cwd == str(tmp_path)
    assert spec.argv == ["python", "server/mwe_bridge_p8_ws15.py", "--host", "127.0.0.1", "--port", "8766"]
    assert spec.env["MWE_SCENARIO_DIR"] == str(tmp_path / "scenarios")


def test_resolve_allowlisted_command_uses_directory_provider(tmp_path) -> None:
    catalog = _catalog(tmp_path)

    spec = resolve_allowlisted_command(
        "repo_terminal",
        catalog=catalog,
        repo_root_path=tmp_path,
    )

    assert spec.command_id == "repo_terminal"
    assert spec.cwd == str(tmp_path.resolve())
    assert spec.argv == []
    assert spec.keep_open is True


def test_launch_konsole_command_fails_cleanly_when_konsole_missing(tmp_path) -> None:
    catalog = _catalog(tmp_path)

    result = launch_konsole_command(
        "artifacts_list",
        label="Run Selected Command in Konsole",
        catalog=catalog,
        repo_root_path=tmp_path,
        which_fn=lambda _name: None,
    )

    assert result.status == "fail"
    assert result.summary == "Konsole is not installed or not found on PATH."
    assert "konsole not found" in result.logs


def test_launch_konsole_command_enforces_allowlist_and_warns_for_unavailable_logs(tmp_path) -> None:
    catalog = _catalog(tmp_path)

    unavailable = launch_konsole_command(
        "tail_latest_logs",
        label="Tail Latest Logs in Konsole",
        catalog=catalog,
        repo_root_path=tmp_path,
        which_fn=lambda _name: "/usr/bin/konsole",
        popen_factory=lambda *args, **kwargs: object(),
    )
    unknown = launch_konsole_command(
        "not_allowed",
        label="Run Selected Command in Konsole",
        catalog=catalog,
        repo_root_path=tmp_path,
        which_fn=lambda _name: "/usr/bin/konsole",
        popen_factory=lambda *args, **kwargs: object(),
    )

    assert unavailable.status == "warn"
    assert "tail logs command unavailable because no canonical log path configured" in unavailable.logs
    assert unknown.status == "fail"
    assert "Selected allowlisted Konsole command is not configured" in unknown.logs[-1]


def test_launch_konsole_command_opens_directory_workflow(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    launched = {}

    def fake_popen(command, *args, **kwargs):
        launched["command"] = command
        return object()

    result = launch_konsole_command(
        "repo_terminal",
        label="Open Repo Terminal",
        catalog=catalog,
        repo_root_path=tmp_path,
        which_fn=lambda _name: "/usr/bin/konsole",
        popen_factory=fake_popen,
    )

    assert result.status == "pass"
    assert result.command_id == "repo_terminal"
    assert launched["command"][:3] == ["/usr/bin/konsole", "--workdir", str(tmp_path.resolve())]


def test_launch_konsole_directory_uses_expected_workdir_and_command(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    launched = {}

    def fake_popen(command, *args, **kwargs):
        launched["command"] = command
        return object()

    result = launch_konsole_directory(
        "repo_root",
        label="Repo Konsole",
        catalog=catalog,
        repo_root_path=tmp_path,
        which_fn=lambda _name: "/usr/bin/konsole",
        popen_factory=fake_popen,
    )

    assert result.status == "pass"
    assert result.workdir == str(tmp_path.resolve())
    assert launched["command"][:3] == ["/usr/bin/konsole", "--workdir", str(tmp_path.resolve())]
