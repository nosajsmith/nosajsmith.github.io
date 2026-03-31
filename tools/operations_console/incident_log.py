from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .gui_action_matrix import GuiActionMatrix, GuiActionMatrixEntry, load_gui_action_matrix
from .models import ConsoleResult
from .report_export import repo_root as report_repo_root, slugify, write_report_json

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


@dataclass(frozen=True)
class AnomalyRule:
    rule_id: str
    title: str
    applies_to_statuses: List[str] = field(default_factory=list)
    affects: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    check: str = ""
    symptom_match: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class AnomalyCatalog:
    rules: List[AnomalyRule] = field(default_factory=list)
    source_path: str = ""


@dataclass(frozen=True)
class AnomalyMatch:
    rule_id: str
    title: str
    notes: str = ""


@dataclass(frozen=True)
class IncidentBundleResult:
    logged: bool
    bundle_dir: str = ""
    incident_json_path: str = ""
    run_report_json_path: str = ""
    copied_artifact_paths: List[str] = field(default_factory=list)
    anomaly_matches: List[AnomalyMatch] = field(default_factory=list)


def incident_metadata_lines(incident: IncidentBundleResult | None) -> List[str]:
    if incident is None:
        return []
    lines: List[str] = []
    if incident.anomaly_matches:
        payload = "; ".join(f"{match.rule_id} | {match.title}" for match in incident.anomaly_matches)
        if payload:
            lines.append(f"INCIDENT ANOMALIES: {payload}")
    if incident.logged:
        if incident.bundle_dir:
            lines.append(f"INCIDENT BUNDLE: {incident.bundle_dir}")
        if incident.incident_json_path:
            lines.append(f"INCIDENT MANIFEST: {incident.incident_json_path}")
        if incident.run_report_json_path:
            lines.append(f"INCIDENT RUN REPORT: {incident.run_report_json_path}")
    return lines


def repo_root() -> Path:
    return report_repo_root()


def anomaly_rules_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "anomaly_rules.yaml"


def default_incident_dir(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "operations_console" / "incidents"


def load_anomaly_rules(path: Path | None = None) -> AnomalyCatalog:
    source_path = Path(path) if path is not None else anomaly_rules_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Anomaly rules must be a top-level object.")
    rows = payload.get("rules")
    if not isinstance(rows, list):
        raise RuntimeError("Anomaly rules file must expose a rules list.")

    rules: List[AnomalyRule] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"Anomaly rule #{index} must be an object.")
        rule = _validate_rule(row, index=index)
        if rule.rule_id in seen_ids:
            raise RuntimeError(f"Duplicate anomaly rule id: {rule.rule_id}")
        seen_ids.add(rule.rule_id)
        rules.append(rule)
    return AnomalyCatalog(rules=rules, source_path=str(source_path))


def detect_anomalies(
    result: ConsoleResult,
    *,
    anomaly_catalog: AnomalyCatalog | None = None,
    action_matrix: GuiActionMatrix | None = None,
) -> List[AnomalyMatch]:
    catalog = anomaly_catalog or load_anomaly_rules()
    matrix = action_matrix or _safe_load_action_matrix()
    matrix_entry = matrix.get_by_label(result.name) if matrix is not None else None
    status = str(result.status or "").strip().lower()
    text_fragments = _result_text_fragments(result)
    scenario_name = str(result.scenario_name or "").strip()

    matches: List[AnomalyMatch] = []
    for rule in catalog.rules:
        if rule.applies_to_statuses and status not in rule.applies_to_statuses:
            continue
        if rule.affects and not _matches_any_pattern(result.name, rule.affects, allow_stem=False):
            continue
        if rule.scenarios and not _matches_any_pattern(scenario_name, rule.scenarios, allow_stem=True):
            continue
        if not _rule_triggered(rule, result=result, text_fragments=text_fragments, matrix_entry=matrix_entry):
            continue
        matches.append(AnomalyMatch(rule_id=rule.rule_id, title=rule.title, notes=rule.notes))
    return matches


