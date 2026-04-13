from __future__ import annotations

from engine.testing_api import TestingApiResult as AdapterResult
from tools.operations_console.app import OperationsConsoleApp
from tools.operations_console.models import ConsoleResult
from tools.operations_console.registry import build_default_registry
from tools.operations_console.report_export import export_result_text, report_dict
from tools.operations_console.runner_utils import run_registry_entry


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


def test_app_registers_campaign_actions_and_runners_work(monkeypatch) -> None:
    class FakeAdapter:
        def campaign_status(self, scenario_name: str = "") -> AdapterResult:
            assert scenario_name == "inchon_mvp"
            return AdapterResult(
                ok=True,
                data={"scenario_id": "inchon_mvp"},
                logs=[
                    "CAMPAIGN STATUS: scenario=Inchon Demo Vertical Slice | objective=SEOUL | front=SECURE | supply=OPEN | main=INCHON AXIS",
                    "CAMPAIGN STATUS DETAIL: turn=TURN 1 | units=6 | objectives=5 | alerts=2",
                ],
                adapter_method="campaign_status",
            )

        def campaign_explain(self, scenario_name: str = "") -> AdapterResult:
            assert scenario_name == "inchon_mvp"
            return AdapterResult(
                ok=True,
                data={"scenario_id": "inchon_mvp"},
                logs=[
                    "CAMPAIGN EXPLAIN: Curated Inchon demo.",
                    "CAMPAIGN NOTES: Exploit the landing before Seoul stabilizes.",
                ],
                adapter_method="campaign_explain",
            )

    monkeypatch.setattr("tools.operations_console.app.EngineTestingAPI", FakeAdapter)

    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.registry = build_default_registry()

    app._register_explainability_actions()

    status_action = app.registry.get_action("ORL / Campaign Status")
    explain_action = app.registry.get_action("ORL / Campaign Explain")

    assert status_action is not None
    assert explain_action is not None

    status_result = run_registry_entry(
        status_action,
        entry_lookup=app.registry.get,
        scenario_input="inchon_mvp",
    )
    explain_result = run_registry_entry(
        explain_action,
        entry_lookup=app.registry.get,
        scenario_input="inchon_mvp",
    )

    assert status_result.status == "pass"
    assert status_result.adapter_method == "campaign_status"
    assert "campaign status retrieved" in status_result.details
    assert any("CAMPAIGN STATUS:" in line for line in status_result.details)
    assert explain_result.status == "pass"
    assert explain_result.adapter_method == "campaign_explain"
    assert "campaign explain retrieved" in explain_result.details
    assert any("CAMPAIGN EXPLAIN:" in line for line in explain_result.details)


def test_handle_result_attaches_explainability_follow_up(monkeypatch) -> None:
    class FakeAdapter:
        def campaign_status(self, scenario_name: str = "") -> AdapterResult:
            assert scenario_name == "inchon_mvp"
            return AdapterResult(
                ok=True,
                data={"scenario_id": "inchon_mvp"},
                logs=[
                    "CAMPAIGN STATUS: scenario=Inchon Demo Vertical Slice | objective=SEOUL | front=SECURE | supply=OPEN | main=INCHON AXIS",
                    "CAMPAIGN STATUS DETAIL: turn=TURN 1 | units=6 | objectives=5 | alerts=2",
                ],
                adapter_method="campaign_status",
            )

        def campaign_explain(self, scenario_name: str = "") -> AdapterResult:
            assert scenario_name == "inchon_mvp"
            return AdapterResult(
                ok=True,
                data={"scenario_id": "inchon_mvp"},
                logs=[
                    "CAMPAIGN EXPLAIN: Curated Inchon demo.",
                    "CAMPAIGN NOTES: Exploit the landing before Seoul stabilizes.",
                    "CAMPAIGN ALERTS: Kimpo corridor remains contested.; NKPA reserves are forming south of Seoul.",
                ],
                adapter_method="campaign_explain",
            )

    monkeypatch.setattr("tools.operations_console.app.EngineTestingAPI", FakeAdapter)

    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.scenario_var = DummyVar("inchon_mvp")
    app.status_var = DummyVar("IDLE")
    app.summary_var = DummyVar("Ready.")
    app.status_badge = DummyWidget()
    app.last_result = None
    output: list[str] = []
    app._append_output = output.append
    app._apply_scenario_contracts = lambda result: (result, None)
    app._append_contract_evaluation = lambda evaluation: None
    app._compare_result_against_baseline = lambda result: None
    app._emit_incident_breadcrumbs = lambda incident: None
    app._log_incident_bundle = lambda result: None
    app._update_control_states = lambda *args, **kwargs: None

    result = ConsoleResult(
        name="ORL / Snapshot Smoke",
        status="fail",
        summary="Snapshot smoke failed.",
        scenario_name="inchon_mvp",
        errors=["snapshot mismatch"],
    )

    app._handle_result(result)

    assert app.last_result is not None
    assert any("FOLLOW-UP EXPLAINABILITY:" == line for line in output)
    assert "explainability attached to incident/report" in output
    assert any(line.startswith("CAMPAIGN STATUS:") for line in output)
    assert any(line.startswith("CAMPAIGN NOTES:") for line in output)
    assert "explainability attached to incident/report" in app.last_result.details
    assert any(line.startswith("CAMPAIGN STATUS:") for line in app.last_result.details)


def test_report_export_includes_explainability_summary(tmp_path) -> None:
    result = ConsoleResult(
        name="ORL / Campaign Status",
        status="pass",
        summary="Campaign status captured.",
        scenario_name="inchon_mvp",
        details=[
            "explainability attached to incident/report",
            "CAMPAIGN STATUS: scenario=Inchon Demo Vertical Slice | objective=SEOUL | front=INCHON BEACHHEAD SECURE | supply=PORT OPEN / AXIS ADVANCE | main=INCHON / SEOUL AXIS",
            "CAMPAIGN STATUS DETAIL: turn=TURN 1 | units=6 | objectives=5 | alerts=2",
            "CAMPAIGN EXPLAIN: Curated Inchon demo.",
            "CAMPAIGN NOTES: Exploit the landing before Seoul stabilizes.",
            "CAMPAIGN ALERTS: Kimpo corridor remains contested.; NKPA reserves are forming south of Seoul.",
        ],
    )

    payload = report_dict(result)
    text_path = export_result_text(result, tmp_path)
    text = text_path.read_text(encoding="utf-8")

    assert payload["explainability_summary"]["objective"] == "SEOUL"
    assert payload["explainability_summary"]["unit_count"] == 6
    assert payload["explainability_summary"]["staff_notes"] == "Exploit the landing before Seoul stabilizes."
    assert payload["explainability_summary"]["attached_to"] == "incident/report"
    assert "Explainability:" in text
    assert "Attached: incident/report" in text
    assert "Objective: SEOUL" in text
    assert "Front Status: INCHON BEACHHEAD SECURE" in text
