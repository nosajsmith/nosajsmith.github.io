from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from . import ARTIFACT_ROOT
from .models import to_plain


def slugify(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "default"


def stable_hash(parts: Iterable[Any]) -> str:
    joined = "|".join(str(part) for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:10]


def default_output_dir(command: str, label_parts: Iterable[Any], override: str | None = None) -> Path:
    if override:
        return Path(override).resolve()
    parts = [slugify(str(part)) for part in label_parts if str(part).strip()]
    return (ARTIFACT_ROOT / slugify(command)).joinpath(*parts).resolve()


def ensure_output_dir(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: str | Path, payload: Any) -> Path:
    output = Path(path)
    output.write_text(json.dumps(to_plain(payload), indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return output


def _scalar_csv_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(to_plain(value), sort_keys=True)


def flatten_mapping(mapping: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for key, value in mapping.items():
        field = f"{prefix}_{key}" if prefix else str(key)
        if isinstance(value, dict):
            row.update(flatten_mapping(value, field))
        else:
            row[field] = _scalar_csv_value(value)
    return row


def run_result_to_row(run_result: Any) -> Dict[str, Any]:
    row = {
        "command": getattr(run_result, "command", "run"),
        "ok": bool(getattr(run_result, "ok", False)),
        "scenario": getattr(run_result, "scenario", ""),
        "scenario_dir": getattr(run_result, "scenario_dir", ""),
        "doctrine": getattr(run_result, "doctrine", ""),
        "personality": getattr(run_result, "personality", ""),
        "tuning": getattr(run_result, "tuning", ""),
        "seed": getattr(run_result, "seed", ""),
        "variant_label": getattr(run_result, "variant_label", ""),
        "error": getattr(run_result, "error", "") or "",
    }
    row.update(flatten_mapping(dict(getattr(run_result, "summary", {}) or {}), "summary"))
    row.update(flatten_mapping(dict(getattr(run_result, "metrics", {}) or {}), "metrics"))
    row.update(flatten_mapping(dict(getattr(run_result, "ai_report", {}) or {}), "ai_report"))
    return row


def write_results_csv(path: str | Path, rows: List[Dict[str, Any]]) -> Path:
    output = Path(path)
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _scalar_csv_value(value) for key, value in row.items()})
    return output


def write_report_txt(path: str | Path, content: str) -> Path:
    output = Path(path)
    output.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output
