from __future__ import annotations

from tools.operations_console.app import OperationsConsoleApp
from tools.operations_console.gui_action_matrix import load_gui_action_matrix
from tools.operations_console.incident_log import AnomalyMatch, IncidentBundleResult
from tools.operations_console.models import ConsoleAction, ConsoleResult, KnownIssueMatch
from tools.operations_console.process_control import ProcessControlResult
from tools.operations_console.runner_utils import make_result


class DummyVar:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class DummyWidget(dict):
    def __init__(self) -> None:
        super().__init__()
        self.config = {}

    def configure(self, **kwargs) -> None:
        self.config.update(kwargs)


class DummyTree:
    def __init__(self, selection: tuple[str, ...] = ()) -> None:
        self._selection = selection

    def selection(self):
        return self._selection


class DummyRegistry:
    def get(self, name: str):
        return object() if name == "ORL / Connectivity" else None

    def command_registry(self):
        return None


class DummyCommandRegistry:
    def command_ids(self):
        return ["repo_terminal", "bridge_launch"]


def build_app_stub(*, scenario_value: str = "", selection: tuple[str, ...] = ("ORL / Connectivity",)):
    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.scenario_var = DummyVar(scenario_value)
    app.command_var = DummyVar("")
    app.status_var = DummyVar("IDLE")
    app.summary_var = DummyVar("Ready.")
    app.scenario_combo = DummyWidget()
    app.command_combo = DummyWidget()
    app.run_button = DummyWidget()
    app.clear_button = DummyWidget()
    app.export_button = DummyWidget()
    app.save_baseline_button = DummyWidget()
    app.compare_baseline_button = DummyWidget()
    app.refresh_scenarios_button = DummyWidget()
    app.bridge_button = DummyWidget()
    app.mwe_button = DummyWidget()
    app.stop_button = DummyWidget()
    app.status_badge = DummyWidget()
    app.tree = DummyTree(selection)
    app.registry = DummyRegistry()
    app.command_registry = None
    app.known_issues = None
    app.gui_action_matrix = None
    app.anomaly_catalog = None
    app.scenario_contracts = None
    app.worker = None
    app.last_result = None
    output: list[str] = []
    app._append_output = output.append
    return app, output


def test_apply_scenario_roster_selects_first_when_blank() -> None:
    app, _output = build_app_stub(scenario_value="")

    auto_selected = app._apply_scenario_roster(["inchon_mvp.json", "mini_gc_1942.json"])

    assert auto_selected is True
    assert app.scenario_combo["values"] == ("inchon_mvp.json", "mini_gc_1942.json")
    assert app.scenario_var.get() == "inchon_mvp.json"


def test_apply_scenario_roster_preserves_manual_entry() -> None:
    app, _output = build_app_stub(scenario_value="custom_scenario")

    auto_selected = app._apply_scenario_roster(["inchon_mvp.json", "mini_gc_1942.json"])

    assert auto_selected is False
    assert app.scenario_combo["values"] == ("inchon_mvp.json", "mini_gc_1942.json")
    assert app.scenario_var.get() == "custom_scenario"


def test_apply_command_options_requires_explicit_selection() -> None:
    app, _output = build_app_stub()
    app.command_registry = DummyCommandRegistry()

    app._apply_command_options()

    assert app.command_combo["values"] == ("repo_terminal", "bridge_launch")
    assert app.command_var.get() == ""


def test_handle_scenario_roster_logs_and_updates_status() -> None:
    app, output = build_app_stub(scenario_value="")

    app._handle_scenario_roster({"scenarios": ["inchon_mvp.json", "mini_gc_1942.json"]})

    assert "refreshed 2 scenarios" in output
    assert "selected scenario: inchon_mvp.json" in output
    assert app.summary_var.get() == "Refreshed 2 scenarios. Selected inchon_mvp.json."
    assert app.status_var.get() == "PASS"


def test_log_action_metadata_emits_matrix_breadcrumb() -> None:
    app, output = build_app_stub(scenario_value="")
    app.gui_action_matrix = load_gui_action_matrix()

    app._log_action_metadata("ORL / Connectivity")

    assert output == ["using action metadata for ORL / Connectivity"]


