from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import ALLOWED_STATUSES, ConsoleResult, KnownIssueMatch

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
MATCHABLE_STATUSES = {"warn", "fail", "error"}
OVERRIDABLE_STATUSES = tuple(status for status in ALLOWED_STATUSES if status not in {"idle", "running"})


@dataclass(frozen=True)
class KnownIssue:
    issue_id: str
    title: str
    severity: str
    category: str
    affects: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    status: str = ""
    expected_status_override: str = ""
    symptom_match: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class KnownIssuesCatalog:
    issues: List[KnownIssue] = field(default_factory=list)
    source_path: str = ""

    def match_result(
        self,
        result: ConsoleResult,
        *,
        entry_name: str = "",
        scenario_name: str = "",
        observed_lines: Sequence[str] | None = None,
    ) -> List[KnownIssueMatch]:
        status = str(result.status or "").strip().lower()
        if status not in MATCHABLE_STATUSES:
            return []

        name = str(entry_name or result.name or "").strip()
        scenario = str(scenario_name or result.scenario_name or "").strip()
        text_fragments = _result_text_fragments(result, observed_lines=observed_lines)
        matches: List[KnownIssueMatch] = []
        for issue in self.issues:
            if not _issue_matches(issue, name=name, scenario=scenario, text_fragments=text_fragments):
                continue
            matches.append(
                KnownIssueMatch(
                    issue_id=issue.issue_id,
                    title=issue.title,
                    severity=issue.severity,
                    category=issue.category,
                    status=issue.status,
                    expected_status_override=issue.expected_status_override,
                    notes=issue.notes,
                )
            )
        return matches

    def annotate_result(
        self,
        result: ConsoleResult,
        *,
        entry_name: str = "",
        scenario_name: str = "",
        observed_lines: Sequence[str] | None = None,
    ) -> ConsoleResult:
        matches = self.match_result(
            result,
            entry_name=entry_name,
            scenario_name=scenario_name,
            observed_lines=observed_lines,
        )
        if not matches:
            return result

        override = _resolved_override(result.status, matches)
        if not override:
            return replace(result, known_issue_matches=matches)
        return replace(
            result,
            status=override,
            original_status=result.status,
            known_issue_matches=matches,
        )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_known_issues_path() -> Path:
    return repo_root() / "tools" / "operations_console" / "known_issues.yaml"


def load_known_issues(path: Path | None = None) -> KnownIssuesCatalog:
    source_path = Path(path) if path is not None else default_known_issues_path()
    payload = _load_payload(source_path)
    issues_raw = _extract_issue_rows(payload)
    issues: List[KnownIssue] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(issues_raw, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"Known issue row #{index} must be an object.")
        issue = _validate_issue_row(row, index=index)
        if issue.issue_id in seen_ids:
            raise RuntimeError(f"Duplicate known issue id: {issue.issue_id}")
        seen_ids.add(issue.issue_id)
        issues.append(issue)
    return KnownIssuesCatalog(issues=issues, source_path=str(source_path))


def apply_known_issues(
    result: ConsoleResult,
    known_issues: KnownIssuesCatalog | None,
    *,
    entry_name: str = "",
    scenario_name: str = "",
    observed_lines: Sequence[str] | None = None,
) -> ConsoleResult:
    if known_issues is None:
        return result
    return known_issues.annotate_result(
        result,
        entry_name=entry_name,
        scenario_name=scenario_name,
        observed_lines=observed_lines,
    )


def summarize_known_issues(catalog: KnownIssuesCatalog | None = None) -> dict:
    loaded = catalog or load_known_issues()
    rows = [
        {
            "id": issue.issue_id,
            "title": issue.title,
            "severity": issue.severity,
            "category": issue.category,
            "status": issue.status,
            "expected_status_override": issue.expected_status_override,
            "affects": list(issue.affects),
            "scenarios": list(issue.scenarios),
            "symptom_match": list(issue.symptom_match),
            "notes": issue.notes,
        }
        for issue in loaded.issues
    ]
    status_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"] or "").strip().lower()
        severity = str(row["severity"] or "").strip().lower()
        status_counts[status] = status_counts.get(status, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "source_path": loaded.source_path,
        "issue_count": len(rows),
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "rows": rows,
    }


