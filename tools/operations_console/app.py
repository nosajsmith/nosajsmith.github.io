from __future__ import annotations

import queue
import json
import sys
import threading
from dataclasses import replace
from pathlib import Path
from tkinter import END, NSEW, StringVar, TclError, Tk
from tkinter import scrolledtext, ttk


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from engine.testing_api import EngineTestingAPI
from tools.operations_console.doctor import run_doctor_console_result
from tools.operations_console.expansion_registry import (
    ExpansionRegistry,
    load_expansion_registry,
    write_expansion_registry_snapshot,
)
from tools.operations_console.gui_action_matrix import GuiActionMatrixEntry
from tools.operations_console.models import ConsoleAction, ConsoleRegistryEntry, ConsoleResult
from tools.operations_console.baselines import BaselineComparison, compare_result_to_baseline, save_baseline
from tools.operations_console.divergence_finder import (
    FirstDivergence,
    compare_result_to_baseline_divergence,
    find_first_divergence_in_artifact_paths,
)
from tools.operations_console.incident_log import (
    AnomalyCatalog,
    IncidentBundleResult,
    attach_incident_metadata,
    load_anomaly_rules,
    log_incident_bundle,
)
from tools.operations_console.known_issues import KnownIssuesCatalog, load_known_issues
from tools.operations_console.process_control import ManagedProcessController, ProcessControlResult
from tools.operations_console.report_export import export_result_json, export_result_text
from tools.operations_console.registry import DEFAULT_BRIDGE_URI, ActionRegistry, build_default_registry, list_live_scenarios
from tools.operations_console.run_manifest import (
    RunManifestCaptureResult,
    capture_run_manifest,
    manifest_metadata_lines,
)
from tools.operations_console.runner_utils import make_result, roll_up_statuses, run_registry_entry
from tools.operations_console.scenario_contracts import (
    ScenarioContractCatalog,
    ScenarioContractEvaluation,
    apply_scenario_contracts,
    load_scenario_contracts,
)


STATUS_COLORS = {
    "idle": "#868686",
    "running": "#3b6ea8",
    "pass": "#2e7d32",
    "fail": "#a8432b",
    "warn": "#8a6b22",
    "error": "#8b2635",
}

EXPLAINABILITY_ACTION_NAMES = {
    "ORL / Campaign Status",
    "ORL / Campaign Explain",
}
AUTO_EXPORT_REPORT_ACTION_NAMES = {
    "ORL / Demo Readiness",
    "ORL / Core Validation Suite",
}


def _adapter_result_to_console_result(
    context,
    *,
    adapter_result,
    success_summary: str,
    failure_summary: str,
) -> ConsoleResult:
    if adapter_result.adapter_method:
        context.log(f"using adapter: {adapter_result.adapter_method}")
    if adapter_result.executed_command:
        context.log(f"command: {' '.join(adapter_result.executed_command)}")
    for line in adapter_result.logs:
        context.log(line)

    status = "pass" if adapter_result.ok else ("fail" if adapter_result.error else "warn")
    summary = success_summary if adapter_result.ok else failure_summary
    if not adapter_result.ok and adapter_result.error:
        summary = f"{failure_summary} {adapter_result.error}"
    scenario_name = str(
        adapter_result.data.get("scenario_id")
        or adapter_result.data.get("scenario_name")
        or context.scenario_name
        or ""
    ).strip()
    return make_result(
        name=context.action_name,
        status=status,
        summary=summary,
        errors=[adapter_result.error] if adapter_result.error else [],
        artifact_paths=adapter_result.artifacts,
        scenario_name=scenario_name,
        adapter_method=adapter_result.adapter_method,
        executed_command=adapter_result.executed_command,
        return_code=adapter_result.return_code,
    )


def run_orl_campaign_status(context) -> ConsoleResult:
    adapter = EngineTestingAPI()
    result = adapter.campaign_status(scenario_name=context.scenario_name)
    if result.ok:
        context.log("campaign status retrieved")
    return _adapter_result_to_console_result(
        context,
        adapter_result=result,
        success_summary="Campaign status captured.",
        failure_summary="Campaign status failed.",
    )


def run_orl_campaign_explain(context) -> ConsoleResult:
    adapter = EngineTestingAPI()
    result = adapter.campaign_explain(scenario_name=context.scenario_name)
    if result.ok:
        context.log("campaign explain retrieved")
    return _adapter_result_to_console_result(
        context,
        adapter_result=result,
        success_summary="Campaign explain captured.",
        failure_summary="Campaign explain failed.",
    )


