from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from engine.testing_api import EngineTestingAPI
from tools.operations_console.known_issues import load_known_issues, summarize_known_issues
from tools.operations_console.report_export import slugify
from tools.orl.readiness import load_demo_checklist, load_round1_manifest


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def pitch_support_docs_root(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "docs" / "pitch_support"


def pitch_support_artifact_root(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "pitch_support"


def export_pitch_support_bundle(
    *,
    scenario_name: str = "",
    repo_root_path: Path | None = None,
) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    checklist = load_demo_checklist(root / "tools" / "orl" / "demo_checklist.yaml")
    selected_scenario = str(scenario_name or checklist.default_scenario).strip()
    target_root = pitch_support_artifact_root(root)
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle_dir = target_root / f"{stamp}-pitch-support-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    checks: List[Dict[str, Any]] = []
    artifacts: List[str] = []
    logs: List[str] = [f"selected scenario: {selected_scenario}", f"bundle_dir: {bundle_dir}"]

    demo_report = _latest_console_report(root, "orl-demo-readiness")
    core_report = _latest_console_report(root, "orl-core-validation-suite")
    copied_reports_dir = bundle_dir / "reports"

    checks.append(_report_copy_check("Latest ORL Demo Readiness Report", demo_report, copied_reports_dir, artifacts, logs))
    checks.append(_report_copy_check("Latest Core Validation Report", core_report, copied_reports_dir, artifacts, logs))

    known_issues_summary = summarize_known_issues(load_known_issues(root / "tools" / "operations_console" / "known_issues.yaml"))
    known_issues_json = _write_json(bundle_dir / "known_issues_summary.json", known_issues_summary)
    known_issues_md = _write_text(bundle_dir / "known_issues_summary.md", _known_issues_markdown(known_issues_summary))
    artifacts.extend([str(known_issues_json), str(known_issues_md)])
    checks.append(
        _component_check(
            "Known Issues Summary",
            status="pass",
            summary=f"{known_issues_summary['issue_count']} known issue(s) summarized.",
            artifact_paths=[str(known_issues_json), str(known_issues_md)],
            logs=[f"source: {known_issues_summary['source_path']}"],
        )
    )

    scenario_fact_sheet = build_scenario_fact_sheet(selected_scenario, repo_root_path=root)
    scenario_fact_json = _write_json(bundle_dir / "scenario_fact_sheet.json", scenario_fact_sheet)
    scenario_fact_md = _write_text(bundle_dir / "scenario_fact_sheet.md", _scenario_fact_markdown(scenario_fact_sheet))
    artifacts.extend([str(scenario_fact_json), str(scenario_fact_md)])
    checks.append(
        _component_check(
            "Scenario Fact Sheet",
            status="pass" if scenario_fact_sheet.get("scenario_id") else "fail",
            summary=f"Scenario fact sheet generated for {selected_scenario}.",
            artifact_paths=[str(scenario_fact_json), str(scenario_fact_md)],
            logs=[f"scenario_id: {scenario_fact_sheet.get('scenario_id') or '<missing>'}"],
        )
    )

    expected_outcomes = build_expected_outcomes_summary(selected_scenario, repo_root_path=root)
    expected_outcomes_json = _write_json(bundle_dir / "expected_outcomes_summary.json", expected_outcomes)
    expected_outcomes_md = _write_text(bundle_dir / "expected_outcomes_summary.md", _expected_outcomes_markdown(expected_outcomes))
    artifacts.extend([str(expected_outcomes_json), str(expected_outcomes_md)])
    checks.append(
        _component_check(
            "Expected Outcomes Summary",
            status="pass" if expected_outcomes.get("combined_expected_outcomes") else "fail",
            summary=f"{len(expected_outcomes.get('combined_expected_outcomes') or [])} expected outcome(s) captured.",
            artifact_paths=[str(expected_outcomes_json), str(expected_outcomes_md)],
            logs=[f"scenario: {selected_scenario}"],
        )
    )

    artifact_directory_summary = build_artifact_directory_summary(repo_root_path=root)
    artifact_summary_json = _write_json(bundle_dir / "artifact_directory_summary.json", artifact_directory_summary)
    artifact_summary_md = _write_text(bundle_dir / "artifact_directory_summary.md", _artifact_directory_markdown(artifact_directory_summary))
    artifacts.extend([str(artifact_summary_json), str(artifact_summary_md)])
    checks.append(
        _component_check(
            "Artifact Directory Summary",
            status="pass",
            summary=f"{len(artifact_directory_summary.get('directories') or [])} artifact directory summaries written.",
            artifact_paths=[str(artifact_summary_json), str(artifact_summary_md)],
        )
    )

    copied_docs = _copy_static_docs(root, bundle_dir / "docs", logs)
    artifacts.extend(copied_docs)
    checks.append(
        _component_check(
            "Pitch Support Runbook",
            status="pass" if any(path.endswith("README.md") for path in copied_docs) else "fail",
            summary="Pitch support runbook copied into the bundle.",
            artifact_paths=[path for path in copied_docs if path.endswith("README.md")],
            logs=[f"docs root: {pitch_support_docs_root(root)}"],
        )
    )
    checks.append(
        _component_check(
            "Architecture Support Note",
            status="pass" if any(path.endswith("architecture_support_note.md") for path in copied_docs) else "fail",
            summary="Architecture/support note copied into the bundle.",
            artifact_paths=[path for path in copied_docs if path.endswith("architecture_support_note.md")],
            logs=[f"docs root: {pitch_support_docs_root(root)}"],
        )
    )

    bundle_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(bundle_dir),
        "selected_scenario": selected_scenario,
        "checks": checks,
        "source_reports": {
            "demo_readiness": demo_report,
            "core_validation": core_report,
        },
        "artifacts": artifacts,
    }
    manifest_path = _write_json(bundle_dir / "bundle_manifest.json", bundle_manifest)
    readme_path = _write_text(bundle_dir / "README.md", _bundle_readme(bundle_manifest))
    artifacts.extend([str(manifest_path), str(readme_path)])

    latest_manifest = {
        "bundle_dir": str(bundle_dir),
        "selected_scenario": selected_scenario,
        "manifest_path": str(manifest_path),
        "created_at": bundle_manifest["created_at"],
    }
    _write_json(target_root / "latest.json", latest_manifest)

    failure_count = sum(1 for check in checks if check.get("status") != "pass")
    logs.append(f"artifact: {manifest_path}")
    return {
        "ok": failure_count == 0,
        "status": "pass" if failure_count == 0 else "fail",
        "summary": "Pitch support bundle exported." if failure_count == 0 else "Pitch support bundle exported with missing components.",
        "checks": checks,
        "artifact_paths": artifacts,
        "bundle_dir": str(bundle_dir),
        "logs": logs,
        "selected_scenario": selected_scenario,
    }


def build_scenario_fact_sheet(scenario_name: str, *, repo_root_path: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    api = EngineTestingAPI(repo_root=root)
    entry = api._resolve_scenario_entry(scenario_name)
    payload = api._read_scenario_payload(entry) if entry is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    status_result = api.campaign_status(scenario_name)
    explain_result = api.campaign_explain(scenario_name)

    objectives = list(explain_result.data.get("objectives") or [item.get("name") for item in list(payload.get("objectives") or []) if isinstance(item, dict)])
    alerts = list(explain_result.data.get("alerts") or list((payload.get("grease_board") or {}).get("alerts") or []))
    orders = list(explain_result.data.get("orders") or list((payload.get("grease_board") or {}).get("orders") or []))
    return {
        "scenario_id": str(status_result.data.get("scenario_id") or payload.get("id") or "").strip(),
        "display_name": str(status_result.data.get("display_name") or payload.get("name") or "").strip(),
        "description": str(explain_result.data.get("description") or payload.get("description") or "").strip(),
        "unit_count": int(status_result.data.get("unit_count") or len(payload.get("units") or []) or 0),
        "objective_count": int(status_result.data.get("objective_count") or len(payload.get("objectives") or []) or 0),
        "turn": str(status_result.data.get("turn") or (payload.get("grease_board") or {}).get("turn") or "").strip(),
        "objective_focus": str(status_result.data.get("objective") or (payload.get("grease_board") or {}).get("objective") or "").strip(),
        "front_status": str(status_result.data.get("front_status") or (payload.get("grease_board") or {}).get("front_status") or "").strip(),
        "supply_status": str(status_result.data.get("supply_status") or (payload.get("grease_board") or {}).get("supply_status") or "").strip(),
        "main_effort": str(status_result.data.get("main_effort") or (payload.get("grease_board") or {}).get("main_effort") or "").strip(),
        "staff_notes": str(explain_result.data.get("staff_notes") or (payload.get("grease_board") or {}).get("staff_notes") or "").strip(),
        "objectives": [str(item or "").strip() for item in objectives if str(item or "").strip()],
        "alerts": [str(item or "").strip() for item in alerts if str(item or "").strip()],
        "orders": [str(item or "").strip() for item in orders if str(item or "").strip()],
        "sources": {
            "bridge_listed": bool(entry and entry.get("bridge_listed")),
            "engine_loadable": bool(entry and entry.get("engine_loadable")),
            "payload_paths": list((entry or {}).get("payload_paths") or []),
        },
    }


def build_expected_outcomes_summary(scenario_name: str, *, repo_root_path: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    checklist = load_demo_checklist(root / "tools" / "orl" / "demo_checklist.yaml")
    manifest = load_round1_manifest(root / "tools" / "orl" / "round1_manifest.yaml")
    primary = next((item for item in manifest.primary_scenarios if item.scenario_id == scenario_name), None)
    combined: List[str] = []
    for value in [
        *(checklist.expected_outcomes.get(scenario_name) or []),
        *([*primary.expected_outcomes] if primary is not None else []),
        *(manifest.expected_outcomes.get(scenario_name) or []),
    ]:
        text = str(value or "").strip()
        if text and text not in combined:
            combined.append(text)
    return {
        "scenario_id": scenario_name,
        "demo_expected_outcomes": list(checklist.expected_outcomes.get(scenario_name) or []),
        "manifest_expected_outcomes": list(manifest.expected_outcomes.get(scenario_name) or []),
        "primary_scenario_label": primary.label if primary is not None else "",
        "primary_scenario_notes": primary.notes if primary is not None else "",
        "primary_scenario_expected_outcomes": list(primary.expected_outcomes) if primary is not None else [],
        "combined_expected_outcomes": combined,
    }


def build_artifact_directory_summary(*, repo_root_path: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    directories = [
        ("operations_console", root / "artifacts" / "operations_console"),
        ("orl", root / "artifacts" / "orl"),
        ("engine_adapter_replays", root / "artifacts" / "operations_console" / "engine_adapter" / "replays"),
        ("engine_adapter_snapshots", root / "artifacts" / "operations_console" / "engine_adapter" / "snapshots"),
        ("engine_adapter_compares", root / "artifacts" / "operations_console" / "engine_adapter" / "compares"),
        ("pitch_support", root / "artifacts" / "pitch_support"),
    ]
    rows = []
    for label, directory in directories:
        files = [path for path in directory.rglob("*") if path.is_file()] if directory.exists() else []
        latest = max(files, key=lambda path: (path.stat().st_mtime, path.name)) if files else None
        rows.append(
            {
                "label": label,
                "path": str(directory),
                "exists": directory.exists(),
                "file_count": len(files),
                "latest_file": str(latest) if latest is not None else "",
                "latest_modified_at": datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).isoformat()
                if latest is not None
                else "",
            }
        )
    return {"directories": rows}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    command = args[0] if args else "export"
    scenario_name = args[1] if len(args) > 1 else ""
    if command != "export":
        print(json.dumps({"ok": False, "error": f"Unsupported command: {command}", "supported": ["export"]}, indent=2))
        return 1
    report = export_pitch_support_bundle(scenario_name=scenario_name)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


def _latest_console_report(root: Path, slug: str) -> Dict[str, str]:
    operations_root = root / "artifacts" / "operations_console"
    stems: Dict[str, float] = {}
    for path in operations_root.glob(f"*-{slug}.*"):
        if not path.is_file() or path.suffix not in {".json", ".txt"}:
            continue
        stems[str(path.with_suffix(""))] = max(stems.get(str(path.with_suffix("")), 0.0), path.stat().st_mtime)
    if not stems:
        return {"json_path": "", "text_path": ""}
    latest_stem = max(stems.items(), key=lambda item: (item[1], item[0]))[0]
    json_path = Path(f"{latest_stem}.json")
    text_path = Path(f"{latest_stem}.txt")
    return {
        "json_path": str(json_path) if json_path.exists() else "",
        "text_path": str(text_path) if text_path.exists() else "",
    }


def _report_copy_check(
    label: str,
    report_paths: Dict[str, str],
    target_dir: Path,
    artifacts: List[str],
    logs: List[str],
) -> Dict[str, Any]:
    source_json = Path(str(report_paths.get("json_path") or "").strip()) if report_paths.get("json_path") else None
    source_text = Path(str(report_paths.get("text_path") or "").strip()) if report_paths.get("text_path") else None
    copied: List[str] = []
    if source_json is not None and source_json.exists():
        copied.append(_copy_file(source_json, target_dir / source_json.name))
    if source_text is not None and source_text.exists():
        copied.append(_copy_file(source_text, target_dir / source_text.name))
    artifacts.extend(copied)
    if copied:
        logs.append(f"{slugify(label)}: copied {len(copied)} file(s)")
        return _component_check(label, status="pass", summary=f"{label} copied into the bundle.", artifact_paths=copied)
    logs.append(f"{slugify(label)}: missing")
    return _component_check(label, status="fail", summary=f"{label} is missing.", logs=["Run the corresponding console suite and export the report."])


def _copy_static_docs(root: Path, target_dir: Path, logs: List[str]) -> List[str]:
    docs_root = pitch_support_docs_root(root)
    copied: List[str] = []
    for path in sorted(docs_root.glob("*.md")):
        copied.append(_copy_file(path, target_dir / path.name))
    logs.append(f"copied docs: {len(copied)}")
    return copied


def _component_check(
    label: str,
    *,
    status: str,
    summary: str,
    artifact_paths: Iterable[str] | None = None,
    logs: Iterable[str] | None = None,
) -> Dict[str, Any]:
    return {
        "check_id": slugify(label),
        "label": label,
        "blocker_class": "support.pitch_support_bundle",
        "status": status,
        "summary": summary,
        "artifacts": list(artifact_paths or []),
        "logs": list(logs or []),
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def _copy_file(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)


def _latest_matching_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists() or not directory.is_dir():
        return None
    matches = [path for path in directory.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime, path.name))


def _known_issues_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Known Issues Summary",
        "",
        f"Source: `{summary.get('source_path')}`",
        f"Issue Count: {summary.get('issue_count', 0)}",
        "",
    ]
    for row in list(summary.get("rows") or []):
        lines.extend(
            [
                f"## {row['id']} — {row['title']}",
                "",
                f"- Severity: {row['severity']}",
                f"- Status: {row['status']}",
                f"- Category: {row['category']}",
                f"- Affects: {', '.join(row['affects']) if row['affects'] else '<all>'}",
                f"- Scenarios: {', '.join(row['scenarios']) if row['scenarios'] else '<all>'}",
                f"- Notes: {row['notes'] or '<none>'}",
                "",
            ]
        )
    return "\n".join(lines)


def _scenario_fact_markdown(fact_sheet: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Scenario Fact Sheet",
            "",
            f"- Scenario Id: {fact_sheet.get('scenario_id') or '<missing>'}",
            f"- Display Name: {fact_sheet.get('display_name') or '<missing>'}",
            f"- Description: {fact_sheet.get('description') or '<missing>'}",
            f"- Unit Count: {fact_sheet.get('unit_count', 0)}",
            f"- Objective Count: {fact_sheet.get('objective_count', 0)}",
            f"- Turn: {fact_sheet.get('turn') or '<missing>'}",
            f"- Objective Focus: {fact_sheet.get('objective_focus') or '<missing>'}",
            f"- Front Status: {fact_sheet.get('front_status') or '<missing>'}",
            f"- Supply Status: {fact_sheet.get('supply_status') or '<missing>'}",
            f"- Main Effort: {fact_sheet.get('main_effort') or '<missing>'}",
            f"- Staff Notes: {fact_sheet.get('staff_notes') or '<missing>'}",
            f"- Objectives: {', '.join(fact_sheet.get('objectives') or []) or '<none>'}",
            f"- Alerts: {', '.join(fact_sheet.get('alerts') or []) or '<none>'}",
            f"- Orders: {', '.join(fact_sheet.get('orders') or []) or '<none>'}",
        ]
    )


def _expected_outcomes_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Expected Outcomes Summary",
        "",
        f"- Scenario: {summary.get('scenario_id') or '<missing>'}",
        f"- Primary Label: {summary.get('primary_scenario_label') or '<none>'}",
        f"- Primary Notes: {summary.get('primary_scenario_notes') or '<none>'}",
        "",
        "## Combined Expected Outcomes",
        "",
    ]
    for item in list(summary.get("combined_expected_outcomes") or []):
        lines.append(f"- {item}")
    if not list(summary.get("combined_expected_outcomes") or []):
        lines.append("- <none>")
    return "\n".join(lines)


