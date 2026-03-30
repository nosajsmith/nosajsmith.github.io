from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .models import ConsoleResult


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_export_dir() -> Path:
    return repo_root() / "artifacts" / "operations_console"


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "run"


def report_dict(result: ConsoleResult) -> Dict[str, object]:
    return {
        "name": result.name,
        "status": result.status,
        "summary": result.summary,
        "scenario_name": result.scenario_name,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "duration_ms": result.duration_ms,
        "details": list(result.details),
        "errors": list(result.errors),
        "artifact_paths": list(result.artifact_paths),
        "adapter_method": result.adapter_method,
        "executed_command": list(result.executed_command),
        "return_code": result.return_code,
        "subresults": [report_dict(item) for item in result.subresults],
    }


def _timestamp_for_filename(result: ConsoleResult) -> str:
    source = result.finished_at or result.started_at
    if source:
        text = re.sub(r"[^0-9]", "", source)
        if text:
            return text[:14] or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def export_result_json(result: ConsoleResult, export_dir: Path | None = None) -> Path:
    target_dir = Path(export_dir) if export_dir is not None else default_export_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_timestamp_for_filename(result)}-{slugify(result.name)}.json"
    path.write_text(json.dumps(report_dict(result), indent=2), encoding="utf-8")
    return path


def _format_text_lines(result: ConsoleResult, depth: int = 0) -> List[str]:
    prefix = "  " * depth
    lines = [
        f"{prefix}Name: {result.name}",
        f"{prefix}Status: {result.status.upper()}",
        f"{prefix}Summary: {result.summary}",
    ]
    if result.scenario_name:
        lines.append(f"{prefix}Scenario: {result.scenario_name}")
    if result.started_at:
        lines.append(f"{prefix}Started: {result.started_at}")
    if result.finished_at:
        lines.append(f"{prefix}Finished: {result.finished_at}")
    if result.duration_ms:
        lines.append(f"{prefix}Duration (ms): {result.duration_ms}")
    if result.artifact_paths:
        lines.append(f"{prefix}Artifacts:")
        lines.extend(f"{prefix}- {path}" for path in result.artifact_paths)
    if result.adapter_method:
        lines.append(f"{prefix}Adapter Method: {result.adapter_method}")
    if result.executed_command:
        lines.append(f"{prefix}Executed Command: {' '.join(result.executed_command)}")
    if result.return_code is not None:
        lines.append(f"{prefix}Return Code: {result.return_code}")
    if result.errors:
        lines.append(f"{prefix}Errors:")
        lines.extend(f"{prefix}- {error}" for error in result.errors)
    if result.details:
        lines.append(f"{prefix}Details:")
        lines.extend(f"{prefix}- {line}" for line in result.details)
    if result.subresults:
        lines.append(f"{prefix}Subresults:")
        for item in result.subresults:
            lines.extend(_format_text_lines(item, depth + 1))
    return lines


def export_result_text(result: ConsoleResult, export_dir: Path | None = None) -> Path:
    target_dir = Path(export_dir) if export_dir is not None else default_export_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_timestamp_for_filename(result)}-{slugify(result.name)}.txt"
    path.write_text("\n".join(_format_text_lines(result)) + "\n", encoding="utf-8")
    return path
