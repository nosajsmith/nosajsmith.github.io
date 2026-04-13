from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


SUPPORTED_GATES: tuple[str, ...] = (
    "core_validation_green",
    "known_issues_under_control",
    "scenario_contracts_present",
    "baseline_compare_available",
    "divergence_support_available",
    "explainability_available",
)


@dataclass(frozen=True)
class ExpansionRegistryEntry:
    entry_id: str
    name: str
    category: str
    theater: str
    era: str
    summary: str
    status: str
    maturity: str
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    support_gates: Dict[str, bool] = field(default_factory=dict)
    risk_level: str = ""
    notes: str = ""
    next_step: str = ""
    planning_state: str = "needs_foundation"
    ready_support_gates: List[str] = field(default_factory=list)
    missing_support_gates: List[str] = field(default_factory=list)

    def to_report_dict(self) -> Dict[str, object]:
        return {
            "id": self.entry_id,
            "name": self.name,
            "category": self.category,
            "theater": self.theater,
            "era": self.era,
            "summary": self.summary,
            "status": self.status,
            "maturity": self.maturity,
            "capabilities": list(self.capabilities),
            "dependencies": list(self.dependencies),
            "support_gates": dict(self.support_gates),
            "risk_level": self.risk_level,
            "notes": self.notes,
            "next_step": self.next_step,
            "planning_state": self.planning_state,
            "ready_support_gates": list(self.ready_support_gates),
            "missing_support_gates": list(self.missing_support_gates),
        }


@dataclass(frozen=True)
class ExpansionRegistry:
    version: int
    entries: List[ExpansionRegistryEntry] = field(default_factory=list)
    source_path: str = ""

    def categories(self) -> List[str]:
        values: List[str] = []
        for entry in self.entries:
            if entry.category not in values:
                values.append(entry.category)
        return values

    def statuses(self) -> List[str]:
        values: List[str] = []
        for entry in self.entries:
            if entry.status not in values:
                values.append(entry.status)
        return values

    def planning_states(self) -> List[str]:
        return ["support_ready", "blocked_by_support", "needs_foundation"]

    def counts_by_planning_state(self) -> Dict[str, int]:
        counts = {state: 0 for state in self.planning_states()}
        for entry in self.entries:
            counts[entry.planning_state] = counts.get(entry.planning_state, 0) + 1
        return counts

    def counts_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in self.entries:
            counts[entry.status] = counts.get(entry.status, 0) + 1
        return counts

    def counts_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in self.entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    def entries_by_planning_state(self) -> Dict[str, List[ExpansionRegistryEntry]]:
        grouped = {state: [] for state in self.planning_states()}
        for entry in self.entries:
            grouped.setdefault(entry.planning_state, []).append(entry)
        return grouped


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def expansion_registry_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "expansion_registry.yaml"


def default_export_dir(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "operations_console" / "expansion_registry"


def load_expansion_registry(path: Path | None = None) -> ExpansionRegistry:
    source_path = Path(path) if path is not None else expansion_registry_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Expansion registry must be a top-level object.")
    version = payload.get("version")
    if not isinstance(version, int):
        raise RuntimeError("Expansion registry must expose an integer version.")
    rows = payload.get("entries")
    if not isinstance(rows, list):
        raise RuntimeError("Expansion registry must expose an entries list.")

    entries: List[ExpansionRegistryEntry] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise RuntimeError(f"Expansion registry row #{index} must be an object.")
        entry = _validate_entry(dict(row), index=index)
        if entry.entry_id in seen_ids:
            raise RuntimeError(f"Duplicate expansion registry id: {entry.entry_id}")
        seen_ids.add(entry.entry_id)
        entries.append(entry)
    return ExpansionRegistry(version=version, entries=entries, source_path=str(source_path))


def write_expansion_registry_snapshot(
    registry: ExpansionRegistry,
    *,
    path: Path | None = None,
    repo_root_path: Path | None = None,
) -> Path:
    target_dir = default_export_dir(repo_root_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = Path(path) if path is not None else target_dir / f"{_timestamp()}-expansion-registry.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": registry.version,
        "generated_at": utc_timestamp(),
        "entry_count": len(registry.entries),
        "planning_state_counts": registry.counts_by_planning_state(),
        "status_counts": registry.counts_by_status(),
        "category_counts": registry.counts_by_category(),
        "entries": [entry.to_report_dict() for entry in registry.entries],
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse expansion registry: {path}") from exc


def _validate_entry(row: Dict[str, object], *, index: int) -> ExpansionRegistryEntry:
    support_gates = _support_gate_map(row.get("support_gates"), field_name=f"entries[{index}].support_gates")
    ready_support_gates = [gate for gate in SUPPORTED_GATES if support_gates.get(gate)]
    missing_support_gates = [gate for gate in SUPPORTED_GATES if not support_gates.get(gate)]
    planning_state = _derive_planning_state(support_gates)
    return ExpansionRegistryEntry(
        entry_id=_required_text(row.get("id"), f"entries[{index}].id"),
        name=_required_text(row.get("name"), f"entries[{index}].name"),
        category=_required_text(row.get("category"), f"entries[{index}].category"),
        theater=_required_text(row.get("theater"), f"entries[{index}].theater"),
        era=_required_text(row.get("era"), f"entries[{index}].era"),
        summary=_required_text(row.get("summary"), f"entries[{index}].summary"),
        status=_required_text(row.get("status"), f"entries[{index}].status"),
        maturity=_required_text(row.get("maturity"), f"entries[{index}].maturity"),
        capabilities=_text_list(row.get("capabilities"), field_name=f"entries[{index}].capabilities"),
        dependencies=_text_list(row.get("dependencies"), field_name=f"entries[{index}].dependencies"),
        support_gates=support_gates,
        risk_level=_required_text(row.get("risk_level"), f"entries[{index}].risk_level"),
        notes=str(row.get("notes") or "").strip(),
        next_step=_required_text(row.get("next_step"), f"entries[{index}].next_step"),
        planning_state=planning_state,
        ready_support_gates=ready_support_gates,
        missing_support_gates=missing_support_gates,
    )


def _derive_planning_state(support_gates: Mapping[str, bool]) -> str:
    ready_count = sum(1 for gate in SUPPORTED_GATES if bool(support_gates.get(gate)))
    if ready_count == len(SUPPORTED_GATES) and ready_count > 0:
        return "support_ready"
    if ready_count == 0:
        return "needs_foundation"
    return "blocked_by_support"


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


def _support_gate_map(value: object, *, field_name: str) -> Dict[str, bool]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{field_name} must be an object of boolean support gates.")
    normalized: Dict[str, bool] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        if key not in SUPPORTED_GATES:
            raise RuntimeError(f"{field_name}.{key} is not a supported gate.")
        if not isinstance(raw_value, bool):
            raise RuntimeError(f"{field_name}.{key} must be a boolean.")
        normalized[key] = raw_value
    return normalized