def log_incident_bundle(
    result: ConsoleResult,
    *,
    anomaly_catalog: AnomalyCatalog | None = None,
    action_matrix: GuiActionMatrix | None = None,
    incidents_dir: Path | None = None,
    repo_root_path: Path | None = None,
) -> IncidentBundleResult:
    catalog = anomaly_catalog or load_anomaly_rules()
    matrix = action_matrix or _safe_load_action_matrix()
    anomaly_matches = detect_anomalies(result, anomaly_catalog=catalog, action_matrix=matrix)
    if not _should_log_incident(result, anomaly_matches):
        return IncidentBundleResult(logged=False, anomaly_matches=anomaly_matches)

    target_root = Path(incidents_dir) if incidents_dir is not None else default_incident_dir(repo_root_path)
    bundle_dir = target_root / _bundle_name(result)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied_artifact_paths = _copy_result_artifacts(result, bundle_dir)
    report_path = write_report_json(result, bundle_dir / "run_report.json", action_matrix=matrix)
    incident_path = bundle_dir / "incident.json"
    payload = _incident_payload(
        result,
        anomaly_matches=anomaly_matches,
        report_path=report_path,
        copied_artifact_paths=copied_artifact_paths,
        matrix_entry=matrix.get_by_label(result.name) if matrix is not None else None,
        repo_root_path=repo_root_path,
    )
    incident_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return IncidentBundleResult(
        logged=True,
        bundle_dir=str(bundle_dir),
        incident_json_path=str(incident_path),
        run_report_json_path=str(report_path),
        copied_artifact_paths=copied_artifact_paths,
        anomaly_matches=anomaly_matches,
    )


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse anomaly rules file: {path}") from exc


def _validate_rule(row: dict, *, index: int) -> AnomalyRule:
    return AnomalyRule(
        rule_id=_required_text(row.get("id"), f"rules[{index}].id"),
        title=_required_text(row.get("title"), f"rules[{index}].title"),
        applies_to_statuses=[value.lower() for value in _text_list(row.get("applies_to_statuses"), field_name=f"rules[{index}].applies_to_statuses")],
        affects=_text_list(row.get("affects"), field_name=f"rules[{index}].affects"),
        scenarios=_text_list(row.get("scenarios"), field_name=f"rules[{index}].scenarios"),
        check=_required_text(row.get("check"), f"rules[{index}].check"),
        symptom_match=_text_list(row.get("symptom_match"), field_name=f"rules[{index}].symptom_match"),
        notes=str(row.get("notes") or "").strip(),
    )


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{field_name} is required.")
    return text


def _text_list(value: object, *, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"{field_name} must be a list of strings.")
    items: List[str] = []
    for index, item in enumerate(value, start=1):
        text = str(item or "").strip()
        if not text:
            raise RuntimeError(f"{field_name}[{index}] must be a non-empty string.")
        items.append(text)
    return items


def _result_text_fragments(result: ConsoleResult) -> List[str]:
    fragments = [
        str(result.summary or "").strip(),
        *[str(item or "").strip() for item in result.errors],
        *[str(item or "").strip() for item in result.details],
    ]
    return [item for item in fragments if item]


def _rule_triggered(
    rule: AnomalyRule,
    *,
    result: ConsoleResult,
    text_fragments: Sequence[str],
    matrix_entry: GuiActionMatrixEntry | None,
) -> bool:
    check = rule.check.strip().lower()
    if check == "empty_scenario_list":
        return _contains_any(
            text_fragments,
            [
                "scenario roster is empty",
                "refreshed 0 scenarios",
                "scenario roster received: 0 item(s)",
            ],
        )
    if check == "zero_units_loaded":
        return _contains_any(
            text_fragments,
            [
                "contains zero units",
                "validated units: 0 total",
                "zero units loaded",
            ],
        )
    if check == "missing_expected_artifact":
        return matrix_entry is not None and bool(matrix_entry.artifact_types) and not bool(result.artifact_paths)
    if check == "symptom_match":
        return _contains_any(text_fragments, rule.symptom_match)
    return False


