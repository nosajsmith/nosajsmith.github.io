from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping

from .gui_action_matrix import GuiActionMatrix, load_gui_action_matrix
from .models import ConsoleResult
from .scenario_contracts import ScenarioContractCatalog, load_scenario_contracts, load_scenario_payload


STATUS_ORDER = {
    "pass": 0,
    "warn": 1,
    "fail": 2,
    "error": 3,
}

BASELINE_VERSION = 1


@dataclass(frozen=True)
class DriftTolerance:
    unit_count_warn_delta: int = 1
    unit_count_fail_delta: int = 2


@dataclass(frozen=True)
class BaselineRecord:
    version: int
    baseline_key: str
    name: str
    scenario_name: str
    saved_at: str
    metrics: Dict[str, object] = field(default_factory=dict)
    source_path: str = ""


@dataclass(frozen=True)
class DriftFinding:
    metric: str
    status: str
    message: str
    baseline_value: object = None
    current_value: object = None


@dataclass(frozen=True)
class BaselineComparison:
    matched: bool
    baseline_key: str
    status: str = "pass"
    findings: List[DriftFinding] = field(default_factory=list)
    baseline_metrics: Dict[str, object] = field(default_factory=dict)
    current_metrics: Dict[str, object] = field(default_factory=dict)
    baseline_path: str = ""
    saved_at: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_baseline_dir(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "operations_console" / "baselines"


def ensure_baseline_dir(path: Path | None = None, *, repo_root_path: Path | None = None) -> Path:
    target = Path(path) if path is not None else default_baseline_dir(repo_root_path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def baseline_key(name: str, scenario_name: str = "") -> str:
    scenario_slug = slugify(scenario_name) if str(scenario_name or "").strip() else "default"
    return f"{slugify(name)}--{scenario_slug}"


def baseline_path_for_result(
    result: ConsoleResult,
    *,
    baseline_dir_path: Path | None = None,
    repo_root_path: Path | None = None,
) -> Path:
    target_dir = Path(baseline_dir_path) if baseline_dir_path is not None else default_baseline_dir(repo_root_path)
    scenario_name = str(result.scenario_name or "").strip()
    return target_dir / f"{baseline_key(result.name, scenario_name)}.json"


def save_baseline(
    result: ConsoleResult,
    *,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
    repo_root_path: Path | None = None,
) -> Path:
    target = baseline_path_for_result(
        result,
        baseline_dir_path=baseline_dir_path,
        repo_root_path=repo_root_path,
    )
    ensure_baseline_dir(target.parent)
    metrics = capture_result_metrics(
        result,
        action_matrix=action_matrix,
        scenario_contracts=scenario_contracts,
        repo_root_path=repo_root_path,
    )
    payload = {
        "version": BASELINE_VERSION,
        "baseline_key": baseline_key(result.name, result.scenario_name),
        "name": result.name,
        "scenario_name": str(result.scenario_name or "").strip(),
        "saved_at": utc_timestamp(),
        "metrics": metrics,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_baseline_for_result(
    result: ConsoleResult,
    *,
    baseline_dir_path: Path | None = None,
    repo_root_path: Path | None = None,
) -> BaselineRecord | None:
    path = baseline_path_for_result(
        result,
        baseline_dir_path=baseline_dir_path,
        repo_root_path=repo_root_path,
    )
    if not path.exists() or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Baseline file must be an object: {path}")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise RuntimeError(f"Baseline metrics must be an object: {path}")
    return BaselineRecord(
        version=int(payload.get("version") or BASELINE_VERSION),
        baseline_key=str(payload.get("baseline_key") or baseline_key(result.name, result.scenario_name)).strip(),
        name=str(payload.get("name") or result.name).strip(),
        scenario_name=str(payload.get("scenario_name") or result.scenario_name or "").strip(),
        saved_at=str(payload.get("saved_at") or "").strip(),
        metrics=dict(metrics),
        source_path=str(path),
    )


def compare_result_to_baseline(
    result: ConsoleResult,
    *,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    baseline_dir_path: Path | None = None,
    repo_root_path: Path | None = None,
    tolerance: DriftTolerance | None = None,
) -> BaselineComparison:
    limits = tolerance or DriftTolerance()
    current_metrics = capture_result_metrics(
        result,
        action_matrix=action_matrix,
        scenario_contracts=scenario_contracts,
        repo_root_path=repo_root_path,
    )
    record = load_baseline_for_result(
        result,
        baseline_dir_path=baseline_dir_path,
        repo_root_path=repo_root_path,
    )
    if record is None:
        return BaselineComparison(
            matched=False,
            baseline_key=baseline_key(result.name, result.scenario_name),
            current_metrics=current_metrics,
        )

    findings: List[DriftFinding] = []
    findings.extend(_compare_status_metric(record.metrics, current_metrics, metric_name="status"))
    findings.extend(
        _compare_exact_metric(
            record.metrics,
            current_metrics,
            metric_name="scenario_name",
            label="Scenario",
            on_change="fail",
        )
    )
    findings.extend(_compare_unit_count(record.metrics, current_metrics, tolerance=limits))
    findings.extend(_compare_artifacts(record.metrics, current_metrics))
    findings.extend(
        _compare_mapping_values(
            record.metrics.get("selected_fields"),
            current_metrics.get("selected_fields"),
            mapping_name="Selected field",
            metric_name="selected_fields",
        )
    )
    findings.extend(
        _compare_mapping_values(
            _drift_relevant_observed_fields(record.metrics.get("observed_fields")),
            _drift_relevant_observed_fields(current_metrics.get("observed_fields")),
            mapping_name="Observed field",
            metric_name="observed_fields",
        )
    )
    findings.extend(
        _compare_mapping_values(
            record.metrics.get("subresult_statuses"),
            current_metrics.get("subresult_statuses"),
            mapping_name="Subresult",
            metric_name="subresult_statuses",
            status_mode=True,
        )
    )

    status = "pass"
    if findings:
        status = "warn" if any(item.status == "warn" for item in findings) else "pass"
        if any(item.status == "fail" for item in findings):
            status = "fail"

    return BaselineComparison(
        matched=True,
        baseline_key=record.baseline_key,
        status=status,
        findings=findings,
        baseline_metrics=dict(record.metrics),
        current_metrics=current_metrics,
        baseline_path=record.source_path,
        saved_at=record.saved_at,
    )


def capture_result_metrics(
    result: ConsoleResult,
    *,
    action_matrix: GuiActionMatrix | None = None,
    scenario_contracts: ScenarioContractCatalog | None = None,
    repo_root_path: Path | None = None,
) -> Dict[str, object]:
    matrix = action_matrix
    if matrix is None:
        try:
            matrix = load_gui_action_matrix()
        except Exception:
            matrix = None

    contracts = scenario_contracts
    if contracts is None:
        try:
            contracts = load_scenario_contracts()
        except Exception:
            contracts = None

    resolved_scenario = str(result.scenario_name or "").strip()
    observed_fields = _extract_observed_fields(result)
    payload = None
    contract = contracts.get(resolved_scenario) if contracts is not None and resolved_scenario else None
    if resolved_scenario:
        payload, _payload_path = load_scenario_payload(resolved_scenario, repo_root_path=repo_root_path)

    selected_fields: Dict[str, object] = {}
    if payload is not None and contract is not None:
        field_paths = list(dict.fromkeys(contract.expected_status_fields + contract.expected_explain_fields))
        for dotted_path in field_paths:
            exists, value = _field_value(payload, dotted_path)
            if exists:
                selected_fields[dotted_path] = _normalize_json_value(value)

    matrix_entry = matrix.get_by_label(result.name) if matrix is not None else None
    artifact_presence = _artifact_presence(
        result.artifact_paths,
        expected_types=matrix_entry.artifact_types if matrix_entry is not None else [],
    )
    return {
        "status": normalize_status(result.status),
        "scenario_name": resolved_scenario,
        "unit_count": _resolve_unit_count(result, payload, observed_fields),
        "artifact_count": len(result.artifact_paths),
        "artifact_presence": artifact_presence,
        "selected_fields": selected_fields,
        "observed_fields": observed_fields,
        "subresult_statuses": {
            item.name: normalize_status(item.status)
            for item in result.subresults
            if str(item.name or "").strip()
        },
    }


def slugify(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "baseline"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_status(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in STATUS_ORDER else "error"


def _compare_status_metric(
    baseline_metrics: Mapping[str, object],
    current_metrics: Mapping[str, object],
    *,
    metric_name: str,
) -> List[DriftFinding]:
    baseline_status = normalize_status(baseline_metrics.get(metric_name))
    current_status = normalize_status(current_metrics.get(metric_name))
    if baseline_status == current_status:
        return []

    baseline_rank = STATUS_ORDER.get(baseline_status, 3)
    current_rank = STATUS_ORDER.get(current_status, 3)
    if current_rank > baseline_rank:
        delta = current_rank - baseline_rank
        finding_status = "warn" if delta == 1 else "fail"
        message = f"Overall status drifted from {baseline_status.upper()} to {current_status.upper()}."
    else:
        finding_status = "warn"
        message = f"Overall status changed from {baseline_status.upper()} to {current_status.upper()}."
    return [
        DriftFinding(
            metric=metric_name,
            status=finding_status,
            message=message,
            baseline_value=baseline_status,
            current_value=current_status,
        )
    ]


def _compare_exact_metric(
    baseline_metrics: Mapping[str, object],
    current_metrics: Mapping[str, object],
    *,
    metric_name: str,
    label: str,
    on_change: str,
) -> List[DriftFinding]:
    baseline_value = baseline_metrics.get(metric_name)
    current_value = current_metrics.get(metric_name)
    if baseline_value == current_value:
        return []
    if baseline_value in {None, ""} and current_value in {None, ""}:
        return []
    return [
        DriftFinding(
            metric=metric_name,
            status=on_change,
            message=f"{label} drifted from {baseline_value!r} to {current_value!r}.",
            baseline_value=baseline_value,
            current_value=current_value,
        )
    ]


def _compare_unit_count(
    baseline_metrics: Mapping[str, object],
    current_metrics: Mapping[str, object],
    *,
    tolerance: DriftTolerance,
) -> List[DriftFinding]:
    baseline_value = _int_or_none(baseline_metrics.get("unit_count"))
    current_value = _int_or_none(current_metrics.get("unit_count"))
    if baseline_value is None and current_value is None:
        return []
    if baseline_value is None or current_value is None:
        return [
            DriftFinding(
                metric="unit_count",
                status="fail",
                message=f"Unit count availability changed from {baseline_value!r} to {current_value!r}.",
                baseline_value=baseline_value,
                current_value=current_value,
            )
        ]
    delta = abs(current_value - baseline_value)
    if delta == 0:
        return []
    finding_status = "warn" if delta <= tolerance.unit_count_warn_delta else "fail"
    if tolerance.unit_count_fail_delta > tolerance.unit_count_warn_delta and delta < tolerance.unit_count_fail_delta:
        finding_status = "warn"
    elif delta >= tolerance.unit_count_fail_delta:
        finding_status = "fail"
    return [
        DriftFinding(
            metric="unit_count",
            status=finding_status,
            message=f"Unit count changed from {baseline_value} to {current_value}.",
            baseline_value=baseline_value,
            current_value=current_value,
        )
    ]


def _compare_artifacts(
    baseline_metrics: Mapping[str, object],
    current_metrics: Mapping[str, object],
) -> List[DriftFinding]:
    findings: List[DriftFinding] = []
    baseline_count = _int_or_none(baseline_metrics.get("artifact_count")) or 0
    current_count = _int_or_none(current_metrics.get("artifact_count")) or 0
    if baseline_count != current_count:
        findings.append(
            DriftFinding(
                metric="artifact_count",
                status="fail" if current_count < baseline_count else "warn",
                message=f"Artifact count drifted from {baseline_count} to {current_count}.",
                baseline_value=baseline_count,
                current_value=current_count,
            )
        )

    baseline_presence = baseline_metrics.get("artifact_presence")
    current_presence = current_metrics.get("artifact_presence")
    if not isinstance(baseline_presence, dict) or not isinstance(current_presence, dict):
        return findings
    for artifact_name in sorted(set(baseline_presence) | set(current_presence)):
        baseline_value = bool(baseline_presence.get(artifact_name))
        current_value = bool(current_presence.get(artifact_name))
        if baseline_value == current_value:
            continue
        findings.append(
            DriftFinding(
                metric=f"artifact_presence.{artifact_name}",
                status="fail" if baseline_value and not current_value else "warn",
                message=f"Artifact presence for {artifact_name} drifted from {baseline_value} to {current_value}.",
                baseline_value=baseline_value,
                current_value=current_value,
            )
        )
    return findings


def _compare_mapping_values(
    baseline_value: object,
    current_value: object,
    *,
    mapping_name: str,
    metric_name: str,
    status_mode: bool = False,
) -> List[DriftFinding]:
    baseline_mapping = baseline_value if isinstance(baseline_value, dict) else {}
    current_mapping = current_value if isinstance(current_value, dict) else {}
    findings: List[DriftFinding] = []
    for key in sorted(set(baseline_mapping) | set(current_mapping)):
        left = baseline_mapping.get(key)
        right = current_mapping.get(key)
        if left == right:
            continue
        if key not in baseline_mapping:
            findings.append(
                DriftFinding(
                    metric=f"{metric_name}.{key}",
                    status="warn",
                    message=f"{mapping_name} {key} is new in the current run.",
                    baseline_value=None,
                    current_value=right,
                )
            )
            continue
        if key not in current_mapping:
            findings.append(
                DriftFinding(
                    metric=f"{metric_name}.{key}",
                    status="fail",
                    message=f"{mapping_name} {key} is missing in the current run.",
                    baseline_value=left,
                    current_value=None,
                )
            )
            continue
        if status_mode:
            findings.extend(
                _compare_status_metric(
                    {"status": left},
                    {"status": right},
                    metric_name=f"{metric_name}.{key}",
                )
            )
            if findings:
                findings[-1] = DriftFinding(
                    metric=f"{metric_name}.{key}",
                    status=findings[-1].status,
                    message=f"{mapping_name} {key} status changed from {str(left).upper()} to {str(right).upper()}.",
                    baseline_value=left,
                    current_value=right,
                )
            continue
        findings.append(
            DriftFinding(
                metric=f"{metric_name}.{key}",
                status="fail",
                message=f"{mapping_name} {key} drifted from {left!r} to {right!r}.",
                baseline_value=left,
                current_value=right,
            )
        )
    return findings


def _resolve_unit_count(
    result: ConsoleResult,
    scenario_payload: Dict[str, object] | None,
    observed_fields: Dict[str, object],
) -> int | None:
    if isinstance(scenario_payload, dict):
        units = scenario_payload.get("units")
        if isinstance(units, list):
            return len(units)
    if isinstance(observed_fields.get("unit_count"), int):
        return int(observed_fields["unit_count"])
    match = re.search(r"\bwith (\d+) unit\(s\)\b", result.summary)
    if match:
        return int(match.group(1))
    return None


def _extract_observed_fields(result: ConsoleResult) -> Dict[str, object]:
    fields: Dict[str, object] = {}
    for line in [*result.details, *result.errors, result.summary]:
        text = str(line or "").strip()
        if not text:
            continue
        match = re.search(r"Scenario roster received: (\d+) item", text)
        if match:
            fields["scenario_count"] = int(match.group(1))
        match = re.search(r"Listed (\d+) scenario", text)
        if match and "scenario_count" not in fields:
            fields["scenario_count"] = int(match.group(1))
        match = re.search(r"Validated units: (\d+) total, (\d+) with basic", text)
        if match:
            fields["unit_count"] = int(match.group(1))
            fields["valid_unit_count"] = int(match.group(2))
        match = re.search(r"Units restored: (\d+)", text)
        if match:
            fields["unit_count"] = int(match.group(1))
        match = re.search(r"Replay compare identical=(True|False)", text)
        if match:
            fields["replay_identical"] = match.group(1) == "True"
        match = re.search(r"Selected scenario: (.+)$", text)
        if match:
            fields["selected_scenario"] = match.group(1).strip()
        match = re.search(r"Loaded scenario successfully: (.+?) \((.+?)\)$", text)
        if match:
            fields["loaded_scenario_name"] = match.group(1).strip()
            fields["loaded_scenario_id"] = match.group(2).strip()
    return fields


def _artifact_presence(artifact_paths: List[str], *, expected_types: List[str]) -> Dict[str, bool]:
    presence: Dict[str, bool] = {"any": bool(artifact_paths)}
    normalized_paths = [str(path or "") for path in artifact_paths]
    for artifact_type in list(dict.fromkeys(str(item or "").strip().lower() for item in expected_types if str(item or "").strip())):
        presence[artifact_type] = any(_artifact_matches_type(path, artifact_type) for path in normalized_paths)
    return presence


def _artifact_matches_type(path: str, artifact_type: str) -> bool:
    candidate = str(path or "").lower()
    if artifact_type == "build":
        return candidate.endswith("index.html") or "/dist/" in candidate
    if artifact_type == "json":
        return candidate.endswith(".json")
    if artifact_type == "text":
        return candidate.endswith(".txt")
    return artifact_type in candidate


def _field_value(payload: Dict[str, object], dotted_path: str) -> tuple[bool, object]:
    current: object = payload
    for segment in str(dotted_path or "").strip().split("."):
        if not segment:
            return False, None
        if not isinstance(current, dict) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def _normalize_json_value(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    return str(value)


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _drift_relevant_observed_fields(value: object) -> Dict[str, object]:
    if not isinstance(value, dict):
        return {}
    ignored = {"unit_count", "valid_unit_count", "selected_scenario"}
    return {
        str(key): item
        for key, item in value.items()
        if str(key) not in ignored
    }
