from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Sequence

from .gui_action_matrix import GuiActionMatrix
from .models import ConsoleResult
from .runner_utils import iter_results

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


STATUS_ORDER = {
    "pass": 0,
    "warn": 1,
    "fail": 2,
    "error": 3,
}


@dataclass(frozen=True)
class ScenarioContract:
    scenario_name: str
    expected_unit_count_range: tuple[int, int] | None = None
    expected_objectives: List[str] = field(default_factory=list)
    expected_status_fields: List[str] = field(default_factory=list)
    expected_explain_fields: List[str] = field(default_factory=list)
    expected_artifacts: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    mismatch_status: str = "fail"
    notes: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class ScenarioContractCatalog:
    version: int = 1
    contracts: List[ScenarioContract] = field(default_factory=list)
    source_path: str = ""

    def get(self, scenario_name: str) -> ScenarioContract | None:
        candidate = _normalize_scenario_name(scenario_name)
        if not candidate:
            return None
        for contract in self.contracts:
            if not contract.enabled:
                continue
            pattern = _normalize_scenario_name(contract.scenario_name)
            if not pattern:
                continue
            if fnmatch(candidate, pattern) or fnmatch(_scenario_stem(candidate), _scenario_stem(pattern)):
                return contract
        return None


@dataclass(frozen=True)
class ScenarioContractEvaluation:
    matched: bool
    scenario_name: str
    contract_scenario_name: str = ""
    status: str = "pass"
    issues: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    expected_artifacts: List[str] = field(default_factory=list)
    notes: str = ""
    payload_path: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def scenario_contracts_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "scenario_contracts.yaml"


def load_scenario_contracts(path: Path | None = None) -> ScenarioContractCatalog:
    source_path = Path(path) if path is not None else scenario_contracts_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Scenario contracts must be a top-level object.")
    version = payload.get("version")
    if not isinstance(version, int):
        raise RuntimeError("Scenario contracts file must expose an integer version.")
    rows = payload.get("contracts")
    if not isinstance(rows, list):
        raise RuntimeError("Scenario contracts file must expose a contracts list.")

    contracts: List[ScenarioContract] = []
    seen_names: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"Scenario contract #{index} must be an object.")
        contract = _validate_contract_row(row, index=index)
        key = _normalize_scenario_name(contract.scenario_name)
        if key in seen_names:
            raise RuntimeError(f"Duplicate scenario contract: {contract.scenario_name}")
        seen_names.add(key)
        contracts.append(contract)
    return ScenarioContractCatalog(version=version, contracts=contracts, source_path=str(source_path))


def evaluate_scenario_contract(
    scenario_name: str,
    *,
    contract_catalog: ScenarioContractCatalog | None = None,
    scenario_payload: Dict[str, object] | None = None,
    payload_path: Path | None = None,
    repo_root_path: Path | None = None,
    observed_unit_count: int | None = None,
    observed_objectives: Sequence[str] | None = None,
    observed_field_paths: Sequence[str] | None = None,
    artifact_paths: Sequence[str] | None = None,
) -> ScenarioContractEvaluation:
    normalized_name = _normalize_scenario_name(scenario_name)
    if not normalized_name:
        return ScenarioContractEvaluation(matched=False, scenario_name="")

    catalog = contract_catalog or load_scenario_contracts()
    contract = catalog.get(normalized_name)
    if contract is None:
        return ScenarioContractEvaluation(matched=False, scenario_name=normalized_name)

    scenario_data = scenario_payload
    resolved_path = Path(payload_path) if payload_path is not None else None
    if scenario_data is None:
        scenario_data, resolved_path = load_scenario_payload(normalized_name, repo_root_path=repo_root_path)

    issues: List[str] = []
    if scenario_data is None:
        if not _has_observed_contract_inputs(
            observed_unit_count=observed_unit_count,
            observed_objectives=observed_objectives,
            observed_field_paths=observed_field_paths,
            artifact_paths=artifact_paths,
        ):
            issues.append(f"Scenario payload could not be resolved for {normalized_name}.")
    validation_issues, passed_checks = _validate_payload_against_contract(
        scenario_data,
        contract,
        observed_unit_count=observed_unit_count,
        observed_objectives=observed_objectives,
        observed_field_paths=observed_field_paths,
        artifact_paths=artifact_paths,
    )
    issues.extend(validation_issues)

    status = "pass" if not issues else contract.mismatch_status
    return ScenarioContractEvaluation(
        matched=True,
        scenario_name=normalized_name,
        contract_scenario_name=contract.scenario_name,
        status=status,
        issues=issues,
        passed_checks=passed_checks,
        known_issues=list(contract.known_issues),
        expected_artifacts=list(contract.expected_artifacts),
        notes=contract.notes,
        payload_path=str(resolved_path or ""),
    )


