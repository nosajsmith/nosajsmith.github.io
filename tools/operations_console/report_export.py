from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .baselines import BaselineComparison, compare_result_to_baseline
from .divergence_finder import (
    FirstDivergence,
    compare_result_to_baseline_divergence,
    find_first_divergence_in_artifact_paths,
)
from .gui_action_matrix import GuiActionMatrix, GuiActionMatrixEntry, load_gui_action_matrix
from .models import ConsoleResult
from .run_manifest import parse_run_manifest_metadata
from .runner_utils import iter_results
from .scenario_contracts import ScenarioContractCatalog, ScenarioContractEvaluation, evaluate_result_contract, load_scenario_contracts


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_export_dir() -> Path:
    return repo_root() / "artifacts" / "operations_console"


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "run"


def report_dict(
    result: ConsoleResult,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
) -> Dict[str, object]:
    matrix = action_matrix if action_matrix is not None else _safe_load_action_matrix()
    matrix_entry = _report_matrix_entry(matrix, result.name)
    contract_evaluation = _report_contract_evaluation(result, matrix, scenario_contracts)
    baseline_drift = _report_baseline_drift(result, matrix, scenario_contracts, baseline_dir_path)
    first_divergence = _report_first_divergence(result, baseline_drift, baseline_dir_path)
    explainability_summary = _extract_explainability_summary(result.details)
    expansion_registry = _extract_expansion_registry_summary(result.details)
    incident_metadata = _extract_incident_metadata(result.details)
    run_manifest = _report_run_manifest(result)
    key_logs = _key_log_lines(result)
    return {
        "name": result.name,
        "status": result.status,
        "original_status": result.original_status,
        "summary": result.summary,
        "scenario_name": result.scenario_name,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "duration_ms": result.duration_ms,
        "details": list(result.details),
        "errors": list(result.errors),
        "artifact_paths": list(result.artifact_paths),
        "key_logs": key_logs,
        "adapter_method": result.adapter_method,
        "executed_command": list(result.executed_command),
        "return_code": result.return_code,
        "known_issue_matches": [
            _known_issue_report_dict(result, match)
            for match in result.known_issue_matches
        ],
        "gui_action_matrix": matrix_entry.to_report_dict() if matrix_entry is not None else None,
        "scenario_contract_evaluation": _contract_report_dict(contract_evaluation),
        "baseline_drift": _baseline_report_dict(baseline_drift),
        "first_divergence": _first_divergence_report_dict(first_divergence),
        "explainability_summary": explainability_summary,
        "expansion_registry": expansion_registry,
        "incident_metadata": incident_metadata,
        "run_manifest": run_manifest,
        "subresults": [report_dict(item, matrix, scenario_contracts, baseline_dir_path) for item in result.subresults],
    }


def write_report_json(
    result: ConsoleResult,
    path: Path,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report_dict(result, action_matrix, scenario_contracts, baseline_dir_path), indent=2),
        encoding="utf-8",
    )
    return target


def _timestamp_for_filename(result: ConsoleResult) -> str:
    source = result.finished_at or result.started_at
    if source:
        text = re.sub(r"[^0-9]", "", source)
        if text:
            return text[:14] or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def export_result_json(
    result: ConsoleResult,
    export_dir: Path | None = None,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
) -> Path:
    target_dir = Path(export_dir) if export_dir is not None else default_export_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_timestamp_for_filename(result)}-{slugify(result.name)}.json"
    return write_report_json(
        result,
        path,
        action_matrix=action_matrix,
        scenario_contracts=scenario_contracts,
        baseline_dir_path=baseline_dir_path,
    )