def _artifact_directory_markdown(summary: Dict[str, Any]) -> str:
    lines = ["# Artifact Directory Summary", ""]
    for row in list(summary.get("directories") or []):
        lines.extend(
            [
                f"## {row['label']}",
                "",
                f"- Path: {row['path']}",
                f"- Exists: {row['exists']}",
                f"- File Count: {row['file_count']}",
                f"- Latest File: {row['latest_file'] or '<none>'}",
                f"- Latest Modified At: {row['latest_modified_at'] or '<none>'}",
                "",
            ]
        )
    return "\n".join(lines)


def _bundle_readme(manifest: Dict[str, Any]) -> str:
    lines = [
        "# Pitch Support Bundle",
        "",
        f"- Created At: {manifest['created_at']}",
        f"- Bundle Dir: {manifest['bundle_dir']}",
        f"- Selected Scenario: {manifest['selected_scenario']}",
        "",
        "## Checks",
        "",
    ]
    for check in list(manifest.get("checks") or []):
        lines.append(f"- {check['label']}: {str(check['status']).upper()} — {check['summary']}")
    lines.extend(
        [
            "",
            "## Contents",
            "",
            "- `reports/` contains the copied demo-readiness and core-validation reports when available.",
            "- `known_issues_summary.*` comes from `tools/operations_console/known_issues.yaml`.",
            "- `scenario_fact_sheet.*` comes from the current demo scenario payload plus campaign status/explain support.",
            "- `expected_outcomes_summary.*` comes from `tools/orl/demo_checklist.yaml` and `tools/orl/round1_manifest.yaml`.",
            "- `artifact_directory_summary.*` summarizes the current artifact directories.",
            "- `docs/` contains the static pitch-support runbook and architecture/support note.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
