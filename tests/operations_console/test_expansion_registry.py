from __future__ import annotations

import json

import pytest

from tools.operations_console.app import OperationsConsoleApp
from tools.operations_console.expansion_registry import (
    ExpansionRegistry,
    ExpansionRegistryEntry,
    load_expansion_registry,
    write_expansion_registry_snapshot,
)
from tools.operations_console.registry import build_default_registry
from tools.operations_console.runner_utils import run_registry_entry


def test_load_expansion_registry_reads_seeded_file_and_derives_states() -> None:
    registry = load_expansion_registry()

    assert registry.version == 1
    assert len(registry.entries) >= 6
    current_slice = next(entry for entry in registry.entries if entry.entry_id == "korea-operational-slice")
    modern_korea = next(entry for entry in registry.entries if entry.entry_id == "modern-korea-concept")
    precision_fires = next(entry for entry in registry.entries if entry.entry_id == "precision-fires-capability")

    assert current_slice.planning_state == "support_ready"
    assert modern_korea.planning_state == "blocked_by_support"
    assert precision_fires.planning_state == "needs_foundation"
    assert "scenario_contracts_present" in modern_korea.missing_support_gates


def test_load_expansion_registry_rejects_unknown_support_gate(tmp_path) -> None:
    path = tmp_path / "expansion_registry.yaml"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "bad-entry",
                        "name": "Bad Entry",
                        "category": "capability",
                        "theater": "cross-theater",
                        "era": "modern",
                        "summary": "Bad gate configuration.",
                        "status": "concept",
                        "maturity": "concept",
                        "capabilities": [],
                        "dependencies": [],
                        "support_gates": {
                            "unknown_gate": True,
                        },
                        "risk_level": "high",
                        "notes": "",
                        "next_step": "Fix the gate list.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="not a supported gate"):
        load_expansion_registry(path)


def test_app_registers_expansion_registry_action_and_writes_snapshot(tmp_path, monkeypatch) -> None:
    catalog = ExpansionRegistry(
        version=1,
        entries=[
            ExpansionRegistryEntry(
                entry_id="core-slice",
                name="Core Slice",
                category="theater-slice",
                theater="Korea",
                era="1950-1951",
                summary="Current supported slice.",
                status="active",
                maturity="polished",
                capabilities=["scenario integrity"],
                dependencies=["core validation"],
                support_gates={"core_validation_green": True},
                risk_level="low",
                notes="",
                next_step="Keep stable.",
                planning_state="blocked_by_support",
                ready_support_gates=["core_validation_green"],
                missing_support_gates=[
                    "known_issues_under_control",
                    "scenario_contracts_present",
                    "baseline_compare_available",
                    "divergence_support_available",
                    "explainability_available",
                ],
            ),
            ExpansionRegistryEntry(
                entry_id="future-capability",
                name="Future Capability",
                category="capability",
                theater="cross-theater",
                era="modern",
                summary="Needs support foundation.",
                status="concept",
                maturity="concept",
                capabilities=["ew"],
                dependencies=["support gates"],
                support_gates={},
                risk_level="high",
                notes="",
                next_step="Define support truth.",
                planning_state="needs_foundation",
                ready_support_gates=[],
                missing_support_gates=[
                    "core_validation_green",
                    "known_issues_under_control",
                    "scenario_contracts_present",
                    "baseline_compare_available",
                    "divergence_support_available",
                    "explainability_available",
                ],
            ),
        ],
    )

    app = OperationsConsoleApp.__new__(OperationsConsoleApp)
    app.registry = build_default_registry()
    app.expansion_registry = catalog
    app._register_expansion_registry_action()

    monkeypatch.setattr(
        "tools.operations_console.app.write_expansion_registry_snapshot",
        lambda registry: write_expansion_registry_snapshot(registry, repo_root_path=tmp_path),
    )

    action = app.registry.get_action("Planning / Expansion Registry")
    assert action is not None
    assert action.category == "Planning"

    result = run_registry_entry(
        action,
        entry_lookup=app.registry.get,
    )

    assert result.status == "pass"
    assert result.adapter_method == "expansion_registry"
    assert result.summary == "Expansion registry loaded: 2 entries."
    assert result.artifact_paths
    snapshot_path = result.artifact_paths[0]
    assert snapshot_path.endswith("expansion-registry.json")
    assert any(line.startswith("EXPANSION REGISTRY COUNTS: total=2") for line in result.details)
    assert "PLANNING STATE: blocked_by_support (1)" in result.details
    assert "PLANNING STATE: needs_foundation (1)" in result.details

    payload = json.loads((tmp_path / "artifacts" / "operations_console" / "expansion_registry").glob("*.json").__next__().read_text(encoding="utf-8"))
    assert payload["entry_count"] == 2
    assert payload["planning_state_counts"]["needs_foundation"] == 1