def _format_text_lines(
    result: ConsoleResult,
    depth: int = 0,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
) -> List[str]:
    prefix = "  " * depth
    matrix = action_matrix if action_matrix is not None else _safe_load_action_matrix()
    matrix_entry = _report_matrix_entry(matrix, result.name)
    contract_evaluation = _report_contract_evaluation(result, matrix, scenario_contracts)
    baseline_drift = _report_baseline_drift(result, matrix, scenario_contracts, baseline_dir_path)
    first_divergence = _report_first_divergence(result, baseline_drift, baseline_dir_path)
    explainability_summary = _extract_explainability_summary(result.details)
    expansion_registry = _extract_expansion_registry_summary(result.details)
    incident_metadata = _extract_incident_metadata(result.details)
    run_manifest = _report_run_manifest(result)
    key_logs = _key_log_lines(result)
    lines = [
        f"{prefix}Name: {result.name}",
        f"{prefix}Status: {result.status.upper()}",
        f"{prefix}Summary: {result.summary}",
    ]
    if result.original_status and result.original_status != result.status:
        lines.append(f"{prefix}Original Status: {result.original_status.upper()}")
    if result.scenario_name:
        lines.append(f"{prefix}Scenario: {result.scenario_name}")
    if result.started_at:
        lines.append(f"{prefix}Started: {result.started_at}")
    if result.finished_at:
        lines.append(f"{prefix}Finished: {result.finished_at}")
    if result.duration_ms:
        lines.append(f"{prefix}Duration (ms): {result.duration_ms}")
    if matrix_entry is not None:
        lines.append(f"{prefix}GUI Action Id: {matrix_entry.action_id}")
        lines.append(f"{prefix}Automation Level: {matrix_entry.automation_level}")
        lines.append(f"{prefix}Expected Status: {matrix_entry.expected_status.upper()}")
        if matrix_entry.expected_log_fragments:
            lines.append(f"{prefix}Expected Logs: {', '.join(matrix_entry.expected_log_fragments)}")
        if matrix_entry.artifact_types:
            lines.append(f"{prefix}Expected Artifacts: {', '.join(matrix_entry.artifact_types)}")
        if not matrix_entry.enabled:
            lines.append(f"{prefix}Matrix Enabled: NO")
    if contract_evaluation is not None and contract_evaluation.matched:
        lines.append(f"{prefix}Scenario Contract: {contract_evaluation.contract_scenario_name}")
        lines.append(f"{prefix}Contract Status: {contract_evaluation.status.upper()}")
        if contract_evaluation.payload_path:
            lines.append(f"{prefix}Contract Payload: {contract_evaluation.payload_path}")
        if contract_evaluation.expected_artifacts:
            lines.append(f"{prefix}Contract Expected Artifacts: {', '.join(contract_evaluation.expected_artifacts)}")
        if contract_evaluation.known_issues:
            lines.append(f"{prefix}Contract Known Issues: {', '.join(contract_evaluation.known_issues)}")
        if contract_evaluation.notes:
            lines.append(f"{prefix}Contract Notes: {contract_evaluation.notes}")
        if contract_evaluation.passed_checks:
            lines.append(f"{prefix}Contract Checks:")
            lines.extend(f"{prefix}- {check}" for check in contract_evaluation.passed_checks)
        if contract_evaluation.issues:
            lines.append(f"{prefix}Contract Issues:")
            lines.extend(f"{prefix}- {issue}" for issue in contract_evaluation.issues)
    if baseline_drift is not None:
        drift_label = baseline_drift.status.upper() if baseline_drift.matched else "NOT FOUND"
        lines.append(f"{prefix}Baseline Drift: {drift_label}")
        if baseline_drift.baseline_path:
            lines.append(f"{prefix}Baseline Path: {baseline_drift.baseline_path}")
        if baseline_drift.saved_at:
            lines.append(f"{prefix}Baseline Saved At: {baseline_drift.saved_at}")
        if baseline_drift.findings:
            lines.append(f"{prefix}Baseline Findings:")
            lines.extend(f"{prefix}- {item.status.upper()}: {item.message}" for item in baseline_drift.findings)
    if first_divergence is not None and first_divergence.comparable and not first_divergence.identical:
        lines.append(f"{prefix}First Divergence: {first_divergence.message}")
        if first_divergence.field_path:
            lines.append(f"{prefix}First Divergence Field: {first_divergence.field_path}")
        if first_divergence.step:
            lines.append(f"{prefix}First Divergence Step: {first_divergence.step}")
        if first_divergence.tick is not None:
            lines.append(f"{prefix}First Divergence Tick: {first_divergence.tick}")
        if first_divergence.phase:
            lines.append(f"{prefix}First Divergence Phase: {first_divergence.phase}")
        left_label, right_label = _divergence_value_labels(first_divergence)
        lines.append(f"{prefix}{left_label}: {_format_divergence_value(first_divergence.left_value)}")
        lines.append(f"{prefix}{right_label}: {_format_divergence_value(first_divergence.right_value)}")
        if first_divergence.artifact_paths:
            lines.append(f"{prefix}First Divergence Inputs: {' | '.join(first_divergence.artifact_paths)}")
    if explainability_summary is not None:
        lines.append(f"{prefix}Explainability:")
        for label, value in _format_explainability_lines(explainability_summary):
            lines.append(f"{prefix}- {label}: {value}")
    if expansion_registry is not None:
        lines.append(f"{prefix}Expansion Registry:")
        if expansion_registry.get("json_path"):
            lines.append(f"{prefix}- JSON: {expansion_registry['json_path']}")
        counts = expansion_registry.get("counts")
        if isinstance(counts, dict):
            lines.append(
                f"{prefix}- Counts: total={counts.get('total', 0)}, "
                f"support_ready={counts.get('support_ready', 0)}, "
                f"blocked_by_support={counts.get('blocked_by_support', 0)}, "
                f"needs_foundation={counts.get('needs_foundation', 0)}"
            )
        status_counts = expansion_registry.get("status_counts")
        if isinstance(status_counts, dict) and status_counts:
            lines.append(f"{prefix}- Status Counts: {_format_mapping_segments(status_counts)}")
        category_counts = expansion_registry.get("category_counts")
        if isinstance(category_counts, dict) and category_counts:
            lines.append(f"{prefix}- Category Counts: {_format_mapping_segments(category_counts)}")
    if incident_metadata is not None:
        lines.append(f"{prefix}Incident Logged: {'YES' if incident_metadata.get('logged') else 'NO'}")
        if incident_metadata.get("bundle_dir"):
            lines.append(f"{prefix}Incident Bundle: {incident_metadata['bundle_dir']}")
        if incident_metadata.get("incident_json_path"):
            lines.append(f"{prefix}Incident Manifest: {incident_metadata['incident_json_path']}")
        if incident_metadata.get("run_report_json_path"):
            lines.append(f"{prefix}Incident Run Report: {incident_metadata['run_report_json_path']}")
        anomaly_matches = list(incident_metadata.get("anomaly_matches") or [])
        if anomaly_matches:
            lines.append(f"{prefix}Incident Anomalies:")
            for match in anomaly_matches:
                anomaly_line = f"{prefix}- {match.get('id', '').strip()}: {match.get('title', '').strip()}".rstrip(": ")
                lines.append(anomaly_line)
    if run_manifest is not None:
        if run_manifest.get("path"):
            lines.append(f"{prefix}Run Manifest: {run_manifest['path']}")
        if run_manifest.get("branch"):
            lines.append(f"{prefix}Run Branch: {run_manifest['branch']}")
        if run_manifest.get("commit"):
            lines.append(f"{prefix}Run Commit: {run_manifest['commit']}")
        if run_manifest.get("worktree_status"):
            lines.append(f"{prefix}Run Worktree: {run_manifest['worktree_status']}")
        if run_manifest.get("working_directory"):
            lines.append(f"{prefix}Run Working Directory: {run_manifest['working_directory']}")
        if run_manifest.get("duration_ms"):
            lines.append(f"{prefix}Run Manifest Duration (ms): {run_manifest['duration_ms']}")
        if run_manifest.get("bridge_uri"):
            lines.append(f"{prefix}Run Bridge URI: {run_manifest['bridge_uri']}")
    if result.artifact_paths:
        lines.append(f"{prefix}Artifacts:")
        lines.extend(f"{prefix}- {path}" for path in result.artifact_paths)
    if result.adapter_method:
        lines.append(f"{prefix}Adapter Method: {result.adapter_method}")
    if result.executed_command:
        lines.append(f"{prefix}Executed Command: {' '.join(result.executed_command)}")
    if result.return_code is not None:
        lines.append(f"{prefix}Return Code: {result.return_code}")
    if result.known_issue_matches:
        lines.append(f"{prefix}Known Issues:")
        if result.scenario_name:
            lines.append(f"{prefix}Known Issue Scenario: {result.scenario_name}")
        for match in result.known_issue_matches:
            line = f"{prefix}- {match.issue_id}: {match.title} [severity={match.severity}, status={match.status}]"
            if match.expected_status_override:
                line = f"{line} -> {match.expected_status_override.upper()}"
                if (
                    result.original_status
                    and result.original_status != result.status
                    and str(match.expected_status_override).strip().lower() == str(result.status or "").strip().lower()
                ):
                    line = f"{line} (downgrade applied)"
            lines.append(line)
            if match.notes:
                lines.append(f"{prefix}- Notes: {match.notes}")
    if key_logs:
        lines.append(f"{prefix}Key Logs:")
        lines.extend(f"{prefix}- {line}" for line in key_logs)
    if result.errors:
        lines.append(f"{prefix}Errors:")
        lines.extend(f"{prefix}- {error}" for error in result.errors)
    if result.details:
        lines.append(f"{prefix}Details:")
        lines.extend(f"{prefix}- {line}" for line in result.details)
    if result.subresults:
        lines.append(f"{prefix}Subresults:")
        for item in result.subresults:
            lines.extend(_format_text_lines(item, depth + 1, matrix, scenario_contracts, baseline_dir_path))
    return lines


