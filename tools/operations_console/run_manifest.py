from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from .models import ConsoleResult
from .runner_utils import iter_results


@dataclass(frozen=True)
class RunManifestCaptureResult:
    written: bool
    manifest_path: str = ""
    branch: str = ""
    commit: str = ""
    worktree_status: str = ""
    bridge_uri: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    working_directory: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_manifest_dir(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "operations_console" / "manifests"


def git_context(repo_root_path: Path | None = None) -> Dict[str, object]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    commit = _run_git(["rev-parse", "HEAD"], cwd=root)
    dirty_output = _run_git(["status", "--porcelain"], cwd=root, allow_empty=True)
    is_dirty = None if dirty_output is None else bool(str(dirty_output).strip())
    worktree_status = "unknown" if is_dirty is None else ("dirty" if is_dirty else "clean")
    return {
        "branch": branch or "",
        "commit": commit or "",
        "is_dirty": is_dirty,
        "worktree_status": worktree_status,
    }


def capture_run_manifest(
    result: ConsoleResult,
    *,
    bridge_uri: str = "",
    manifests_dir: Path | None = None,
    repo_root_path: Path | None = None,
) -> RunManifestCaptureResult:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    target_dir = Path(manifests_dir) if manifests_dir is not None else default_manifest_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    started_at = str(result.started_at or "").strip() or created_at
    finished_at = str(result.finished_at or "").strip() or created_at
    git = git_context(root)
    incident_metadata = _incident_metadata_from_details(result.details)
    payload = {
        "version": 1,
        "created_at": created_at,
        "action_name": result.name,
        "status": result.status,
        "original_status": result.original_status,
        "summary": result.summary,
        "scenario_name": result.scenario_name,
        "bridge_uri": str(bridge_uri or "").strip(),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": result.duration_ms,
        "working_directory": str(root),
        "artifact_paths": list(result.artifact_paths),
        "executed_command": list(result.executed_command),
        "return_code": result.return_code,
        "adapter_method": result.adapter_method,
        "known_issue_matches": _known_issue_rows(result),
        "incident_metadata": incident_metadata,
        "git": git,
    }
    filename = f"{_timestamp_for_filename(finished_at)}-{_slugify(result.name)}-manifest.json"
    manifest_path = target_dir / filename
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return RunManifestCaptureResult(
        written=True,
        manifest_path=str(manifest_path),
        branch=str(git.get("branch") or "").strip(),
        commit=str(git.get("commit") or "").strip(),
        worktree_status=str(git.get("worktree_status") or "").strip(),
        bridge_uri=str(bridge_uri or "").strip(),
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=result.duration_ms,
        working_directory=str(root),
    )


def manifest_metadata_lines(manifest: RunManifestCaptureResult | None) -> List[str]:
    if manifest is None or not manifest.written:
        return []
    lines = [
        f"RUN MANIFEST: {manifest.manifest_path}",
        f"RUN BRANCH: {manifest.branch}",
        f"RUN COMMIT: {manifest.commit}",
        f"RUN WORKTREE: {manifest.worktree_status}",
    ]
    if manifest.working_directory:
        lines.append(f"RUN CWD: {manifest.working_directory}")
    if manifest.duration_ms:
        lines.append(f"RUN DURATION MS: {manifest.duration_ms}")
    if manifest.bridge_uri:
        lines.append(f"RUN BRIDGE URI: {manifest.bridge_uri}")
    return lines


def parse_run_manifest_metadata(details: Iterable[str]) -> Dict[str, object] | None:
    metadata: Dict[str, object] = {
        "path": "",
        "branch": "",
        "commit": "",
        "worktree_status": "",
        "working_directory": "",
        "duration_ms": 0,
        "bridge_uri": "",
    }
    for line in list(details or []):
        text = str(line or "").strip()
        if not text:
            continue
        if text.startswith("RUN MANIFEST: "):
            metadata["path"] = text.partition(": ")[2].strip()
        elif text.startswith("RUN BRANCH: "):
            metadata["branch"] = text.partition(": ")[2].strip()
        elif text.startswith("RUN COMMIT: "):
            metadata["commit"] = text.partition(": ")[2].strip()
        elif text.startswith("RUN WORKTREE: "):
            metadata["worktree_status"] = text.partition(": ")[2].strip()
        elif text.startswith("RUN CWD: "):
            metadata["working_directory"] = text.partition(": ")[2].strip()
        elif text.startswith("RUN DURATION MS: "):
            value = text.partition(": ")[2].strip()
            metadata["duration_ms"] = int(value) if value.isdigit() else 0
        elif text.startswith("RUN BRIDGE URI: "):
            metadata["bridge_uri"] = text.partition(": ")[2].strip()
    if not any(str(value or "").strip() for value in metadata.values()):
        return None
    return metadata


def _timestamp_for_filename(value: str) -> str:
    text = re.sub(r"[^0-9]", "", str(value or "").strip())
    if text:
        return text[:14]
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "run"


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


def _known_issue_rows(result: ConsoleResult) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in iter_results(result):
        for match in item.known_issue_matches:
            rows.append(
                {
                    "id": match.issue_id,
                    "title": match.title,
                    "severity": match.severity,
                    "category": match.category,
                    "status": match.status,
                    "expected_status_override": match.expected_status_override,
                    "notes": match.notes,
                    "result_name": item.name,
                    "scenario_name": item.scenario_name or result.scenario_name,
                }
            )
    return rows


def _incident_metadata_from_details(details: Iterable[str]) -> Dict[str, str] | None:
    metadata = {
        "bundle_dir": "",
        "incident_json_path": "",
        "run_report_json_path": "",
    }
    for line in list(details or []):
        text = str(line or "").strip()
        if not text:
            continue
        if text.startswith("INCIDENT BUNDLE: "):
            metadata["bundle_dir"] = text.partition(": ")[2].strip()
        elif text.startswith("INCIDENT MANIFEST: "):
            metadata["incident_json_path"] = text.partition(": ")[2].strip()
        elif text.startswith("INCIDENT RUN REPORT: "):
            metadata["run_report_json_path"] = text.partition(": ")[2].strip()
    if not any(metadata.values()):
        return None
    return metadata
