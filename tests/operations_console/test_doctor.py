from __future__ import annotations

from tools.operations_console.doctor import run_doctor, run_doctor_console_result


def test_run_doctor_warns_when_bridge_and_artifacts_are_unavailable(tmp_path) -> None:
    result = run_doctor(
        bridge_uri="ws://127.0.0.1:8766",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}" if name in {"git", "python", "pytest", "node", "npm"} else None,
        bridge_probe=lambda _uri: False,
    )

    assert result.status == "fail"
    assert any(check.label == "Bridge Reachability" and check.status == "warn" for check in result.checks)
    assert any(check.label == "Required Paths" and check.status == "fail" for check in result.checks)
    assert any(check.label == "Artifact Directory" and check.status == "warn" for check in result.checks)
    assert any(check.label == "Basic Commands" and check.status == "warn" for check in result.checks)


def test_run_doctor_passes_when_environment_checks_are_satisfied(tmp_path) -> None:
    (tmp_path / "server").mkdir()
    (tmp_path / "server" / "mwe_bridge_p8_ws15.py").write_text("print('bridge')\n", encoding="utf-8")
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "package.json").write_text('{"scripts":{"dev":"vite"}}\n', encoding="utf-8")
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "tools" / "operations_console").mkdir(parents=True)
    (tmp_path / "artifacts" / "operations_console").mkdir(parents=True)

    result = run_doctor(
        bridge_uri="ws://127.0.0.1:8766",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}",
        bridge_probe=lambda _uri: True,
    )

    assert result.status == "pass"
    assert result.summary == "mwe doctor completed with status PASS."
    assert all(check.status == "pass" for check in result.checks)


def test_run_doctor_console_result_surfaces_subresults_and_logs(tmp_path) -> None:
    console_result = run_doctor_console_result(
        bridge_uri="ws://127.0.0.1:8766",
        scenario_name="inchon_mvp",
        repo_root_path=tmp_path,
        which_fn=lambda name: f"/usr/bin/{name}" if name in {"git", "python", "pytest", "node", "npm"} else None,
        bridge_probe=lambda _uri: False,
    )

    assert console_result.name == "Utilities / mwe doctor"
    assert console_result.scenario_name == "inchon_mvp"
    assert console_result.subresults
    assert any(item.name == "Bridge Reachability" for item in console_result.subresults)
    assert any("Bridge Reachability:" in line for line in console_result.details)