def _safe_load_action_matrix() -> GuiActionMatrix | None:
    try:
        return load_gui_action_matrix()
    except Exception:
        return None


def _safe_load_scenario_contracts() -> ScenarioContractCatalog | None:
    try:
        return load_scenario_contracts()
    except Exception:
        return None


def _report_matrix_entry(action_matrix: GuiActionMatrix | None, label: str) -> GuiActionMatrixEntry | None:
    if action_matrix is None:
        return None
    return action_matrix.get_by_label(label)


def _report_contract_evaluation(
    result: ConsoleResult,
    action_matrix: GuiActionMatrix | None,
    scenario_contracts: ScenarioContractCatalog | None,
) -> ScenarioContractEvaluation | None:
    contracts = scenario_contracts if scenario_contracts is not None else _safe_load_scenario_contracts()
    return evaluate_result_contract(
        result,
        action_matrix=action_matrix,
        contract_catalog=contracts,
    )


def _contract_report_dict(evaluation: ScenarioContractEvaluation | None) -> Dict[str, object] | None:
    if evaluation is None:
        return None
    return {
        "matched": evaluation.matched,
        "scenario_name": evaluation.scenario_name,
        "contract_scenario_name": evaluation.contract_scenario_name,
        "status": evaluation.status,
        "issues": list(evaluation.issues),
        "passed_checks": list(evaluation.passed_checks),
        "known_issues": list(evaluation.known_issues),
        "expected_artifacts": list(evaluation.expected_artifacts),
        "notes": evaluation.notes,
        "payload_path": evaluation.payload_path,
    }


