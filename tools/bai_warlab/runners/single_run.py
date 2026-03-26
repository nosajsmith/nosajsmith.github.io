from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .. import PROJECT_ROOT
from ..ai_report_adapter import empty_ai_report, normalize_ai_report
from ..config_loader import ConfigLoader
from ..engine_adapter import apply_ai_config_policy, inject_engine_config
from ..metrics import compute_behavior_metrics, compute_logistics_metrics, compute_outcome_metrics
from ..models import RunRequest, RunResult


DEFAULT_MAX_STEPS = 12
DEFAULT_DT_HOURS = 24


def _resolved_max_steps(request: RunRequest, merged_run: Dict[str, Any]) -> int:
    if request.max_steps is not None:
        return int(request.max_steps)
    if "max_steps" in merged_run:
        return int(merged_run["max_steps"])
    return 0


def _resolved_dt_hours(request: RunRequest, merged_run: Dict[str, Any]) -> int:
    if request.dt_hours is not None:
        return int(request.dt_hours)
    if "dt_hours" in merged_run:
        return int(merged_run["dt_hours"])
    return 0


def _failure_result(
    *,
    request: RunRequest,
    max_steps: int,
    dt_hours: int,
    error: str,
    terminal_status: str,
    warnings: Iterable[str],
    applied_axis: Dict[str, Any] | None = None,
    run_options: Dict[str, Any] | None = None,
    ai_report: Dict[str, Any] | None = None,
) -> RunResult:
    return RunResult(
        ok=False,
        command="run",
        scenario=request.scenario,
        scenario_dir=request.scenario_dir,
        doctrine=request.doctrine,
        personality=request.personality,
        tuning=request.tuning,
        seed=int(request.seed),
        max_steps=int(max_steps),
        dt_hours=int(dt_hours),
        variant_label=request.variant_label,
        error=error,
        warnings=list(warnings),
        applied_axis=dict(applied_axis or {}),
        run_options=dict(run_options or {}),
        summary={
            "ok": False,
            "execution_status": "failed",
            "result": "error",
            "terminal_status": terminal_status,
            "hours_elapsed": 0,
            "steps_completed": 0,
            "configured_max_steps": int(max_steps),
            "configured_dt_hours": int(dt_hours),
            "max_steps_exhausted": False,
        },
        metrics={
            "outcome": {
                "available": False,
                "reason": terminal_status,
            }
        },
        ai_report=dict(ai_report or empty_ai_report()),
    )


def _scenario_name_candidates(value: str) -> List[str]:
    if not str(value or "").strip():
        return []
    path = Path(str(value))
    raw_name = path.name
    if path.suffix.lower() == ".json":
        return [raw_name]
    return [raw_name, f"{raw_name}.json"]


def _candidate_roots(scenario_dir: str) -> List[Path]:
    roots: List[Path] = []
    raw_dir = Path(str(scenario_dir or ""))

    if str(scenario_dir or "").strip():
        if raw_dir.is_absolute():
            roots.append(raw_dir)
        else:
            roots.extend(
                [
                    (PROJECT_ROOT / raw_dir).resolve(),
                    (PROJECT_ROOT / "server" / raw_dir).resolve(),
                    (PROJECT_ROOT / "server" / "rules" / raw_dir).resolve(),
                ]
            )

    roots.extend(
        [
            (PROJECT_ROOT / "server" / "rules" / "scenarios").resolve(),
            (PROJECT_ROOT / "server" / "scenarios").resolve(),
            (PROJECT_ROOT / "scenarios").resolve(),
        ]
    )

    unique: List[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)
    return unique


def _resolve_scenario_path(scenario: str, scenario_dir: str) -> Path:
    raw = Path(str(scenario))

    direct_candidates = [raw]
    if not raw.is_absolute():
        direct_candidates.extend(
            [
                (PROJECT_ROOT / raw).resolve(),
                (PROJECT_ROOT / "server" / raw).resolve(),
                (PROJECT_ROOT / "server" / "rules" / raw).resolve(),
            ]
        )

    for candidate in direct_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    names = _scenario_name_candidates(str(scenario))
    for root in _candidate_roots(scenario_dir):
        for name in names:
            candidate = root / name
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()

    raise FileNotFoundError(
        f"Scenario not found: {scenario!r} (searched scenario_dir={scenario_dir!r} and standard scenario roots)"
    )