def test_handle_result_surfaces_known_issue_and_waiver() -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    app._log_incident_bundle = lambda result: None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None
    result = ConsoleResult(
        name="ORL / Snapshot Smoke",
        status="warn",
        original_status="fail",
        summary="Snapshot load failed.",
        scenario_name="inchon_mvp",
        known_issue_matches=[
            KnownIssueMatch(
                issue_id="KI-777",
                title="Waived snapshot mismatch",
                severity="high",
                category="ORL",
                status="waived",
                expected_status_override="warn",
                notes="Temporary waiver.",
            )
        ],
    )

    app._handle_result(result)

    assert "KNOWN ISSUE: KI-777 | Waived snapshot mismatch | severity=high | status=waived | override=WARN" in output
    assert "KNOWN ISSUE WAIVER APPLIED: FAIL -> WARN" in output
    assert app.status_var.get() == "WARN"
    assert "KNOWN ISSUE: KI-777" in app.summary_var.get()


def test_result_summary_text_includes_nested_known_issue_ids() -> None:
    app, _output = build_app_stub(scenario_value="inchon_mvp")
    result = ConsoleResult(
        name="ORL / Demo Checklist",
        status="fail",
        summary="Checklist failed.",
        scenario_name="inchon_mvp",
        subresults=[
            ConsoleResult(
                name="Replay Compare",
                status="warn",
                original_status="fail",
                summary="Replay compare mismatch.",
                scenario_name="inchon_mvp",
                known_issue_matches=[
                    KnownIssueMatch(
                        issue_id="KI-778",
                        title="Waived replay mismatch",
                        severity="high",
                        category="ORL",
                        status="waived",
                        expected_status_override="warn",
                        notes="Temporary waiver.",
                    )
                ],
            )
        ],
    )

    summary = app._result_summary_text(result)

    assert summary == "Checklist failed. [KNOWN ISSUE: KI-778]"


def test_handle_result_auto_exports_demo_readiness_report(tmp_path, monkeypatch) -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    app._log_incident_bundle = lambda result: None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None
    json_path = tmp_path / "20260330120000-orl-demo-readiness.json"
    text_path = tmp_path / "20260330120000-orl-demo-readiness.txt"
    monkeypatch.setattr("tools.operations_console.app.export_result_json", lambda result: json_path)
    monkeypatch.setattr("tools.operations_console.app.export_result_text", lambda result: text_path)

    app._handle_result(
        ConsoleResult(
            name="ORL / Demo Readiness",
            status="pass",
            summary="demo ready",
            scenario_name="inchon_mvp",
            artifact_paths=["/tmp/replay.json"],
        )
    )

    assert app.last_result is not None
    assert str(json_path) in app.last_result.artifact_paths
    assert str(text_path) in app.last_result.artifact_paths
    assert f"AUTO REPORT JSON: {json_path}" in output
    assert f"AUTO REPORT TEXT: {text_path}" in output


def test_handle_result_auto_exports_core_validation_report(tmp_path, monkeypatch) -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    app._log_incident_bundle = lambda result: None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None
    json_path = tmp_path / "20260330120000-orl-core-validation-suite.json"
    text_path = tmp_path / "20260330120000-orl-core-validation-suite.txt"
    monkeypatch.setattr("tools.operations_console.app.export_result_json", lambda result: json_path)
    monkeypatch.setattr("tools.operations_console.app.export_result_text", lambda result: text_path)

    app._handle_result(
        ConsoleResult(
            name="ORL / Core Validation Suite",
            status="pass",
            summary="core ready",
            scenario_name="inchon_mvp",
        )
    )

    assert app.last_result is not None
    assert str(json_path) in app.last_result.artifact_paths
    assert str(text_path) in app.last_result.artifact_paths
    assert f"AUTO REPORT JSON: {json_path}" in output