def _report_baseline_drift(
    result: ConsoleResult,
    action_matrix: GuiActionMatrix | None,
    scenario_contracts: ScenarioContractCatalog | None,
    baseline_dir_path: Path | None,
) -> BaselineComparison | None:
    try:
        return compare_result_to_baseline(
            result,
            action_matrix=action_matrix,
            scenario_contracts=scenario_contracts,
            baseline_dir_path=baseline_dir_path,
        )
    except Exception:
        return None


def _baseline_report_dict(comparison: BaselineComparison | None) -> Dict[str, object] | None:
    if comparison is None:
        return None
    return {
        "matched": comparison.matched,
        "baseline_key": comparison.baseline_key,
        "status": comparison.status,
        "baseline_path": comparison.baseline_path,
        "saved_at": comparison.saved_at,
        "findings": [
            {
                "metric": item.metric,
                "status": item.status,
                "message": item.message,
                "baseline_value": item.baseline_value,
                "current_value": item.current_value,
            }
            for item in comparison.findings
        ],
        "baseline_metrics": dict(comparison.baseline_metrics),
        "current_metrics": dict(comparison.current_metrics),
    }


def _report_first_divergence(
    result: ConsoleResult,
    baseline_drift: BaselineComparison | None,
    baseline_dir_path: Path | None,
) -> FirstDivergence | None:
    try:
        if len(result.artifact_paths) >= 2:
            divergence = find_first_divergence_in_artifact_paths(result.artifact_paths)
            if divergence is not None and divergence.comparable and not divergence.identical:
                return divergence
        if baseline_drift is not None and baseline_drift.matched and baseline_drift.status != "pass":
            divergence = compare_result_to_baseline_divergence(result, baseline_dir_path=baseline_dir_path)
            if divergence.comparable and not divergence.identical:
                return divergence
    except Exception:
        return None
    return None


def _first_divergence_report_dict(divergence: FirstDivergence | None) -> Dict[str, object] | None:
    if divergence is None:
        return None
    return divergence.to_report_dict()


def _key_log_lines(result: ConsoleResult) -> List[str]:
    priority_lines = [str(item or "").strip() for item in result.errors if str(item or "").strip()]
    detail_lines = [str(item or "").strip() for item in result.details if str(item or "").strip()]
    nested_lines: List[str] = []
    for item in list(iter_results(result))[1:]:
        nested_lines.extend(str(error or "").strip() for error in item.errors if str(error or "").strip())
        nested_lines.extend(str(line or "").strip() for line in item.details if str(line or "").strip())
    combined = [*priority_lines, *detail_lines[-20:], *nested_lines[-20:]]
    deduped: List[str] = []
    for line in combined:
        if line not in deduped:
            deduped.append(line)
    return deduped[:20]


