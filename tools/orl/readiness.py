from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from engine.engine_api import EngineAPI
from tools.bai_warlab.ai_report_adapter import normalize_ai_report
from tools.bai_warlab.config_loader import ConfigLoader

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    yaml = None


PRIMARY_VARIANT_IDS = ("base", "aggressive", "cautious")


@dataclass(frozen=True)
class DemoChecklistItem:
    item_id: str
    label: str
    required: bool = True
    notes: str = ""


@dataclass(frozen=True)
class DemoChecklist:
    label: str = ""
    default_scenario: str = ""
    checklist: List[DemoChecklistItem] = field(default_factory=list)
    inspect_artifacts: List[str] = field(default_factory=list)
    bug_reports_to: str = ""
    expected_outcomes: Dict[str, List[str]] = field(default_factory=dict)
    source_path: str = ""


@dataclass(frozen=True)
class Round1Scenario:
    scenario_id: str
    label: str
    minimum_units: int = 1
    minimum_objectives: int = 0
    require_grease_board: bool = False
    ai_side: str = "AXIS"
    matrix_enabled: bool = True
    expected_outcomes: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class Round1Variant:
    variant_id: str
    label: str
    personality: str = ""
    ai_side: str = "AXIS"
    notes: str = ""


@dataclass(frozen=True)
class Round1Manifest:
    primary_scenarios: List[Round1Scenario] = field(default_factory=list)
    variants: List[Round1Variant] = field(default_factory=list)
    run_tests: List[str] = field(default_factory=list)
    inspect_artifacts: List[str] = field(default_factory=list)
    bug_reports_to: str = ""
    expected_outcomes: Dict[str, List[str]] = field(default_factory=dict)
    source_path: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def round1_manifest_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "orl" / "round1_manifest.yaml"


def round1_readme_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "orl" / "README.md"


def demo_checklist_path(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "tools" / "orl" / "demo_checklist.yaml"


def artifact_root(repo_root_path: Path | None = None) -> Path:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    return root / "artifacts" / "orl"


def write_orl_artifact(name: str, payload: Mapping[str, Any], repo_root_path: Path | None = None) -> Path:
    target_root = artifact_root(repo_root_path)
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(name or "").strip().lower()).strip("-") or "artifact"
    path = target_root / f"{stamp}-{slug}.json"
    path.write_text(json.dumps(dict(payload), indent=2), encoding="utf-8")
    return path


def load_round1_manifest(path: Path | None = None) -> Round1Manifest:
    source_path = Path(path) if path is not None else round1_manifest_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Round 1 manifest must be a top-level object.")

    scenarios_raw = payload.get("primary_scenarios")
    variants_raw = payload.get("variants")
    if not isinstance(scenarios_raw, list):
        raise RuntimeError("Round 1 manifest must expose a primary_scenarios list.")
    if not isinstance(variants_raw, list):
        raise RuntimeError("Round 1 manifest must expose a variants list.")

    scenarios: List[Round1Scenario] = []
    variants: List[Round1Variant] = []
    seen_scenarios: set[str] = set()
    seen_variants: set[str] = set()

    for index, row in enumerate(scenarios_raw, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"primary_scenarios[{index}] must be an object.")
        scenario = Round1Scenario(
            scenario_id=_required_text(row.get("id"), f"primary_scenarios[{index}].id"),
            label=_required_text(row.get("label"), f"primary_scenarios[{index}].label"),
            minimum_units=max(0, int(row.get("minimum_units", 1) or 0)),
            minimum_objectives=max(0, int(row.get("minimum_objectives", 0) or 0)),
            require_grease_board=bool(row.get("require_grease_board")),
            ai_side=_required_text(row.get("ai_side") or "AXIS", f"primary_scenarios[{index}].ai_side").upper(),
            matrix_enabled=bool(row.get("matrix_enabled", True)),
            expected_outcomes=_text_list(
                row.get("expected_outcomes"),
                field_name=f"primary_scenarios[{index}].expected_outcomes",
            ),
            notes=str(row.get("notes") or "").strip(),
        )
        if scenario.scenario_id in seen_scenarios:
            raise RuntimeError(f"Duplicate primary scenario id: {scenario.scenario_id}")
        seen_scenarios.add(scenario.scenario_id)
        scenarios.append(scenario)

    for index, row in enumerate(variants_raw, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"variants[{index}] must be an object.")
        variant = Round1Variant(
            variant_id=_required_text(row.get("id"), f"variants[{index}].id"),
            label=_required_text(row.get("label"), f"variants[{index}].label"),
            personality=str(row.get("personality") or "").strip(),
            ai_side=_required_text(row.get("ai_side") or "AXIS", f"variants[{index}].ai_side").upper(),
            notes=str(row.get("notes") or "").strip(),
        )
        if variant.variant_id in seen_variants:
            raise RuntimeError(f"Duplicate variant id: {variant.variant_id}")
        seen_variants.add(variant.variant_id)
        variants.append(variant)

    return Round1Manifest(
        primary_scenarios=scenarios,
        variants=variants,
        run_tests=_text_list(payload.get("run_tests"), field_name="run_tests"),
        inspect_artifacts=_text_list(payload.get("inspect_artifacts"), field_name="inspect_artifacts"),
        bug_reports_to=str(payload.get("bug_reports_to") or "").strip(),
        expected_outcomes={
            str(key): _text_list(value, field_name=f"expected_outcomes.{key}")
            for key, value in dict(payload.get("expected_outcomes") or {}).items()
        },
        source_path=str(source_path),
    )