def _contains_any(text_fragments: Iterable[str], needles: Sequence[str]) -> bool:
    haystacks = [str(fragment or "").strip().lower() for fragment in text_fragments if str(fragment or "").strip()]
    for needle in needles:
        text = str(needle or "").strip().lower()
        if text and any(text in haystack for haystack in haystacks):
            return True
    return False


def _matches_any_pattern(value: str, patterns: Sequence[str], *, allow_stem: bool) -> bool:
    candidate = str(value or "").strip()
    if not candidate:
        return False
    candidate_lower = candidate.lower()
    candidate_stem = candidate_lower[:-5] if allow_stem and candidate_lower.endswith(".json") else candidate_lower
    for pattern in patterns:
        text = str(pattern or "").strip().lower()
        if not text:
            continue
        pattern_stem = text[:-5] if allow_stem and text.endswith(".json") else text
        if fnmatch(candidate_lower, text) or fnmatch(candidate_stem, pattern_stem):
            return True
        if candidate_lower == text or candidate_stem == pattern_stem:
            return True
    return False


def _should_log_incident(result: ConsoleResult, anomaly_matches: Sequence[AnomalyMatch]) -> bool:
    status = str(result.status or "").strip().lower()
    if status in {"fail", "error"}:
        return True
    return status == "warn" and bool(anomaly_matches)


def _bundle_name(result: ConsoleResult) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{stamp}-{slugify(result.name)}"


def _copy_result_artifacts(result: ConsoleResult, bundle_dir: Path) -> List[str]:
    copied: List[str] = []
    artifacts_dir = bundle_dir / "artifacts"
    for index, artifact_path in enumerate(result.artifact_paths, start=1):
        source = Path(str(artifact_path or "").strip())
        if not source.exists() or not source.is_file():
            continue
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:8]
        target = artifacts_dir / f"{index:02d}-{digest}-{source.name}"
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _incident_payload(
    result: ConsoleResult,
    *,
    anomaly_matches: Sequence[AnomalyMatch],
    report_path: Path,
    copied_artifact_paths: Sequence[str],
    matrix_entry: GuiActionMatrixEntry | None,
    repo_root_path: Path | None = None,
) -> Dict[str, object]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "action_name": result.name,
        "status": result.status,
        "original_status": result.original_status,
        "summary": result.summary,
        "scenario_name": result.scenario_name,
        "known_issue_matches": [
            {
                "id": match.issue_id,
                "title": match.title,
                "severity": match.severity,
                "category": match.category,
                "status": match.status,
                "expected_status_override": match.expected_status_override,
                "notes": match.notes,
            }
            for match in result.known_issue_matches
        ],
        "anomaly_matches": [
            {
                "id": match.rule_id,
                "title": match.title,
                "notes": match.notes,
            }
            for match in anomaly_matches
        ],
        "key_errors": list(result.errors),
        "key_logs": list(result.details[-40:]),
        "artifact_paths": list(result.artifact_paths),
        "copied_artifact_paths": list(copied_artifact_paths),
        "executed_command": list(result.executed_command),
        "return_code": result.return_code,
        "gui_action_matrix": matrix_entry.to_report_dict() if matrix_entry is not None else None,
        "git": _git_context(repo_root_path),
        "run_report_json": str(report_path),
    }


def _git_context(repo_root_path: Path | None = None) -> Dict[str, object]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    commit = _run_git(["rev-parse", "HEAD"], cwd=root)
    dirty_output = _run_git(["status", "--porcelain"], cwd=root, allow_empty=True)
    dirty = None if dirty_output is None else bool(str(dirty_output).strip())
    worktree_status = "unknown" if dirty is None else ("dirty" if dirty else "clean")
    return {
        "branch": branch or "",
        "commit": commit or "",
        "is_dirty": dirty,
        "worktree_status": worktree_status,
    }


def _run_git(args: List[str], *, cwd: Path, allow_empty: bool = False) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    if not output and not allow_empty:
        return None
    return output


def _safe_load_action_matrix() -> GuiActionMatrix | None:
    try:
        return load_gui_action_matrix()
    except Exception:
        return None