def _known_issue_report_dict(result: ConsoleResult, match) -> Dict[str, object]:
    downgrade_applied = bool(
        match.expected_status_override
        and result.original_status
        and result.original_status != result.status
        and str(match.expected_status_override).strip().lower() == str(result.status or "").strip().lower()
    )
    return {
        "id": match.issue_id,
        "title": match.title,
        "severity": match.severity,
        "category": match.category,
        "status": match.status,
        "waived": str(match.status or "").strip().lower() == "waived",
        "downgrade_applied": downgrade_applied,
        "expected_status_override": match.expected_status_override,
        "downgraded_to": result.status if downgrade_applied else "",
        "scenario_name": result.scenario_name,
        "result_name": result.name,
        "notes": match.notes,
    }


def _extract_explainability_summary(details: List[str]) -> Dict[str, object] | None:
    summary: Dict[str, object] = {}
    for line in list(details or []):
        text = str(line or "").strip()
        if not text:
            continue
        if text.startswith("CAMPAIGN STATUS: "):
            summary.update(_parse_key_value_segments(text.partition(": ")[2]))
        elif text.startswith("CAMPAIGN STATUS DETAIL: "):
            summary.update(_parse_key_value_segments(text.partition(": ")[2]))
        elif text.startswith("CAMPAIGN EXPLAIN: "):
            summary["description"] = text.partition(": ")[2].strip()
        elif text.startswith("CAMPAIGN NOTES: "):
            summary["staff_notes"] = text.partition(": ")[2].strip()
        elif text.startswith("CAMPAIGN ALERTS: "):
            summary["alerts_text"] = text.partition(": ")[2].strip()
            summary["alerts"] = _split_semicolon_items(summary["alerts_text"])
        elif text.startswith("CAMPAIGN ORDERS: "):
            summary["orders_text"] = text.partition(": ")[2].strip()
            summary["orders"] = _split_semicolon_items(summary["orders_text"])
        elif text.startswith("CAMPAIGN OBJECTIVES: "):
            summary["objectives_text"] = text.partition(": ")[2].strip()
            summary["objectives_list"] = _split_semicolon_items(summary["objectives_text"])
        elif text == "explainability attached to incident/report":
            summary["attached_to"] = "incident/report"
    return summary or None


def _extract_incident_metadata(details: List[str]) -> Dict[str, object] | None:
    metadata: Dict[str, object] = {
        "logged": False,
        "bundle_dir": "",
        "incident_json_path": "",
        "run_report_json_path": "",
        "anomaly_matches": [],
    }
    anomaly_matches: List[Dict[str, str]] = []
    for line in list(details or []):
        text = str(line or "").strip()
        if not text:
            continue
        if text.startswith("INCIDENT BUNDLE: "):
            metadata["bundle_dir"] = text.partition(": ")[2].strip()
            metadata["logged"] = True
        elif text.startswith("INCIDENT MANIFEST: "):
            metadata["incident_json_path"] = text.partition(": ")[2].strip()
            metadata["logged"] = True
        elif text.startswith("INCIDENT RUN REPORT: "):
            metadata["run_report_json_path"] = text.partition(": ")[2].strip()
            metadata["logged"] = True
        elif text.startswith("INCIDENT ANOMALIES: "):
            payload = text.partition(": ")[2].strip()
            for segment in payload.split(";"):
                item = segment.strip()
                if not item:
                    continue
                issue_id, separator, title = item.partition("|")
                anomaly_matches.append(
                    {
                        "id": issue_id.strip(),
                        "title": title.strip() if separator else "",
                    }
                )
    if anomaly_matches:
        metadata["anomaly_matches"] = anomaly_matches
    if not metadata["logged"] and not anomaly_matches:
        return None
    return metadata