def evaluate_result_contract(
    result: ConsoleResult,
    *,
    scenario_name: str = "",
    contract_catalog: ScenarioContractCatalog | None = None,
    action_matrix: GuiActionMatrix | None = None,
    repo_root_path: Path | None = None,
) -> ScenarioContractEvaluation | None:
    observed = _extract_contract_observations(result)
    resolved_scenario = str(scenario_name or result.scenario_name or observed.get("scenario_name") or "").strip()
    matrix_entry = action_matrix.get_by_label(result.name) if action_matrix is not None else None
    if not resolved_scenario:
        return None
    if matrix_entry is not None and "scenario_name" not in matrix_entry.inputs:
        return None
    return evaluate_scenario_contract(
        resolved_scenario,
        contract_catalog=contract_catalog,
        repo_root_path=repo_root_path,
        observed_unit_count=_int_or_none(observed.get("unit_count")),
        observed_objectives=observed.get("objectives") or [],
        observed_field_paths=observed.get("field_paths") or [],
        artifact_paths=observed.get("artifact_paths") or [],
    )


def apply_scenario_contracts(
    result: ConsoleResult,
    *,
    scenario_name: str = "",
    contract_catalog: ScenarioContractCatalog | None = None,
    action_matrix: GuiActionMatrix | None = None,
    repo_root_path: Path | None = None,
) -> tuple[ConsoleResult, ScenarioContractEvaluation | None]:
    evaluation = evaluate_result_contract(
        result,
        scenario_name=scenario_name,
        contract_catalog=contract_catalog,
        action_matrix=action_matrix,
        repo_root_path=repo_root_path,
    )
    if evaluation is None or not evaluation.matched or evaluation.status == "pass":
        return result, evaluation

    target_status = _max_status(result.status, evaluation.status)
    detail_lines = list(result.details)
    detail_lines.append(
        f"Scenario contract {evaluation.contract_scenario_name} evaluated {evaluation.status.upper()}."
    )
    detail_lines.extend(f"CONTRACT MISMATCH: {issue}" for issue in evaluation.issues)

    error_lines = list(result.errors)
    if evaluation.status in {"fail", "error"}:
        for issue in evaluation.issues:
            if issue not in error_lines:
                error_lines.append(issue)

    summary = result.summary
    if evaluation.issues:
        suffix = f" Scenario contract mismatch ({len(evaluation.issues)})."
        if suffix.strip() not in summary:
            summary = f"{summary}{suffix}"

    updated = replace(
        result,
        status=target_status,
        details=detail_lines,
        errors=error_lines,
        summary=summary,
    )
    return updated, evaluation


def load_scenario_payload(
    scenario_name: str,
    *,
    repo_root_path: Path | None = None,
) -> tuple[Dict[str, object] | None, Path | None]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    filename = _scenario_filename(scenario_name)
    candidates = [
        root / "scenarios" / filename,
        root / "server" / "scenarios" / filename,
        root / "server" / "rules" / "scenarios" / filename,
    ]
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload, path
    return None, None


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse scenario contracts file: {path}") from exc


def _validate_contract_row(row: dict, *, index: int) -> ScenarioContract:
    scenario_name = _required_text(row.get("scenario_name"), f"contracts[{index}].scenario_name")
    mismatch_status = _required_text(row.get("mismatch_status", "fail"), f"contracts[{index}].mismatch_status").lower()
    if mismatch_status not in {"warn", "fail", "error"}:
        raise RuntimeError(f"contracts[{index}].mismatch_status must be warn, fail, or error.")
    return ScenarioContract(
        scenario_name=scenario_name,
        expected_unit_count_range=_unit_count_range(
            row.get("expected_unit_count_range"),
            field_name=f"contracts[{index}].expected_unit_count_range",
        ),
        expected_objectives=_text_list(row.get("expected_objectives"), field_name=f"contracts[{index}].expected_objectives"),
        expected_status_fields=_text_list(row.get("expected_status_fields"), field_name=f"contracts[{index}].expected_status_fields"),
        expected_explain_fields=_text_list(row.get("expected_explain_fields"), field_name=f"contracts[{index}].expected_explain_fields"),
        expected_artifacts=_text_list(row.get("expected_artifacts"), field_name=f"contracts[{index}].expected_artifacts"),
        known_issues=_text_list(row.get("known_issues"), field_name=f"contracts[{index}].known_issues"),
        mismatch_status=mismatch_status,
        notes=str(row.get("notes") or "").strip(),
        enabled=_bool_value(row.get("enabled", True), field_name=f"contracts[{index}].enabled"),
    )


