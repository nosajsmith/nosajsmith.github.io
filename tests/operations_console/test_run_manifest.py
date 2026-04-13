from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.operations_console.models import KnownIssueMatch
from tools.operations_console.report_export import report_dict
from tools.operations_console.run_manifest import (
    RunManifestCaptureResult,
    capture_run_manifest,
    default_manifest_dir,
    manifest_metadata_lines,
)
from tools.operations_console.runner_utils import make_result


def test_default_manifest_dir_uses_repo_local_manifests_path(tmp_path) -> None:
    assert default_manifest_dir(tmp_path) == tmp_path / "artifacts" / "operations_console" / "manifests"


def test_capture_run_manifest_writes_expected_context(tmp_path, monkeypatch) -> None:
    def fake_run(args, cwd=None, capture_output=None, text=None, check=None):
        if args[1:] == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="main\n", stderr="")
        if args[1:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc123\n", stderr="")
        if args[1:] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr("tools.operations_console.run_manifest.subprocess.run", fake_run)
    result = make_result(
        name="ORL / Smoke Suite",
        status="pass",
        summary="smoke ok",
        scenario_name="inchon_mvp",
        started_at="2026-03-31T10:00:00+00:00",
        finished_at="2026-03-31T10:00:05+00:00",
        details=[
            "INCIDENT BUNDLE: /tmp/incidents/smoke",
            "INCIDENT MANIFEST: /tmp/incidents/smoke/incident.json",
        ],
        known_issue_matches=[
            KnownIssueMatch(
                issue_id="KI-777",
                title="Known smoke waiver",
                severity="medium",
                category="ORL",
                status="waived",
                expected_status_override="warn",
                notes="Temporary smoke waiver.",
            )
        ],
    )

    manifest = capture_run_manifest(
        result,
        bridge_uri="ws://127.0.0.1:8766",
        manifests_dir=tmp_path,
        repo_root_path=tmp_path,
    )

    assert manifest.written is True
    assert manifest.branch == "main"
    assert manifest.commit == "abc123"
    assert manifest.worktree_status == "clean"
    assert manifest.duration_ms == 0
    assert manifest.working_directory == str(tmp_path.resolve())
    payload = json.loads(Path(manifest.manifest_path).read_text(encoding="utf-8"))
    assert Path(manifest.manifest_path).name == "20260331100005-orl-smoke-suite-manifest.json"
    assert payload["action_name"] == "ORL / Smoke Suite"
    assert payload["scenario_name"] == "inchon_mvp"
    assert payload["bridge_uri"] == "ws://127.0.0.1:8766"
    assert payload["working_directory"] == str(Path(manifest.working_directory))
    assert payload["git"]["branch"] == "main"
    assert payload["git"]["commit"] == "abc123"
    assert payload["git"]["worktree_status"] == "clean"
    assert payload["started_at"] == "2026-03-31T10:00:00+00:00"
    assert payload["finished_at"] == "2026-03-31T10:00:05+00:00"
    assert payload["known_issue_matches"][0]["id"] == "KI-777"
    assert payload["incident_metadata"]["bundle_dir"] == "/tmp/incidents/smoke"
    assert payload["incident_metadata"]["incident_json_path"] == "/tmp/incidents/smoke/incident.json"


def test_capture_run_manifest_handles_unavailable_git_context(tmp_path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise OSError("git missing")

    monkeypatch.setattr("tools.operations_console.run_manifest.subprocess.run", fake_run)
    result = make_result(
        name="ORL / Core Validation Suite",
        status="fail",
        summary="core failed",
        finished_at="2026-03-31T11:00:05+00:00",
    )

    manifest = capture_run_manifest(result, manifests_dir=tmp_path, repo_root_path=tmp_path)

    payload = json.loads(Path(manifest.manifest_path).read_text(encoding="utf-8"))
    assert manifest.branch == ""
    assert manifest.commit == ""
    assert manifest.worktree_status == "unknown"
    assert payload["git"]["branch"] == ""
    assert payload["git"]["commit"] == ""
    assert payload["git"]["worktree_status"] == "unknown"


def test_report_dict_surfaces_run_manifest_metadata(tmp_path) -> None:
    manifest_path = tmp_path / "run-manifest.json"
    result = make_result(
        name="ORL / UI Build Check",
        status="pass",
        summary="build ok",
        scenario_name="inchon_mvp",
        started_at="2026-03-31T10:00:00+00:00",
        finished_at="2026-03-31T10:00:05+00:00",
        details=[
            *manifest_metadata_lines(
                RunManifestCaptureResult(
                    written=True,
                    manifest_path=str(manifest_path),
                    branch="main",
                    commit="abc123",
                    worktree_status="dirty",
                    bridge_uri="ws://127.0.0.1:8766",
                    duration_ms=5000,
                    working_directory=str(tmp_path),
                )
            )
        ],
    )

    payload = report_dict(result)

    assert payload["run_manifest"]["path"] == str(manifest_path)
    assert payload["run_manifest"]["branch"] == "main"
    assert payload["run_manifest"]["commit"] == "abc123"
    assert payload["run_manifest"]["worktree_status"] == "dirty"
    assert payload["run_manifest"]["working_directory"] == str(tmp_path)
    assert payload["run_manifest"]["duration_ms"] == 5000
    assert payload["run_manifest"]["bridge_uri"] == "ws://127.0.0.1:8766"
    assert payload["run_manifest"]["scenario_name"] == "inchon_mvp"
