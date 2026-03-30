from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.engine_api import EngineAPI
from server.scenario_store import list_scenarios as store_list_scenarios
from server.scenario_store import read_scenario


@dataclass(frozen=True)
class TestingApiResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    adapter_method: str = ""
    executed_command: List[str] = field(default_factory=list)
    return_code: int | None = None


class EngineTestingAPI:
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]

    def artifact_root(self) -> Path:
        return self.repo_root / "artifacts" / "operations_console" / "engine_adapter"

    def list_scenarios(self) -> TestingApiResult:
        scenarios = store_list_scenarios()
        return TestingApiResult(
            ok=True,
            data={"scenarios": scenarios},
            metrics={"scenario_count": len(scenarios)},
            logs=[f"Listed {len(scenarios)} scenario(s)."],
            adapter_method="list_scenarios",
        )

    def load_scenario(self, name: str = "") -> TestingApiResult:
        resolved_name = self._resolve_scenario_name(name)
        if resolved_name is None:
            return TestingApiResult(
                ok=False,
                error="Scenario not found in roster.",
                logs=[f"Unable to resolve scenario: {name or '<default>'}"],
                adapter_method="load_scenario",
            )

        payload = read_scenario(resolved_name)
        if not isinstance(payload, dict):
            return TestingApiResult(
                ok=False,
                error=f"Unable to read scenario payload: {resolved_name}",
                logs=[f"Scenario payload missing for {resolved_name}."],
                adapter_method="load_scenario",
            )

        scenario_id = str(payload.get("id") or resolved_name.removesuffix(".json")).strip()
        api = EngineAPI()
        meta = api.load_scenario(scenario_id)
        state = api.start_game()
        logs = [
            f"Resolved scenario: {resolved_name}",
            f"Loaded scenario id: {scenario_id}",
            f"Started scenario: {meta.get('name') or scenario_id}",
        ]
        return TestingApiResult(
            ok=True,
            data={
                "scenario_name": resolved_name,
                "scenario_id": scenario_id,
                "meta": meta,
                "state": state,
            },
            metrics={"unit_count": len(state.get("units") or [])},
            logs=logs,
            adapter_method="load_scenario",
        )

    def save_snapshot(self, path: str | Path | None = None, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "save_snapshot")

        meta = dict(loaded.data.get("meta") or {})
        scenario_id = str(loaded.data.get("scenario_id") or meta.get("id") or "").strip()
        api = EngineAPI()
        api.load_scenario(scenario_id)
        api.start_game()

        final_path = Path(path) if path is not None else self._snapshot_artifact_path(scenario_id or "snapshot")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_snapshot_file(final_path, api)

        logs = list(loaded.logs) + [f"Snapshot saved: {final_path}"]
        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": scenario_id,
                "scenario_name": meta.get("name") or scenario_id,
                "snapshot_path": str(final_path),
                "time": self._time_to_dict(api.time),
            },
            artifacts=[str(final_path)],
            metrics={"unit_count": len(api.units.all_units()) if api.units is not None else 0},
            logs=logs,
            adapter_method="save_snapshot",
        )

    def load_snapshot(self, path: str | Path) -> TestingApiResult:
        source_path = Path(path)
        if not source_path.exists() or not source_path.is_file():
            return TestingApiResult(
                ok=False,
                error=f"Snapshot file not found: {source_path}",
                logs=[f"Snapshot file missing: {source_path}"],
                adapter_method="load_snapshot",
            )

        snapshot_data = self._read_snapshot_file(source_path)
        scenario_id = str(snapshot_data.get("scenario_id") or "").strip()
        if not scenario_id:
            return TestingApiResult(
                ok=False,
                error="Snapshot file is missing a scenario_id.",
                logs=[f"Snapshot file missing scenario_id: {source_path}"],
                adapter_method="load_snapshot",
            )

        api = EngineAPI()
        meta = dict(api.load_scenario(scenario_id) or {})
        api.start_game()
        self._restore_snapshot_state(api, snapshot_data)

        game_time = api.time
        game_map = api.game_map
        units = api.units
        meta.update(dict(snapshot_data.get("meta") or {}))
        unit_count = len(units.all_units()) if units is not None else 0
        logs = [
            f"Snapshot loaded: {source_path}",
            f"Scenario restored: {meta.get('id') or scenario_id}",
            f"Units restored: {unit_count}",
        ]
        return TestingApiResult(
            ok=True,
            data={
                "snapshot_path": str(source_path),
                "scenario_id": str(meta.get("id") or scenario_id).strip(),
                "scenario_name": str(meta.get("name") or meta.get("id") or "").strip(),
                "time": self._time_to_dict(game_time),
                "game_map": game_map,
            },
            artifacts=[str(source_path)],
            metrics={"unit_count": unit_count},
            logs=logs,
            adapter_method="load_snapshot",
        )

    def snapshot_smoke(self, scenario_name: str = "") -> TestingApiResult:
        saved = self.save_snapshot(scenario_name=scenario_name)
        if not saved.ok:
            return self._with_method(saved, "snapshot_smoke")

        snapshot_path = saved.artifacts[0]
        loaded = self.load_snapshot(snapshot_path)
        if not loaded.ok:
            return self._with_method(loaded, "snapshot_smoke")

        saved_id = str(saved.data.get("scenario_id") or "").strip()
        loaded_id = str(loaded.data.get("scenario_id") or "").strip()
        if saved_id and loaded_id and saved_id != loaded_id:
            return TestingApiResult(
                ok=False,
                error=f"Snapshot reload mismatch: expected {saved_id}, got {loaded_id}",
                artifacts=list(saved.artifacts),
                logs=list(saved.logs) + list(loaded.logs),
                adapter_method="snapshot_smoke",
            )

        unit_count = int(loaded.metrics.get("unit_count") or 0)
        if unit_count <= 0:
            return TestingApiResult(
                ok=False,
                error="Snapshot smoke restored zero units.",
                artifacts=list(saved.artifacts),
                logs=list(saved.logs) + list(loaded.logs),
                adapter_method="snapshot_smoke",
            )

        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": loaded_id or saved_id,
                "snapshot_path": snapshot_path,
            },
            artifacts=list(saved.artifacts),
            metrics={"unit_count": unit_count},
            logs=list(saved.logs) + list(loaded.logs) + ["Snapshot smoke passed."],
            adapter_method="snapshot_smoke",
        )

    def export_replay(self, path: str | Path | None = None, scenario_name: str = "") -> TestingApiResult:
        loaded = self.load_scenario(scenario_name)
        if not loaded.ok:
            return self._with_method(loaded, "export_replay")

        scenario_id = str(loaded.data.get("scenario_id") or "").strip()
        api = EngineAPI()
        api.load_scenario(scenario_id)
        start_state = api.start_game()
        end_state = api.process_turn()
        payload = self._build_replay_payload(start_state, end_state, api.get_logs())

        replay_path = Path(path) if path is not None else self._replay_artifact_path(scenario_id or "replay")
        replay_path.parent.mkdir(parents=True, exist_ok=True)
        replay_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return TestingApiResult(
            ok=True,
            data={
                "scenario_id": scenario_id,
                "replay_path": str(replay_path),
            },
            artifacts=[str(replay_path)],
            metrics={
                "unit_count": len(payload.get("final_units") or []),
                "log_count": len(payload.get("logs") or []),
            },
            logs=list(loaded.logs) + [f"Replay exported: {replay_path}"],
            adapter_method="export_replay",
        )

    def compare_replay(self, path_a: str | Path, path_b: str | Path) -> TestingApiResult:
        replay_a = Path(path_a)
        replay_b = Path(path_b)
        if not replay_a.exists() or not replay_b.exists():
            missing = replay_a if not replay_a.exists() else replay_b
            return TestingApiResult(
                ok=False,
                error=f"Replay file not found: {missing}",
                logs=[f"Replay file missing: {missing}"],
                adapter_method="compare_replay",
            )

        payload_a = json.loads(replay_a.read_text(encoding="utf-8"))
        payload_b = json.loads(replay_b.read_text(encoding="utf-8"))
        identical = payload_a == payload_b
        logs = [
            f"Replay A: {replay_a}",
            f"Replay B: {replay_b}",
            f"Replay compare identical={identical}",
        ]
        return TestingApiResult(
            ok=identical,
            data={"identical": identical},
            error="" if identical else "Replay payloads differ.",
            artifacts=[str(replay_a), str(replay_b)],
            logs=logs,
            adapter_method="compare_replay",
        )

    def replay_validation(self, scenario_name: str = "") -> TestingApiResult:
        first_path = self._replay_artifact_path(f"{self._slug(scenario_name or 'default')}-a")
        second_path = self._replay_artifact_path(f"{self._slug(scenario_name or 'default')}-b")

        first = self.export_replay(first_path, scenario_name=scenario_name)
        if not first.ok:
            return self._with_method(first, "replay_validation")

        second = self.export_replay(second_path, scenario_name=scenario_name)
        if not second.ok:
            return self._with_method(second, "replay_validation")

        compared = self.compare_replay(first.artifacts[0], second.artifacts[0])
        if not compared.ok:
            return TestingApiResult(
                ok=False,
                error=compared.error,
                artifacts=list(first.artifacts) + list(second.artifacts),
                logs=list(first.logs) + list(second.logs) + list(compared.logs),
                adapter_method="replay_validation",
            )

        return TestingApiResult(
            ok=True,
            data={"scenario_name": scenario_name},
            artifacts=list(first.artifacts) + list(second.artifacts),
            metrics={"artifact_count": len(first.artifacts) + len(second.artifacts)},
            logs=list(first.logs) + list(second.logs) + list(compared.logs) + ["Replay validation passed."],
            adapter_method="replay_validation",
        )

    def run_all_green(self) -> TestingApiResult:
        command = self._all_green_command()
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return TestingApiResult(
                ok=False,
                error=str(exc),
                logs=[f"All-green command failed to start: {exc}"],
                adapter_method="run_all_green",
                executed_command=command,
            )

        logs = []
        for stream_name, payload in (("stdout", completed.stdout), ("stderr", completed.stderr)):
            for line in str(payload or "").splitlines():
                text = line.rstrip()
                if text:
                    logs.append(f"{stream_name}: {text}")

        return TestingApiResult(
            ok=completed.returncode == 0,
            data={"command": command},
            error="" if completed.returncode == 0 else f"All-green command exited with code {completed.returncode}.",
            logs=logs or ["All-green command completed."],
            adapter_method="run_all_green",
            executed_command=command,
            return_code=completed.returncode,
        )

    def _resolve_scenario_name(self, requested: str = "") -> str | None:
        scenarios = store_list_scenarios()
        if not scenarios:
            return None

        requested_text = str(requested or "").strip()
        if not requested_text:
            return scenarios[0]

        requested_lower = requested_text.lower()
        requested_json = requested_lower if requested_lower.endswith(".json") else f"{requested_lower}.json"
        for candidate in scenarios:
            candidate_lower = candidate.lower()
            candidate_stem = candidate_lower[:-5] if candidate_lower.endswith(".json") else candidate_lower
            if candidate_lower in {requested_lower, requested_json} or candidate_stem == requested_lower:
                return candidate
        return None

    def _snapshot_artifact_path(self, stem: str) -> Path:
        return self.artifact_root() / "snapshots" / f"{self._timestamp()}-{self._slug(stem)}.json"

    def _replay_artifact_path(self, stem: str) -> Path:
        return self.artifact_root() / "replays" / f"{self._timestamp()}-{self._slug(stem)}.json"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip()).strip("-") or "artifact"

    def _time_to_dict(self, value: Any) -> Dict[str, Any]:
        return {
            "day": int(getattr(value, "day", 0) or 0),
            "phase": str(getattr(value, "phase", "") or ""),
        }

    def _build_replay_payload(self, start_state: Dict[str, Any], end_state: Dict[str, Any], logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "initial_game": dict(start_state.get("game") or {}),
            "final_game": dict(end_state.get("game") or {}),
            "initial_units": self._simplify_units(start_state.get("units") or []),
            "final_units": self._simplify_units(end_state.get("units") or []),
            "logs": list(logs or []),
        }

    def _simplify_units(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for unit in units:
            if not isinstance(unit, dict):
                continue
            rows.append(
                {
                    "id": unit.get("id") or unit.get("unit_id"),
                    "location_id": unit.get("location_id"),
                    "strength": unit.get("strength"),
                    "supply": unit.get("supply"),
                    "readiness": unit.get("readiness"),
                }
            )
        rows.sort(key=lambda row: str(row.get("id") or ""))
        return rows

    def _serialize_units(self, api: EngineAPI) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        units = getattr(api, "units", None)
        all_units = units.all_units() if units is not None else []
        for unit in all_units:
            rows.append(
                {
                    "id": getattr(unit, "id", ""),
                    "location_id": getattr(unit, "location_id", ""),
                    "strength": getattr(unit, "strength", 0),
                    "fatigue": getattr(unit, "fatigue", 0),
                    "morale": getattr(unit, "morale", 0),
                    "supply": getattr(unit, "supply", 0),
                    "readiness": getattr(unit, "readiness", 0),
                    "hq_unit_id": getattr(unit, "hq_unit_id", None),
                }
            )
        rows.sort(key=lambda row: str(row.get("id") or ""))
        return rows

    def _snapshot_payload(self, api: EngineAPI) -> Dict[str, Any]:
        meta = dict(getattr(api, "meta", None) or {})
        scenario_id = str(meta.get("id") or "").strip()
        return {
            "scenario_id": scenario_id,
            "time": self._time_to_dict(getattr(api, "time", None)),
            "units": self._serialize_units(api),
            "meta": meta,
        }

    def _write_snapshot_file(self, path: Path, api: EngineAPI) -> None:
        path.write_text(json.dumps(self._snapshot_payload(api), indent=2), encoding="utf-8")

    def _read_snapshot_file(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _restore_snapshot_state(self, api: EngineAPI, snapshot_data: Dict[str, Any]) -> None:
        time_data = dict(snapshot_data.get("time") or {})
        if getattr(api, "time", None) is not None:
            if "day" in time_data:
                api.time.day = int(time_data.get("day") or getattr(api.time, "day", 0) or 0)
            if "phase" in time_data:
                api.time.phase = str(time_data.get("phase") or getattr(api.time, "phase", "") or "")

        units = getattr(api, "units", None)
        if units is None:
            return
        saved_units = {
            str(row.get("id") or "").strip(): row
            for row in list(snapshot_data.get("units") or [])
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        for unit_id, row in saved_units.items():
            unit = self._find_unit(units, unit_id)
            if unit is None:
                continue
            for field_name in ("location_id", "strength", "fatigue", "morale", "supply", "readiness", "hq_unit_id"):
                if field_name in row:
                    setattr(unit, field_name, row.get(field_name))

    def _find_unit(self, units: Any, unit_id: str) -> Any:
        if hasattr(units, "get") and callable(getattr(units, "get")):
            unit = units.get(unit_id)
            if unit is not None:
                return unit
        if hasattr(units, "all_units") and callable(getattr(units, "all_units")):
            for unit in units.all_units():
                if str(getattr(unit, "id", "") or "") == unit_id:
                    return unit
        return None

    def _all_green_command(self) -> List[str]:
        return [
            "pytest",
            "-q",
            str(self.repo_root / "tests" / "test_inchon_scenario_stub.py"),
            str(self.repo_root / "tests" / "test_bridge_live_path.py"),
        ]

    def _with_method(self, result: TestingApiResult, method: str) -> TestingApiResult:
        return TestingApiResult(
            ok=result.ok,
            data=dict(result.data),
            error=result.error,
            artifacts=list(result.artifacts),
            metrics=dict(result.metrics),
            logs=list(result.logs),
            adapter_method=method,
            executed_command=list(result.executed_command),
            return_code=result.return_code,
        )