def _load_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
        if payload is not None:
            return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse known issues file: {path}") from exc


def _extract_issue_rows(payload: object) -> List[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get("known_issues", payload.get("issues"))
        if isinstance(rows, list):
            return rows
    raise RuntimeError("Known issues file must contain a known_issues list.")


def _validate_issue_row(row: dict, *, index: int) -> KnownIssue:
    issue_id = _required_text(row.get("id"), f"known_issues[{index}].id")
    title = _required_text(row.get("title"), f"known_issues[{index}].title")
    severity = _required_text(row.get("severity"), f"known_issues[{index}].severity")
    category = _required_text(row.get("category"), f"known_issues[{index}].category")
    status = _required_text(row.get("status"), f"known_issues[{index}].status").lower()
    expected_status_override = _optional_text(row.get("expected_status_override")).lower()
    if expected_status_override and expected_status_override not in OVERRIDABLE_STATUSES:
        raise RuntimeError(
            f"known_issues[{index}].expected_status_override must be one of {', '.join(OVERRIDABLE_STATUSES)}"
        )
    return KnownIssue(
        issue_id=issue_id,
        title=title,
        severity=severity,
        category=category,
        affects=_text_list(row.get("affects"), field_name=f"known_issues[{index}].affects"),
        scenarios=_text_list(row.get("scenarios"), field_name=f"known_issues[{index}].scenarios"),
        status=status,
        expected_status_override=expected_status_override,
        symptom_match=_text_list(row.get("symptom_match"), field_name=f"known_issues[{index}].symptom_match"),
        notes=_optional_text(row.get("notes")),
    )


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{field_name} is required.")
    return text


def _optional_text(value: object) -> str:
    return str(value or "").strip()


def _text_list(value: object, *, field_name: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        raise RuntimeError(f"{field_name} must be a string or list of strings.")
    items: List[str] = []
    for index, item in enumerate(value, start=1):
        text = str(item or "").strip()
        if not text:
            raise RuntimeError(f"{field_name}[{index}] must be a non-empty string.")
        items.append(text)
    return items


def _result_text_fragments(result: ConsoleResult, *, observed_lines: Sequence[str] | None = None) -> List[str]:
    lines = [
        str(result.summary or "").strip(),
        *[str(item or "").strip() for item in result.errors],
        *[str(item or "").strip() for item in result.details],
        *[str(item or "").strip() for item in list(observed_lines or [])],
    ]
    return [line for line in lines if line]


def _issue_matches(
    issue: KnownIssue,
    *,
    name: str,
    scenario: str,
    text_fragments: Iterable[str],
) -> bool:
    if issue.affects and not _matches_any_pattern(name, issue.affects, allow_stem=False):
        return False
    if issue.scenarios and not _matches_any_pattern(scenario, issue.scenarios, allow_stem=True):
        return False
    if issue.symptom_match and not _match_any_fragment(text_fragments, issue.symptom_match):
        return False
    return True


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


def _match_any_fragment(text_fragments: Iterable[str], fragments: Sequence[str]) -> bool:
    haystacks = [str(fragment or "").strip().lower() for fragment in text_fragments if str(fragment or "").strip()]
    for fragment in fragments:
        needle = str(fragment or "").strip().lower()
        if not needle:
            continue
        if any(needle in haystack for haystack in haystacks):
            return True
    return False


def _resolved_override(current_status: str, matches: Sequence[KnownIssueMatch]) -> str:
    if not matches:
        return ""
    overrides = [match.expected_status_override for match in matches if match.expected_status_override]
    if not overrides or len(overrides) != len(matches):
        return ""
    normalized = [str(status).strip().lower() for status in overrides]
    current = str(current_status or "").strip().lower()
    if current not in STATUS_ORDER:
        return ""
    target = max(normalized, key=lambda status: STATUS_ORDER.get(status, -1))
    if STATUS_ORDER.get(target, -1) >= STATUS_ORDER[current]:
        return ""
    return target
