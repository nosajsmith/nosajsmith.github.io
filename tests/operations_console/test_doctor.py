from __future__ import annotations

import json
from pathlib import Path

from tools.operations_console.doctor import run_doctor, run_doctor_console_result


def _write_command_registry(root: Path) -> None:
    path = root / "tools" / "operations_console" / "command_registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "directories": [
                    {"id": "repo_root", "label": "Repo Root", "path": "."},
                    {"id": "ui_dir", "label": "UI Directory", "path": "ui"},
                    {"id": "bridge_dir", "label": "Bridge Directory", "path": "server"},
                    {"id": "artifacts_dir", "label": "Artifacts Directory", "path": "artifacts/operations_console", "create_if_missing": True},
                ],
                "commands": [
                    {
                        "id": "repo_terminal",
                        "label": "Open Repo Terminal",
                        "provider": "directory",
                        "directory": "repo_root",
                        "keep_open": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_run_doctor_warns_when_bridge_and_artifacts_are_unavailable(tmp_path) -> None:
    result = run_doctor(
        bridge_uri="ws://127.0.0.1:8766",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}" if name in {"git", "python", "pytest", "node", "npm"} else None,
        bridge_probe=lambda _uri: False,
        import_fn=lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)) if name == "websockets" else object(),
    )

    assert result.status == "fail"
    assert any(check.label == "Bridge URI" and check.status == "pass" for check in result.checks)
    assert any(check.label == "Bridge Reachability" and check.status == "warn" for check in result.checks)
    assert any(check.label == "Required Paths" and check.status == "fail" for check in result.checks)
    assert any(check.label == "Artifact Directory" and check.status == "pass" for check in result.checks)
    assert any(check.label == "Tooling Commands" and check.status == "pass" for check in result.checks)
    assert any(check.label == "Konsole Availability" and check.status == "warn" for check in result.checks)
    assert any(check.label == "Command Registry" and check.status == "fail" for check in result.checks)
    assert any(check.label == "Python Modules" and check.status == "warn" for check in result.checks)
    assert any(line.startswith("doctor summary: ") for line in result.logs)


def test_run_doctor_passes_when_environment_checks_are_satisfied(tmp_path) -> None:
    (tmp_path / "server").mkdir()
    (tmp_path / "server" / "mwe_bridge_p8_ws15.py").write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "package.json").write_text('{"scripts":{"dev":"vite"}}\n', encoding="utf-8")
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "tools" / "operations_console").mkdir(parents=True)
    (tmp_path / "artifacts" / "operations_console").mkdir(parents=True)
    _write_command_registry(tmp_path)

    result = run_doctor(
        bridge_uri="ws://127.0.0.1:8766",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}",
        bridge_probe=lambda _uri: True,
        import_fn=lambda _name: object(),
    )

    assert result.status == "pass"
    assert result.summary == "mwe doctor completed with status PASS."
    assert all(check.status == "pass" for check in result.checks)
    assert "doctor summary: 8 pass, 0 warn, 0 fail" in result.logs


def test_run_doctor_console_result_surfaces_subresults_and_logs(tmp_path) -> None:
    console_result = run_doctor_console_result(
        bridge_uri="ws://127.0.0.1:8766",
        scenario_name="inchon_mvp",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}" if name in {"git", "python", "pytest", "node", "npm"} else None,
        bridge_probe=lambda _uri: False,
        import_fn=lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)) if name == "websockets" else object(),
    )

    assert console_result.name == "Utilities / mwe doctor"
    assert console_result.scenario_name == "inchon_mvp"
    assert console_result.subresults
    assert any(item.name == "Bridge URI" for item in console_result.subresults)
    assert any(item.name == "Bridge Reachability" for item in console_result.subresults)
    assert any(line.startswith("doctor check failed: Required Paths") for line in console_result.details)
    assert any(line.startswith("doctor summary: ") for line in console_result.details)
