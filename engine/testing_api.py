from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.engine_api import EngineAPI
from server.scenario_store import list_scenarios as store_list_scenarios
from server.scenario_store import read_scenario
from tools.orl import (
    check_round1_documentation_support,
    load_demo_checklist,
    load_round1_manifest,
    latest_demo_artifact_shelf,
    run_round1_scenario_matrix,
    validate_demo_artifact_shelf,
    validate_round1_scenarios,
    write_orl_artifact,
)


@dataclass(frozen=True)
class TestingApiResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    adapter_method: str = ""
    executed_command: List[str] = field(default_factory=list)
    return_code: int | None = None


class EngineTestingAPI:
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]

    def artifact_root(self) -> Path:
        return self.repo_root / "artifacts" / "operations_console" / "engine_adapter"

    def list_scenarios(self) -> TestingApiResult:
        catalog = self._scenario_catalog()
        scenarios = [entry["file_name"] for entry in self._sorted_catalog_entries(catalog) if entry.get("file_name")]
        bridge_scenarios = [entry["file_name"] for entry in self._sorted_catalog_entries(catalog) if entry.get("bridge_listed")]
        engine_scenarios = [entry["scenario_id"] for entry in self._sorted_catalog_entries(catalog) if entry.get("engine_loadable")]
        return TestingApiResult(
            ok=True,
            data={
                "scenarios": scenarios,
                "bridge_scenarios": bridge_scenarios,
                "engine_scenarios": engine_scenarios,
                "primary_scenarios": self._primary_scenario_ids(),
            },
            metrics={"scenario_count": len(scenarios)},
            logs=[
                f"Listed {len(scenarios)} scenario(s).",
                f"Bridge roster scenarios: {len(bridge_scenarios)}",
                f"Engine-loadable scenarios: {len(engine_scenarios)}",
            ],
            adapter_method="list_scenarios",
        )

    def load_scenario(self, name: str = "") -> TestingApiResult:
        entry = self._resolve_scenario_entry(name)
        if entry is None:
            return TestingApiResult(
                ok=False,
                error="Scenario not found in roster.",
                logs=[f"Unable to resolve scenario: {name or '<default>'}"],
                adapter_method="load_scenario",
            )

        resolved_name = str(entry.get("file_name") or f"{entry.get('scenario_id')}.json").strip()
        scenario_id = str(entry.get("scenario_id") or resolved_name.removesuffix(".json")).strip()
        payload = self._read_scenario_payload(entry)
        if not isinstance(payload, dict):
            return TestingApiResult(
                ok=False,
                error=f"Unable to read scenario payload: {scenario_id or resolved_name}",
                logs=[f"Scenario payload missing for {scenario_id or resolved_name}."],
                adapter_method="load_scenario",
            )

        api = EngineAPI()
        try:
            meta = api.load_scenario(scenario_id)
            state = api.start_game()
        except Exception as exc:
            if not entry.get("engine_loadable"):
                error = "Scenario is available in content storage but not engine-loadable for ORL checks."
                log_detail = (
                    f"Scenario is not available in engine-ready directories for headless ORL checks: {scenario_id or resolved_name}"
                )
            else:
                error = f"Engine failed to load scenario {scenario_id}: {exc}"
                log_detail = f"Engine load failed for {scenario_id}: {exc}"
            return TestingApiResult(
                ok=False,
                error=error,
                logs=[
                    f"Resolved scenario: {resolved_name}",
                    log_detail,
                ],
                adapter_method="load_scenario",
            )
        logs = [
            f"Resolved scenario: {resolved_name}",
            f"Loaded scenario id: {scenario_id}",
            f"Started scenario: {meta.get('name') or scenario_id}",
        ]
        return TestingApiResult(
            ok=True,
            data={
                "scenario_name": resolved_name,
                "scenario_id": scenario_id,
                "meta": meta,
                "state": state,
            },
            metrics={"unit_count": len(state.get("units") or [])},
            logs=logs,
            adapter_method="load_scenario",
        )

    def scenario_validator(self) -> TestingApiResult:
        report = validate_round1_scenarios(repo_root_path=self.repo_root)
        return TestingApiResult(
            ok=bool(report.get("ok")),
            data={
                "rows": list(report.get("rows") or []),
                "failures": list(report.get("failures") or []),
                "blocker_class": str(report.get("blocker_class") or "scenario.validator"),
            },
            error="" if report.get("ok") else "Round 1 scenario validation failed.",
            artifacts=[str(report.get("artifact_path") or "")] if report.get("artifact_path") else [],
            metrics={
                "scenario_count": len(report.get("rows") or []),
                "failure_count": len(report.get("failures") or []),
            },
            logs=list(report.get("logs") or []),
            adapter_method="scenario_validator",
        )

    def scenario_matrix(self) -> TestingApiResult:
        report = run_round1_scenario_matrix(repo_root_path=self.repo_root)
        return TestingApiResult(
            ok=bool(report.get("ok")),
            data={
                "rows": list(report.get("rows") or []),
                "failures": list(report.get("failures") or []),
                "blocker_class": str(report.get("blocker_class") or "scenario.matrix"),
            },
            error="" if report.get("ok") else "Round 1 scenario matrix failed.",
            artifacts=[str(report.get("artifact_path") or "")] if report.get("artifact_path") else [],
            metrics={
                "case_count": len(report.get("rows") or []),
                "failure_count": len(report.get("failures") or []),
            },
            logs=list(report.get("logs") or []),
            adapter_method="scenario_matrix",
        )

    def explainability_smoke(self) -> TestingApiResult:
        manifest = load_round1_manifest(self.repo_root / "tools" / "orl" / "round1_manifest.yaml")
        target_scenarios = [scenario for scenario in manifest.primary_scenarios if scenario.require_grease_board]
        checks: List[Dict[str, Any]] = []
        failures: List[str] = []
        logs: List[str] = []

        for scenario in target_scenarios:
            status_result = self.campaign_status(scenario.scenario_id)
            explain_result = self.campaign_explain(scenario.scenario_id)
            row_ok = bool(
                status_result.ok
                and explain_result.ok
                and status_result.data.get("objective")
                and status_result.data.get("front_status")
                and explain_result.data.get("staff_notes")
            )
            if not row_ok:
                failures.append(scenario.scenario_id)
            checks.append(
                {
                    "check_id": f"explainability.{scenario.scenario_id}",
                    "label": f"Explainability Smoke / {scenario.scenario_id}",
                    "blocker_class": "tooling.explainability_smoketest",
                    "status": "pass" if row_ok else "fail",
                    "summary": "Explainability smoke passed." if row_ok else "Explainability smoke failed.",
                    "artifacts": [],
                    "logs": list(status_result.logs) + list(explain_result.logs),
                }
            )
            logs.append(
                f"{scenario.scenario_id}: {'PASS' if row_ok else 'FAIL'} objective={status_result.data.get('objective') or '<none>'}"
            )

        artifact_path = write_orl_artifact(
            "round1-explainability-smoke",
            {
                "status": "pass" if not failures else "fail",
                "checks": checks,
                "failures": failures,
            },
            repo_root_path=self.repo_root,
        )
        logs.append(f"artifact: {artifact_path}")
        return TestingApiResult(
            ok=not failures,
            data={"checks": checks, "failures": failures},
            error="" if not failures else "Explainability smoke failed.",
            artifacts=[str(artifact_path)],
            metrics={"scenario_count": len(checks), "failure_count": len(failures)},
            logs=logs,
            adapter_method="explainability_smoke",
        )

    def demo_checklist(self, scenario_name: str = "") -> TestingApiResult:
        try:
            checklist = load_demo_checklist(self.repo_root / "tools" / "orl" / "demo_checklist.yaml")
        except Exception as exc:
            return TestingApiResult(
                ok=False,
                error=f"Unable to load demo checklist: {exc}",
                logs=[f"demo checklist load failed: {exc}"],
                adapter_method="demo_checklist",
            )

        selected_scenario = str(scenario_name or checklist.default_scenario).strip()
        expected_outcomes = list(checklist.expected_outcomes.get(selected_scenario) or [])
        rows = [
            {
                "item_id": item.item_id,
                "label": item.label,
                "required": item.required,
                "notes": item.notes,
            }
            for item in checklist.checklist
        ]
        checks = [
            {
                "check_id": f"checklist.{item.item_id}",
                "label": item.label,
                "blocker_class": "demo.checklist",
                "status": "pass",
                "summary": f"{'Required' if item.required else 'Optional'} checklist item.",
                "artifacts": [],
                "logs": [item.notes] if item.notes else [],
            }
            for item in checklist.checklist
        ]
        logs = [f"Demo checklist loaded: {checklist.source_path}", f"Selected scenario: {selected_scenario}"]
        logs.extend(
            f"checklist: {'REQUIRED' if item.required else 'OPTIONAL'} {item.label} - {item.notes}"
            for item in checklist.checklist
        )
        logs.extend(f"expected outcome: {item}" for item in expected_outcomes)
        logs.extend(f"inspect artifact: {item}" for item in checklist.inspect_artifacts)
        if checklist.bug_reports_to:
            logs.append(f"bug reports: {checklist.bug_reports_to}")

        artifact_path = write_orl_artifact(
            "demo-checklist",
            {
                "selected_scenario": selected_scenario,
                "rows": rows,
                "inspect_artifacts": checklist.inspect_artifacts,
                "bug_reports_to": checklist.bug_reports_to,
                "expected_outcomes": expected_outcomes,
            },
            repo_root_path=self.repo_root,
        )
        logs.append(f"artifact: {artifact_path}")
        return TestingApiResult(
            ok=True,
            data={
                "selected_scenario": selected_scenario,
                "rows": rows,
                "checks": checks,
                "inspect_artifacts": list(checklist.inspect_artifacts),
                "bug_reports_to": checklist.bug_reports_to,
                "expected_outcomes": expected_outcomes,
            },
            artifacts=[str(artifact_path)],
            metrics={"checklist_count": len(rows), "expected_outcome_count": len(expected_outcomes)},
            logs=logs,
            adapter_method="demo_checklist",
        )

    def deterministic_demo_runner(self, scenario_name: str = "") -> TestingApiResult:
        try:
            checklist = load_demo_checklist(self.repo_root / "tools" / "orl" / "demo_checklist.yaml")
        except Exception as exc:
            return TestingApiResult(
                ok=False,
                error=f"Unable to load demo checklist: {exc}",
                logs=[f"demo checklist load failed: {exc}"],
                adapter_method="deterministic_demo_runner",
            )

        selected_scenario = str(scenario_name or checklist.default_scenario).strip()
        status_result = self.campaign_status(selected_scenario)
        explain_result = self.campaign_explain(selected_scenario)
        snapshot_result = self.snapshot_smoke(selected_scenario)
        replay_result = self.replay_validation(selected_scenario)

        checks = [
            self._check_from_result(
                status_result,
                check_id="demo.campaign_status",
                label="Campaign Status",
                blocker_class="demo.campaign_status",
            ),
            self._check_from_result(
                explain_result,
                check_id="demo.campaign_explain",
                label="Campaign Explain",
                blocker_class="demo.campaign_explain",
            ),
            self._check_from_result(
                snapshot_result,
                check_id="demo.snapshot_smoke",
                label="Snapshot Smoke",
                blocker_class="demo.snapshot_smoke",
            ),
            self._check_from_result(
                replay_result,
                check_id="demo.replay_compare",
                label="Replay Compare",
                blocker_class="demo.replay_compare",
            ),
        ]
        artifacts: List[str] = []
        logs = [f"Selected scenario: {selected_scenario}"]
        failure_count = 0

        for check in checks:
            artifacts.extend(str(path) for path in list(check.get("artifacts") or []) if str(path).strip())
            logs.append(f"[{check['blocker_class']}] {check['label']}: {check['status'].upper()} - {check['summary']}")
            for line in list(check.get("logs") or [])[:20]:
                logs.append(f"  {line}")
            if check.get("status") != "pass":
                failure_count += 1

        expected_outcomes = list(checklist.expected_outcomes.get(selected_scenario) or [])
        logs.extend(f"expected outcome: {item}" for item in expected_outcomes)
        if checklist.bug_reports_to:
            logs.append(f"bug reports: {checklist.bug_reports_to}")

        artifact_path = write_orl_artifact(
            "deterministic-demo-runner",
            {
                "status": "pass" if failure_count == 0 else "fail",
                "selected_scenario": selected_scenario,
                "checks": checks,
                "expected_outcomes": expected_outcomes,
                "bug_reports_to": checklist.bug_reports_to,
            },
            repo_root_path=self.repo_root,
        )
        artifacts.append(str(artifact_path))
        logs.append(f"artifact: {artifact_path}")
        return TestingApiResult(
            ok=failure_count == 0,
            data={
                "selected_scenario": selected_scenario,
                "checks": checks,
                "expected_outcomes": expected_outcomes,
                "bug_reports_to": checklist.bug_reports_to,
            },
            error="" if failure_count == 0 else "Deterministic demo runner failed.",
            artifacts=artifacts,
            metrics={"check_count": len(checks), "failure_count": failure_count},
            logs=logs,
            adapter_method="deterministic_demo_runner",
        )

    def latest_artifacts(self) -> TestingApiResult:
        shelf = latest_demo_artifact_shelf(repo_root_path=self.repo_root)
        checks: List[Dict[str, Any]] = []
        artifacts: List[str] = []
        missing = 0
        logs: List[str] = []

        for slot_id, info in shelf.items():
            path = str(info.get("path") or "").strip()
            exists = bool(info.get("exists"))
            if path:
                artifacts.append(path)
            if not exists:
                missing += 1
            logs.append(f"{slot_id}: {path or '<missing>'}")
            checks.append(
                {
                    "check_id": f"latest.{slot_id}",
                    "label": str(info.get("label") or slot_id),
                    "blocker_class": "demo.latest_artifacts",
                    "status": "pass" if exists else "warn",
                    "summary": f"{info.get('label') or slot_id}: {path or 'missing'}",
                    "artifacts": [path] if path else [],
                    "logs": [
                        f"path: {path or '<missing>'}",
                        *([f"modified_at: {info['modified_at']}"] if info.get("modified_at") else []),
                        *([f"size_bytes: {info['size_bytes']}"] if info.get("size_bytes") else []),
                    ],
                }
            )

        artifact_path = write_orl_artifact(
            "latest-demo-artifacts",
            {
                "status": "pass" if missing == 0 else "warn",
                "shelf": shelf,
                "checks": checks,
            },
            repo_root_path=self.repo_root,
        )
        artifacts.append(str(artifact_path))
        logs.append(f"artifact: {artifact_path}")
        return TestingApiResult(
            ok=missing == 0,
            data={"shelf": shelf, "checks": checks},
            error="",
            artifacts=artifacts,
            metrics={"artifact_slot_count": len(shelf), "missing_count": missing},
            logs=logs,
            adapter_method="latest_artifacts",
        )

    def demo_artifact_validation(self) -> TestingApiResult:
        report = validate_demo_artifact_shelf(repo_root_path=self.repo_root)
        artifacts = [str(report.get("artifact_path") or "")] if report.get("artifact_path") else []
        for check in list(report.get("checks") or []):
            for artifact_path in list(check.get("artifacts") or []):
                if str(artifact_path).strip():
                    artifacts.append(str(artifact_path))

        deduped_artifacts = list(dict.fromkeys(artifacts))
        return TestingApiResult(
            ok=bool(report.get("ok")),
            data={
                "checks": list(report.get("checks") or []),
                "missing": list(report.get("missing") or []),
                "shelf": dict(report.get("shelf") or {}),
                "blocker_class": str(report.get("blocker_class") or "demo.artifact_output"),
            },
            error="" if report.get("ok") else "Demo artifact validation failed.",
            artifacts=deduped_artifacts,
            metrics={
                "artifact_slot_count": len(dict(report.get("shelf") or {})),
                "missing_count": len(list(report.get("missing") or [])),
            },
            logs=list(report.get("logs") or []),
            adapter_method="demo_artifact_validation",
        )

    def pitch_support_bundle(self, scenario_name: str = "") -> TestingApiResult:
        from tools.orl.pitch_support import export_pitch_support_bundle

        report = export_pitch_support_bundle(scenario_name=scenario_name, repo_root_path=self.repo_root)
        failure_count = sum(1 for check in list(report.get("checks") or []) if check.get("status") != "pass")
        return TestingApiResult(
            ok=bool(report.get("ok")),
            data={
                "checks": list(report.get("checks") or []),
                "bundle_dir": str(report.get("bundle_dir") or ""),
                "selected_scenario": str(report.get("selected_scenario") or ""),
            },
            error="" if report.get("ok") else "Pitch support bundle export is missing required components.",
            artifacts=list(dict.fromkeys(str(path) for path in list(report.get("artifact_paths") or []) if str(path).strip())),
            metrics={"check_count": len(list(report.get("checks") or [])), "failure_count": failure_count},
            logs=list(report.get("logs") or []),
            adapter_method="pitch_support_bundle",
        )

    def round1_gate(self) -> TestingApiResult:
        manifest = load_round1_manifest(self.repo_root / "tools" / "orl" / "round1_manifest.yaml")
        checks: List[Dict[str, Any]] = []
        artifacts: List[str] = []
        logs: List[str] = []

        checks.append(
            self._run_pytest_check(
                check_id="rules.objective_contest",
                label="Objective Contest Rules",
                blocker_class="rules.objective_contest",
                pytest_args=[
                    str(self.repo_root / "tests" / "engine" / "test_round1_support.py::test_objective_contest_rules_hold_contested_locations_neutral"),
                ],
            )
        )
        checks.append(
            self._run_pytest_check(
                check_id="rules.movement_semantics",
                label="Movement Semantics V1",
                blocker_class="rules.movement_semantics",
                pytest_args=[
                    str(self.repo_root / "tests" / "engine" / "test_round1_support.py::test_engine_api_move_action_uses_current_movement_semantics_v1"),
                ],
            )
        )
        checks.append(
            self._run_pytest_check(
                check_id="rules.objective_scoring",
                label="Objective Control And Scoring",
                blocker_class="rules.objective_control_scoring",
                pytest_args=[
                    str(self.repo_root / "tests" / "engine" / "test_round1_support.py::test_objective_control_and_scoring_award_once_per_capture"),
                ],
            )
        )
        checks.append(
            self._run_pytest_check(
                check_id="ai.objective_reasoning",
                label="AI Objective Reasoning Sanity",
                blocker_class="ai.objective_reasoning",
                pytest_args=[
                    str(self.repo_root / "tests" / "test_engine_bai_controller.py"),
                    str(self.repo_root / "tests" / "test_engine_bai_operational.py"),
                    str(self.repo_root / "tests" / "test_bai_first_playable.py"),
                ],
            )
        )

        snapshot = self.snapshot_smoke("inchon_mvp")
        replay = self.replay_validation("inchon_mvp")
        persistence_logs = list(snapshot.logs) + list(replay.logs)
        persistence_artifacts = list(snapshot.artifacts) + list(replay.artifacts)
        checks.append(
            {
                "check_id": "persistence.snapshot_replay_compare",
                "label": "Save Load Replay Compare Stability",
                "blocker_class": "persistence.snapshot_replay_compare",
                "status": "pass" if snapshot.ok and replay.ok else "fail",
                "summary": "Snapshot and replay stability passed."
                if snapshot.ok and replay.ok
                else "Snapshot and replay stability failed.",
                "artifacts": persistence_artifacts,
                "logs": persistence_logs,
            }
        )

        validator = self.scenario_validator()
        matrix = self.scenario_matrix()
        explainability = self.explainability_smoke()
        documentation = check_round1_documentation_support(repo_root_path=self.repo_root, manifest=manifest)
        all_green = self.run_all_green()

        checks.extend(
            [
                self._check_from_result(
                    validator,
                    check_id="tooling.scenario_validator",
                    label="Scenario Validator",
                    blocker_class="tooling.scenario_validator",
                ),
                self._check_from_result(
                    matrix,
                    check_id="tooling.scenario_matrix",
                    label="Scenario Matrix",
                    blocker_class="tooling.scenario_matrix",
                ),
                self._check_from_result(
                    explainability,
                    check_id="tooling.explainability_smoketest",
                    label="Explainability Smoketest",
                    blocker_class="tooling.explainability_smoketest",
                ),
                {
                    "check_id": "support.documentation",
                    "label": "Documentation And Support Guidance",
                    "blocker_class": str(documentation.get("blocker_class") or "support.documentation"),
                    "status": str(documentation.get("status") or "fail"),
                    "summary": str(documentation.get("summary") or "Documentation support check failed."),
                    "artifacts": [str(documentation.get("artifact_path") or "")] if documentation.get("artifact_path") else [],
                    "logs": list(documentation.get("logs") or []),
                },
                self._check_from_result(
                    all_green,
                    check_id="tooling.all_green",
                    label="All Green Runner",
                    blocker_class="tooling.all_green",
                ),
            ]
        )

        failure_count = 0
        blocker_classes: List[str] = []
        for check in checks:
            artifacts.extend(str(path) for path in list(check.get("artifacts") or []) if str(path).strip())
            logs.append(f"[{check['blocker_class']}] {check['label']}: {check['status'].upper()} - {check['summary']}")
            blocker_classes.append(str(check.get("blocker_class") or "").strip())
            if check.get("status") != "pass":
                failure_count += 1
            for line in list(check.get("logs") or [])[:40]:
                logs.append(f"  {line}")

        logs.extend(f"How to run tests: {item}" for item in manifest.run_tests)
        logs.extend(f"Inspect artifacts: {item}" for item in manifest.inspect_artifacts)
        if manifest.bug_reports_to:
            logs.append(f"Bug reports: {manifest.bug_reports_to}")

        artifact_path = write_orl_artifact(
            "round1-gate",
            {
                "status": "pass" if failure_count == 0 else "fail",
                "checks": checks,
                "bug_reports_to": manifest.bug_reports_to,
                "run_tests": manifest.run_tests,
                "inspect_artifacts": manifest.inspect_artifacts,
            },
            repo_root_path=self.repo_root,
        )
        artifacts.append(str(artifact_path))
        logs.append(f"artifact: {artifact_path}")

        return TestingApiResult(
            ok=failure_count == 0,
            data={
                "checks": checks,
                "blocker_classes": sorted({item for item in blocker_classes if item}),
                "bug_reports_to": manifest.bug_reports_to,
                "run_tests": list(manifest.run_tests),
                "inspect_artifacts": list(manifest.inspect_artifacts),
            },
            error="" if failure_count == 0 else "Round 1 gate failed.",
            artifacts=artifacts,
            metrics={"check_count": len(checks), "failure_count": failure_count},
            logs=logs,
            adapter_method="round1_gate",
        )

    def campaign_status(self, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "campaign_status")

        payload = self._scenario_payload_for_loaded(loaded)
        if payload is None:
            return TestingApiResult(
                ok=False,
                error="Scenario payload missing for campaign status.",
                logs=list(loaded.logs),
                metrics=dict(loaded.metrics),
                adapter_method="campaign_status",
            )

        meta = dict(loaded.data.get("meta") or {})
        state = dict(loaded.data.get("state") or {})
        grease_board = dict(payload.get("grease_board") or {})
        objectives = [
            str(item.get("name") or "").strip()
            for item in list(payload.get("objectives") or [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        alerts = [
            str(item or "").strip()
            for item in list(grease_board.get("alerts") or [])
            if str(item or "").strip()
        ]
        data = {
            "scenario_id": str(loaded.data.get("scenario_id") or meta.get("id") or "").strip(),
            "scenario_name": str(loaded.data.get("scenario_name") or "").strip(),
            "display_name": str(meta.get("name") or payload.get("name") or "").strip(),
            "turn": str(grease_board.get("turn") or "").strip(),
            "objective": str(grease_board.get("objective") or "").strip(),
            "front_status": str(grease_board.get("front_status") or "").strip(),
            "supply_status": str(grease_board.get("supply_status") or "").strip(),
            "main_effort": str(grease_board.get("main_effort") or "").strip(),
            "unit_count": int(loaded.metrics.get("unit_count") or len(state.get("units") or []) or 0),
            "objective_count": len(objectives),
            "alert_count": len(alerts),
            "ai_status": dict((state.get("game") or {}).get("ai") or {}),
            "vp": dict((state.get("game") or {}).get("vp") or {}),
        }
        return TestingApiResult(
            ok=True,
            data=data,
            metrics={
                "unit_count": data["unit_count"],
                "objective_count": data["objective_count"],
                "alert_count": data["alert_count"],
            },
            logs=self._campaign_status_logs(data),
            adapter_method="campaign_status",
        )

    def campaign_explain(self, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "campaign_explain")

        payload = self._scenario_payload_for_loaded(loaded)
        if payload is None:
            return TestingApiResult(
                ok=False,
                error="Scenario payload missing for campaign explain.",
                logs=list(loaded.logs),
                metrics=dict(loaded.metrics),
                adapter_method="campaign_explain",
            )

        meta = dict(loaded.data.get("meta") or {})
        grease_board = dict(payload.get("grease_board") or {})
        orders = [
            str(item or "").strip()
            for item in list(grease_board.get("orders") or [])
            if str(item or "").strip()
        ]
        alerts = [
            str(item or "").strip()
            for item in list(grease_board.get("alerts") or [])
            if str(item or "").strip()
        ]
        objectives = [
            str(item.get("name") or "").strip()
            for item in list(payload.get("objectives") or [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        data = {
            "scenario_id": str(loaded.data.get("scenario_id") or meta.get("id") or "").strip(),
            "scenario_name": str(loaded.data.get("scenario_name") or "").strip(),
            "display_name": str(meta.get("name") or payload.get("name") or "").strip(),
            "description": str(payload.get("description") or "").strip(),
            "staff_notes": str(grease_board.get("staff_notes") or "").strip(),
            "orders": orders,
            "alerts": alerts,
            "objectives": objectives,
        }
        return TestingApiResult(
            ok=True,
            data=data,
            metrics={
                "order_count": len(orders),
                "alert_count": len(alerts),
                "objective_count": len(objectives),
            },
            logs=self._campaign_explain_logs(data),
            adapter_method="campaign_explain",
        )

    def save_snapshot(self, path: str | Path | None = None, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "save_snapshot")

        meta = dict(loaded.data.get("meta") or {})
        scenario_id = str(loaded.data.get("scenario_id") or meta.get("id") or "").strip()
        api = EngineAPI()
        api.load_scenario(scenario_id)
        api.start_game()

        final_path = Path(path) if path is not None else self._snapshot_artifact_path(scenario_id or "snapshot")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_snapshot_file(final_path, api)

        logs = list(loaded.logs) + [f"Snapshot saved: {final_path}"]
        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": scenario_id,
                "scenario_name": meta.get("name") or scenario_id,
                "snapshot_path": str(final_path),
                "time": self._time_to_dict(api.time),
            },
            artifacts=[str(final_path)],
            metrics={"unit_count": len(api.units.all_units()) if api.units is not None else 0},
            logs=logs,
            adapter_method="save_snapshot",
        )

    def load_snapshot(self, path: str | Path) -> TestingApiResult:
        source_path = Path(path)
        if not source_path.exists() or not source_path.is_file():
            return TestingApiResult(
                ok=False,
                error=f"Snapshot file not found: {source_path}",
                logs=[f"Snapshot file missing: {source_path}"],
                adapter_method="load_snapshot",
            )

        snapshot_data = self._read_snapshot_file(source_path)
        scenario_id = str(snapshot_data.get("scenario_id") or "").strip()
        if not scenario_id:
            return TestingApiResult(
                ok=False,
                error="Snapshot file is missing a scenario_id.",
                logs=[f"Snapshot file missing scenario_id: {source_path}"],
                adapter_method="load_snapshot",
            )

        api = EngineAPI()
        meta = dict(api.load_scenario(scenario_id) or {})
        api.start_game()
        self._restore_snapshot_state(api, snapshot_data)

        game_time = api.time
        game_map = api.game_map
        units = api.units
        meta.update(dict(snapshot_data.get("meta") or {}))
        unit_count = len(units.all_units()) if units is not None else 0
        logs = [
            f"Snapshot loaded: {source_path}",
            f"Scenario restored: {meta.get('id') or scenario_id}",
            f"Units restored: {unit_count}",
        ]
        return TestingApiResult(
            ok=True,
            data={
                "snapshot_path": str(source_path),
                "scenario_id": str(meta.get("id") or scenario_id).strip(),
                "scenario_name": str(meta.get("name") or meta.get("id") or "").strip(),
                "time": self._time_to_dict(game_time),
                "game_map": game_map,
            },
            artifacts=[str(source_path)],
            metrics={"unit_count": unit_count},
            logs=logs,
            adapter_method="load_snapshot",
        )

    def snapshot_smoke(self, scenario_name: str = "") -> TestingApiResult:
        saved = self.save_snapshot(scenario_name=scenario_name)
        if not saved.ok:
            return self._with_method(saved, "snapshot_smoke")

        snapshot_path = saved.artifacts[0]
        loaded = self.load_snapshot(snapshot_path)
        if not loaded.ok:
            return self._with_method(loaded, "snapshot_smoke")

        saved_id = str(saved.data.get("scenario_id") or "").strip()
        loaded_id = str(loaded.data.get("scenario_id") or "").strip()
        if saved_id and loaded_id and saved_id != loaded_id:
            return TestingApiResult(
                ok=False,
                error=f"Snapshot reload mismatch: expected {saved_id}, got {loaded_id}",
                artifacts=list(saved.artifacts),
                logs=list(saved.logs) + list(loaded.logs),
                adapter_method="snapshot_smoke",
            )

        unit_count = int(loaded.metrics.get("unit_count") or 0)
        if unit_count <= 0:
            return TestingApiResult(
                ok=False,
                error="Snapshot smoke restored zero units.",
                artifacts=list(saved.artifacts),
                logs=list(saved.logs) + list(loaded.logs),
                adapter_method="snapshot_smoke",
            )

        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": loaded_id or saved_id,
                "snapshot_path": snapshot_path,
            },
            artifacts=list(saved.artifacts),
            metrics={"unit_count": unit_count},
            logs=list(saved.logs) + list(loaded.logs) + ["Snapshot smoke passed."],
            adapter_method="snapshot_smoke",
        )

    def export_replay(self, path: str | Path | None = None, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "export_replay")

        scenario_id = str(loaded.data.get("scenario_id") or "").strip()
        api = EngineAPI()
        api.load_scenario(scenario_id)
        start_state = api.start_game()
        end_state = api.process_turn()
        payload = self._build_replay_payload(start_state, end_state, api.get_logs())

        replay_path = Path(path) if path is not None else self._replay_artifact_path(scenario_id or "replay")
        replay_path.parent.mkdir(parents=True, exist_ok=True)
        replay_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": scenario_id,
                "replay_path": str(replay_path),
            },
            artifacts=[str(replay_path)],
            metrics={
                "unit_count": len(payload.get("final_units") or []),
                "log_count": len(payload.get("logs") or []),
            },
            logs=list(loaded.logs) + [f"Replay exported: {replay_path}"],
            adapter_method="export_replay",
        )

    def compare_replay(
        self,
        path_a: str | Path,
        path_b: str | Path,
        output_path: str | Path | None = None,
    ) -> TestingApiResult:
        replay_a = Path(path_a)
        replay_b = Path(path_b)
        if not replay_a.exists() or not replay_b.exists():
            missing = replay_a if not replay_a.exists() else replay_b
            return TestingApiResult(
                ok=False,
                error=f"Replay file not found: {missing}",
                logs=[f"Replay file missing: {missing}"],
                adapter_method="compare_replay",
            )

        payload_a = json.loads(replay_a.read_text(encoding="utf-8"))
        payload_b = json.loads(replay_b.read_text(encoding="utf-8"))
        identical = payload_a == payload_b
        artifact_paths = [str(replay_a), str(replay_b)]
        logs = [
            f"Replay A: {replay_a}",
            f"Replay B: {replay_b}",
            f"Replay compare identical={identical}",
        ]
        data = {"identical": identical}
        if output_path is not None:
            compare_path = Path(output_path)
            compare_path.parent.mkdir(parents=True, exist_ok=True)
            compare_payload = {
                "replay_a": str(replay_a),
                "replay_b": str(replay_b),
                "identical": identical,
            }
            compare_path.write_text(json.dumps(compare_payload, indent=2), encoding="utf-8")
            artifact_paths.append(str(compare_path))
            data["compare_output_path"] = str(compare_path)
            logs.append(f"Replay compare output: {compare_path}")
        return TestingApiResult(
            ok=identical,
            data=data,
            error="" if identical else "Replay payloads differ.",
            artifacts=artifact_paths,
            logs=logs,
            adapter_method="compare_replay",
        )

    def replay_validation(self, scenario_name: str = "") -> TestingApiResult:
        first_path = self._replay_artifact_path(f"{self._slug(scenario_name or 'default')}-a")
        second_path = self._replay_artifact_path(f"{self._slug(scenario_name or 'default')}-b")
        compare_path = self._compare_artifact_path(self._slug(scenario_name or "default"))

        first = self.export_replay(first_path, scenario_name=scenario_name)
        if not first.ok:
            return self._with_method(first, "replay_validation")

        second = self.export_replay(second_path, scenario_name=scenario_name)
        if not second.ok:
            return self._with_method(second, "replay_validation")

        compared = self.compare_replay(first.artifacts[0], second.artifacts[0], compare_path)
        if not compared.ok:
            return TestingApiResult(
                ok=False,
                error=compared.error,
                artifacts=list(first.artifacts) + list(second.artifacts) + list(compared.artifacts[2:]),
                logs=list(first.logs) + list(second.logs) + list(compared.logs),
                adapter_method="replay_validation",
            )

        return TestingApiResult(
            ok=True,
            data={
                "scenario_name": scenario_name,
                "compare_output_path": str(compared.data.get("compare_output_path") or ""),
            },
            artifacts=list(first.artifacts) + list(second.artifacts) + list(compared.artifacts[2:]),
            metrics={"artifact_count": len(first.artifacts) + len(second.artifacts) + len(compared.artifacts[2:])},
            logs=list(first.logs) + list(second.logs) + list(compared.logs) + ["Replay validation passed."],
            adapter_method="replay_validation",
        )

    def run_all_green(self) -> TestingApiResult:
        command = self._all_green_command()
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return TestingApiResult(
                ok=False,
                error=str(exc),
                logs=[f"All-green command failed to start: {exc}"],
                adapter_method="run_all_green",
                executed_command=command,
            )

        logs = []
        for stream_name, payload in (("stdout", completed.stdout), ("stderr", completed.stderr)):
            for line in str(payload or "").splitlines():
                text = line.rstrip()
                if text:
                    logs.append(f"{stream_name}: {text}")

        return TestingApiResult(
            ok=completed.returncode == 0,
            data={"command": command},
            error="" if completed.returncode == 0 else f"All-green command exited with code {completed.returncode}.",
            logs=logs or ["All-green command completed."],
            adapter_method="run_all_green",
            executed_command=command,
            return_code=completed.returncode,
        )

    def _resolve_scenario_entry(self, requested: str = "") -> Dict[str, Any] | None:
        entries = self._sorted_catalog_entries(self._scenario_catalog())
        if not entries:
            return None

        requested_text = str(requested or "").strip()
        if not requested_text:
            for entry in entries:
                if entry.get("engine_loadable"):
                    return entry
            return entries[0]

        requested_lower = requested_text.lower()
        requested_json = requested_lower if requested_lower.endswith(".json") else f"{requested_lower}.json"
        for entry in entries:
            candidate_file = str(entry.get("file_name") or "").strip().lower()
            candidate_stem = candidate_file[:-5] if candidate_file.endswith(".json") else candidate_file
            scenario_id = str(entry.get("scenario_id") or "").strip().lower()
            if requested_lower in {candidate_file, candidate_stem, scenario_id, requested_json}:
                return entry
        return None

    def _snapshot_artifact_path(self, stem: str) -> Path:
        return self.artifact_root() / "snapshots" / f"{self._timestamp()}-{self._slug(stem)}.json"

    def _replay_artifact_path(self, stem: str) -> Path:
        return self.artifact_root() / "replays" / f"{self._timestamp()}-{self._slug(stem)}.json"

    def _compare_artifact_path(self, stem: str) -> Path:
        return self.artifact_root() / "compares" / f"{self._timestamp()}-{self._slug(stem)}.json"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip()).strip("-") or "artifact"

    def _time_to_dict(self, value: Any) -> Dict[str, Any]:
        return {
            "day": int(getattr(value, "day", 0) or 0),
            "phase": str(getattr(value, "phase", "") or ""),
        }

    def _build_replay_payload(self, start_state: Dict[str, Any], end_state: Dict[str, Any], logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "initial_game": dict(start_state.get("game") or {}),
            "final_game": dict(end_state.get("game") or {}),
            "initial_units": self._simplify_units(start_state.get("units") or []),
            "final_units": self._simplify_units(end_state.get("units") or []),
            "logs": list(logs or []),
        }

    def _simplify_units(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for unit in units:
            if not isinstance(unit, dict):
                continue
            rows.append(
                {
                    "id": unit.get("id") or unit.get("unit_id"),
                    "location_id": unit.get("location_id"),
                    "strength": unit.get("strength"),
                    "supply": unit.get("supply"),
                    "readiness": unit.get("readiness"),
                }
            )
        rows.sort(key=lambda row: str(row.get("id") or ""))
        return rows

    def _serialize_units(self, api: EngineAPI) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        units = getattr(api, "units", None)
        all_units = units.all_units() if units is not None else []
        for unit in all_units:
            rows.append(
                {
                    "id": getattr(unit, "id", ""),
                    "location_id": getattr(unit, "location_id", ""),
                    "strength": getattr(unit, "strength", 0),
                    "fatigue": getattr(unit, "fatigue", 0),
                    "morale": getattr(unit, "morale", 0),
                    "supply": getattr(unit, "supply", 0),
                    "readiness": getattr(unit, "readiness", 0),
                    "hq_unit_id": getattr(unit, "hq_unit_id", None),
                }
            )
        rows.sort(key=lambda row: str(row.get("id") or ""))
        return rows

    def _snapshot_payload(self, api: EngineAPI) -> Dict[str, Any]:
        meta = dict(getattr(api, "meta", None) or {})
        scenario_id = str(meta.get("id") or "").strip()
        return {
            "scenario_id": scenario_id,
            "time": self._time_to_dict(getattr(api, "time", None)),
            "units": self._serialize_units(api),
            "meta": meta,
        }

    def _write_snapshot_file(self, path: Path, api: EngineAPI) -> None:
        path.write_text(json.dumps(self._snapshot_payload(api), indent=2), encoding="utf-8")

    def _read_snapshot_file(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _restore_snapshot_state(self, api: EngineAPI, snapshot_data: Dict[str, Any]) -> None:
        time_data = dict(snapshot_data.get("time") or {})
        if getattr(api, "time", None) is not None:
            if "day" in time_data:
                api.time.day = int(time_data.get("day") or getattr(api.time, "day", 0) or 0)
            if "phase" in time_data:
                api.time.phase = str(time_data.get("phase") or getattr(api.time, "phase", "") or "")

        units = getattr(api, "units", None)
        if units is None:
            return
        saved_units = {
            str(row.get("id") or "").strip(): row
            for row in list(snapshot_data.get("units") or [])
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        for unit_id, row in saved_units.items():
            unit = self._find_unit(units, unit_id)
            if unit is None:
                continue
            for field_name in ("location_id", "strength", "fatigue", "morale", "supply", "readiness", "hq_unit_id"):
                if field_name in row:
                    setattr(unit, field_name, row.get(field_name))

    def _find_unit(self, units: Any, unit_id: str) -> Any:
        if hasattr(units, "get") and callable(getattr(units, "get")):
            unit = units.get(unit_id)
            if unit is not None:
                return unit
        if hasattr(units, "all_units") and callable(getattr(units, "all_units")):
            for unit in units.all_units():
                if str(getattr(unit, "id", "") or "") == unit_id:
                    return unit
        return None

    def _all_green_command(self) -> List[str]:
        return [
            "pytest",
            "-q",
            str(self.repo_root / "tests" / "engine" / "test_testing_api.py"),
            str(self.repo_root / "tests" / "engine" / "test_round1_support.py"),
            str(self.repo_root / "tests" / "orl"),
            str(self.repo_root / "tests" / "operations_console"),
            str(self.repo_root / "tests" / "test_engine_api_bai_hook.py"),
            str(self.repo_root / "tests" / "test_bai_first_playable.py"),
            str(self.repo_root / "tests" / "test_engine_bai_controller.py"),
            str(self.repo_root / "tests" / "test_engine_bai_operational.py"),
            str(self.repo_root / "tests" / "test_bridge_live_path.py"),
            str(self.repo_root / "tests" / "test_inchon_scenario_stub.py"),
        ]

    def _scenario_payload_for_loaded(self, loaded: TestingApiResult) -> Dict[str, Any] | None:
        scenario_id = str(loaded.data.get("scenario_id") or "").strip()
        scenario_name = str(loaded.data.get("scenario_name") or "").strip()
        entry = self._resolve_scenario_entry(scenario_id or scenario_name)
        if entry is None:
            return None
        return self._read_scenario_payload(entry)

    def _scenario_catalog(self) -> Dict[str, Dict[str, Any]]:
        catalog: Dict[str, Dict[str, Any]] = {}
        for file_name in store_list_scenarios():
            scenario_id = str(file_name or "").strip()
            if scenario_id.endswith(".json"):
                scenario_id = scenario_id[:-5]
            entry = catalog.setdefault(
                scenario_id,
                {
                    "scenario_id": scenario_id,
                    "file_name": f"{scenario_id}.json",
                    "bridge_listed": False,
                    "engine_loadable": False,
                    "payload_paths": [],
                },
            )
            entry["bridge_listed"] = True
            entry["file_name"] = str(file_name or entry["file_name"]).strip()
            bridge_path = self.repo_root / "scenarios" / entry["file_name"]
            if bridge_path.exists():
                entry["payload_paths"].append(str(bridge_path))

        for source_dir in (
            self.repo_root / "server" / "rules" / "scenarios",
            self.repo_root / "server" / "scenarios",
        ):
            if not source_dir.exists():
                continue
            for path in sorted(source_dir.glob("*.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    payload = {}
                scenario_id = str(payload.get("id") or path.stem).strip()
                entry = catalog.setdefault(
                    scenario_id,
                    {
                        "scenario_id": scenario_id,
                        "file_name": f"{scenario_id}.json",
                        "bridge_listed": False,
                        "engine_loadable": False,
                        "payload_paths": [],
                    },
                )
                entry["engine_loadable"] = True
                entry["file_name"] = str(path.name or entry["file_name"]).strip()
                if str(path) not in entry["payload_paths"]:
                    entry["payload_paths"].append(str(path))

        return catalog

    def _sorted_catalog_entries(self, catalog: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            catalog.values(),
            key=lambda entry: (
                0 if entry.get("engine_loadable") else 1,
                0 if entry.get("bridge_listed") else 1,
                str(entry.get("scenario_id") or ""),
            ),
        )

    def _primary_scenario_ids(self) -> List[str]:
        try:
            manifest = load_round1_manifest(self.repo_root / "tools" / "orl" / "round1_manifest.yaml")
        except Exception:
            return []
        return [scenario.scenario_id for scenario in manifest.primary_scenarios]

    def _read_scenario_payload(self, entry: Dict[str, Any]) -> Dict[str, Any] | None:
        file_name = str(entry.get("file_name") or "").strip()
        if file_name:
            payload = read_scenario(file_name)
            if isinstance(payload, dict):
                return payload
        for raw_path in list(entry.get("payload_paths") or []):
            path = Path(str(raw_path))
            if not path.exists() or not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        return None

    def _run_pytest_check(
        self,
        *,
        check_id: str,
        label: str,
        blocker_class: str,
        pytest_args: List[str],
    ) -> Dict[str, Any]:
        command = ["pytest", "-q", *pytest_args]
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return {
                "check_id": check_id,
                "label": label,
                "blocker_class": blocker_class,
                "status": "error",
                "summary": str(exc),
                "artifacts": [],
                "logs": [f"command failed to start: {exc}"],
                "executed_command": command,
            }

        logs: List[str] = []
        for stream_name, payload in (("stdout", completed.stdout), ("stderr", completed.stderr)):
            for line in str(payload or "").splitlines():
                text = line.rstrip()
                if text:
                    logs.append(f"{stream_name}: {text}")
        return {
            "check_id": check_id,
            "label": label,
            "blocker_class": blocker_class,
            "status": "pass" if completed.returncode == 0 else "fail",
            "summary": f"{label} passed." if completed.returncode == 0 else f"{label} failed.",
            "artifacts": [],
            "logs": logs or [f"return code: {completed.returncode}"],
            "executed_command": command,
        }

    def _check_from_result(
        self,
        result: TestingApiResult,
        *,
        check_id: str,
        label: str,
        blocker_class: str,
    ) -> Dict[str, Any]:
        return {
            "check_id": check_id,
            "label": label,
            "blocker_class": blocker_class,
            "status": "pass" if result.ok else "fail",
            "summary": f"{label} passed." if result.ok else (result.error or f"{label} failed."),
            "artifacts": list(result.artifacts),
            "logs": list(result.logs),
            "executed_command": list(result.executed_command),
        }

    def _campaign_status_logs(self, data: Dict[str, Any]) -> List[str]:
        return [
            (
                "CAMPAIGN STATUS: "
                f"scenario={data.get('display_name') or data.get('scenario_id') or '<unknown>'} | "
                f"objective={data.get('objective') or '<unknown>'} | "
                f"front={data.get('front_status') or '<unknown>'} | "
                f"supply={data.get('supply_status') or '<unknown>'} | "
                f"main={data.get('main_effort') or '<unknown>'}"
            ),
            (
                "CAMPAIGN STATUS DETAIL: "
                f"turn={data.get('turn') or '<unknown>'} | "
                f"units={int(data.get('unit_count') or 0)} | "
                f"objectives={int(data.get('objective_count') or 0)} | "
                f"alerts={int(data.get('alert_count') or 0)}"
            ),
        ]

    def _campaign_explain_logs(self, data: Dict[str, Any]) -> List[str]:
        logs = []
        description = str(data.get("description") or "").strip()
        staff_notes = str(data.get("staff_notes") or "").strip()
        alerts = self._join_items(data.get("alerts"), limit=2)
        orders = self._join_items(data.get("orders"), limit=2)
        objectives = self._join_items(data.get("objectives"), limit=3)

        if description:
            logs.append(f"CAMPAIGN EXPLAIN: {description}")
        if staff_notes:
            logs.append(f"CAMPAIGN NOTES: {staff_notes}")
        if objectives:
            logs.append(f"CAMPAIGN OBJECTIVES: {objectives}")
        if alerts:
            logs.append(f"CAMPAIGN ALERTS: {alerts}")
        if orders:
            logs.append(f"CAMPAIGN ORDERS: {orders}")
        return logs

    def _join_items(self, value: Any, *, limit: int) -> str:
        items = [
            str(item or "").strip()
            for item in list(value or [])
            if str(item or "").strip()
        ]
        if not items:
            return ""
        visible = items[:limit]
        suffix = f" (+{len(items) - limit} more)" if len(items) > limit else ""
        return "; ".join(visible) + suffix

    def _with_method(self, result: TestingApiResult, method: str) -> TestingApiResult:
        return TestingApiResult(
            ok=result.ok,
            data=dict(result.data),
            error=result.error,
            artifacts=list(result.artifacts),
            metrics=dict(result.metrics),
            logs=list(result.logs),
            adapter_method=method,
            executed_command=list(result.executed_command),
            return_code=result.return_code,
        )
