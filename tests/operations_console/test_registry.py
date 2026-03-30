from __future__ import annotations

import json
import subprocess

import pytest

from tools.operations_console.models import ConsoleAction, ConsoleRunContext
from tools.operations_console.registry import (
    ActionRegistry,
    DEFAULT_CATEGORIES,
    build_default_registry,
    resolve_target_scenario,
    run_orl_all_green_check,
    run_orl_replay_validation,
    run_orl_ui_build_check,
    run_orl_scenario_integrity,
    run_orl_snapshot_smoke,
    validate_loaded_scenario_payload,
)
from tools.operations_console.runner_utils import make_result


def _dummy_action(name: str = "Utilities / Dummy", category: str = "Utilities") -> ConsoleAction:
    return ConsoleAction(
        name=name,
        category=category,
        description="Dummy action for registry tests.",
        runner=lambda _context: make_result(name=name, status="pass", summary="ok"),
    )


def test_registry_registers_and_looks_up_actions() -> None:
    registry = ActionRegistry()
    action = _dummy_action()

    registered = registry.register(action)

    assert registered is action
    assert registry.get(action.name) is action
    assert registry.list_actions() == [action]
    assert registry.list_entries() == [action]
    assert "Utilities" in registry.categories()


def test_registry_rejects_duplicate_action_names() -> None:
    registry = ActionRegistry()
    registry.register(_dummy_action())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_dummy_action())


def test_default_registry_exposes_expected_categories_and_connectivity_action() -> None:
    registry = build_default_registry()

    assert registry.categories()[: len(DEFAULT_CATEGORIES)] == list(DEFAULT_CATEGORIES)
    assert {action.category for action in registry.list_actions()} >= set(DEFAULT_CATEGORIES)

    connectivity = registry.get("ORL / Connectivity")
    assert connectivity is not None
    assert connectivity.category == "ORL"
    assert "bridge" in connectivity.description.lower()

    integrity = registry.get("ORL / Scenario Integrity")
    assert integrity is not None
    assert integrity.category == "ORL"
    assert "scenario" in integrity.description.lower()

    smoke_suite = registry.get_suite("ORL / Smoke Suite")
    assert smoke_suite is not None
    assert smoke_suite.category == "ORL"
    assert smoke_suite.action_names == ["ORL / Connectivity", "ORL / Scenario Integrity"]
    assert smoke_suite in registry.list_suites()

    ui_build = registry.get("ORL / UI Build Check")
    assert ui_build is not None
    assert ui_build.category == "ORL"
    assert "build" in ui_build.description.lower()

    demo_readiness = registry.get_suite("ORL / Demo Readiness")
    assert demo_readiness is not None
    assert demo_readiness.category == "ORL"
    assert demo_readiness.action_names == ["ORL / Smoke Suite", "ORL / UI Build Check"]

    replay_validation = registry.get("ORL / Replay Validation")
    assert replay_validation is not None
    assert replay_validation.category == "ORL"

    snapshot_smoke = registry.get("ORL / Snapshot Smoke")
    assert snapshot_smoke is not None
    assert snapshot_smoke.category == "ORL"

    all_green = registry.get("ORL / All-Green Check")
    assert all_green is not None
    assert all_green.category == "ORL"

    core_validation = registry.get_suite("ORL / Core Validation Suite")
    assert core_validation is not None
    assert core_validation.action_names == [
        "ORL / Smoke Suite",
        "ORL / Replay Validation",
        "ORL / Snapshot Smoke",
        "ORL / All-Green Check",
    ]


def test_resolve_target_scenario_uses_requested_name_stem_or_first_available() -> None:
    scenarios = ["inchon_mvp.json", "mini_gc_1942.json"]

    assert resolve_target_scenario(scenarios, "") == "inchon_mvp.json"
    assert resolve_target_scenario(scenarios, "mini_gc_1942") == "mini_gc_1942.json"
    assert resolve_target_scenario(scenarios, "inchon_mvp.json") == "inchon_mvp.json"
    assert resolve_target_scenario(scenarios, "missing") is None


def test_validate_loaded_scenario_payload_accepts_current_repo_shape() -> None:
    payload = {
        "id": "inchon_mvp",
        "name": "inchon_mvp.json",
        "scenario": {
            "id": "inchon_mvp",
            "name": "Inchon Demo Vertical Slice",
            "units": [
                {
                    "id": "US-1MAR",
                    "name": "1st Marine Division",
                    "location_id": "INCHON_PORT",
                }
            ],
        },
    }

    summary = validate_loaded_scenario_payload(payload)

    assert summary["scenario_id"] == "inchon_mvp"
    assert summary["scenario_name"] == "Inchon Demo Vertical Slice"
    assert summary["unit_count"] == 1
    assert summary["valid_unit_count"] == 1


def test_validate_loaded_scenario_payload_rejects_units_without_identity_and_location() -> None:
    payload = {
        "scenario": {
            "id": "bad_scenario",
            "name": "Bad Scenario",
            "units": [
                {
                    "fatigue": 10,
                }
            ],
        }
    }

    with pytest.raises(RuntimeError, match="identity and position/location"):
        validate_loaded_scenario_payload(payload)


