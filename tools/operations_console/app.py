from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from tkinter import END, NSEW, StringVar, TclError, Tk
from tkinter import scrolledtext, ttk


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from tools.operations_console.models import ConsoleRegistryEntry, ConsoleResult
from tools.operations_console.process_control import ManagedProcessController, ProcessControlResult
from tools.operations_console.report_export import export_result_json, export_result_text
from tools.operations_console.registry import DEFAULT_BRIDGE_URI, ActionRegistry, build_default_registry, list_live_scenarios
from tools.operations_console.runner_utils import run_registry_entry


STATUS_COLORS = {
    "idle": "#868686",
    "running": "#3b6ea8",
    "pass": "#2e7d32",
    "fail": "#a8432b",
    "warn": "#8a6b22",
    "error": "#8b2635",
}


class OperationsConsoleApp:
    def __init__(self, root: Tk, registry: ActionRegistry | None = None):
        self.root = root
        self.registry = registry or build_default_registry()
        self.event_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_result: ConsoleResult | None = None
        self.process_controller = ManagedProcessController(
            log_sink=lambda line: self.event_queue.put(("log", line)),
        )

        self.bridge_uri_var = StringVar(value=DEFAULT_BRIDGE_URI)
        self.scenario_var = StringVar(value="")
        self.status_var = StringVar(value="IDLE")
        self.summary_var = StringVar(value="Ready.")
        self.description_var = StringVar(value="Select an action to view details.")

        self.tree: ttk.Treeview
        self.scenario_combo: ttk.Combobox
        self.description_label: ttk.Label
        self.output_text: scrolledtext.ScrolledText
        self.run_button: ttk.Button
        self.clear_button: ttk.Button
        self.export_button: ttk.Button
        self.refresh_scenarios_button: ttk.Button
        self.bridge_button: ttk.Button
        self.mwe_button: ttk.Button
        self.stop_button: ttk.Button
        self.status_badge: ttk.Label

        self._build()
        self._populate_actions()
        self._set_status("idle", "Ready.")
        self._update_control_states()
        self._append_output("MWE Operations Console ready.")
        self.root.after(75, self._poll_events)

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
        controls.columnconfigure(5, weight=1)
        self.run_button = ttk.Button(controls, text="Run", command=self._run_selected, state="disabled")
        self.run_button.grid(row=0, column=0, sticky="w")
        self.clear_button = ttk.Button(controls, text="Clear Output", command=self._clear_output)
        self.clear_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.export_button = ttk.Button(controls, text="Export Report", command=self._export_report, state="disabled")
        self.export_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.bridge_button = ttk.Button(controls, text="Run Bridge", command=self._launch_bridge)
        self.bridge_button.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.mwe_button = ttk.Button(controls, text="Run MWE", command=self._launch_mwe)
        self.mwe_button.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self.stop_button = ttk.Button(controls, text="Stop Managed Processes", command=self._stop_managed_processes)
        self.stop_button.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

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
        self.description_var.set(entry.description)
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
        self._append_output("")
        self._append_output(f"== Running {entry.name} ==")
        self._set_status("running", f"Running {entry.name}...")
        self._update_control_states(running_override=True)

        def worker() -> None:
            result = run_registry_entry(
                entry,
                entry_lookup=self.registry.get,
                scenario_input=scenario_input,
                bridge_uri=bridge_uri,
                log_sink=lambda line: self.event_queue.put(("log", line)),
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
        self._set_status("running", "Refreshing scenarios...")
        self._update_control_states(running_override=True)

        def worker() -> None:
            try:
                scenarios = list_live_scenarios(uri)
                self.event_queue.put(("scenario_roster", {"scenarios": scenarios, "uri": uri}))
            except Exception as exc:
                self.event_queue.put(("task_error", ("Scenario refresh failed.", str(exc))))

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

    def _run_process_control(self, *, label: str, summary: str, runner) -> None:
        if self._is_running():
            return
        self._append_output("")
        self._append_output(f"== {label} ==")
        self._set_status("running", summary)
        self._update_control_states(running_override=True)

        def worker() -> None:
            try:
                result = runner()
                self.event_queue.put(("process_result", result))
            except Exception as exc:
                self.event_queue.put(("task_error", (f"{label} failed.", str(exc))))

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
        self.last_result = result
        if result.errors:
            for error in result.errors:
                self._append_output(f"ERROR: {error}")
        self._append_output(f"== {result.status.upper()} :: {result.summary} ({result.duration_ms} ms) ==")
        self._set_status(result.status, result.summary)
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
        self._set_status(status, summary)
        self._update_control_states()

    def _handle_process_result(self, result: ProcessControlResult) -> None:
        self._append_output(f"== {result.status.upper()} :: {result.summary} ==")
        self._set_status(result.status, result.summary)
        self._update_control_states()

    def _handle_task_error(self, payload: tuple[str, str]) -> None:
        summary, error = payload
        self._append_output(f"ERROR: {error}")
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

    def _apply_scenario_roster(self, scenarios: list[str]) -> bool:
        normalized = tuple(str(value or "").strip() for value in scenarios if str(value or "").strip())
        self.scenario_combo["values"] = normalized
        current = self.scenario_var.get().strip()
        if current or not normalized:
            return False
        self.scenario_var.set(normalized[0])
        return True

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

    def _is_running(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def _update_control_states(self, *, running_override: bool | None = None) -> None:
        is_running = self._is_running() if running_override is None else bool(running_override)
        idle_state = "disabled" if is_running else "normal"
        self.refresh_scenarios_button.configure(state=idle_state)
        self.bridge_button.configure(state=idle_state)
        self.mwe_button.configure(state=idle_state)
        self.stop_button.configure(state=idle_state)
        self.clear_button.configure(state=idle_state)
        self.export_button.configure(state="normal" if (not is_running and self.last_result is not None) else "disabled")
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