def load_demo_checklist(path: Path | None = None) -> DemoChecklist:
    source_path = Path(path) if path is not None else demo_checklist_path()
    payload = _load_payload(source_path)
    if not isinstance(payload, dict):
        raise RuntimeError("Demo checklist must be a top-level object.")

    checklist_raw = payload.get("checklist")
    if not isinstance(checklist_raw, list):
        raise RuntimeError("Demo checklist must expose a checklist list.")

    checklist: List[DemoChecklistItem] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(checklist_raw, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"checklist[{index}] must be an object.")
        item = DemoChecklistItem(
            item_id=_required_text(row.get("id"), f"checklist[{index}].id"),
            label=_required_text(row.get("label"), f"checklist[{index}].label"),
            required=bool(row.get("required", True)),
            notes=str(row.get("notes") or "").strip(),
        )
        if item.item_id in seen_ids:
            raise RuntimeError(f"Duplicate demo checklist id: {item.item_id}")
        seen_ids.add(item.item_id)
        checklist.append(item)

    return DemoChecklist(
        label=str(payload.get("label") or "").strip(),
        default_scenario=_required_text(payload.get("default_scenario"), "default_scenario"),
        checklist=checklist,
        inspect_artifacts=_text_list(payload.get("inspect_artifacts"), field_name="inspect_artifacts"),
        bug_reports_to=str(payload.get("bug_reports_to") or "").strip(),
        expected_outcomes={
            str(key): _text_list(value, field_name=f"expected_outcomes.{key}")
            for key, value in dict(payload.get("expected_outcomes") or {}).items()
        },
        source_path=str(source_path),
    )