def test_handle_result_refreshes_demo_artifact_validation_after_auto_export(tmp_path, monkeypatch) -> None:
    class DemoRegistry:
        def get(self, name: str):
            if name == "ORL / Demo Artifact Validation":
                return ConsoleAction(
                    name=name,
                    category="ORL",
                    description="validate",
                    runner=lambda _context: make_result(
                        name=name,
                        status="pass",
                        summary="artifact validation ok",
                        artifact_paths=[str(tmp_path / "demo-artifact-shelf.json")],
                    ),
                )
            return None

    app, output = build_app_stub(scenario_value="inchon_mvp")
    app.registry = DemoRegistry()
    app._log_incident_bundle = lambda result: None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None
    app.bridge_uri_var = DummyVar("ws://127.0.0.1:8766")
    json_path = tmp_path / "20260330120000-orl-demo-readiness.json"
    text_path = tmp_path / "20260330120000-orl-demo-readiness.txt"
    monkeypatch.setattr("tools.operations_console.app.export_result_json", lambda result: json_path)
    monkeypatch.setattr("tools.operations_console.app.export_result_text", lambda result: text_path)

    app._handle_result(
        ConsoleResult(
            name="ORL / Demo Readiness",
            status="fail",
            summary="demo not ready",
            scenario_name="inchon_mvp",
            artifact_paths=["/tmp/replay.json"],
            subresults=[
                ConsoleResult(name="ORL / Smoke Suite", status="pass", summary="smoke ok"),
                ConsoleResult(name="ORL / Demo Artifact Validation", status="fail", summary="report missing"),
            ],
        )
    )

    assert app.last_result is not None
    assert app.last_result.status == "pass"
    assert any(item.name == "ORL / Demo Artifact Validation" and item.status == "pass" for item in app.last_result.subresults)
    assert "AUTO REFRESH: reran ORL / Demo Artifact Validation after demo report export." in app.last_result.details
    assert any("ORL / Demo Artifact Validation" in line for line in output)


def test_handle_process_result_stores_last_result_for_export() -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    incident_calls: list[str] = []
    app._log_incident_bundle = lambda result: incident_calls.append(result.name) or None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None

    app._handle_process_result(
        (
            "Run Bridge",
            ProcessControlResult(
                ok=True,
                status="pass",
                summary="Bridge launched.",
                logs=["launched bridge process"],
                command=["python", "server/mwe_bridge_p8_ws15.py"],
            ),
        )
    )

    assert app.last_result is not None
    assert app.last_result.name == "Run Bridge"
    assert app.last_result.executed_command == ["python", "server/mwe_bridge_p8_ws15.py"]
    assert incident_calls == ["Run Bridge"]
    assert "== PASS :: Bridge launched. ==" in output


def test_handle_process_result_attaches_incident_metadata_to_last_result() -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    app._log_incident_bundle = lambda result: IncidentBundleResult(
        logged=True,
        bundle_dir="/tmp/incidents/bridge",
        incident_json_path="/tmp/incidents/bridge/incident.json",
        run_report_json_path="/tmp/incidents/bridge/run_report.json",
        anomaly_matches=[AnomalyMatch(rule_id="ANOM-003", title="Missing expected artifact")],
    )
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None

    app._handle_process_result(
        (
            "Run Bridge",
            ProcessControlResult(
                ok=True,
                status="pass",
                summary="Bridge launched.",
                logs=["launched bridge process"],
                command=["python", "server/mwe_bridge_p8_ws15.py"],
            ),
        )
    )

    assert app.last_result is not None
    assert "INCIDENT ANOMALIES: ANOM-003 | Missing expected artifact" in app.last_result.details
    assert "INCIDENT BUNDLE: /tmp/incidents/bridge" in app.last_result.details
    assert "/tmp/incidents/bridge/incident.json" in app.last_result.artifact_paths
    assert "/tmp/incidents/bridge/run_report.json" in app.last_result.artifact_paths
    assert "== PASS :: Bridge launched. ==" in output


def test_handle_task_error_converts_aux_failure_into_console_result() -> None:
    app, output = build_app_stub(scenario_value="inchon_mvp")
    incident_calls: list[str] = []
    app._log_incident_bundle = lambda result: incident_calls.append(result.name) or None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._update_control_states = lambda *args, **kwargs: None

    app._handle_task_error(("Refresh Scenarios", "Scenario refresh failed.", "connection refused"))

    assert app.last_result is not None
    assert app.last_result.name == "Refresh Scenarios"
    assert app.last_result.status == "error"
    assert app.last_result.errors == ["connection refused"]
    assert incident_calls == ["Refresh Scenarios"]
    assert "ERROR: connection refused" in output
    assert app.summary_var.get() == "Scenario refresh failed."
    assert app.status_var.get() == "ERROR"
