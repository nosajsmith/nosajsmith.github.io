from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


@dataclass(frozen=True)
class GuiActionMatrixEntry:
    action_id: str
    label: str
    category: str
    description: str = ""
    inputs: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    runner: str = ""
    expected_status: str = ""
    expected_log_fragments: List[str] = field(default_factory=list)
    artifact_types: List[str] = field(default_factory=list)
    automation_level: str = ""
    enabled: bool = True

    def to_report_dict(self) -> Dict[str, object]:
        return {
            "id": self.action_id,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "inputs": list(self.inputs),
            "preconditions": list(self.preconditions),
            "runner": self.runner,
            "expected_status": self.expected_status,
            "expected_log_fragments": list(self.expected_log_fragments),
            "artifact_types": list(self.artifact_types),
            "automation_level": self.automation_level,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class GuiActionMatrix:
    version: int
    entries: List[GuiActionMatrixEntry] = field(default_factory=list)
    source_path: str = ""

    def categories(self) -> List[str]:
        categories: List[str] = []
        for entry in self.entries:
            if entry.category not in categories:
                categories.append(entry.category)
        return categories

    def entries_by_category(self) -> Dict[str, List[GuiActionMatrixEntry]]:
        grouped: Dict[str, List[GuiActionMatrixEntry]] = {category: [] for category in self.categories()}
        for entry in self.entries:
            grouped.setdefault(entry.category, []).append(entry)
        return grouped

    def enabled_entries(self) -> List[GuiActionMatrixEntry]:
        return [entry for entry in self.entries if entry.enabled]

    def get_by_id(self, action_id: str) -> GuiActionMatrixEntry | None:
        target = str(action_id or "").strip()
        for entry in self.entries:
            if entry.action_id == target:
                return entry
        return None

    def get_by_label(self, label: str) -> GuiActionMatrixEntry | None:
        target = str(label or "").strip()
        for entry in self.entries:
            if entry.label == target:
                return entry
        return None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def gui_action_matrix_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "operations_console" / "gui_action_matrix.yaml"


def load_gui_action_matrix(path: Path | None = None) -> GuiActionMatrix:
    source_path = Path(path) if path is not None else gui_action_matrix_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("GUI action matrix must be a top-level object.")
    version = payload.get("version")
    if not isinstance(version, int):
        raise RuntimeError("GUI action matrix must expose an integer version.")
    rows = payload.get("actions")
    if not isinstance(rows, list):
        raise RuntimeError("GUI action matrix must expose an actions list.")

    entries: List[GuiActionMatrixEntry] = []
    seen_ids: set[str] = set()
    seen_labels: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"GUI action row #{index} must be an object.")
        entry = _validate_entry(row, index=index)
        if entry.action_id in seen_ids:
            raise RuntimeError(f"Duplicate GUI action id: {entry.action_id}")
        if entry.label in seen_labels:
            raise RuntimeError(f"Duplicate GUI action label: {entry.label}")
        seen_ids.add(entry.action_id)
        seen_labels.add(entry.label)
        entries.append(entry)
    return GuiActionMatrix(version=version, entries=entries, source_path=str(source_path))


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse GUI action matrix: {path}") from exc


def _validate_entry(row: dict, *, index: int) -> GuiActionMatrixEntry:
    return GuiActionMatrixEntry(
        action_id=_required_text(row.get("id"), f"actions[{index}].id"),
        label=_required_text(row.get("label"), f"actions[{index}].label"),
        category=_required_text(row.get("category"), f"actions[{index}].category"),
        description=_required_text(row.get("description"), f"actions[{index}].description"),
        inputs=_text_list(row.get("inputs"), field_name=f"actions[{index}].inputs"),
        preconditions=_text_list(row.get("preconditions"), field_name=f"actions[{index}].preconditions"),
        runner=_required_text(row.get("runner"), f"actions[{index}].runner"),
        expected_status=_required_text(row.get("expected_status"), f"actions[{index}].expected_status"),
        expected_log_fragments=_text_list(
            row.get("expected_log_fragments"),
            field_name=f"actions[{index}].expected_log_fragments",
        ),
        artifact_types=_text_list(row.get("artifact_types"), field_name=f"actions[{index}].artifact_types"),
        automation_level=_required_text(row.get("automation_level"), f"actions[{index}].automation_level"),
        enabled=_bool_value(row.get("enabled", True), field_name=f"actions[{index}].enabled"),
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


def _bool_value(value: object, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise RuntimeError(f"{field_name} must be a boolean.")