def discover_round1_scenarios(repo_root_path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    catalog: Dict[str, Dict[str, Any]] = {}
    for source_name, source_dir, engine_ready in _scenario_dirs(root):
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                payload = None
            file_stem = path.stem
            scenario_id = ""
            if isinstance(payload, dict):
                scenario_id = str(payload.get("id") or "").strip()
            key = scenario_id or file_stem
            record = catalog.setdefault(
                key,
                {
                    "scenario_id": key,
                    "sources": [],
                    "bridge_listed": False,
                    "engine_ready_sources": [],
                    "file_names": [],
                },
            )
            record["sources"].append(
                {
                    "source": source_name,
                    "path": str(path),
                    "engine_ready": engine_ready,
                    "payload_name": str(payload.get("name") or "").strip() if isinstance(payload, dict) else "",
                }
            )
            record["file_names"].append(path.name)
            if source_name == "bridge_roster":
                record["bridge_listed"] = True
            if engine_ready:
                record["engine_ready_sources"].append(str(path))
    return catalog


def validate_round1_scenarios(
    *,
    repo_root_path: Path | None = None,
    manifest: Round1Manifest | None = None,
) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    loaded_manifest = manifest or load_round1_manifest()
    catalog = discover_round1_scenarios(root)

    rows: List[Dict[str, Any]] = []
    logs: List[str] = []
    failures: List[str] = []

    for scenario in loaded_manifest.primary_scenarios:
        row_logs: List[str] = []
        record = catalog.get(scenario.scenario_id)
        payload = _read_scenario_payload(scenario.scenario_id, repo_root_path=root)
        engine_meta: Dict[str, Any] = {}
        engine_state: Dict[str, Any] = {}
        engine_error = ""
        try:
            api = EngineAPI()
            engine_meta = api.load_scenario(scenario.scenario_id)
            engine_state = api.start_game()
        except Exception as exc:
            engine_error = str(exc)

        row_status = "pass"
        if record is None:
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: scenario source not found")
            row_logs.append("scenario source not found in bridge or engine catalogs")
        if payload is None:
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: payload missing")
            row_logs.append("scenario payload missing")
        if engine_error:
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: engine load failed")
            row_logs.append(f"engine load failed: {engine_error}")

        unit_count = int(len((engine_state.get("units") or [])) if engine_state else len((payload or {}).get("units") or []))
        objective_count = int(len(engine_meta.get("objectives") or (payload or {}).get("objectives") or []))
        if unit_count < scenario.minimum_units:
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: unit count below threshold")
            row_logs.append(f"unit count {unit_count} fell below minimum {scenario.minimum_units}")
        if objective_count < scenario.minimum_objectives:
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: objective count below threshold")
            row_logs.append(
                f"objective count {objective_count} fell below minimum {scenario.minimum_objectives}"
            )
        if scenario.require_grease_board and not bool((payload or {}).get("grease_board")):
            row_status = "fail"
            failures.append(f"{scenario.scenario_id}: grease board missing")
            row_logs.append("grease_board block is required for explainability support")

        row_logs.append(f"expected outcomes: {' | '.join(scenario.expected_outcomes)}")
        row = {
            "scenario_id": scenario.scenario_id,
            "label": scenario.label,
            "status": row_status,
            "bridge_listed": bool(record and record.get("bridge_listed")),
            "engine_ready": not bool(engine_error),
            "unit_count": unit_count,
            "objective_count": objective_count,
            "require_grease_board": scenario.require_grease_board,
            "sources": list((record or {}).get("sources") or []),
            "expected_outcomes": list(scenario.expected_outcomes),
            "notes": scenario.notes,
            "logs": row_logs,
        }
        rows.append(row)
        logs.append(f"{scenario.scenario_id}: {row_status.upper()} units={unit_count} objectives={objective_count}")

    variant_ids = {variant.variant_id for variant in loaded_manifest.variants}
    missing_variants = [variant_id for variant_id in PRIMARY_VARIANT_IDS if variant_id not in variant_ids]
    if missing_variants:
        failures.append(f"missing required variants: {', '.join(missing_variants)}")
        logs.append(f"variants: FAIL missing {', '.join(missing_variants)}")
    else:
        logs.append("variants: PASS base/aggressive/cautious variants available")

    artifact_path = write_orl_artifact(
        "round1-scenario-validator",
        {
            "status": "pass" if not failures else "fail",
            "failures": failures,
            "rows": rows,
            "manifest_path": loaded_manifest.source_path,
        },
        repo_root_path=root,
    )
    logs.append(f"artifact: {artifact_path}")
    return {
        "ok": not failures,
        "status": "pass" if not failures else "fail",
        "summary": "Round 1 primary scenarios validated." if not failures else "Round 1 scenario validation failed.",
        "failures": failures,
        "rows": rows,
        "logs": logs,
        "artifact_path": str(artifact_path),
        "blocker_class": "scenario.validator",
    }


def run_round1_scenario_matrix(
    *,
    repo_root_path: Path | None = None,
    manifest: Round1Manifest | None = None,
) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    loaded_manifest = manifest or load_round1_manifest()
    loader = ConfigLoader(root / "configs" / "ai")

    rows: List[Dict[str, Any]] = []
    failures: List[str] = []
    logs: List[str] = []

    for scenario in loaded_manifest.primary_scenarios:
        if not scenario.matrix_enabled:
            continue
        for variant in loaded_manifest.variants:
            row_logs: List[str] = []
            try:
                engine_config = _engine_config_for_variant(loader, variant, scenario.ai_side or variant.ai_side)
                api = EngineAPI(
                    ai_enabled=True,
                    ai_side=scenario.ai_side or variant.ai_side,
                    engine_config=engine_config,
                )
                api.load_scenario(
                    scenario.scenario_id,
                    ai_enabled=True,
                    ai_side=scenario.ai_side or variant.ai_side,
                    engine_config=engine_config,
                )
                state = api.process_turn()
                normalized = normalize_ai_report(state)
                ai_status = dict((state.get("game") or {}).get("ai") or {})
                row_ok = bool(
                    ai_status.get("enabled")
                    and int(ai_status.get("last_orders", 0) or 0) >= 1
                    and normalized.get("chosen_operation")
                )
                if not row_ok:
                    failures.append(f"{scenario.scenario_id}/{variant.variant_id}: matrix run incomplete")
                row_logs.append(
                    f"ai enabled={bool(ai_status.get('enabled'))} last_orders={int(ai_status.get('last_orders', 0) or 0)}"
                )
                row_logs.append(f"chosen operation: {normalized.get('chosen_operation') or '<none>'}")
                row_logs.append(f"main objective: {normalized.get('main_objective') or '<none>'}")
                rows.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "variant_id": variant.variant_id,
                        "status": "pass" if row_ok else "fail",
                        "ai_side": scenario.ai_side or variant.ai_side,
                        "chosen_operation": normalized.get("chosen_operation"),
                        "posture": normalized.get("posture"),
                        "main_objective": normalized.get("main_objective"),
                        "reserve_level": normalized.get("reserve_level"),
                        "last_orders": int(ai_status.get("last_orders", 0) or 0),
                        "logs": row_logs,
                    }
                )
                logs.append(
                    f"{scenario.scenario_id}/{variant.variant_id}: {'PASS' if row_ok else 'FAIL'} "
                    f"orders={int(ai_status.get('last_orders', 0) or 0)}"
                )
            except Exception as exc:
                failures.append(f"{scenario.scenario_id}/{variant.variant_id}: {exc}")
                rows.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "variant_id": variant.variant_id,
                        "status": "fail",
                        "ai_side": scenario.ai_side or variant.ai_side,
                        "chosen_operation": "",
                        "posture": "",
                        "main_objective": "",
                        "reserve_level": "",
                        "last_orders": 0,
                        "logs": [str(exc)],
                    }
                )
                logs.append(f"{scenario.scenario_id}/{variant.variant_id}: FAIL {exc}")

    artifact_path = write_orl_artifact(
        "round1-scenario-matrix",
        {
            "status": "pass" if not failures else "fail",
            "rows": rows,
            "failures": failures,
            "manifest_path": loaded_manifest.source_path,
        },
        repo_root_path=root,
    )
    logs.append(f"artifact: {artifact_path}")
    return {
        "ok": not failures,
        "status": "pass" if not failures else "fail",
        "summary": "Round 1 scenario matrix passed." if not failures else "Round 1 scenario matrix failed.",
        "rows": rows,
        "failures": failures,
        "logs": logs,
        "artifact_path": str(artifact_path),
        "blocker_class": "scenario.matrix",
    }