class OperationsConsoleApp:
    def __init__(
        self,
        root: Tk,
        registry: ActionRegistry | None = None,
        known_issues: KnownIssuesCatalog | None = None,
        anomaly_catalog: AnomalyCatalog | None = None,
        scenario_contracts: ScenarioContractCatalog | None = None,
        expansion_registry: ExpansionRegistry | None = None,
    ):
        self.root = root
        self.registry = registry or build_default_registry()
        self._register_explainability_actions()
        self._register_divergence_action()
        self.expansion_registry = expansion_registry or load_expansion_registry()
        self._register_expansion_registry_action()
        self.gui_action_matrix = self.registry.action_matrix()
        self.command_registry = getattr(self.registry, "command_registry", lambda: None)()
        self.known_issues = known_issues or load_known_issues()
        self.anomaly_catalog = anomaly_catalog or load_anomaly_rules()
        self.scenario_contracts = scenario_contracts or load_scenario_contracts()
        self.event_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_result: ConsoleResult | None = None
        self.process_controller = ManagedProcessController(
            log_sink=lambda line: self.event_queue.put(("log", line)),
        )

        self.bridge_uri_var = StringVar(value=DEFAULT_BRIDGE_URI)
        self.scenario_var = StringVar(value="")
        self.command_var = StringVar(value="")
        self.status_var = StringVar(value="IDLE")
        self.summary_var = StringVar(value="Ready.")
        self.description_var = StringVar(value="Select an action to view details.")

        self.tree: ttk.Treeview
        self.scenario_combo: ttk.Combobox
        self.command_combo: ttk.Combobox
        self.description_label: ttk.Label
        self.output_text: scrolledtext.ScrolledText
        self.run_button: ttk.Button
        self.clear_button: ttk.Button
        self.export_button: ttk.Button
        self.save_baseline_button: ttk.Button
        self.compare_baseline_button: ttk.Button
        self.refresh_scenarios_button: ttk.Button
        self.bridge_button: ttk.Button
        self.mwe_button: ttk.Button
        self.stop_button: ttk.Button
        self.doctor_button: ttk.Button
        self.status_badge: ttk.Label

        self._build()
        self._apply_command_options()
        self._populate_actions()
        self._set_status("idle", "Ready.")
        self._update_control_states()
        self._append_output("MWE Operations Console ready.")
        self._append_output(f"Loaded {len(self.gui_action_matrix.entries)} GUI action matrix rows.")
        self._append_output(f"Loaded {len(self.known_issues.issues)} known issue definitions.")
        self._append_output(f"Loaded {len(self.anomaly_catalog.rules)} anomaly rules.")
        self._append_output(f"Loaded {len(self.scenario_contracts.contracts)} scenario contracts.")
        self._append_output(f"Loaded {len(self.expansion_registry.entries)} expansion registry entries.")
        self._append_output(
            f"Loaded {len(getattr(self.command_registry, 'commands', []))} allowlisted Konsole commands."
        )
        self._append_output("Baseline drift support ready.")
        self._append_output("Explainability drilldown ready.")
        self._append_output("First-divergence finder ready.")
        self._append_output("Expansion registry ready.")
        self._append_output("Doctor support ready.")
        self.root.after(75, self._poll_events)

    def _register_explainability_actions(self) -> None:
        if self.registry.get("ORL / Campaign Status") is None:
            self.registry.register(
                ConsoleAction(
                    name="ORL / Campaign Status",
                    category="ORL",
                    description="Capture concise structured campaign status for the selected scenario.",
                    runner=run_orl_campaign_status,
                )
            )
        if self.registry.get("ORL / Campaign Explain") is None:
            self.registry.register(
                ConsoleAction(
                    name="ORL / Campaign Explain",
                    category="ORL",
                    description="Capture concise scenario explanation, staff notes, alerts, and orders.",
                    runner=run_orl_campaign_explain,
                )
            )

    def _register_divergence_action(self) -> None:
        if self.registry.get("Utilities / First Divergence Finder") is None:
            self.registry.register(
                ConsoleAction(
                    name="Utilities / First Divergence Finder",
                    category="Utilities",
                    description="Compare the last result against its saved baseline or the first comparable artifact pair and report the earliest meaningful difference.",
                    runner=self._run_first_divergence_finder_action,
                )
            )

    def _register_expansion_registry_action(self) -> None:
        if self.registry.get("Planning / Expansion Registry") is None:
            self.registry.register(
                ConsoleAction(
                    name="Planning / Expansion Registry",
                    category="Planning",
                    description="Summarize future theater and capability ideas with support-gate blockers and export a JSON planning snapshot.",
                    runner=self._run_expansion_registry_action,
                )
            )

    def _build(self) -> None:
        self.root.title("MWE Operations Console")
        self.root.geometry("1120x720")
        self.root.minsize(960, 600)

        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky=NSEW)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        top = ttk.LabelFrame(frame, text="Bridge / Scenario", padding=10)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)
        top.columnconfigure(4, weight=0)

        ttk.Label(top, text="Bridge URI").grid(row=0, column=0, sticky="w", padx=(0, 8))
        bridge_entry = ttk.Entry(top, textvariable=self.bridge_uri_var)
        bridge_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(top, text="Scenario").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.scenario_combo = ttk.Combobox(top, textvariable=self.scenario_var, state="normal")
        self.scenario_combo.grid(row=0, column=3, sticky="ew", padx=(0, 8))
        self.refresh_scenarios_button = ttk.Button(top, text="Refresh Scenarios", command=self._refresh_scenarios)
        self.refresh_scenarios_button.grid(row=0, column=4, sticky="e")
        ttk.Label(
            top,
            text="Scenario-sensitive actions use the Scenario field if provided; otherwise they default to the first live roster entry. Leave Bridge URI at the default local bridge unless you need to target a different websocket endpoint.",
            wraplength=920,
            foreground="#666666",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(
            top,
            text="Examples: inchon_mvp or inchon_mvp.json",
            foreground="#666666",
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(top, text="Konsole Command").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        self.command_combo = ttk.Combobox(top, textvariable=self.command_var, state="readonly")
        self.command_combo.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=(8, 0))
        ttk.Label(
            top,
            text="Used only by 'Run Selected Command in Konsole'. Values come from the allowlisted command registry.",
            wraplength=640,
            foreground="#666666",
        ).grid(row=2, column=2, columnspan=3, sticky="w", pady=(8, 0))

        left = ttk.LabelFrame(frame, text="Tools / Actions", padding=8)
        left.grid(row=1, column=0, sticky="nsw", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, show="tree", selectmode="browse", height=24)
        self.tree.grid(row=0, column=0, sticky=NSEW)
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._handle_selection)
        self.tree.bind("<Double-1>", self._handle_double_click)

        right = ttk.Frame(frame)
        right.grid(row=1, column=1, sticky=NSEW)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        description_frame = ttk.LabelFrame(right, text="Action Details", padding=10)
        description_frame.grid(row=0, column=0, sticky="ew")
        description_frame.columnconfigure(0, weight=1)
        self.description_label = ttk.Label(
            description_frame,
            textvariable=self.description_var,
            justify="left",
            wraplength=760,
        )
        self.description_label.grid(row=0, column=0, sticky="w")

        controls = ttk.Frame(right)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        controls.columnconfigure(6, weight=1)
        self.run_button = ttk.Button(controls, text="Run", command=self._run_selected, state="disabled")
        self.run_button.grid(row=0, column=0, sticky="w")
        self.clear_button = ttk.Button(controls, text="Clear Output", command=self._clear_output)
        self.clear_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.export_button = ttk.Button(controls, text="Export Report", command=self._export_report, state="disabled")
        self.export_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.save_baseline_button = ttk.Button(controls, text="Save Baseline", command=self._save_baseline, state="disabled")
        self.save_baseline_button.grid(row=0, column=3, sticky="w", padx=(8, 0))
        self.compare_baseline_button = ttk.Button(
            controls,
            text="Compare Baseline",
            command=self._compare_current_baseline,
            state="disabled",
        )
        self.compare_baseline_button.grid(row=0, column=4, sticky="w", padx=(8, 0))
        self.bridge_button = ttk.Button(controls, text="Run Bridge", command=self._launch_bridge)
        self.bridge_button.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.mwe_button = ttk.Button(controls, text="Run MWE", command=self._launch_mwe)
        self.mwe_button.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self.stop_button = ttk.Button(controls, text="Stop Managed Processes", command=self._stop_managed_processes)
        self.stop_button.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))
        self.doctor_button = ttk.Button(controls, text="Run Doctor", command=self._run_doctor)
        self.doctor_button.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(8, 0))

        output_frame = ttk.LabelFrame(right, text="Output", padding=8)
        output_frame.grid(row=2, column=0, sticky=NSEW)
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap="word",
            height=24,
            state="disabled",
            font=("TkFixedFont", 10),
        )
        self.output_text.grid(row=0, column=0, sticky=NSEW)

        status_frame = ttk.Frame(frame)
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(2, weight=1)
        ttk.Label(status_frame, text="Status").grid(row=0, column=0, sticky="w")
        self.status_badge = ttk.Label(status_frame, textvariable=self.status_var, padding=(8, 4))
        self.status_badge.grid(row=0, column=1, sticky="w", padx=(8, 12))
        ttk.Label(status_frame, textvariable=self.summary_var).grid(row=0, column=2, sticky="w")

    def _populate_actions(self) -> None:
        for category in self.registry.categories():
            parent_id = f"category::{category}"
            self.tree.insert("", END, iid=parent_id, text=category, open=True)
            for entry in self.registry.entries_by_category().get(category, []):
                self.tree.insert(parent_id, END, iid=entry.name, text=entry.name)

    def _selected_entry(self) -> ConsoleRegistryEntry | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.registry.get(selection[0])

    def _handle_selection(self, _event=None) -> None:
        entry = self._selected_entry()
        if entry is None:
            self.description_var.set("Select an action to view details.")
            self._update_control_states()
            return
        self.description_var.set(self._entry_description(entry))
        self._update_control_states()

    def _handle_double_click(self, _event=None) -> None:
        if self._selected_entry() is not None and not self._is_running():
            self._run_selected()

    def _run_selected(self) -> None:
        if self._is_running():
            return
        entry = self._selected_entry()
        if entry is None:
            self._set_status("warn", "Select an action before running.")
            return

        scenario_input = self.scenario_var.get().strip()
        bridge_uri = self.bridge_uri_var.get().strip()
        command_input = self.command_var.get().strip()
        self._append_output("")
        self._append_output(f"== Running {entry.name} ==")
        self._log_action_metadata(entry.name)
        self._set_status("running", f"Running {entry.name}...")
        self._update_control_states(running_override=True)

        def worker() -> None:
            result = run_registry_entry(
                entry,
                entry_lookup=self.registry.get,
                scenario_input=scenario_input,
                bridge_uri=bridge_uri,
                command_input=command_input,
                log_sink=lambda line: self.event_queue.put(("log", line)),
                known_issues=self.known_issues,
            )
            self.event_queue.put(("result", result))

        self.worker = threading.Thread(target=worker, name="operations-console-runner", daemon=True)
        self.worker.start()

    def _refresh_scenarios(self) -> None:
        if self._is_running():
            return
        uri = self.bridge_uri_var.get().strip() or DEFAULT_BRIDGE_URI
        self._append_output("")
        self._append_output("== Refreshing Scenarios ==")
        self._log_action_metadata("Refresh Scenarios")
        self._set_status("running", "Refreshing scenarios...")
        self._update_control_states(running_override=True)

        def worker() -> None:
            try:
                scenarios = list_live_scenarios(uri)
                self.event_queue.put(("scenario_roster", {"scenarios": scenarios, "uri": uri}))
            except Exception as exc:
                self.event_queue.put(("task_error", ("Refresh Scenarios", "Scenario refresh failed.", str(exc))))

        self.worker = threading.Thread(target=worker, name="operations-console-refresh", daemon=True)
        self.worker.start()

    def _launch_bridge(self) -> None:
        self._run_process_control(
            label="Run Bridge",
            summary="Launching bridge...",
            runner=lambda: self.process_controller.launch_bridge(self.bridge_uri_var.get().strip() or DEFAULT_BRIDGE_URI),
        )

    def _launch_mwe(self) -> None:
        self._run_process_control(
            label="Run MWE",
            summary="Launching MWE...",
            runner=lambda: self.process_controller.launch_mwe(self.bridge_uri_var.get().strip() or DEFAULT_BRIDGE_URI),
        )

    def _stop_managed_processes(self) -> None:
        self._run_process_control(
            label="Stop Managed Processes",
            summary="Stopping managed processes...",
            runner=self.process_controller.stop_managed_processes,
        )

    def _run_doctor(self) -> None:
        if self._is_running():
            return
        bridge_uri = self.bridge_uri_var.get().strip() or DEFAULT_BRIDGE_URI
        scenario_name = self.scenario_var.get().strip()
        self._append_output("")
        self._append_output("== mwe doctor ==")
        self._log_action_metadata("Utilities / mwe doctor")
        self._set_status("running", "Running environment doctor...")
        self._update_control_states(running_override=True)

        def worker() -> None:
            try:
                result = run_doctor_console_result(
                    bridge_uri=bridge_uri,
                    scenario_name=scenario_name,
                )
                self.event_queue.put(("result", result))
            except Exception as exc:
                self.event_queue.put(("task_error", ("Utilities / mwe doctor", "mwe doctor failed.", str(exc))))

        self.worker = threading.Thread(target=worker, name="operations-console-doctor", daemon=True)
        self.worker.start()

    def _run_process_control(self, *, label: str, summary: str, runner) -> None:
        if self._is_running():
            return
        self._append_output("")
        self._append_output(f"== {label} ==")
        self._log_action_metadata(label)
        self._set_status("running", summary)
        self._update_control_states(running_override=True)

        def worker() -> None:
            try:
                result = runner()
                self.event_queue.put(("process_result", (label, result)))
            except Exception as exc:
                self.event_queue.put(("task_error", (label, f"{label} failed.", str(exc))))

        self.worker = threading.Thread(target=worker, name="operations-console-process", daemon=True)
        self.worker.start()

    def _poll_events(self) -> None:
        while True:
            try:
                event, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break
            if event == "log":
                self._append_output(str(payload))
            elif event == "result":
                self._handle_result(payload)  # type: ignore[arg-type]
            elif event == "scenario_roster":
                self._handle_scenario_roster(payload)  # type: ignore[arg-type]
            elif event == "process_result":
                self._handle_process_result(payload)  # type: ignore[arg-type]
            elif event == "task_error":
                self._handle_task_error(payload)  # type: ignore[arg-type]
        self.root.after(75, self._poll_events)

    def _handle_result(self, result: ConsoleResult) -> None:
        result, contract_evaluation = self._apply_scenario_contracts(result)
        result = self._attach_explainability_follow_up(result)
        result = self._maybe_auto_export_result(result)
        result = self._refresh_demo_artifact_validation(result)
        drift = self._compare_result_against_baseline(result)
        divergence = self._find_result_divergence(result, drift)
        manifest = self._capture_run_manifest(result)
        result = self._attach_run_manifest_metadata(result, manifest)
        incident = self._log_incident_bundle(result)
        result = self._attach_incident_metadata(result, incident)
        manifest = self._refresh_run_manifest_after_incident_metadata(result, manifest, incident)
        result = self._attach_run_manifest_metadata(result, manifest)
        result = self._refresh_auto_export_after_support_metadata(result, manifest, incident)
        self.last_result = result
        self._append_contract_evaluation(contract_evaluation)
        if result.errors:
            for error in result.errors:
                self._append_output(f"ERROR: {error}")
        self._append_known_issue_annotations(result)
        self._append_baseline_drift(drift)
        self._append_first_divergence(divergence)
        self._emit_incident_breadcrumbs(incident)
        self._append_output(f"== {result.status.upper()} :: {result.summary} ({result.duration_ms} ms) ==")
        self._set_status(result.status, self._result_summary_text(result, drift))
        self._update_control_states()

    def _handle_scenario_roster(self, payload: dict) -> None:
        scenarios = list(payload.get("scenarios") or [])
        normalized = [str(value or "").strip() for value in scenarios if str(value or "").strip()]
        auto_selected = self._apply_scenario_roster(normalized)
        self._append_output(f"refreshed {len(normalized)} scenarios")
        if self.scenario_var.get().strip():
            self._append_output(f"selected scenario: {self.scenario_var.get().strip()}")
        status = "pass" if normalized else "warn"
        summary = f"Refreshed {len(normalized)} scenarios."
        if auto_selected:
            summary = f"{summary} Selected {self.scenario_var.get().strip()}."
        if not normalized:
            summary = "Scenario refresh completed, but the live roster is empty."
        pseudo_result = make_result(
            name="Refresh Scenarios",
            status=status,
            summary=summary,
            scenario_name=self.scenario_var.get().strip(),
            details=[
                f"refreshed {len(normalized)} scenarios",
                *([f"selected scenario: {self.scenario_var.get().strip()}"] if self.scenario_var.get().strip() else []),
            ],
        )
        manifest = self._capture_run_manifest(pseudo_result)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        incident = self._log_incident_bundle(pseudo_result)
        pseudo_result = self._attach_incident_metadata(pseudo_result, incident)
        manifest = self._refresh_run_manifest_after_incident_metadata(pseudo_result, manifest, incident)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        self.last_result = pseudo_result
        self._emit_incident_breadcrumbs(incident)
        self._set_status(status, summary)
        self._update_control_states()

    def _handle_process_result(self, payload: tuple[str, ProcessControlResult]) -> None:
        label, result = payload
        pseudo_result = make_result(
            name=label,
            status=result.status,
            summary=result.summary,
            scenario_name=self.scenario_var.get().strip(),
            details=result.logs,
            executed_command=result.command,
        )
        manifest = self._capture_run_manifest(pseudo_result)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        incident = self._log_incident_bundle(pseudo_result)
        pseudo_result = self._attach_incident_metadata(pseudo_result, incident)
        manifest = self._refresh_run_manifest_after_incident_metadata(pseudo_result, manifest, incident)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        self.last_result = pseudo_result
        self._emit_incident_breadcrumbs(incident)
        self._append_output(f"== {result.status.upper()} :: {result.summary} ==")
        self._set_status(result.status, result.summary)
        self._update_control_states()

    def _handle_task_error(self, payload: tuple[str, str, str]) -> None:
        name, summary, error = payload
        pseudo_result = make_result(
            name=name,
            status="error",
            summary=summary,
            scenario_name=self.scenario_var.get().strip(),
            errors=[error],
            details=[error],
        )
        manifest = self._capture_run_manifest(pseudo_result)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        incident = self._log_incident_bundle(pseudo_result)
        pseudo_result = self._attach_incident_metadata(pseudo_result, incident)
        manifest = self._refresh_run_manifest_after_incident_metadata(pseudo_result, manifest, incident)
        pseudo_result = self._attach_run_manifest_metadata(pseudo_result, manifest)
        self.last_result = pseudo_result
        self._append_output(f"ERROR: {error}")
        self._emit_incident_breadcrumbs(incident)
        self._set_status("error", summary)
        self._update_control_states()

    def _clear_output(self) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", END)
        self.output_text.configure(state="disabled")

    def _export_report(self) -> None:
        if self.last_result is None:
            self._set_status("warn", "No completed run is available for export.")
            return
        try:
            json_path = export_result_json(self.last_result)
            text_path = export_result_text(self.last_result)
        except Exception as exc:
            self._append_output(f"ERROR: Report export failed: {exc}")
            self._set_status("error", "Report export failed.")
            return

        self._append_output(f"Report exported (json): {json_path}")
        self._append_output(f"Report exported (text): {text_path}")
        self.summary_var.set(f"Report exported: {json_path.name}")

    def _save_baseline(self) -> None:
        if self.last_result is None:
            self._set_status("warn", "No completed run is available for baseline save.")
            return
        try:
            path = save_baseline(
                self.last_result,
                action_matrix=getattr(self, "gui_action_matrix", None),
                scenario_contracts=getattr(self, "scenario_contracts", None),
            )
        except Exception as exc:
            self._append_output(f"ERROR: Baseline save failed: {exc}")
            self._set_status("error", "Baseline save failed.")
            return
        self._append_output(f"baseline saved: {path}")
        self.summary_var.set(f"Baseline saved: {path.name}")
        self._update_control_states()

    def _compare_current_baseline(self) -> None:
        if self.last_result is None:
            self._set_status("warn", "No completed run is available for baseline compare.")
            return
        drift = self._compare_result_against_baseline(self.last_result)
        if drift is None:
            self._set_status("error", "Baseline compare failed.")
            return
        if not drift.matched:
            self._append_output(f"BASELINE: no saved baseline for {self.last_result.name}")
            self._set_status("warn", "No matching baseline is saved for the current result.")
            return
        self._append_baseline_drift(drift)
        self._append_first_divergence(self._find_result_divergence(self.last_result, drift))
        self._set_status(self.last_result.status, self._result_summary_text(self.last_result, drift))
        self._update_control_states()

    def _apply_scenario_roster(self, scenarios: list[str]) -> bool:
        normalized = tuple(str(value or "").strip() for value in scenarios if str(value or "").strip())
        self.scenario_combo["values"] = normalized
        current = self.scenario_var.get().strip()
        if current or not normalized:
            return False
        self.scenario_var.set(normalized[0])
        return True

    def _apply_command_options(self) -> None:
        registry = getattr(self, "command_registry", None)
        options = tuple(getattr(registry, "command_ids", lambda: [])())
        self.command_combo["values"] = options
        current = self.command_var.get().strip()
        if current in options:
            return
        self.command_var.set("")

    def _append_output(self, message: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.insert(END, f"{message}\n")
        self.output_text.see(END)
        self.output_text.configure(state="disabled")

    def _set_status(self, status: str, summary: str) -> None:
        text = str(status or "idle").strip().lower()
        self.status_var.set(text.upper())
        self.summary_var.set(summary)
        color = STATUS_COLORS.get(text, STATUS_COLORS["idle"])
        self.status_badge.configure(foreground=color)

    def _entry_description(self, entry: ConsoleRegistryEntry) -> str:
        matrix_entry = self._matrix_entry_for_label(entry.name)
        parts = [matrix_entry.description if matrix_entry is not None and matrix_entry.description else entry.description]
        if matrix_entry is None:
            return parts[0]
        if matrix_entry.automation_level:
            parts.append(f"Automation: {matrix_entry.automation_level}")
        if matrix_entry.runner:
            parts.append(f"Runner: {matrix_entry.runner}")
        if matrix_entry.inputs:
            parts.append(f"Inputs: {', '.join(matrix_entry.inputs)}")
        if matrix_entry.preconditions:
            parts.append(f"Preconditions: {', '.join(matrix_entry.preconditions)}")
        if matrix_entry.expected_status:
            parts.append(f"Expected Status: {matrix_entry.expected_status.upper()}")
        if matrix_entry.expected_log_fragments:
            parts.append(f"Expected Logs: {', '.join(matrix_entry.expected_log_fragments)}")
        if matrix_entry.artifact_types:
            parts.append(f"Artifacts: {', '.join(matrix_entry.artifact_types)}")
        if entry.name == "Utilities / Run Selected Command in Konsole":
            command_ids = getattr(self.command_registry, "command_ids", lambda: [])()
            if command_ids:
                parts.append(f"Allowlisted Commands: {', '.join(command_ids)}")
        return "\n\n".join(part for part in parts if part)

    def _matrix_entry_for_label(self, label: str) -> GuiActionMatrixEntry | None:
        lookup = getattr(self.registry, "matrix_entry_for_label", None)
        if callable(lookup):
            try:
                entry = lookup(label)
            except Exception:
                entry = None
            if entry is not None:
                return entry
        matrix = getattr(self, "gui_action_matrix", None)
        if matrix is None:
            return None
        return matrix.get_by_label(label)

    def _log_action_metadata(self, label: str) -> None:
        matrix_entry = self._matrix_entry_for_label(label)
        if matrix_entry is None:
            return
        self._append_output(f"using action metadata for {label}")

    def _result_summary_text(
        self,
        result: ConsoleResult,
        baseline_drift: BaselineComparison | None = None,
    ) -> str:
        summary = result.summary
        issue_ids = ", ".join(self._known_issue_ids(result))
        if issue_ids:
            if result.original_status and result.original_status != result.status:
                summary = f"{summary} [KNOWN ISSUE: {issue_ids}; waived from {result.original_status.upper()}]"
            else:
                summary = f"{summary} [KNOWN ISSUE: {issue_ids}]"
        if baseline_drift is not None and baseline_drift.matched:
            summary = f"{summary} [DRIFT: {baseline_drift.status.upper()}]"
        return summary

    def _iter_results(self, result: ConsoleResult):
        yield result
        for item in result.subresults:
            yield from self._iter_results(item)

    def _known_issue_ids(self, result: ConsoleResult) -> list[str]:
        seen: set[str] = set()
        issue_ids: list[str] = []
        for item in self._iter_results(result):
            for match in item.known_issue_matches:
                if match.issue_id in seen:
                    continue
                seen.add(match.issue_id)
                issue_ids.append(match.issue_id)
        return issue_ids

    def _append_known_issue_annotations(self, result: ConsoleResult) -> None:
        for item in self._iter_results(result):
            if not item.known_issue_matches:
                continue
            if item is not result:
                self._append_output(f"KNOWN ISSUE RESULT: {item.name}")
                if item.scenario_name:
                    self._append_output(f"KNOWN ISSUE SCENARIO: {item.scenario_name}")
            for match in item.known_issue_matches:
                parts = [
                    f"KNOWN ISSUE: {match.issue_id}",
                    match.title,
                    f"severity={match.severity}",
                    f"status={match.status}",
                ]
                if match.expected_status_override:
                    parts.append(f"override={match.expected_status_override.upper()}")
                self._append_output(" | ".join(parts))
            if item.original_status and item.original_status != item.status:
                if item is result:
                    self._append_output(
                        f"KNOWN ISSUE WAIVER APPLIED: {item.original_status.upper()} -> {item.status.upper()}"
                    )
                else:
                    self._append_output(
                        f"KNOWN ISSUE WAIVER APPLIED [{item.name}]: {item.original_status.upper()} -> {item.status.upper()}"
                    )

    def _apply_scenario_contracts(self, result: ConsoleResult) -> tuple[ConsoleResult, ScenarioContractEvaluation | None]:
        try:
            scenario_name = self.scenario_var.get().strip() if self._should_apply_scenario_contracts(result.name) else ""
            return apply_scenario_contracts(
                result,
                scenario_name=scenario_name,
                contract_catalog=getattr(self, "scenario_contracts", None),
                action_matrix=getattr(self, "gui_action_matrix", None),
            )
        except Exception as exc:
            self._append_output(f"ERROR: Scenario contract evaluation failed: {exc}")
            return result, None

    def _should_apply_scenario_contracts(self, label: str) -> bool:
        matrix_entry = self._matrix_entry_for_label(label)
        if matrix_entry is not None:
            return "scenario_name" in matrix_entry.inputs
        return str(label or "").startswith("ORL /")

    def _append_contract_evaluation(self, evaluation: ScenarioContractEvaluation | None) -> None:
        if evaluation is None or not evaluation.matched:
            return
        self._append_output(f"loaded scenario contract: {evaluation.contract_scenario_name}")
        self._append_output(
            f"SCENARIO CONTRACT: {evaluation.contract_scenario_name} [{evaluation.status.upper()}]"
        )
        for check in evaluation.passed_checks:
            self._append_output(f"contract check passed: {check}")
        for issue in evaluation.issues:
            self._append_output(f"contract mismatch: {issue}")

    def _attach_explainability_follow_up(self, result: ConsoleResult) -> ConsoleResult:
        scenario_name = str(result.scenario_name or self.scenario_var.get() or "").strip()
        if not scenario_name:
            return result
        if not str(result.name or "").startswith("ORL /"):
            return replace(result, scenario_name=result.scenario_name or scenario_name)
        if result.status not in {"warn", "fail", "error"}:
            return replace(result, scenario_name=result.scenario_name or scenario_name)
        if result.name in EXPLAINABILITY_ACTION_NAMES:
            return replace(result, scenario_name=result.scenario_name or scenario_name)
        if any(str(line or "").startswith("CAMPAIGN STATUS:") for line in result.details):
            return replace(result, scenario_name=result.scenario_name or scenario_name)

        adapter = EngineTestingAPI()
        lines: list[str] = []
        try:
            status_result = adapter.campaign_status(scenario_name=scenario_name)
            explain_result = adapter.campaign_explain(scenario_name=scenario_name)
        except Exception as exc:
            self._append_output(f"ERROR: Explainability follow-up failed: {exc}")
            return replace(result, scenario_name=result.scenario_name or scenario_name)

        if status_result.logs or explain_result.logs or status_result.error or explain_result.error:
            lines.append("FOLLOW-UP EXPLAINABILITY:")
            lines.append("explainability attached to incident/report")
        lines.extend(status_result.logs)
        if status_result.error:
            lines.append(f"CAMPAIGN STATUS ERROR: {status_result.error}")
        lines.extend(explain_result.logs)
        if explain_result.error:
            lines.append(f"CAMPAIGN EXPLAIN ERROR: {explain_result.error}")

        if not lines:
            return replace(result, scenario_name=result.scenario_name or scenario_name)

        existing = set(result.details)
        appended = [line for line in lines if line not in existing]
        for line in appended:
            self._append_output(line)
        if not appended:
            return replace(result, scenario_name=result.scenario_name or scenario_name)
        return replace(
            result,
            scenario_name=result.scenario_name or scenario_name,
            details=[*result.details, *appended],
        )

    def _maybe_auto_export_result(self, result: ConsoleResult) -> ConsoleResult:
        if result.name not in AUTO_EXPORT_REPORT_ACTION_NAMES:
            return result
        try:
            json_path = export_result_json(result)
            text_path = export_result_text(result)
        except Exception as exc:
            self._append_output(f"ERROR: Demo report export failed: {exc}")
            return result

        lines = [
            f"AUTO REPORT JSON: {json_path}",
            f"AUTO REPORT TEXT: {text_path}",
        ]
        for line in lines:
            self._append_output(line)

        artifact_paths = list(result.artifact_paths)
        for path in (str(json_path), str(text_path)):
            if path not in artifact_paths:
                artifact_paths.append(path)

        details = list(result.details)
        for line in lines:
            if line not in details:
                details.append(line)
        return replace(result, artifact_paths=artifact_paths, details=details)

    def _refresh_demo_artifact_validation(self, result: ConsoleResult) -> ConsoleResult:
        if result.name != "ORL / Demo Readiness":
            return result
        if not any(item.name == "ORL / Demo Artifact Validation" for item in result.subresults):
            return result

        entry = self.registry.get("ORL / Demo Artifact Validation")
        if not isinstance(entry, ConsoleAction):
            return result

        log_lines: list[str] = []
        refreshed = run_registry_entry(
            entry,
            entry_lookup=self.registry.get,
            scenario_input=self.scenario_var.get().strip() or result.scenario_name,
            bridge_uri=self.bridge_uri_var.get().strip(),
            command_input=self.command_var.get().strip(),
            log_sink=log_lines.append,
            known_issues=self.known_issues,
        )
        for line in log_lines:
            self._append_output(line)

        new_subresults = [
            refreshed if item.name == "ORL / Demo Artifact Validation" else item
            for item in result.subresults
        ]
        artifact_paths = list(dict.fromkeys([
            *result.artifact_paths,
            *[path for item in new_subresults for path in item.artifact_paths],
        ]))
        step_summary = ", ".join(f"{item.name}={item.status.upper()}" for item in new_subresults)
        summary = f"Suite completed with status {roll_up_statuses(item.status for item in new_subresults).upper()}."
        if step_summary:
            summary = f"{summary} {step_summary}"
        details = list(result.details)
        marker = "AUTO REFRESH: reran ORL / Demo Artifact Validation after demo report export."
        if marker not in details:
            details.append(marker)
        for line in log_lines:
            if line not in details:
                details.append(line)
        return replace(
            result,
            status=roll_up_statuses(item.status for item in new_subresults),
            summary=summary,
            subresults=new_subresults,
            artifact_paths=artifact_paths,
            details=details,
        )

    def _compare_result_against_baseline(self, result: ConsoleResult) -> BaselineComparison | None:
        try:
            return compare_result_to_baseline(
                result,
                action_matrix=getattr(self, "gui_action_matrix", None),
                scenario_contracts=getattr(self, "scenario_contracts", None),
            )
        except Exception as exc:
            self._append_output(f"ERROR: Baseline compare failed: {exc}")
            return None

    def _append_baseline_drift(self, drift: BaselineComparison | None) -> None:
        if drift is None or not drift.matched:
            return
        if drift.baseline_path:
            self._append_output(f"baseline compared: {drift.baseline_path}")
        if drift.status == "pass" or not drift.findings:
            self._append_output("drift check passed")
            return
        for finding in drift.findings:
            prefix = {
                "warn": "drift warning",
                "fail": "drift failure",
                "error": "drift error",
            }.get(finding.status, "drift notice")
            self._append_output(f"{prefix}: {finding.message}")

    def _find_result_divergence(
        self,
        result: ConsoleResult,
        drift: BaselineComparison | None = None,
    ) -> FirstDivergence | None:
        if result.status in {"warn", "fail", "error"} and len(result.artifact_paths) >= 2:
            try:
                divergence = find_first_divergence_in_artifact_paths(result.artifact_paths)
            except Exception as exc:
                self._append_output(f"ERROR: Divergence compare failed: {exc}")
            else:
                if divergence is not None and divergence.comparable and not divergence.identical:
                    return divergence
        if drift is None or not drift.matched or drift.status == "pass":
            return None
        try:
            divergence = compare_result_to_baseline_divergence(result)
        except Exception as exc:
            self._append_output(f"ERROR: Baseline divergence compare failed: {exc}")
            return None
        if not divergence.comparable or divergence.identical:
            return None
        return divergence

    def _append_first_divergence(self, divergence: FirstDivergence | None) -> None:
        if divergence is None or not divergence.comparable or divergence.identical:
            return
        self._append_output(f"FIRST DIVERGENCE: {divergence.message}")
        if divergence.field_path:
            self._append_output(f"first divergence at field: {divergence.field_path}")
        if divergence.step:
            self._append_output(f"step: {divergence.step}")
        if divergence.tick is not None:
            self._append_output(f"tick: {divergence.tick}")
        if divergence.phase:
            self._append_output(f"phase: {divergence.phase}")
        if divergence.scenario_name:
            self._append_output(f"scenario: {divergence.scenario_name}")
        left_label, right_label = self._divergence_value_labels(divergence)
        self._append_output(f"{left_label}: {self._format_divergence_value(divergence.left_value)}")
        self._append_output(f"{right_label}: {self._format_divergence_value(divergence.right_value)}")
        if divergence.artifact_paths:
            self._append_output(f"DIVERGENCE INPUTS: {' | '.join(divergence.artifact_paths)}")

    def _run_first_divergence_finder_action(self, context) -> ConsoleResult:
        source_result = self.last_result
        if source_result is None:
            context.log("no completed run available for divergence compare")
            return make_result(
                name=context.action_name,
                status="warn",
                summary="No completed run is available for first divergence compare.",
            )

        divergence, source_kind = self._resolve_manual_divergence(source_result)
        if divergence is None:
            context.log("first divergence compare unavailable because no comparable baseline or artifact pair was found")
            return make_result(
                name=context.action_name,
                status="warn",
                summary="No comparable baseline or artifact pair is available for first divergence compare.",
            )

        if source_kind == "baseline":
            context.log("comparing current result against saved baseline")
        elif source_kind == "artifacts":
            context.log("comparing comparable artifacts from the last result")

        if divergence.artifact_paths:
            context.log(f"compared artifact paths: {' | '.join(divergence.artifact_paths)}")
        if divergence.scenario_name:
            context.log(f"scenario: {divergence.scenario_name}")

        if not divergence.comparable:
            context.log(divergence.message)
            return make_result(
                name=context.action_name,
                status="warn",
                summary="First divergence compare unavailable.",
                scenario_name=source_result.scenario_name,
                adapter_method="first_divergence_finder",
            )

        if divergence.identical:
            context.log("no divergence found")
            return make_result(
                name=context.action_name,
                status="pass",
                summary="No divergence found.",
                scenario_name=source_result.scenario_name or divergence.scenario_name,
                adapter_method="first_divergence_finder",
            )

        context.log(f"first divergence at field: {divergence.field_path}")
        if divergence.step:
            context.log(f"step: {divergence.step}")
        if divergence.tick is not None:
            context.log(f"tick: {divergence.tick}")
        if divergence.phase:
            context.log(f"phase: {divergence.phase}")
        left_label, right_label = self._divergence_value_labels(divergence)
        context.log(f"{left_label}: {self._format_divergence_value(divergence.left_value)}")
        context.log(f"{right_label}: {self._format_divergence_value(divergence.right_value)}")

        return make_result(
            name=context.action_name,
            status="warn",
            summary=f"First divergence found at {divergence.field_path}.",
            scenario_name=source_result.scenario_name or divergence.scenario_name,
            adapter_method="first_divergence_finder",
        )

    def _resolve_manual_divergence(self, result: ConsoleResult) -> tuple[FirstDivergence | None, str]:
        baseline_divergence = compare_result_to_baseline_divergence(result)
        if baseline_divergence.comparable:
            return baseline_divergence, "baseline"
        artifact_divergence = find_first_divergence_in_artifact_paths(result.artifact_paths)
        if artifact_divergence is not None:
            return artifact_divergence, "artifacts"
        return baseline_divergence, "baseline"

    def _divergence_value_labels(self, divergence: FirstDivergence) -> tuple[str, str]:
        if divergence.comparison_kind == "baseline_metrics":
            return ("baseline", "current")
        return ("left", "right")

    def _format_divergence_value(self, value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)) or value is None:
            return str(value)
        if isinstance(value, dict):
            return "{...}"
        if isinstance(value, list):
            return "[...]"
        try:
            return json.dumps(value, sort_keys=True)
        except TypeError:
            return str(value)

    def _get_expansion_registry(self) -> ExpansionRegistry:
        registry = getattr(self, "expansion_registry", None)
        if registry is None:
            registry = load_expansion_registry()
            self.expansion_registry = registry
        return registry

    def _run_expansion_registry_action(self, context) -> ConsoleResult:
        registry = self._get_expansion_registry()
        snapshot_path = write_expansion_registry_snapshot(registry)
        planning_counts = registry.counts_by_planning_state()
        status_counts = registry.counts_by_status()
        category_counts = registry.counts_by_category()

        context.log(f"EXPANSION REGISTRY JSON: {snapshot_path}")
        context.log(
            "EXPANSION REGISTRY COUNTS: "
            f"total={len(registry.entries)} | "
            f"support_ready={planning_counts.get('support_ready', 0)} | "
            f"blocked_by_support={planning_counts.get('blocked_by_support', 0)} | "
            f"needs_foundation={planning_counts.get('needs_foundation', 0)}"
        )
        context.log(f"EXPANSION REGISTRY STATUS COUNTS: {self._format_count_segments(status_counts)}")
        context.log(f"EXPANSION REGISTRY CATEGORY COUNTS: {self._format_count_segments(category_counts)}")

        grouped = registry.entries_by_planning_state()
        for planning_state in registry.planning_states():
            entries = grouped.get(planning_state, [])
            if not entries:
                continue
            context.log(f"PLANNING STATE: {planning_state} ({len(entries)})")
            for entry in entries:
                context.log(
                    f"- {entry.name} [status={entry.status}, maturity={entry.maturity}, "
                    f"category={entry.category}, theater={entry.theater}, risk={entry.risk_level}]"
                )
                if entry.missing_support_gates:
                    context.log(f"  support blockers: {', '.join(entry.missing_support_gates)}")
                else:
                    context.log(f"  support gates ready: {', '.join(entry.ready_support_gates)}")
                if entry.capabilities:
                    context.log(f"  capabilities: {', '.join(entry.capabilities)}")
                if entry.next_step:
                    context.log(f"  next step: {entry.next_step}")

        return make_result(
            name=context.action_name,
            status="pass",
            summary=f"Expansion registry loaded: {len(registry.entries)} entries.",
            artifact_paths=[str(snapshot_path)],
            adapter_method="expansion_registry",
        )

    def _format_count_segments(self, counts: dict[str, int]) -> str:
        segments = [
            f"{key}={counts[key]}"
            for key in counts
        ]
        return " | ".join(segments)

    def _log_incident_bundle(self, result: ConsoleResult) -> IncidentBundleResult | None:
        try:
            return log_incident_bundle(
                result,
                anomaly_catalog=self.anomaly_catalog,
                action_matrix=self.gui_action_matrix,
            )
        except Exception as exc:
            self._append_output(f"ERROR: Incident logging failed: {exc}")
            return None

    def _emit_incident_breadcrumbs(self, incident: IncidentBundleResult | None) -> None:
        if incident is None:
            return
        for match in incident.anomaly_matches:
            self._append_output(f"POTENTIAL ISSUE: {match.rule_id} | {match.title}")
        if incident.logged:
            self._append_output(f"INCIDENT LOGGED: {incident.bundle_dir}")

    def _attach_incident_metadata(
        self,
        result: ConsoleResult,
        incident: IncidentBundleResult | None,
    ) -> ConsoleResult:
        return attach_incident_metadata(result, incident)

    def _capture_run_manifest(
        self,
        result: ConsoleResult,
        *,
        emit_output: bool = True,
    ) -> RunManifestCaptureResult | None:
        try:
            bridge_var = getattr(self, "bridge_uri_var", None)
            bridge_uri = bridge_var.get().strip() if bridge_var is not None else DEFAULT_BRIDGE_URI
            manifest = capture_run_manifest(
                result,
                bridge_uri=bridge_uri or DEFAULT_BRIDGE_URI,
            )
            if manifest.written and emit_output:
                self._append_output(f"wrote run manifest: {manifest.manifest_path}")
            return manifest
        except Exception as exc:
            self._append_output(f"ERROR: Run manifest capture failed: {exc}")
            return None

    def _attach_run_manifest_metadata(
        self,
        result: ConsoleResult,
        manifest: RunManifestCaptureResult | None,
    ) -> ConsoleResult:
        if manifest is None or not manifest.written:
            return result
        detail_lines = list(result.details)
        for line in manifest_metadata_lines(manifest):
            if line not in detail_lines:
                detail_lines.append(line)
        artifact_paths = list(result.artifact_paths)
        if manifest.manifest_path and manifest.manifest_path not in artifact_paths:
            artifact_paths.append(manifest.manifest_path)
        return replace(
            result,
            details=detail_lines,
            artifact_paths=artifact_paths,
            started_at=result.started_at or manifest.started_at,
            finished_at=result.finished_at or manifest.finished_at,
        )

    def _refresh_run_manifest_after_incident_metadata(
        self,
        result: ConsoleResult,
        manifest: RunManifestCaptureResult | None,
        incident: IncidentBundleResult | None,
    ) -> RunManifestCaptureResult | None:
        if manifest is None or not manifest.written:
            return manifest
        if incident is None or not incident.logged:
            return manifest
        refreshed = self._capture_run_manifest(result, emit_output=False)
        return refreshed or manifest

    def _refresh_auto_export_after_support_metadata(
        self,
        result: ConsoleResult,
        manifest: RunManifestCaptureResult | None,
        incident: IncidentBundleResult | None,
    ) -> ConsoleResult:
        has_manifest = bool(manifest is not None and manifest.written)
        has_incident = bool(
            incident is not None and (incident.logged or incident.anomaly_matches)
        )
        if not has_manifest and not has_incident:
            return result
        if result.name not in AUTO_EXPORT_REPORT_ACTION_NAMES:
            return result
        try:
            export_result_json(result)
            export_result_text(result)
        except Exception as exc:
            self._append_output(f"ERROR: Auto report refresh failed: {exc}")
        return result

    def _is_running(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def _update_control_states(self, *, running_override: bool | None = None) -> None:
        is_running = self._is_running() if running_override is None else bool(running_override)
        idle_state = "disabled" if is_running else "normal"
        self.refresh_scenarios_button.configure(state=idle_state)
        self.bridge_button.configure(state=idle_state)
        self.mwe_button.configure(state=idle_state)
        self.stop_button.configure(state=idle_state)
        doctor_button = getattr(self, "doctor_button", None)
        if doctor_button is not None:
            doctor_button.configure(state=idle_state)
        self.clear_button.configure(state=idle_state)
        self.export_button.configure(state="normal" if (not is_running and self.last_result is not None) else "disabled")
        self.save_baseline_button.configure(state="normal" if (not is_running and self.last_result is not None) else "disabled")
        self.compare_baseline_button.configure(
            state="normal" if (not is_running and self.last_result is not None) else "disabled"
        )
        if is_running or self._selected_entry() is None:
            self.run_button.configure(state="disabled")
        else:
            self.run_button.configure(state="normal")


def main() -> int:
    try:
        root = Tk()
    except TclError as exc:
        print(f"MWE Operations Console requires a desktop display: {exc}", file=sys.stderr)
        return 1
    OperationsConsoleApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
