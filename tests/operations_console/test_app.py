from __future__ import annotations

from tools.operations_console.app import OperationsConsoleApp


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


def build_app_stub(*, scenario_value: str = "", selection: tuple[str, ...] = ("ORL / Connectivity",)):
    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.scenario_var = DummyVar(scenario_value)
    app.status_var = DummyVar("IDLE")
    app.summary_var = DummyVar("Ready.")
    app.scenario_combo = DummyWidget()
    app.run_button = DummyWidget()
    app.clear_button = DummyWidget()
    app.export_button = DummyWidget()
    app.refresh_scenarios_button = DummyWidget()
    app.bridge_button = DummyWidget()
    app.mwe_button = DummyWidget()
    app.stop_button = DummyWidget()
    app.status_badge = DummyWidget()
    app.tree = DummyTree(selection)
    app.registry = DummyRegistry()
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


def test_handle_scenario_roster_logs_and_updates_status() -> None:
    app, output = build_app_stub(scenario_value="")

    app._handle_scenario_roster({"scenarios": ["inchon_mvp.json", "mini_gc_1942.json"]})

    assert "refreshed 2 scenarios" in output
    assert "selected scenario: inchon_mvp.json" in output
    assert app.summary_var.get() == "Refreshed 2 scenarios. Selected inchon_mvp.json."
    assert app.status_var.get() == "PASS"
