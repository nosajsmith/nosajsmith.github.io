from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Sequence

from .gui_action_matrix import GuiActionMatrix
from .models import ConsoleResult

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
    known_issues: List[str] = field(default_factory=list)
    mismatch_status: str = "fail"
    notes: str = ""


@dataclass(frozen=True)
class ScenarioContractCatalog:
    contracts: List[ScenarioContract] = field(default_factory=list)
    source_path: str = ""

    def get(self, scenario_name: str) -> ScenarioContract | None:
        candidate = _normalize_scenario_name(scenario_name)
        if not candidate:
            return None
        for contract in self.contracts:
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
    known_issues: List[str] = field(default_factory=list)
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
    return ScenarioContractCatalog(contracts=contracts, source_path=str(source_path))


def evaluate_scenario_contract(
    scenario_name: str,
    *,
    contract_catalog: ScenarioContractCatalog | None = None,
    scenario_payload: Dict[str, object] | None = None,
    payload_path: Path | None = None,
    repo_root_path: Path | None = None,
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
        issues.append(f"Scenario payload could not be resolved for {normalized_name}.")
    else:
        issues.extend(_validate_payload_against_contract(scenario_data, contract))

    status = "pass" if not issues else contract.mismatch_status
    return ScenarioContractEvaluation(
        matched=True,
        scenario_name=normalized_name,
        contract_scenario_name=contract.scenario_name,
        status=status,
        issues=issues,
        known_issues=list(contract.known_issues),
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
    resolved_scenario = str(scenario_name or result.scenario_name or "").strip()
    if not resolved_scenario:
        return None
    matrix_entry = action_matrix.get_by_label(result.name) if action_matrix is not None else None
    if matrix_entry is not None and "scenario_name" not in matrix_entry.inputs and not result.scenario_name:
        return None
    return evaluate_scenario_contract(
        resolved_scenario,
        contract_catalog=contract_catalog,
        repo_root_path=repo_root_path,
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
        known_issues=_text_list(row.get("known_issues"), field_name=f"contracts[{index}].known_issues"),
        mismatch_status=mismatch_status,
        notes=str(row.get("notes") or "").strip(),
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


def _validate_payload_against_contract(payload: Dict[str, object], contract: ScenarioContract) -> List[str]:
    issues: List[str] = []
    units = payload.get("units")
    unit_count = len(units) if isinstance(units, list) else 0
    if contract.expected_unit_count_range is not None:
        minimum, maximum = contract.expected_unit_count_range
        if unit_count < minimum or unit_count > maximum:
            issues.append(
                f"Unit count {unit_count} fell outside expected range [{minimum}, {maximum}]."
            )

    objectives = payload.get("objectives")
    objective_names = {
        str(item.get("name") or "").strip()
        for item in objectives
        if isinstance(objectives, list) and isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    for objective_name in contract.expected_objectives:
        if objective_name not in objective_names:
            issues.append(f"Expected objective missing: {objective_name}.")

    for field_path in contract.expected_status_fields:
        if not _field_exists(payload, field_path):
            issues.append(f"Expected status field missing: {field_path}.")

    for field_path in contract.expected_explain_fields:
        if not _field_exists(payload, field_path):
            issues.append(f"Expected explain field missing: {field_path}.")

    return issues


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
