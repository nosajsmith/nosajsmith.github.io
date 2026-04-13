from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from . import BAI_WARLAB_VERSION, PROJECT_ROOT
from .config_loader import ConfigLoader
from .models import ManifestRecord, ProfileDocument
from .report_io import write_json


def _sha256_for_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint_path(path: str | Path) -> Dict[str, Any]:
    resolved = Path(path).resolve()
    record: Dict[str, Any] = {
        "source_path": str(resolved),
        "exists": resolved.exists(),
    }
    if resolved.exists() and resolved.is_file():
        record["sha256"] = _sha256_for_path(resolved)
    return record


def _profile_record(doc: ProfileDocument, selector: str) -> Dict[str, Any]:
    record = {
        "selector": selector,
        "name": doc.name,
        "kind": doc.kind,
        "description": doc.description,
    }
    if doc.source_path:
        record.update(_fingerprint_path(doc.source_path))
    return record


def _resolve_profile(loader: ConfigLoader, group: str, selector: str) -> Dict[str, Any]:
    methods = {
        "doctrine": loader.load_doctrine,
        "personality": loader.load_personality,
        "tuning": loader.load_tuning,
    }
    record: Dict[str, Any] = {"selector": selector}
    try:
        doc = methods[group](selector)
    except Exception as exc:
        record["error"] = str(exc)
        return record
    return _profile_record(doc, selector)


def _profile_records(loader: ConfigLoader, group: str, value: Any) -> Any:
    if isinstance(value, list):
        return [_profile_records(loader, group, item) for item in value]
    if isinstance(value, dict):
        return {str(key): _profile_records(loader, group, item) for key, item in value.items()}
    if isinstance(value, str):
        return _resolve_profile(loader, group, value)
    return value


def _iter_runs(result: Any) -> Iterable[Any]:
    if hasattr(result, "summary") and hasattr(result, "scenario"):
        yield result
    for attr in ("runs", "left_runs", "right_runs"):
        for run in getattr(result, attr, []) or []:
            yield run


def _resolved_profile_records(result: Any) -> Any:
    if hasattr(result, "resolved_profile") and dict(getattr(result, "resolved_profile", {}) or {}):
        return dict(getattr(result, "resolved_profile", {}) or {})

    records: Dict[str, Any] = {}
    for index, run in enumerate(_iter_runs(result), start=1):
        profile = dict(getattr(run, "resolved_profile", {}) or {})
        if not profile:
            continue
        key = (
            str(profile.get("variant_id") or "").strip()
            or str(getattr(run, "variant_id", "") or getattr(run, "variant_label", "") or f"run_{index}")
        )
        records[key] = profile
    return records or {}


def _artifact_records(result: Any, output_dir: Path) -> Dict[str, Any]:
    standard = {
        "summary_json": str((output_dir / "summary.json").resolve()),
        "report_txt": str((output_dir / "report.txt").resolve()),
        "results_csv": str((output_dir / "results.csv").resolve()),
        "manifest_json": str((output_dir / "manifest.json").resolve()),
    }
    manifest_refs = [str(getattr(run, "manifest_path", "")).strip() for run in _iter_runs(result)]
    manifest_refs = [item for item in manifest_refs if item]
    artifact_paths = []
    if hasattr(result, "artifacts"):
        artifact_paths.extend(str(item) for item in list(getattr(result, "artifacts", []) or []) if str(item).strip())
    for run in _iter_runs(result):
        artifact_paths.extend(str(item) for item in list(getattr(run, "artifacts", []) or []) if str(item).strip())
    return {
        "bundle": standard,
        "run_manifest_refs": manifest_refs,
        "artifact_paths": sorted(dict.fromkeys(artifact_paths)),
    }


def _scenario_records(result: Any, scenario: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for run in _iter_runs(result):
        summary = dict(getattr(run, "summary", {}) or {})
        run_options = dict(getattr(run, "run_options", {}) or {})
        selector = str(getattr(run, "scenario", "") or "")
        scenario_path = str(summary.get("scenario_path") or run_options.get("scenario_path") or "").strip()
        key = (selector, scenario_path)
        if key in seen:
            continue
        seen.add(key)

        record: Dict[str, Any] = {"selector": selector}
        if summary.get("scenario_id"):
            record["scenario_id"] = summary["scenario_id"]
        if summary.get("scenario_name"):
            record["scenario_name"] = summary["scenario_name"]
        if scenario_path:
            record.update(_fingerprint_path(scenario_path))
        records.append(record)

    if records:
        return records

    if isinstance(scenario, list):
        return [{"selector": str(item)} for item in scenario]
    if isinstance(scenario, dict):
        return [{"selector": str(key), "value": value} for key, value in scenario.items()]
    if scenario is not None:
        return [{"selector": str(scenario)}]
    return []


def build_manifest_record(
    *,
    command: str,
    output_dir: Path,
    scenario: Any,
    doctrine: Any,
    personality: Any,
    tuning: Any,
    seed_policy: Dict[str, Any],
    command_line: str,
    command_argv: List[str],
    config_root: str | Path,
    loader: ConfigLoader,
    result: Any,
) -> ManifestRecord:
    resolved_output_dir = Path(output_dir).resolve()
    resolved_config_root = Path(config_root).resolve()
    return ManifestRecord(
        bai_version=BAI_WARLAB_VERSION,
        command=command,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        scenario=scenario,
        doctrine=doctrine,
        personality=personality,
        tuning=tuning,
        seed_policy=dict(seed_policy),
        command_line=command_line,
        output_dir=str(resolved_output_dir),
        extra={
            "project_root": str(PROJECT_ROOT.resolve()),
            "config_root": str(resolved_config_root),
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "command_argv": list(command_argv),
            "rerun": {
                "cwd": str(PROJECT_ROOT.resolve()),
                "argv": list(command_argv),
                "command_line": command_line,
            },
            "scenario_records": _scenario_records(result, scenario),
            "profile_records": {
                "doctrine": _profile_records(loader, "doctrine", doctrine),
                "personality": _profile_records(loader, "personality", personality),
                "tuning": _profile_records(loader, "tuning", tuning),
            },
            "resolved_profile": _resolved_profile_records(result),
            "artifacts": _artifact_records(result, resolved_output_dir),
        },
    )


def write_manifest(path: str | Path, manifest: ManifestRecord) -> Path:
    return write_json(path, manifest)


__all__ = ["build_manifest_record", "write_manifest"]