def _unit_count_range(value: object, *, field_name: str) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        minimum = value.get("min")
        maximum = value.get("max")
    elif isinstance(value, list) and len(value) == 2:
        minimum, maximum = value
    else:
        raise RuntimeError(f"{field_name} must be [min, max] or {{min, max}}.")
    try:
        minimum_int = int(minimum)
        maximum_int = int(maximum)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{field_name} must contain integer bounds.") from exc
    if minimum_int < 0 or maximum_int < minimum_int:
        raise RuntimeError(f"{field_name} must define a valid inclusive range.")
    return (minimum_int, maximum_int)


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


def _bool_value(value: object, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise RuntimeError(f"{field_name} must be a boolean.")


def _validate_payload_against_contract(
    payload: Dict[str, object] | None,
    contract: ScenarioContract,
    *,
    observed_unit_count: int | None = None,
    observed_objectives: Sequence[str] | None = None,
    observed_field_paths: Sequence[str] | None = None,
    artifact_paths: Sequence[str] | None = None,
) -> tuple[List[str], List[str]]:
    issues: List[str] = []
    passed_checks: List[str] = []

    unit_count = _resolve_unit_count(payload, observed_unit_count)
    if contract.expected_unit_count_range is not None:
        minimum, maximum = contract.expected_unit_count_range
        if unit_count is None:
            issues.append(f"Unit count unavailable for expected range [{minimum}, {maximum}].")
        elif unit_count < minimum or unit_count > maximum:
            issues.append(
                f"Unit count {unit_count} fell outside expected range [{minimum}, {maximum}]."
            )
        else:
            passed_checks.append(f"unit count in range [{minimum}, {maximum}] (observed {unit_count})")

    objective_names = _resolve_objective_names(payload, observed_objectives)
    missing_objectives = [objective_name for objective_name in contract.expected_objectives if objective_name not in objective_names]
    for objective_name in missing_objectives:
        issues.append(f"Expected objective missing: {objective_name}.")
    if contract.expected_objectives and not missing_objectives:
        passed_checks.append(f"expected objectives present ({len(contract.expected_objectives)})")

    available_fields = _resolve_field_paths(payload, observed_field_paths)
    missing_status_fields: List[str] = []
    for field_path in contract.expected_status_fields:
        if field_path not in available_fields:
            missing_status_fields.append(field_path)
            issues.append(f"Expected status field missing: {field_path}.")
    if contract.expected_status_fields and not missing_status_fields:
        passed_checks.append(f"status fields present: {', '.join(contract.expected_status_fields)}")

    missing_explain_fields: List[str] = []
    for field_path in contract.expected_explain_fields:
        if field_path not in available_fields:
            missing_explain_fields.append(field_path)
            issues.append(f"Expected explain field missing: {field_path}.")
    if contract.expected_explain_fields and not missing_explain_fields:
        passed_checks.append(f"explain fields present: {', '.join(contract.expected_explain_fields)}")

    normalized_artifacts = [str(path or "").strip() for path in list(artifact_paths or []) if str(path or "").strip()]
    missing_artifacts: List[str] = []
    for artifact_name in contract.expected_artifacts:
        if not _artifact_present(artifact_name, normalized_artifacts):
            missing_artifacts.append(artifact_name)
            issues.append(f"Expected artifact missing: {artifact_name}.")
    if contract.expected_artifacts and not missing_artifacts:
        passed_checks.append(f"expected artifacts present: {', '.join(contract.expected_artifacts)}")

    return issues, passed_checks


def _field_exists(payload: Dict[str, object], dotted_path: str) -> bool:
    current: object = payload
    for segment in str(dotted_path or "").strip().split("."):
        if not segment:
            return False
        if not isinstance(current, dict) or segment not in current:
            return False
        current = current[segment]
    return True


def _normalize_scenario_name(value: str) -> str:
    return str(value or "").strip().lower()


def _scenario_filename(value: str) -> str:
    text = str(value or "").strip()
    if text.endswith(".json"):
        return text
    return f"{text}.json"


def _scenario_stem(value: str) -> str:
    text = _normalize_scenario_name(value)
    return text[:-5] if text.endswith(".json") else text


def _max_status(current: str, incoming: str) -> str:
    current_text = str(current or "pass").strip().lower()
    incoming_text = str(incoming or "pass").strip().lower()
    return incoming_text if STATUS_ORDER.get(incoming_text, 0) > STATUS_ORDER.get(current_text, 0) else current_text


def _resolve_unit_count(payload: Dict[str, object] | None, observed_unit_count: int | None) -> int | None:
    if observed_unit_count is not None:
        return observed_unit_count
    if not isinstance(payload, dict):
        return None
    units = payload.get("units")
    if isinstance(units, list):
        return len(units)
    return None


def _resolve_objective_names(
    payload: Dict[str, object] | None,
    observed_objectives: Sequence[str] | None,
) -> set[str]:
    objective_names = {
        str(item or "").strip()
        for item in list(observed_objectives or [])
        if str(item or "").strip()
    }
    if isinstance(payload, dict):
        objectives = payload.get("objectives")
        if isinstance(objectives, list):
            objective_names.update(
                str(item.get("name") or "").strip()
                for item in objectives
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            )
    return objective_names


def _resolve_field_paths(
    payload: Dict[str, object] | None,
    observed_field_paths: Sequence[str] | None,
) -> set[str]:
    field_paths = {
        str(path or "").strip()
        for path in list(observed_field_paths or [])
        if str(path or "").strip()
    }
    if isinstance(payload, dict):
        field_paths.update(_payload_field_paths(payload))
    return field_paths


def _payload_field_paths(payload: Dict[str, object], *, prefix: str = "") -> set[str]:
    field_paths: set[str] = set()
    for key, value in payload.items():
        segment = str(key or "").strip()
        if not segment:
            continue
        dotted = f"{prefix}.{segment}" if prefix else segment
        field_paths.add(dotted)
        if isinstance(value, dict):
            field_paths.update(_payload_field_paths(value, prefix=dotted))
    return field_paths


def _artifact_present(expected_artifact: str, artifact_paths: Sequence[str]) -> bool:
    fragment = str(expected_artifact or "").strip().lower()
    if not fragment:
        return False
    for path in artifact_paths:
        candidate = str(path or "").strip().lower()
        if fragment == candidate or fragment in candidate:
            return True
    return False


def _has_observed_contract_inputs(
    *,
    observed_unit_count: int | None,
    observed_objectives: Sequence[str] | None,
    observed_field_paths: Sequence[str] | None,
    artifact_paths: Sequence[str] | None,
) -> bool:
    return any(
        value
        for value in (
            observed_unit_count is not None,
            list(observed_objectives or []),
            list(observed_field_paths or []),
            list(artifact_paths or []),
        )
    )


def _extract_contract_observations(result: ConsoleResult) -> Dict[str, object]:
    observations: Dict[str, object] = {
        "scenario_name": "",
        "unit_count": None,
        "objectives": [],
        "field_paths": [],
        "artifact_paths": [],
    }
    objectives: List[str] = []
    field_paths: List[str] = []
    artifact_paths: List[str] = []
    scenario_name = ""
    unit_count: int | None = None

    for item in iter_results(result):
        artifact_paths.extend(str(path or "").strip() for path in item.artifact_paths if str(path or "").strip())
        for line in item.details:
            text = str(line or "").strip()
            if not text:
                continue
            if not scenario_name:
                match = re.search(r"Selected scenario: (.+)$", text)
                if match:
                    scenario_name = _scenario_stem(match.group(1).strip())
            if not scenario_name:
                match = re.search(r"Loaded scenario successfully: .+? \((.+?)\)$", text)
                if match:
                    scenario_name = _scenario_stem(match.group(1).strip())
            match = re.search(r"Validated units: (\d+) total, (\d+) with basic", text)
            if match:
                unit_count = int(match.group(1))
            if text.startswith("CAMPAIGN STATUS DETAIL: "):
                detail_values = _parse_key_value_segments(text.partition(": ")[2])
                detail_unit_count = _int_or_none(detail_values.get("units"))
                if detail_unit_count is not None:
                    unit_count = detail_unit_count
            elif text.startswith("CAMPAIGN STATUS: "):
                values = _parse_key_value_segments(text.partition(": ")[2])
                if "front" in values:
                    field_paths.append("grease_board.front_status")
                if "supply" in values:
                    field_paths.append("grease_board.supply_status")
                if "main" in values:
                    field_paths.append("grease_board.main_effort")
                objective = str(values.get("objective") or "").strip()
                if objective and objective.lower() != "<unknown>":
                    objectives.append(objective)
            elif text.startswith("CAMPAIGN EXPLAIN: "):
                field_paths.append("description")
            elif text.startswith("CAMPAIGN NOTES: "):
                field_paths.append("grease_board.staff_notes")
            elif text.startswith("CAMPAIGN OBJECTIVES: "):
                objectives.extend(_split_semicolon_items(text.partition(": ")[2]))

    observations["scenario_name"] = scenario_name
    observations["unit_count"] = unit_count
    observations["objectives"] = list(dict.fromkeys(objectives))
    observations["field_paths"] = list(dict.fromkeys(field_paths))
    observations["artifact_paths"] = list(dict.fromkeys(artifact_paths))
    return observations


def _parse_key_value_segments(payload: str) -> Dict[str, object]:
    values: Dict[str, object] = {}
    for segment in str(payload or "").split("|"):
        key, separator, value = segment.partition("=")
        if not separator:
            continue
        values[key.strip().lower()] = value.strip()
    return values


def _split_semicolon_items(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
