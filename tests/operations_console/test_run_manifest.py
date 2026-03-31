from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.operations_console.report_export import report_dict
from tools.operations_console.run_manifest import (
    RunManifestCaptureResult,
    capture_run_manifest,
    manifest_metadata_lines,
)
from tools.operations_console.runner_utils import make_result


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
    )

    manifest = capture_run_manifest(
        result,
        bridge_uri="ws://127.0.0.1:8766",
        manifests_dir=tmp_path,
    )

    assert manifest.written is True
    assert manifest.branch == "main"
    assert manifest.commit == "abc123"
    assert manifest.worktree_status == "clean"
    payload = json.loads(Path(manifest.manifest_path).read_text(encoding="utf-8"))
    assert payload["action_name"] == "ORL / Smoke Suite"
    assert payload["scenario_name"] == "inchon_mvp"
    assert payload["bridge_uri"] == "ws://127.0.0.1:8766"
    assert payload["git"]["branch"] == "main"
    assert payload["git"]["commit"] == "abc123"
    assert payload["git"]["worktree_status"] == "clean"
    assert payload["started_at"] == "2026-03-31T10:00:00+00:00"
    assert payload["finished_at"] == "2026-03-31T10:00:05+00:00"


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
                )
            )
        ],
    )

    payload = report_dict(result)

    assert payload["run_manifest"]["path"] == str(manifest_path)
    assert payload["run_manifest"]["branch"] == "main"
    assert payload["run_manifest"]["commit"] == "abc123"
    assert payload["run_manifest"]["worktree_status"] == "dirty"
    assert payload["run_manifest"]["bridge_uri"] == "ws://127.0.0.1:8766"
    assert payload["run_manifest"]["scenario_name"] == "inchon_mvp"