def check_round1_documentation_support(
    *,
    repo_root_path: Path | None = None,
    manifest: Round1Manifest | None = None,
) -> Dict[str, Any]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    loaded_manifest = manifest or load_round1_manifest()
    readme_path = round1_readme_path(root)
    logs: List[str] = []
    failures: List[str] = []

    if not readme_path.exists():
        failures.append(f"missing README: {readme_path}")
    else:
        text = readme_path.read_text(encoding="utf-8")
        for section in ("How To Run Tests", "Artifacts", "Bug Reports", "Expected Outcomes"):
            if section not in text:
                failures.append(f"missing README section: {section}")
        logs.append(f"readme: {readme_path}")

    if not loaded_manifest.run_tests:
        failures.append("manifest missing run_tests guidance")
    if not loaded_manifest.inspect_artifacts:
        failures.append("manifest missing inspect_artifacts guidance")
    if not loaded_manifest.bug_reports_to:
        failures.append("manifest missing bug_reports_to guidance")

    logs.extend(f"run tests: {item}" for item in loaded_manifest.run_tests)
    logs.extend(f"inspect artifacts: {item}" for item in loaded_manifest.inspect_artifacts)
    if loaded_manifest.bug_reports_to:
        logs.append(f"bug reports: {loaded_manifest.bug_reports_to}")

    artifact_path = write_orl_artifact(
        "round1-documentation-support",
        {
            "status": "pass" if not failures else "fail",
            "failures": failures,
            "readme_path": str(readme_path),
            "manifest_path": loaded_manifest.source_path,
        },
        repo_root_path=root,
    )
    logs.append(f"artifact: {artifact_path}")
    return {
        "ok": not failures,
        "status": "pass" if not failures else "fail",
        "summary": "Round 1 documentation/support guidance is present."
        if not failures
        else "Round 1 documentation/support guidance is incomplete.",
        "failures": failures,
        "logs": logs,
        "artifact_path": str(artifact_path),
        "blocker_class": "support.documentation",
    }