def _load_scenario_payload(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Scenario at {path} must load as a JSON object")
    return payload


def _normalize_side(value: Any) -> str:
    raw = str(value or "ALLIED").strip().upper()
    if raw == "ALLIED":
        return "ALLIED"
    if raw == "AXIS":
        return "AXIS"
    raise ValueError(f"Unsupported side value: {value!r}")


def _normalize_posture(value: Any) -> str:
    raw = str(value or "DEFEND").strip().upper()
    if raw in {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"}:
        return raw
    return "DEFEND"


def _normalize_unit_type(value: Any) -> str:
    raw = str(value or "INFANTRY").strip().upper()
    if raw in {"INFANTRY", "ARMOR", "ARTILLERY", "HQ", "NAVAL", "AIR"}:
        return raw
    return "INFANTRY"


def _normalize_unit(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(payload.get("id", "")).strip(),
        "name": str(payload.get("name", "")).strip(),
        "side": _normalize_side(payload.get("side")),
        "unit_type": _normalize_unit_type(payload.get("unit_type")),
        "strength": int(payload.get("strength", 100)),
        "fatigue": int(payload.get("fatigue", 0)),
        "morale": int(payload.get("morale", 50)),
        "supply": int(payload.get("supply", 50)),
        "readiness": int(payload.get("readiness", 50)),
        "location_id": str(payload.get("location_id", "")).strip(),
        "posture": _normalize_posture(payload.get("posture")),
        "hq_unit_id": payload.get("hq_unit_id"),
    }


def _normalize_reinforcement(payload: Dict[str, Any]) -> Dict[str, Any]:
    unit = _normalize_unit(
        {
            "id": payload.get("id"),
            "name": payload.get("name"),
            "side": payload.get("side"),
            "unit_type": payload.get("unit_type"),
            "strength": payload.get("strength", 100),
            "fatigue": payload.get("fatigue", 0),
            "morale": payload.get("morale", 50),
            "supply": payload.get("supply", 100),
            "readiness": payload.get("readiness", 50),
            "location_id": payload.get("entry_location_id", payload.get("location_id", "")),
            "posture": payload.get("posture", "DEFEND"),
            "hq_unit_id": payload.get("hq_unit_id"),
        }
    )
    unit["arrival_day"] = int(payload.get("arrival_day", 0))
    return unit


def _normalize_objectives(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    objectives: List[Dict[str, Any]] = []
    for index, raw in enumerate(payload.get("objectives", []) or []):
        if not isinstance(raw, dict):
            continue
        location_id = str(raw.get("location_id", "")).strip()
        side = raw.get("side")
        if not location_id or side is None:
            continue
        objectives.append(
            {
                "id": str(raw.get("id") or f"objective_{index}"),
                "location_id": location_id,
                "side": _normalize_side(side),
                "value": int(raw.get("value", 0)),
                "description": str(raw.get("description", "")).strip(),
            }
        )
    return objectives


def _normalize_supply_sources(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for raw in payload.get("supply_sources", []) or []:
        if not isinstance(raw, dict):
            continue
        location_id = str(raw.get("location_id", "")).strip()
        side = raw.get("side")
        if not location_id or side is None:
            continue
        sources.append(
            {
                "location_id": location_id,
                "side": _normalize_side(side),
                "daily_supply": int(raw.get("daily_supply", 0)),
                "description": str(raw.get("description", "")).strip(),
            }
        )
    return sources


def _map_defense_bonus(payload: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    raw_tiles = (payload.get("map") or {}).get("tiles", {})
    if isinstance(raw_tiles, list):
        items = []
        for raw in raw_tiles:
            if not isinstance(raw, dict):
                continue
            tile_id = raw.get("tile_id") or raw.get("id")
            if tile_id is None:
                continue
            items.append((str(tile_id), raw))
    else:
        items = [(str(tile_id), raw) for tile_id, raw in dict(raw_tiles or {}).items()]

    for tile_id, raw in items:
        if not isinstance(raw, dict):
            continue
        out[tile_id] = int(raw.get("defense_bonus", 0))
    return out


def _living_units(units: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [unit for unit in units if int(unit.get("strength", 0)) > 0]


def _strength_by_side(units: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    totals = {"ALLIED": 0, "AXIS": 0}
    for unit in _living_units(units):
        totals[unit["side"]] += int(unit["strength"])
    return totals


def _unit_count_by_side(units: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"ALLIED": 0, "AXIS": 0}
    for unit in _living_units(units):
        counts[unit["side"]] += 1
    return counts


def _average_supply_by_side(units: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    buckets: Dict[str, List[int]] = {"ALLIED": [], "AXIS": []}
    for unit in _living_units(units):
        buckets[unit["side"]].append(int(unit["supply"]))
    return {
        side: round(sum(values) / len(values), 3) if values else 0.0
        for side, values in buckets.items()
    }


def _low_supply_counts(units: Iterable[Dict[str, Any]], threshold: int = 30) -> Dict[str, int]:
    counts = {"ALLIED": 0, "AXIS": 0}
    for unit in _living_units(units):
        if int(unit["supply"]) < threshold:
            counts[unit["side"]] += 1
    return counts


def _objective_control_map(state: Dict[str, Any]) -> Dict[str, str | None]:
    return {
        objective["id"]: _control_for_location(state["units"], objective["location_id"])
        for objective in state["objectives"]
    }


def _spawn_reinforcements(state: Dict[str, Any], day: int, logs: List[Dict[str, Any]]) -> None:
    for unit in state["reinforcements"]:
        if unit["id"] in state["arrived_ids"]:
            continue
        if int(unit.get("arrival_day", 0)) != day:
            continue
        spawned = dict(unit)
        spawned.pop("arrival_day", None)
        state["units"].append(spawned)
        state["arrived_ids"].add(unit["id"])
        logs.append(
            {
                "src": "G7",
                "turn": day,
                "phase": "reinforcements",
                "message": f"{spawned['id']} arrived at {spawned['location_id']}",
            }
        )


def _resolve_battles(
    *,
    units: List[Dict[str, Any]],
    defense_bonus_by_loc: Dict[str, int],
    day: int,
    rng: random.Random,
    logs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_loc: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: {"ALLIED": [], "AXIS": []})
    for unit in _living_units(units):
        by_loc[unit["location_id"]][unit["side"]].append(unit)

    battles: List[Dict[str, Any]] = []
    for location_id, sides in by_loc.items():
        allied = sides["ALLIED"]
        axis = sides["AXIS"]
        if not allied or not axis:
            continue

        allied_strength = sum(int(unit["strength"]) for unit in allied)
        axis_strength = sum(int(unit["strength"]) for unit in axis)
        defense_bonus = int(defense_bonus_by_loc.get(location_id, 0))
        axis_effective = axis_strength + defense_bonus

        if allied_strength >= axis_effective:
            winner = "ALLIED"
            losers = axis
            note = f"Allies win at {location_id} ({allied_strength} vs {axis_effective})."
        else:
            winner = "AXIS"
            losers = allied
            note = f"Axis holds at {location_id} ({allied_strength} vs {axis_effective})."

        for unit in losers:
            strength_loss = rng.randint(8, 12)
            unit["strength"] = max(0, int(unit["strength"]) - strength_loss)
            unit["morale"] = max(0, int(unit["morale"]) - 5)
            unit["readiness"] = max(0, int(unit["readiness"]) - 5)

        logs.append({"src": "G3", "turn": day, "phase": "combat", "message": note})
        battles.append(
            {
                "day": day,
                "location_id": location_id,
                "attacker": "ALLIED",
                "winner": winner,
                "attack_success": winner == "ALLIED",
                "allied_strength": allied_strength,
                "axis_strength": axis_strength,
                "defense_bonus": defense_bonus,
                "notes": note,
            }
        )

    units[:] = _living_units(units)
    return battles


def _apply_logistics(units: List[Dict[str, Any]], supply_sources: List[Dict[str, Any]], day: int, logs: List[Dict[str, Any]]) -> None:
    for unit in _living_units(units):
        posture = unit["posture"]
        consumption = 1
        if posture == "ATTACK":
            consumption += 2
        elif posture in {"MOVE", "DEFEND"}:
            consumption += 1

        before = int(unit["supply"])
        unit["supply"] = max(0, before - consumption)
        logs.append(
            {
                "src": "G4",
                "turn": day,
                "phase": "consumption",
                "message": f"{unit['id']} consumed {consumption}, supply {before}->{unit['supply']}",
            }
        )

    for source in supply_sources:
        daily_supply = int(source.get("daily_supply", 0))
        if daily_supply <= 0:
            continue
        units_here = [
            unit
            for unit in _living_units(units)
            if unit["location_id"] == source["location_id"] and unit["side"] == source["side"]
        ]
        if not units_here:
            continue
        per_unit = max(1, daily_supply // len(units_here))
        for unit in units_here:
            before = int(unit["supply"])
            unit["supply"] = min(100, before + per_unit)
            unit["fatigue"] = max(0, int(unit["fatigue"]) - 2)
            unit["readiness"] = min(100, int(unit["readiness"]) + 2)
            logs.append(
                {
                    "src": "G4",
                    "turn": day,
                    "phase": "resupply",
                    "message": f"{unit['id']} resupplied +{per_unit} at {source['location_id']}, supply {before}->{unit['supply']}",
                }
            )


def _control_for_location(units: List[Dict[str, Any]], location_id: str) -> str | None:
    present = {unit["side"] for unit in _living_units(units) if unit["location_id"] == location_id}
    if present == {"ALLIED"}:
        return "ALLIED"
    if present == {"AXIS"}:
        return "AXIS"
    return None


def _evaluate_objectives(state: Dict[str, Any], day: int, logs: List[Dict[str, Any]]) -> None:
    for objective in state["objectives"]:
        current_control = _control_for_location(state["units"], objective["location_id"])
        previous_control = state["objective_control"].get(objective["id"])
        if current_control == previous_control:
            continue

        state["objective_control"][objective["id"]] = current_control
        desired_side = objective["side"]
        if current_control == desired_side:
            state["vp"][desired_side] += int(objective["value"])
            message = (
                f"Day {day}: {desired_side} secured objective {objective['location_id']} "
                f"(+{objective['value']} VP). {objective['description']}"
            ).strip()
            state["objective_events"].append(message)
            logs.append({"src": "G8", "turn": day, "phase": "objective", "message": message})
        elif previous_control is not None:
            message = f"Day {day}: Objective {objective['location_id']} control changed to {current_control or 'CONTESTED'}."
            state["objective_events"].append(message)
            logs.append({"src": "G8", "turn": day, "phase": "objective", "message": message})


def _terminal_status(state: Dict[str, Any]) -> str | None:
    living_sides = {unit["side"] for unit in _living_units(state["units"])}
    if not living_sides:
        return "no_units_remaining"
    if living_sides == {"ALLIED"}:
        return "axis_eliminated"
    if living_sides == {"AXIS"}:
        return "allied_eliminated"
    return None


def _scenario_outcome(state: Dict[str, Any], terminal_status: str | None) -> Tuple[str, str | None]:
    if terminal_status == "axis_eliminated":
        return "allied_victory", "ALLIED"
    if terminal_status == "allied_eliminated":
        return "axis_victory", "AXIS"

    allied_vp = int(state["vp"]["ALLIED"])
    axis_vp = int(state["vp"]["AXIS"])
    if allied_vp > axis_vp:
        return "allied_victory", "ALLIED"
    if axis_vp > allied_vp:
        return "axis_victory", "AXIS"
    return "draw", None


def execute_single_run(request: RunRequest, loader: ConfigLoader) -> RunResult:
    try:
        resolved = loader.resolve_profiles(request.doctrine, request.personality, request.tuning)
    except Exception as exc:
        return _failure_result(
            request=request,
            max_steps=int(request.max_steps or 0),
            dt_hours=int(request.dt_hours or 0),
            error=str(exc),
            terminal_status="config_error",
            warnings=["Configuration resolution failed."],
        )

    warnings = list(resolved.warnings)
    ai_report = normalize_ai_report(
        resolved.merged_run.get("bai_report"),
        resolved.merged_run.get("ai_report"),
        resolved.merged_run.get("reasoning"),
    )

    max_steps = _resolved_max_steps(request, resolved.merged_run)
    dt_hours = _resolved_dt_hours(request, resolved.merged_run)
    if max_steps <= 0:
        max_steps = DEFAULT_MAX_STEPS
        warnings.append(f"No max_steps configured; defaulted to {DEFAULT_MAX_STEPS} for headless execution.")
    if dt_hours <= 0:
        dt_hours = DEFAULT_DT_HOURS
        warnings.append(f"No dt_hours configured; defaulted to {DEFAULT_DT_HOURS}.")

    run_options = dict(resolved.merged_run)
    run_options.update(
        {
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "stop_on_terminal": bool(request.stop_on_terminal),
            "execution_mode": "headless_single_run",
            "seed_used": int(request.seed),
        }
    )

    try:
        scenario_path = _resolve_scenario_path(request.scenario, request.scenario_dir)
        scenario_payload = _load_scenario_payload(scenario_path)
    except Exception as exc:
        run_options["scenario_resolution_error"] = str(exc)
        return _failure_result(
            request=request,
            max_steps=max_steps,
            dt_hours=dt_hours,
            error=str(exc),
            terminal_status="scenario_load_error",
            warnings=[*warnings, "Scenario loading failed."],
            applied_axis=resolved.merged_axis,
            run_options=run_options,
            ai_report=ai_report,
        )

    rng = random.Random(int(request.seed))
    units = [_normalize_unit(unit) for unit in scenario_payload.get("units", []) if isinstance(unit, dict)]
    initial_counts = _unit_count_by_side(units)
    initial_strength = _strength_by_side(units)
    initial_units = [dict(unit) for unit in units]
    state = {
        "units": units,
        "reinforcements": [
            _normalize_reinforcement(unit) for unit in scenario_payload.get("reinforcements", []) if isinstance(unit, dict)
        ],
        "arrived_ids": set(),
        "supply_sources": _normalize_supply_sources(scenario_payload),
        "objectives": _normalize_objectives(scenario_payload),
        "objective_control": {},
        "objective_events": [],
        "vp": {"ALLIED": 0, "AXIS": 0},
        "battle_history": [],
    }
    defense_bonus_by_loc = _map_defense_bonus(scenario_payload)
    logs: List[Dict[str, Any]] = []
    engine_config = inject_engine_config(state=state, resolved=resolved, logs=logs)
    warnings.extend(str(item) for item in engine_config.get("warnings", []) if str(item).strip())
    snapshots: List[Dict[str, Any]] = []
    start_day = int(scenario_payload.get("start_day", 1))
    current_day = start_day
    steps_completed = 0
    terminal_status: str | None = None

    try:
        while steps_completed < max_steps:
            _spawn_reinforcements(state, current_day, logs)
            apply_ai_config_policy(state, current_day, logs)
            state["battle_history"].extend(
                _resolve_battles(
                    units=state["units"],
                    defense_bonus_by_loc=defense_bonus_by_loc,
                    day=current_day,
                    rng=rng,
                    logs=logs,
                )
            )
            _evaluate_objectives(state, current_day, logs)
            _apply_logistics(state["units"], state["supply_sources"], current_day, logs)

            snapshots.append(
                {
                    "day": current_day,
                    "unit_count": len(_living_units(state["units"])),
                    "unit_counts": _unit_count_by_side(state["units"]),
                    "strengths": _strength_by_side(state["units"]),
                    "low_supply_counts": _low_supply_counts(state["units"]),
                    "average_supply": _average_supply_by_side(state["units"]),
                    "objective_control": _objective_control_map(state),
                    "vp_allied": int(state["vp"]["ALLIED"]),
                    "vp_axis": int(state["vp"]["AXIS"]),
                }
            )

            steps_completed += 1
            terminal_status = _terminal_status(state)
            if terminal_status and request.stop_on_terminal:
                break
            current_day += 1
    except Exception as exc:
        run_options["scenario_path"] = str(scenario_path)
        return _failure_result(
            request=request,
            max_steps=max_steps,
            dt_hours=dt_hours,
            error=str(exc),
            terminal_status="runtime_error",
            warnings=[*warnings, "Headless execution failed."],
            applied_axis=resolved.merged_axis,
            run_options=run_options,
            ai_report=ai_report,
        )

    final_counts = _unit_count_by_side(state["units"])
    final_strength = _strength_by_side(state["units"])
    final_units = [dict(unit) for unit in state["units"]]
    scenario_outcome, winning_side = _scenario_outcome(state, terminal_status)
    max_steps_exhausted = steps_completed >= max_steps and terminal_status is None
    terminal_label = terminal_status or ("max_steps" if max_steps_exhausted else "completed")
    final_day = snapshots[-1]["day"] if snapshots else start_day
    secured_objectives = sum(
        1 for objective in state["objectives"] if state["objective_control"].get(objective["id"]) == objective["side"]
    )
    contested_objectives = sum(
        1 for objective in state["objectives"] if state["objective_control"].get(objective["id"]) is None
    )

    run_options["scenario_path"] = str(scenario_path)
    run_options["scenario_name"] = str(scenario_payload.get("name") or scenario_path.stem)
    run_options["profile_selection"] = dict(engine_config.get("profile_selection") or {})
    run_options["engine_config"] = engine_config
    run_options["engine_received_settings"] = True
    metric_context = {
        "ai_report": ai_report,
        "ai_side": engine_config.get("ai_side"),
        "battle_history": state["battle_history"],
        "final_strength": final_strength,
        "final_units": final_units,
        "initial_strength": initial_strength,
        "initial_units": initial_units,
        "max_steps_exhausted": max_steps_exhausted,
        "objectives": state["objectives"],
        "scenario_outcome": scenario_outcome,
        "snapshots": snapshots,
        "steps_completed": steps_completed,
        "vp": state["vp"],
        "winning_side": winning_side,
    }
    outcome_metrics = compute_outcome_metrics(metric_context)
    behavior_metrics = compute_behavior_metrics(metric_context)
    logistics_metrics = compute_logistics_metrics(metric_context)

    return RunResult(
        ok=True,
        command="run",
        scenario=request.scenario,
        scenario_dir=request.scenario_dir,
        doctrine=request.doctrine,
        personality=request.personality,
        tuning=request.tuning,
        seed=int(request.seed),
        max_steps=max_steps,
        dt_hours=dt_hours,
        variant_label=request.variant_label,
        warnings=warnings,
        applied_axis=dict(resolved.merged_axis),
        run_options=run_options,
        summary={
            "ok": True,
            "execution_status": "completed",
            "result": scenario_outcome,
            "terminal_status": terminal_label,
            "hours_elapsed": steps_completed * dt_hours,
            "steps_completed": steps_completed,
            "configured_max_steps": max_steps,
            "configured_dt_hours": dt_hours,
            "max_steps_exhausted": max_steps_exhausted,
            "scenario_id": str(scenario_payload.get("id") or scenario_path.stem),
            "scenario_name": str(scenario_payload.get("name") or scenario_path.stem),
            "scenario_path": str(scenario_path),
            "start_day": start_day,
            "final_day": final_day,
            "scenario_outcome": scenario_outcome,
            "winning_side": winning_side,
            "ai_side": engine_config.get("ai_side"),
        },
        metrics={
            "outcome": {
                **outcome_metrics,
                "terminal_reason": terminal_label,
            },
            "behavior": behavior_metrics,
            "logistics": logistics_metrics,
            "forces": {
                "initial_allied_units": initial_counts["ALLIED"],
                "initial_axis_units": initial_counts["AXIS"],
                "final_allied_units": final_counts["ALLIED"],
                "final_axis_units": final_counts["AXIS"],
                "initial_allied_strength": initial_strength["ALLIED"],
                "initial_axis_strength": initial_strength["AXIS"],
                "final_allied_strength": final_strength["ALLIED"],
                "final_axis_strength": final_strength["AXIS"],
            },
            "objectives": {
                "total": len(state["objectives"]),
                "secured": secured_objectives,
                "contested": contested_objectives,
                "events": len(state["objective_events"]),
            },
            "execution": {
                "battle_count": len(state["battle_history"]),
                "reinforcements_arrived": len(state["arrived_ids"]),
                "log_count": len(logs),
                "snapshot_count": len(snapshots),
            },
        },
        ai_report=ai_report,
    )


__all__ = ["execute_single_run"]