def test_run_orl_scenario_integrity_uses_mocked_bridge_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run(_uri: str, requested_scenario: str = "") -> dict:
        assert requested_scenario == "inchon_mvp"
        return {
            "scenario_count": 2,
            "selected_scenario": "inchon_mvp.json",
            "requested_scenario": requested_scenario,
            "scenario_id": "inchon_mvp",
            "scenario_name": "Inchon Demo Vertical Slice",
            "unit_count": 6,
            "valid_unit_count": 6,
        }

    monkeypatch.setattr("tools.operations_console.registry._run_scenario_integrity_check", fake_run)

    logs: list[str] = []
    result = run_orl_scenario_integrity(
        ConsoleRunContext(
            action_name="ORL / Scenario Integrity",
            category="ORL",
            scenario_name="inchon_mvp",
            bridge_uri="ws://127.0.0.1:8766",
            log=logs.append,
        )
    )

    assert result.status == "pass"
    assert "Scenario integrity passed" in result.summary
    assert any("Selected scenario: inchon_mvp.json" in line for line in logs)
    assert any("Validated units: 6 total, 6 with basic identity/location fields" in line for line in logs)


def test_run_orl_ui_build_check_reports_success(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    ui_dir = tmp_path / "ui"
    dist_dir = ui_dir / "dist"
    dist_dir.mkdir(parents=True)
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}), encoding="utf-8")
    artifact_path = dist_dir / "index.html"
    artifact_path.write_text("<html></html>", encoding="utf-8")

    completed = subprocess.CompletedProcess(
        args=["npm", "run", "build"],
        returncode=0,
        stdout="vite v7 build complete\n",
        stderr="",
    )
    monkeypatch.setattr("tools.operations_console.registry.resolve_ui_directory", lambda: ui_dir)
    monkeypatch.setattr("tools.operations_console.registry.subprocess.run", lambda *args, **kwargs: completed)

    logs: list[str] = []
    result = run_orl_ui_build_check(
        ConsoleRunContext(
            action_name="ORL / UI Build Check",
            category="ORL",
            log=logs.append,
        )
    )

    assert result.status == "pass"
    assert result.artifact_paths == [str(artifact_path)]
    assert any("package.json found" in line for line in logs)
    assert any("UI build completed" in line for line in logs)


def test_run_orl_ui_build_check_reports_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}), encoding="utf-8")

    completed = subprocess.CompletedProcess(
        args=["npm", "run", "build"],
        returncode=2,
        stdout="",
        stderr="build failed\n",
    )
    monkeypatch.setattr("tools.operations_console.registry.resolve_ui_directory", lambda: ui_dir)
    monkeypatch.setattr("tools.operations_console.registry.subprocess.run", lambda *args, **kwargs: completed)

    result = run_orl_ui_build_check(
        ConsoleRunContext(
            action_name="ORL / UI Build Check",
            category="ORL",
        )
    )

    assert result.status == "fail"
    assert result.summary == "UI build check failed."
    assert result.errors == ["Build command exited with code 2."]


def test_run_orl_ui_build_check_handles_unreadable_package_json(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "package.json").write_text("{not valid json", encoding="utf-8")

    monkeypatch.setattr("tools.operations_console.registry.resolve_ui_directory", lambda: ui_dir)

    result = run_orl_ui_build_check(
        ConsoleRunContext(
            action_name="ORL / UI Build Check",
            category="ORL",
        )
    )

    assert result.status == "error"
    assert result.summary == "UI build check hit an unexpected error."
    assert result.executed_command == ["npm", "run", "build"]
    assert result.errors


def test_adapter_backed_orl_actions_surface_adapter_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdapter:
        def __init__(self, repo_root=None):
            self.repo_root = repo_root

        def replay_validation(self, scenario_name: str = ""):
            return _adapter_result("replay_validation", scenario_name, ["/tmp/replay-a.json"])

        def snapshot_smoke(self, scenario_name: str = ""):
            return _adapter_result("snapshot_smoke", scenario_name, ["/tmp/snapshot.json"])

        def run_all_green(self):
            return _adapter_result("run_all_green", "", [], command=["pytest", "-q", "tests/test_inchon_scenario_stub.py"], return_code=0)

    monkeypatch.setattr("tools.operations_console.registry.EngineTestingAPI", FakeAdapter)

    replay = run_orl_replay_validation(
        ConsoleRunContext(
            action_name="ORL / Replay Validation",
            category="ORL",
            scenario_name="inchon_mvp",
        )
    )
    snapshot = run_orl_snapshot_smoke(
        ConsoleRunContext(
            action_name="ORL / Snapshot Smoke",
            category="ORL",
            scenario_name="inchon_mvp",
        )
    )
    all_green = run_orl_all_green_check(
        ConsoleRunContext(
            action_name="ORL / All-Green Check",
            category="ORL",
        )
    )

    assert replay.status == "pass"
    assert replay.adapter_method == "replay_validation"
    assert replay.artifact_paths == ["/tmp/replay-a.json"]
    assert snapshot.adapter_method == "snapshot_smoke"
    assert all_green.executed_command == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert all_green.return_code == 0


def _adapter_result(method: str, scenario_name: str, artifacts: list[str], command: list[str] | None = None, return_code: int | None = None):
    from engine.testing_api import TestingApiResult

    logs = [f"{method} invoked", f"scenario={scenario_name or '<default>'}"]
    return TestingApiResult(
        ok=True,
        data={"scenario_name": scenario_name},
        artifacts=artifacts,
        logs=logs,
        adapter_method=method,
        executed_command=command or [],
        return_code=return_code,
    )