def latest_demo_artifact_shelf(*, repo_root_path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    operations_root = root / "artifacts" / "operations_console"
    engine_adapter_root = operations_root / "engine_adapter"
    shelf_specs = (
        ("demo_report", "Latest Demo Report", operations_root, "*-orl-demo-readiness.json"),
        ("replay", "Latest Replay", engine_adapter_root / "replays", "*.json"),
        ("snapshot", "Latest Snapshot", engine_adapter_root / "snapshots", "*.json"),
        ("compare_output", "Latest Compare Output", engine_adapter_root / "compares", "*.json"),
    )

    shelf: Dict[str, Dict[str, Any]] = {}
    for slot_id, label, directory, pattern in shelf_specs:
        path = _latest_matching_file(directory, pattern)
        shelf[slot_id] = {
            "slot_id": slot_id,
            "label": label,
            "path": str(path) if path is not None else "",
            "exists": path is not None,
            "size_bytes": path.stat().st_size if path is not None else 0,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            if path is not None
            else "",
        }
    return shelf


def validate_demo_artifact_shelf(*, repo_root_path: Path | None = None) -> Dict[str, Any]:
    shelf = latest_demo_artifact_shelf(repo_root_path=repo_root_path)
    checks: List[Dict[str, Any]] = []
    missing: List[str] = []
    logs: List[str] = []

    for slot_id, info in shelf.items():
        exists = bool(info.get("exists"))
        label = str(info.get("label") or slot_id).strip()
        path = str(info.get("path") or "").strip()
        check_logs = [f"slot: {slot_id}"]
        if path:
            check_logs.append(f"path: {path}")
        if info.get("modified_at"):
            check_logs.append(f"modified_at: {info['modified_at']}")
        if info.get("size_bytes"):
            check_logs.append(f"size_bytes: {info['size_bytes']}")
        if not exists:
            missing.append(slot_id)
            check_logs.append("artifact missing")
        checks.append(
            {
                "check_id": f"artifact.{slot_id}",
                "label": label,
                "blocker_class": "demo.artifact_output",
                "status": "pass" if exists else "fail",
                "summary": f"{label} found." if exists else f"{label} is missing.",
                "artifacts": [path] if path else [],
                "logs": check_logs,
            }
        )
        logs.append(f"{slot_id}: {'PASS' if exists else 'FAIL'} {path or '<missing>'}")

    artifact_path = write_orl_artifact(
        "demo-artifact-shelf",
        {
            "status": "pass" if not missing else "fail",
            "checks": checks,
            "missing": missing,
            "shelf": shelf,
        },
        repo_root_path=repo_root_path,
    )
    logs.append(f"artifact: {artifact_path}")
    return {
        "ok": not missing,
        "status": "pass" if not missing else "fail",
        "summary": "Demo artifact shelf is complete." if not missing else "Demo artifact shelf is incomplete.",
        "checks": checks,
        "missing": missing,
        "shelf": shelf,
        "logs": logs,
        "artifact_path": str(artifact_path),
        "blocker_class": "demo.artifact_output",
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
        raise RuntimeError(f"Unable to parse ORL manifest: {path}") from exc


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{field_name} is required.")
    return text


def _text_list(value: object, *, field_name: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        raise RuntimeError(f"{field_name} must be a list of strings.")
    items: List[str] = []
    for index, item in enumerate(value, start=1):
        text = str(item or "").strip()
        if not text:
            raise RuntimeError(f"{field_name}[{index}] must be a non-empty string.")
        items.append(text)
    return items


def _scenario_dirs(root: Path) -> Iterable[tuple[str, Path, bool]]:
    yield ("bridge_roster", root / "scenarios", False)
    yield ("server_shared", root / "server" / "scenarios", True)
    yield ("server_rules", root / "server" / "rules" / "scenarios", True)


def _read_scenario_payload(scenario_id: str, *, repo_root_path: Path | None = None) -> Dict[str, Any] | None:
    root = Path(repo_root_path) if repo_root_path is not None else repo_root()
    for _source_name, source_dir, _engine_ready in _scenario_dirs(root):
        for candidate_name in (f"{scenario_id}.json",):
            path = source_dir / candidate_name
            if not path.exists() or not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
    return None


def _engine_config_for_variant(loader: ConfigLoader, variant: Round1Variant, ai_side: str) -> Dict[str, Any]:
    if not variant.personality:
        return {
            "profile_selection": {"personality": variant.variant_id},
            "ai_side": ai_side,
        }
    personality = loader.load_personality(variant.personality)
    return {
        "profile_selection": {"personality": variant.variant_id},
        "ai_side": ai_side,
        "axis": dict(personality.axis),
        "run": dict(personality.run),
        "personality": {
            "axis": dict(personality.axis),
            "run": dict(personality.run),
            "metadata": dict(personality.metadata),
        },
    }


def _latest_matching_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists() or not directory.is_dir():
        return None
    matches = [path for path in directory.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime, path.name))
