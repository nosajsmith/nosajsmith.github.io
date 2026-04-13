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
    run_orl_demo_artifact_validation,
    run_orl_demo_checklist,
    run_orl_deterministic_demo_runner,
    run_orl_latest_artifacts,
    run_orl_pitch_support_bundle,
    run_orl_round1_gate,
    run_open_artifacts_konsole,
    run_open_bridge_konsole,
    run_open_repo_konsole,
    run_open_ui_konsole,
    run_mwe_doctor,
    run_orl_all_green_check,
    run_orl_explainability_smoketest,
    run_selected_command_in_konsole,
    run_orl_replay_validation,
    run_orl_scenario_matrix,
    run_orl_scenario_validator,
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
    assert demo_readiness.action_names == [
        "ORL / Smoke Suite",
        "ORL / UI Build Check",
        "ORL / Deterministic Demo Runner",
        "ORL / Demo Artifact Validation",
    ]

    replay_validation = registry.get("ORL / Replay Validation")
    assert replay_validation is not None
    assert replay_validation.category == "ORL"

    assert registry.get("ORL / Deterministic Demo Runner") is not None
    assert registry.get("ORL / Demo Artifact Validation") is not None
    assert registry.get("ORL / Demo Checklist") is not None
    assert registry.get("ORL / Latest Artifacts") is not None
    assert registry.get("ORL / Pitch Support Bundle") is not None

    snapshot_smoke = registry.get("ORL / Snapshot Smoke")
    assert snapshot_smoke is not None
    assert snapshot_smoke.category == "ORL"

    all_green = registry.get("ORL / All-Green Check")
    assert all_green is not None
    assert all_green.category == "ORL"

    assert registry.get("ORL / Scenario Validator") is not None
    assert registry.get("ORL / Scenario Matrix") is not None
    assert registry.get("ORL / Explainability Smoketest") is not None
    assert registry.get("ORL / Round 1 Gate") is not None

    core_validation = registry.get_suite("ORL / Core Validation Suite")
    assert core_validation is not None
    assert core_validation.action_names == [
        "ORL / Smoke Suite",
        "ORL / Replay Validation",
        "ORL / Snapshot Smoke",
        "ORL / All-Green Check",
    ]

    connectivity_matrix = registry.matrix_entry_for_label("ORL / Connectivity")
    assert connectivity_matrix is not None
    assert connectivity_matrix.description
    assert connectivity_matrix.runner == "registry.run_orl_connectivity"
    assert connectivity_matrix.category == "ORL"
    assert connectivity_matrix.enabled is True
    assert "scenario_name" not in connectivity_matrix.inputs

    integrity_matrix = registry.matrix_entry_for_label("ORL / Scenario Integrity")
    assert integrity_matrix is not None
    assert "scenario_name" in integrity_matrix.inputs

    smoke_matrix = registry.matrix_entry_for_label("ORL / Smoke Suite")
    assert smoke_matrix is not None
    assert "scenario_name" in smoke_matrix.inputs

    process_control_matrix = registry.matrix_entry_for_id("run-bridge")
    assert process_control_matrix is not None
    assert process_control_matrix.label == "Run Bridge"
    assert process_control_matrix.category == "Process Control"
    assert process_control_matrix.description

    replay_validation = registry.matrix_entry_for_label("ORL / Replay Validation")
    assert replay_validation is not None
    assert replay_validation.runner == "registry.run_orl_replay_validation"

    core_validation = registry.matrix_entry_for_label("ORL / Core Validation Suite")
    assert core_validation is not None
    assert core_validation.runner == "runner_utils.run_suite"
    assert "scenario_name" in core_validation.inputs

    assert registry.get("Utilities / Open Repo Konsole") is not None
    assert registry.get("Utilities / Open UI Konsole") is not None
    assert registry.get("Utilities / Open Bridge Konsole") is not None
    assert registry.get("Utilities / Open Artifacts Konsole") is not None
    assert registry.get("Utilities / Tail Latest Logs in Konsole") is not None
    assert registry.get("Utilities / Run Selected Command in Konsole") is not None
    assert registry.get("Utilities / mwe doctor") is not None
    assert {
        "repo_terminal",
        "ui_terminal",
        "bridge_terminal",
        "artifacts_terminal",
        "bridge_launch",
        "ui_launch",
        "artifacts_list",
        "tail_latest_logs",
    } <= set(registry.allowlisted_command_ids())


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

        def deterministic_demo_runner(self, scenario_name: str = ""):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=True,
                data={
                    "checks": [
                        {
                            "check_id": "demo.replay_compare",
                            "label": "Replay Compare",
                            "blocker_class": "demo.replay_compare",
                            "status": "pass",
                            "summary": "Replay compare passed.",
                            "artifacts": ["/tmp/replay.json", "/tmp/compare.json"],
                            "logs": ["replay ok"],
                        }
                    ]
                },
                artifacts=["/tmp/replay.json", "/tmp/compare.json"],
                logs=[f"deterministic scenario={scenario_name or '<default>'}"],
                adapter_method="deterministic_demo_runner",
            )

        def demo_artifact_validation(self):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=True,
                data={
                    "checks": [
                        {
                            "check_id": "artifact.demo_report",
                            "label": "Latest Demo Report",
                            "blocker_class": "demo.artifact_output",
                            "status": "pass",
                            "summary": "Latest Demo Report found.",
                            "artifacts": ["/tmp/demo-report.json"],
                            "logs": ["demo report ok"],
                        }
                    ]
                },
                artifacts=["/tmp/demo-artifact-shelf.json"],
                logs=["artifact shelf ok"],
                adapter_method="demo_artifact_validation",
            )

        def demo_checklist(self, scenario_name: str = ""):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=True,
                data={
                    "checks": [
                        {
                            "check_id": "checklist.smoke_suite",
                            "label": "Smoke Suite",
                            "blocker_class": "demo.checklist",
                            "status": "pass",
                            "summary": "Required checklist item.",
                            "artifacts": [],
                            "logs": ["smoke suite must pass"],
                        }
                    ],
                    "scenario_name": scenario_name,
                },
                artifacts=["/tmp/demo-checklist.json"],
                logs=["checklist ok"],
                adapter_method="demo_checklist",
            )

        def latest_artifacts(self):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=False,
                data={
                    "checks": [
                        {
                            "check_id": "latest.demo_report",
                            "label": "Latest Demo Report",
                            "blocker_class": "demo.latest_artifacts",
                            "status": "warn",
                            "summary": "Latest Demo Report: missing",
                            "artifacts": [],
                            "logs": ["path: <missing>"],
                        }
                    ]
                },
                artifacts=["/tmp/latest-demo-artifacts.json"],
                logs=["latest artifacts incomplete"],
                adapter_method="latest_artifacts",
            )

        def pitch_support_bundle(self, scenario_name: str = ""):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=True,
                data={
                    "checks": [
                        {
                            "check_id": "latest-orl-demo-readiness-report",
                            "label": "Latest ORL Demo Readiness Report",
                            "blocker_class": "support.pitch_support_bundle",
                            "status": "pass",
                            "summary": "Latest ORL Demo Readiness Report copied into the bundle.",
                            "artifacts": ["/tmp/pitch-support/reports/demo.json"],
                            "logs": ["report copied"],
                        }
                    ],
                    "bundle_dir": "/tmp/pitch-support",
                },
                artifacts=["/tmp/pitch-support/bundle_manifest.json"],
                logs=[f"bundle_dir: /tmp/pitch-support", f"selected scenario: {scenario_name or 'inchon_mvp'}"],
                adapter_method="pitch_support_bundle",
            )

        def scenario_validator(self):
            return _adapter_result("scenario_validator", "", ["/tmp/validator.json"])

        def scenario_matrix(self):
            return _adapter_result("scenario_matrix", "", ["/tmp/matrix.json"])

        def explainability_smoke(self):
            return _adapter_result("explainability_smoke", "", ["/tmp/explainability.json"])

        def round1_gate(self):
            from engine.testing_api import TestingApiResult

            return TestingApiResult(
                ok=True,
                data={
                    "checks": [
                        {
                            "check_id": "tooling.scenario_validator",
                            "label": "Scenario Validator",
                            "blocker_class": "tooling.scenario_validator",
                            "status": "pass",
                            "summary": "Scenario validator passed.",
                            "artifacts": ["/tmp/validator.json"],
                            "logs": ["validator ok"],
                        }
                    ]
                },
                artifacts=["/tmp/round1-gate.json"],
                logs=["gate ok"],
                adapter_method="round1_gate",
            )

    monkeypatch.setattr("tools.operations_console.registry.EngineTestingAPI", FakeAdapter)

    replay = run_orl_replay_validation(
        ConsoleRunContext(
            action_name="ORL / Replay Validation",
            category="ORL",
            scenario_name="inchon_mvp",
        )
    )
    deterministic_demo = run_orl_deterministic_demo_runner(
        ConsoleRunContext(
            action_name="ORL / Deterministic Demo Runner",
            category="ORL",
            scenario_name="inchon_mvp",
        )
    )
    demo_artifacts = run_orl_demo_artifact_validation(
        ConsoleRunContext(
            action_name="ORL / Demo Artifact Validation",
            category="ORL",
        )
    )
    checklist = run_orl_demo_checklist(
        ConsoleRunContext(
            action_name="ORL / Demo Checklist",
            category="ORL",
            scenario_name="inchon_mvp",
        )
    )
    latest_artifacts = run_orl_latest_artifacts(
        ConsoleRunContext(
            action_name="ORL / Latest Artifacts",
            category="ORL",
        )
    )
    pitch_bundle = run_orl_pitch_support_bundle(
        ConsoleRunContext(
            action_name="ORL / Pitch Support Bundle",
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
    validator = run_orl_scenario_validator(
        ConsoleRunContext(
            action_name="ORL / Scenario Validator",
            category="ORL",
        )
    )
    matrix = run_orl_scenario_matrix(
        ConsoleRunContext(
            action_name="ORL / Scenario Matrix",
            category="ORL",
        )
    )
    explainability = run_orl_explainability_smoketest(
        ConsoleRunContext(
            action_name="ORL / Explainability Smoketest",
            category="ORL",
        )
    )
    gate = run_orl_round1_gate(
        ConsoleRunContext(
            action_name="ORL / Round 1 Gate",
            category="ORL",
        )
    )

    assert replay.status == "pass"
    assert replay.adapter_method == "replay_validation"
    assert replay.artifact_paths == ["/tmp/replay-a.json"]
    assert deterministic_demo.adapter_method == "deterministic_demo_runner"
    assert deterministic_demo.subresults[0].name == "Replay Compare"
    assert demo_artifacts.adapter_method == "demo_artifact_validation"
    assert demo_artifacts.subresults[0].name == "Latest Demo Report"
    assert checklist.adapter_method == "demo_checklist"
    assert checklist.subresults[0].name == "Smoke Suite"
    assert latest_artifacts.status == "warn"
    assert latest_artifacts.adapter_method == "latest_artifacts"
    assert pitch_bundle.status == "pass"
    assert pitch_bundle.adapter_method == "pitch_support_bundle"
    assert pitch_bundle.subresults[0].name == "Latest ORL Demo Readiness Report"
    assert snapshot.adapter_method == "snapshot_smoke"
    assert all_green.executed_command == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert all_green.return_code == 0
    assert validator.artifact_paths == ["/tmp/validator.json"]
    assert matrix.adapter_method == "scenario_matrix"
    assert explainability.adapter_method == "explainability_smoke"
    assert gate.adapter_method == "round1_gate"
    assert gate.subresults[0].name == "Scenario Validator"
    assert gate.subresults[0].details[0] == "BLOCKER CLASS: tooling.scenario_validator"


def test_konsole_actions_use_allowlisted_launchers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResult:
        def __init__(self, summary: str, command_id: str = ""):
            self.ok = True
            self.status = "pass"
            self.summary = summary
            self.logs = [summary]
            self.command = ["konsole", "--workdir", "/tmp"]
            self.workdir = "/tmp"
            self.command_id = command_id

    directory_calls: list[tuple[str, str]] = []
    command_calls: list[tuple[str, str]] = []

    def fake_launch_directory(directory_id: str, *, label: str, **kwargs):
        directory_calls.append((directory_id, label))
        return FakeResult(f"opened {label.lower()} terminal")

    monkeypatch.setattr(
        "tools.operations_console.registry.launch_konsole_directory",
        fake_launch_directory,
    )
    def fake_launch_command(command_id: str, **kwargs):
        command_calls.append((command_id, str(kwargs.get("label") or "")))
        return FakeResult(f"ran {command_id}", command_id=command_id)

    monkeypatch.setattr("tools.operations_console.registry.launch_konsole_command", fake_launch_command)

    repo_result = run_open_repo_konsole(
        ConsoleRunContext(
            action_name="Utilities / Open Repo Konsole",
            category="Utilities",
        )
    )
    ui_result = run_open_ui_konsole(
        ConsoleRunContext(
            action_name="Utilities / Open UI Konsole",
            category="Utilities",
        )
    )
    bridge_result = run_open_bridge_konsole(
        ConsoleRunContext(
            action_name="Utilities / Open Bridge Konsole",
            category="Utilities",
        )
    )
    artifacts_result = run_open_artifacts_konsole(
        ConsoleRunContext(
            action_name="Utilities / Open Artifacts Konsole",
            category="Utilities",
        )
    )
    selected_result = run_selected_command_in_konsole(
        ConsoleRunContext(
            action_name="Utilities / Run Selected Command in Konsole",
            category="Utilities",
            command_id="bridge_launch",
        )
    )

    assert repo_result.status == "pass"
    assert repo_result.adapter_method == "konsole"
    assert repo_result.executed_command == ["konsole", "--workdir", "/tmp"]
    assert repo_result.summary == "opened repo terminal"
    assert ui_result.summary == "opened ui terminal"
    assert bridge_result.summary == "opened bridge terminal"
    assert artifacts_result.summary == "opened artifacts terminal"
    assert selected_result.status == "pass"
    assert selected_result.summary == "ran bridge_launch"
    assert directory_calls == [
        ("repo_root", "Repo"),
        ("ui_dir", "UI"),
        ("bridge_dir", "Bridge"),
        ("artifacts_dir", "Artifacts"),
    ]
    assert command_calls == [("bridge_launch", "Run Selected Command in Konsole")]


def test_run_mwe_doctor_delegates_to_doctor_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tools.operations_console.doctor.run_doctor_console_result",
        lambda **kwargs: make_result(
            name="Utilities / mwe doctor",
            status="pass",
            summary=f"doctor ran for {kwargs['scenario_name']}",
            scenario_name=kwargs["scenario_name"],
        ),
    )

    result = run_mwe_doctor(
        ConsoleRunContext(
            action_name="Utilities / mwe doctor",
            category="Utilities",
            scenario_name="inchon_mvp",
            bridge_uri="ws://127.0.0.1:8766",
        )
    )

    assert result.status == "pass"
    assert result.summary == "doctor ran for inchon_mvp"


def test_run_selected_command_in_konsole_warns_when_no_command_is_selected() -> None:
    result = run_selected_command_in_konsole(
        ConsoleRunContext(
            action_name="Utilities / Run Selected Command in Konsole",
            category="Utilities",
        )
    )

    assert result.status == "warn"
    assert result.summary == "No allowlisted Konsole command is selected."


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