def _extract_expansion_registry_summary(details: List[str]) -> Dict[str, object] | None:
    metadata: Dict[str, object] = {
        "json_path": "",
        "counts": {},
        "status_counts": {},
        "category_counts": {},
    }
    for line in list(details or []):
        text = str(line or "").strip()
        if not text:
            continue
        if text.startswith("EXPANSION REGISTRY JSON: "):
            metadata["json_path"] = text.partition(": ")[2].strip()
        elif text.startswith("EXPANSION REGISTRY COUNTS: "):
            metadata["counts"] = _parse_count_segments(text.partition(": ")[2].strip())
        elif text.startswith("EXPANSION REGISTRY STATUS COUNTS: "):
            metadata["status_counts"] = _parse_count_segments(text.partition(": ")[2].strip())
        elif text.startswith("EXPANSION REGISTRY CATEGORY COUNTS: "):
            metadata["category_counts"] = _parse_count_segments(text.partition(": ")[2].strip())
    if not metadata["json_path"] and not metadata["counts"] and not metadata["status_counts"] and not metadata["category_counts"]:
        return None
    return metadata


def _report_run_manifest(result: ConsoleResult) -> Dict[str, object] | None:
    metadata = parse_run_manifest_metadata(result.details)
    if metadata is None:
        return None
    return {
        "path": metadata.get("path", ""),
        "branch": metadata.get("branch", ""),
        "commit": metadata.get("commit", ""),
        "worktree_status": metadata.get("worktree_status", ""),
        "working_directory": metadata.get("working_directory", ""),
        "duration_ms": metadata.get("duration_ms", 0),
        "bridge_uri": metadata.get("bridge_uri", ""),
        "name": result.name,
        "scenario_name": result.scenario_name,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def _parse_key_value_segments(payload: str) -> Dict[str, object]:
    values: Dict[str, object] = {}
    key_map = {
        "scenario": "scenario",
        "objective": "objective",
        "front": "front_status",
        "supply": "supply_status",
        "main": "main_effort",
        "turn": "turn",
        "units": "unit_count",
        "objectives": "objective_count",
        "alerts": "alert_count",
    }
    for segment in str(payload or "").split("|"):
        key, separator, value = segment.partition("=")
        if not separator:
            continue
        normalized_key = key_map.get(key.strip().lower())
        if not normalized_key:
            continue
        text = value.strip()
        values[normalized_key] = int(text) if text.isdigit() else text
    return values


def _split_semicolon_items(value: str) -> List[str]:
    items = [item.strip() for item in str(value or "").split(";") if item.strip()]
    return items


def _parse_count_segments(payload: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for segment in str(payload or "").split("|"):
        key, separator, value = segment.partition("=")
        if not separator:
            continue
        key_text = key.strip()
        value_text = value.strip()
        if not key_text or not value_text.isdigit():
            continue
        values[key_text] = int(value_text)
    return values


def _format_explainability_lines(summary: Dict[str, object]) -> List[tuple[str, str]]:
    rows: List[tuple[str, str]] = []
    ordered_fields = [
        ("Attached", "attached_to"),
        ("Scenario", "scenario"),
        ("Objective", "objective"),
        ("Front Status", "front_status"),
        ("Supply Status", "supply_status"),
        ("Main Effort", "main_effort"),
        ("Turn", "turn"),
        ("Unit Count", "unit_count"),
        ("Objective Count", "objective_count"),
        ("Alert Count", "alert_count"),
        ("Description", "description"),
        ("Staff Notes", "staff_notes"),
        ("Objectives", "objectives_text"),
        ("Alerts", "alerts_text"),
        ("Orders", "orders_text"),
    ]
    for label, key in ordered_fields:
        value = summary.get(key)
        if value in {None, ""}:
            continue
        rows.append((label, str(value)))
    return rows


def _format_mapping_segments(values: Dict[str, object]) -> str:
    segments = [
        f"{key}={values[key]}"
        for key in values
    ]
    return ", ".join(segments)


def _divergence_value_labels(divergence: FirstDivergence) -> tuple[str, str]:
    if divergence.comparison_kind == "baseline_metrics":
        return ("Baseline", "Current")
    return ("Left", "Right")


def _format_divergence_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return str(value)
    if isinstance(value, list):
        return "[...]"
    if isinstance(value, dict):
        return "{...}"
    return str(value)


def export_result_text(
    result: ConsoleResult,
    export_dir: Path | None = None,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
) -> Path:
    target_dir = Path(export_dir) if export_dir is not None else default_export_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_timestamp_for_filename(result)}-{slugify(result.name)}.txt"
    path.write_text(
        "\n".join(
            _format_text_lines(
                result,
                action_matrix=action_matrix if action_matrix is not None else _safe_load_action_matrix(),
                scenario_contracts=scenario_contracts if scenario_contracts is not None else _safe_load_scenario_contracts(),
                baseline_dir_path=baseline_dir_path,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return path
