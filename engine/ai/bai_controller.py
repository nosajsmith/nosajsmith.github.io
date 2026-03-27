from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter_ns
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .bai_eval import (
    EvaluationScore,
    build_evaluation,
    doctrinal_bias_component,
    enemy_threat_component,
    force_ratio_component,
    location_strength,
    objective_value_component,
    reserve_requirement_component,
    supply_feasibility_component,
    terrain_value_component,
)
from .bai_models import OperationCandidate, StrategicDirective, TacticalIntent, UnitOrderWrapper
from .bai_operational import plan_operational_layer
from .bai_personality import build_runtime_behavior_profile
from .bai_report import build_bai_report
from .bai_reserves import ReservePlan, plan_reserves
from .bai_strategic import plan_strategic_directive
from .bai_tactical import plan_tactical_layer
from .bai_validator import LEGAL_POSTURES, OrderValidationContext, validate_orders


@dataclass
class BAIControllerConfig:
    default_time_budget_ms: int = 25
    reserve_fraction: float = 0.25
    minimum_reserve_units: int = 1


@dataclass
class BAIControllerResult:
    side: str
    orders: List[Dict[str, Any]]
    report: Dict[str, Any]
    timing_breakdown: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    engine_received_settings: bool = False
    generated_order_count: int = 0
    legal_order_count: int = 0
    time_budget_ms: int = 0
    budget_exceeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "side": self.side,
            "orders": list(self.orders),
            "report": dict(self.report),
            "timing_breakdown": dict(self.timing_breakdown),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "engine_received_settings": bool(self.engine_received_settings),
            "generated_order_count": int(self.generated_order_count),
            "legal_order_count": int(self.legal_order_count),
            "time_budget_ms": int(self.time_budget_ms),
            "budget_exceeded": bool(self.budget_exceeded),
        }


@dataclass
class _Snapshot:
    side: str
    day: int
    phase: str
    units: List[Any]
    game_map: Any
    friendly_units: List[Any]
    enemy_units: List[Any]
    objectives: List[Dict[str, Any]]
    supply_sources: List[Dict[str, Any]]
    known_locations: List[str]


class BAIController:
    def __init__(self, config: BAIControllerConfig | None = None) -> None:
        self.config = config or BAIControllerConfig()

    def plan_turn(
        self,
        engine_state: Any,
        *,
        side: str | None = None,
        time_budget_ms: int | None = None,
        engine_config: Mapping[str, Any] | None = None,
    ) -> BAIControllerResult:
        effective_engine_config = _extract_engine_config(engine_state, engine_config)
        runtime_profile = build_runtime_behavior_profile(effective_engine_config)
        side_value = _resolve_side_for_controller(side, effective_engine_config, engine_state)
        budget_ms = _resolve_time_budget(
            explicit_budget_ms=time_budget_ms,
            engine_config=runtime_profile,
            default_budget_ms=self.config.default_time_budget_ms,
        )
        start_ns = perf_counter_ns()
        stage_times: Dict[str, int] = {}

        snapshot = self._stage(
            "campaign_stub",
            stage_times,
            lambda: self._build_snapshot(engine_state, side_value),
        )
        diagnostics: List[Dict[str, Any]] = []
        if not snapshot.friendly_units:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "controller.no_friendly_units",
                    "message": f"No units available for {side_value}.",
                }
            )

        directive = self._stage(
            "strategic",
            stage_times,
            lambda: self._run_strategic_layer(engine_state, snapshot, runtime_profile),
        )
        operational_plan = self._stage(
            "operational",
            stage_times,
            lambda: self._run_operational_layer(snapshot, directive, runtime_profile),
        )
        operation = operational_plan.primary_operation
        reserve_plan = self._stage(
            "reserves",
            stage_times,
            lambda: self._run_reserve_layer(snapshot, directive, operation, runtime_profile),
        )

        if budget_ms <= 0 or self._elapsed_ms(start_ns) > budget_ms:
            tactical_output = self._run_budget_fallback(snapshot, directive, operation, reserve_plan, diagnostics, runtime_profile)
        else:
            tactical_output = self._stage(
                "tactical",
                stage_times,
                lambda: self._run_tactical_layer(snapshot, directive, operation, reserve_plan, runtime_profile),
            )
        diagnostics.extend(list(tactical_output.get("diagnostics", [])))

        validated = self._stage(
            "validate",
            stage_times,
            lambda: self._validate_orders(snapshot, tactical_output["orders"]),
        )
        diagnostics.extend(validated["diagnostics"])

        total_elapsed_ms = self._elapsed_ms(start_ns)
        timing_breakdown = dict(stage_times)
        timing_breakdown["total_ms"] = total_elapsed_ms
        budget_exceeded = budget_ms <= 0 or total_elapsed_ms > budget_ms
        if budget_exceeded:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "controller.time_budget_exceeded",
                    "message": f"AI planning used {total_elapsed_ms}ms against a {budget_ms}ms budget.",
                }
            )

        report = self._stage(
            "report",
            stage_times,
            lambda: build_bai_report(
                posture=directive.posture,
                main_objective=directive.main_objective,
                chosen_operation=operation,
                reserve_level=operation.reserve_level,
                timing_breakdown=timing_breakdown,
                strategic_directive=directive,
                tactical_intents=tactical_output["intents"],
                unit_orders=tactical_output["wrapped_orders"],
                extra={
                    "campaign_layer": "stub",
                    "ai_side": side_value,
                    "validation_diagnostics": diagnostics,
                    "generated_order_count": len(tactical_output["orders"]),
                    "legal_order_count": len(validated["orders"]),
                    "time_budget_ms": budget_ms,
                    "budget_exceeded": budget_exceeded,
                    "engine_received_settings": bool(effective_engine_config),
                    "profile_selection": dict((effective_engine_config or {}).get("profile_selection") or {}),
                    "runtime_profile": {
                        "axis": dict(runtime_profile.get("axis") or {}),
                        "run": dict(runtime_profile.get("run") or {}),
                        "thresholds": dict(runtime_profile.get("thresholds") or {}),
                        "weights": dict(runtime_profile.get("weights") or {}),
                        "sources": dict(runtime_profile.get("sources") or {}),
                    },
                    "operations": operational_plan.candidates,
                    "support_actions": operational_plan.support_actions,
                    "reserve_plan": reserve_plan.to_dict(),
                    "defense_assessment": dict(tactical_output.get("metadata", {}) or {}).get("defense_assessment", {}),
                },
            ),
        )
        timing_breakdown["report"] = stage_times.get("report", 0)

        return BAIControllerResult(
            side=side_value,
            orders=validated["orders"],
            report=report,
            timing_breakdown=timing_breakdown,
            diagnostics=diagnostics,
            engine_received_settings=bool(effective_engine_config),
            generated_order_count=len(tactical_output["orders"]),
            legal_order_count=len(validated["orders"]),
            time_budget_ms=budget_ms,
            budget_exceeded=budget_exceeded,
        )

    def _run_strategic_layer(
        self,
        engine_state: Any,
        snapshot: _Snapshot,
        runtime_profile: Mapping[str, Any] | None,
    ) -> StrategicDirective:
        previous_memory = _get_strategic_memory(engine_state, snapshot.side)
        directive, updated_memory = plan_strategic_directive(snapshot, runtime_profile, previous_memory)
        _set_strategic_memory(engine_state, snapshot.side, updated_memory.to_dict())
        return directive

    def _run_operational_layer(
        self,
        snapshot: _Snapshot,
        directive: StrategicDirective,
        runtime_profile: Mapping[str, Any] | None,
    ):
        return plan_operational_layer(snapshot, directive, runtime_profile)

    def _run_tactical_layer(
        self,
        snapshot: _Snapshot,
        directive: StrategicDirective,
        operation: OperationCandidate,
        reserve_plan: ReservePlan,
        runtime_profile: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        plan = plan_tactical_layer(
            snapshot,
            directive,
            operation,
            runtime_profile,
            reserve_ids=reserve_plan.held_reserve_ids,
        )
        return {
            "orders": list(plan.orders),
            "intents": list(plan.intents),
            "wrapped_orders": list(plan.wrapped_orders),
            "diagnostics": list(plan.diagnostics),
            "metadata": dict(getattr(plan, "metadata", {}) or {}),
        }

    def _run_reserve_layer(
        self,
        snapshot: _Snapshot,
        directive: StrategicDirective,
        operation: OperationCandidate,
        runtime_profile: Mapping[str, Any] | None,
    ) -> ReservePlan:
        return plan_reserves(
            snapshot,
            directive,
            operation,
            runtime_profile,
            default_fraction=self.config.reserve_fraction,
            minimum_reserve_units=self.config.minimum_reserve_units,
        )

    def _run_budget_fallback(
        self,
        snapshot: _Snapshot,
        directive: StrategicDirective,
        operation: OperationCandidate,
        reserve_plan: ReservePlan,
        diagnostics: List[Dict[str, Any]],
        runtime_profile: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        diagnostics.append(
            {
                "level": "warn",
                "code": "controller.tactical_budget_fallback",
                "message": "Time budget reached before full tactical pass; using minimal hold orders.",
            }
        )
        reserve_ids = set(reserve_plan.held_reserve_ids)
        orders: List[Dict[str, Any]] = []
        intents: List[TacticalIntent] = []
        wrapped_orders: List[UnitOrderWrapper] = []

        for priority, unit in enumerate(_sort_units(snapshot.friendly_units)[: max(1, len(snapshot.friendly_units))], start=1):
            unit_id = _unit_value(unit, "id", "")
            current_location = _unit_value(unit, "location_id", "")
            if not unit_id or not current_location:
                continue
            is_reserve = unit_id in reserve_ids
            posture = "HOLD" if is_reserve else _strategic_to_unit_posture(directive.posture, current_location, current_location, runtime_profile)
            intent = TacticalIntent(
                intent_id=f"intent_{unit_id}_{snapshot.day}_fallback",
                unit_id=unit_id,
                action="hold",
                posture=posture,
                target_location_id=current_location,
                objective_id=str(directive.main_objective or current_location),
                priority=priority,
                rationale="Budget fallback preserved legal orders.",
            )
            intents.append(intent)
            wrapped_orders.append(
                UnitOrderWrapper(
                    unit_id=unit_id,
                    action="hold",
                    posture=posture,
                    target_location_id=current_location,
                    objective_id=str(directive.main_objective or current_location),
                    intent_id=intent.intent_id,
                    operation_id=operation.operation_id,
                    directive_id=directive.directive_id,
                    priority=priority,
                    notes="Budget fallback order.",
                )
            )
            orders.append({"type": "move", "unit_id": unit_id, "target": current_location, "posture": posture})

        return {"orders": orders, "intents": intents, "wrapped_orders": wrapped_orders, "metadata": {}}

    def _validate_orders(self, snapshot: _Snapshot, orders: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        result = validate_orders(orders, OrderValidationContext.from_snapshot(snapshot))
        return result.to_dict()

    def _build_snapshot(self, engine_state: Any, side: str) -> _Snapshot:
        units = list(_extract_units(engine_state))
        objectives = _extract_objectives(engine_state)
        supply_sources = _extract_supply_sources(engine_state)
        known_locations = sorted(_extract_known_locations(engine_state, units, objectives, supply_sources))
        friendly_units = [unit for unit in units if _normalize_side(_unit_value(unit, "side", "")) == side]
        enemy_units = [unit for unit in units if _normalize_side(_unit_value(unit, "side", "")) and _normalize_side(_unit_value(unit, "side", "")) != side]

        time_obj = _get_value(engine_state, "time")
        day = int(_unit_value(time_obj, "day", 1) or 1)
        phase = str(_unit_value(time_obj, "phase", "day") or "day")

        return _Snapshot(
            side=side,
            day=day,
            phase=phase,
            units=units,
            game_map=_get_value(engine_state, "game_map") or _get_value(engine_state, "map"),
            friendly_units=friendly_units,
            enemy_units=enemy_units,
            objectives=objectives,
            supply_sources=supply_sources,
            known_locations=known_locations,
        )

    def _order_posture_for_unit(
        self,
        directive_posture: str,
        is_reserve: bool,
        current_location: str,
        target_location: str,
        runtime_profile: Mapping[str, Any] | None,
    ) -> str:
        if is_reserve:
            return "HOLD"
        return _strategic_to_unit_posture(directive_posture, current_location, target_location, runtime_profile)

    def _order_action_for_unit(self, posture: str, current_location: str, target_location: str) -> str:
        if posture == "ATTACK":
            return "attack" if current_location != target_location else "hold"
        if posture == "MOVE":
            return "move"
        if posture == "REST":
            return "rest"
        return "hold"

    def _evaluate_tactical_unit(
        self,
        snapshot: _Snapshot,
        directive: StrategicDirective,
        operation: OperationCandidate,
        unit: Any,
        target: str,
        is_reserve: bool,
        runtime_profile: Mapping[str, Any] | None,
    ) -> EvaluationScore:
        axis = dict((runtime_profile or {}).get("axis") or {})
        thresholds = dict((runtime_profile or {}).get("thresholds") or {})
        unit_strength = float(_unit_value(unit, "strength", 0) or 0)
        unit_supply = float(_unit_value(unit, "supply", 0) or 0)
        current_location = str(_unit_value(unit, "location_id", "") or "")
        target_location = str(target or current_location)
        local_enemy_strength = location_strength(snapshot.enemy_units, target_location)
        objective_value = _objective_value_for_location(snapshot.objectives, target_location)
        reserve_fraction = float((directive.metadata or {}).get("reserve_fraction", self.config.reserve_fraction) or self.config.reserve_fraction)

        supply_floor = int(
            thresholds.get(
                "attack_supply_floor" if directive.posture == "OFFENSIVE" else "defend_supply_floor",
                45 if directive.posture == "OFFENSIVE" else 35,
            )
        )
        doctrinal_source = (
            axis.get("reserve_preservation_bias", 0.5)
            if is_reserve
            else axis.get("aggression" if directive.posture == "OFFENSIVE" else "caution_bias", 0.5)
        )

        return build_evaluation(
            f"tactical::{_unit_value(unit, 'id', '')}",
            base=0.02 if not is_reserve else 0.0,
            components=[
                objective_value_component(
                    objective_value,
                    weight=0.20,
                    label=f"Objective stake at {target_location}",
                ),
                terrain_value_component(
                    snapshot.game_map,
                    current_location if is_reserve else target_location,
                    weight=0.12 if is_reserve else 0.08,
                    label="Terrain for the unit order",
                ),
                force_ratio_component(
                    unit_strength,
                    local_enemy_strength,
                    weight=-0.10 if is_reserve else 0.24,
                    label=f"Unit force ratio near {target_location}",
                ),
                supply_feasibility_component(
                    unit_supply,
                    floor=supply_floor,
                    weight=0.16,
                    label="Unit supply feasibility",
                ),
                enemy_threat_component(
                    local_enemy_strength,
                    unit_strength,
                    contested=current_location == target_location,
                    weight=0.14 if is_reserve or directive.posture == "DEFENSIVE" else -0.10,
                    label="Threat shaping the unit order",
                ),
                reserve_requirement_component(
                    reserve_fraction,
                    0.0 if is_reserve else reserve_fraction,
                    weight=0.18 if is_reserve else -0.08,
                    label="Reserve requirement for this unit",
                ),
                doctrinal_bias_component(
                    doctrinal_source,
                    weight=0.16,
                    label="Doctrinal bias for this unit order",
                ),
            ],
        )

    def _intent_rationale(self, posture: str, is_reserve: bool, target: str, evaluation: EvaluationScore) -> str:
        if is_reserve:
            base = f"Preserve reserve posture near {target}."
        elif posture == "OFFENSIVE":
            base = f"Advance on {target} as the main effort."
        elif posture == "DEFENSIVE":
            base = f"Hold and defend {target}."
        else:
            base = f"Contain the enemy around {target} while preserving options."
        if evaluation.dominant_reason:
            return f"{base} {evaluation.dominant_reason}"
        return base

    def _stage(self, name: str, timing: Dict[str, int], fn):
        started = perf_counter_ns()
        result = fn()
        timing[name] = int(round((perf_counter_ns() - started) / 1_000_000))
        return result

    def _elapsed_ms(self, started_ns: int) -> int:
        return int(round((perf_counter_ns() - started_ns) / 1_000_000))


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _unit_value(unit: Any, key: str, default: Any = None) -> Any:
    value = _get_value(unit, key, default)
    return getattr(value, "value", value)


def _normalize_side(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value)).upper().strip()


def _average(units: Sequence[Any], field_name: str, default: int) -> float:
    if not units:
        return float(default)
    return sum(float(_unit_value(unit, field_name, default) or default) for unit in units) / len(units)


def _objective_value_for_location(objectives: Sequence[Mapping[str, Any]], location_id: str) -> float:
    total = 0.0
    for objective in objectives:
        if str(objective.get("location_id", "") or "") != str(location_id or ""):
            continue
        total += float(objective.get("value", 0) or 0)
    return total


def _sort_units(units: Iterable[Any]) -> List[Any]:
    return sorted(
        list(units),
        key=lambda unit: (
            -float(_unit_value(unit, "readiness", 0) or 0),
            -float(_unit_value(unit, "supply", 0) or 0),
            -float(_unit_value(unit, "strength", 0) or 0),
            str(_unit_value(unit, "id", "")),
        ),
    )


def _reserve_level(reserve_count: int, total_count: int) -> str:
    if total_count <= 0 or reserve_count <= 0:
        return "NONE"
    ratio = reserve_count / total_count
    if ratio >= 0.4:
        return "HIGH"
    if ratio >= 0.2:
        return "MEDIUM"
    return "LOW"


def _extract_units(engine_state: Any) -> Iterable[Any]:
    units_obj = _get_value(engine_state, "units")
    if units_obj is None:
        return []
    if hasattr(units_obj, "all_units") and callable(getattr(units_obj, "all_units")):
        return list(units_obj.all_units())
    if isinstance(units_obj, Mapping):
        return list(units_obj.values())
    if isinstance(units_obj, Sequence) and not isinstance(units_obj, (str, bytes)):
        return list(units_obj)
    return []


def _extract_objectives(engine_state: Any) -> List[Dict[str, Any]]:
    meta = _get_value(engine_state, "meta", {})
    raw = []
    if isinstance(meta, Mapping):
        raw = meta.get("objectives", [])
    elif hasattr(meta, "objectives"):
        raw = getattr(meta, "objectives")
    objectives: List[Dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, Mapping):
            objectives.append(dict(item))
    return objectives


def _extract_supply_sources(engine_state: Any) -> List[Dict[str, Any]]:
    meta = _get_value(engine_state, "meta", {})
    raw = []
    if isinstance(meta, Mapping):
        raw = meta.get("supply_sources", [])
    elif hasattr(meta, "supply_sources"):
        raw = getattr(meta, "supply_sources")
    supply_sources: List[Dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, Mapping):
            supply_sources.append(dict(item))
    return supply_sources


def _extract_known_locations(
    engine_state: Any,
    units: Sequence[Any],
    objectives: Sequence[Mapping[str, Any]],
    supply_sources: Sequence[Mapping[str, Any]],
) -> set[str]:
    known_locations: set[str] = set()

    game_map = _get_value(engine_state, "game_map") or _get_value(engine_state, "map")
    if game_map is not None:
        if hasattr(game_map, "tiles") and callable(getattr(game_map, "tiles")):
            for tile in game_map.tiles():
                tile_id = _unit_value(tile, "tile_id", "") or _unit_value(tile, "id", "")
                if tile_id:
                    known_locations.add(str(tile_id))
        elif isinstance(game_map, Mapping):
            known_locations.update(str(key) for key in game_map.keys())

    for unit in units:
        loc = _unit_value(unit, "location_id", "")
        if loc:
            known_locations.add(str(loc))

    for objective in objectives:
        loc = objective.get("location_id")
        if loc:
            known_locations.add(str(loc))

    for source in supply_sources:
        loc = source.get("location_id")
        if loc:
            known_locations.add(str(loc))

    return known_locations


def _safe_location(location_id: str | None, known_locations: Sequence[str]) -> str:
    if location_id and location_id in known_locations:
        return location_id
    return str(known_locations[0]) if known_locations else ""


def _strategic_to_unit_posture(
    strategic_posture: str,
    current_location: str,
    target_location: str,
    runtime_profile: Mapping[str, Any] | None,
) -> str:
    run = dict((runtime_profile or {}).get("run") or {})
    posture = str(strategic_posture or "").upper().strip()
    if posture == "OFFENSIVE":
        return "ATTACK"
    if posture == "DEFENSIVE":
        return "DEFEND"
    if posture == "CONTAIN":
        if current_location != target_location:
            return "MOVE"
        fallback_posture = str(run.get("fallback_posture", "HOLD")).upper().strip()
        return fallback_posture if fallback_posture in LEGAL_POSTURES else "HOLD"
    return "HOLD"


def _get_strategic_memory(engine_state: Any, side: str) -> Dict[str, Any] | None:
    if isinstance(engine_state, Mapping):
        memory_store = engine_state.get("bai_memory")
        if isinstance(memory_store, Mapping):
            value = memory_store.get(side)
            return dict(value) if isinstance(value, Mapping) else None
        return None

    memory_store = getattr(engine_state, "bai_memory", None)
    if isinstance(memory_store, Mapping):
        value = memory_store.get(side)
        return dict(value) if isinstance(value, Mapping) else None
    return None


def _set_strategic_memory(engine_state: Any, side: str, value: Mapping[str, Any]) -> None:
    if isinstance(engine_state, Mapping):
        memory_store = engine_state.setdefault("bai_memory", {})
        if isinstance(memory_store, dict):
            memory_store[side] = dict(value)
        return

    memory_store = getattr(engine_state, "bai_memory", None)
    if not isinstance(memory_store, dict):
        memory_store = {}
        setattr(engine_state, "bai_memory", memory_store)
    memory_store[side] = dict(value)


def _extract_engine_config(
    engine_state: Any,
    explicit_engine_config: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    if explicit_engine_config is not None:
        return dict(explicit_engine_config)
    engine_config = _get_value(engine_state, "engine_config")
    if isinstance(engine_config, Mapping):
        return dict(engine_config)
    meta = _get_value(engine_state, "meta", {})
    if isinstance(meta, Mapping):
        scenario_ai = meta.get("ai")
        if isinstance(scenario_ai, Mapping):
            return dict(scenario_ai.get("engine_config") or {})
    return {}


def _resolve_side_for_controller(
    explicit_side: str | None,
    engine_config: Mapping[str, Any],
    engine_state: Any,
) -> str:
    if explicit_side:
        return _normalize_side(explicit_side)

    side = engine_config.get("ai_side")
    if side:
        return _normalize_side(side)

    run = engine_config.get("run")
    if isinstance(run, Mapping) and run.get("ai_side"):
        return _normalize_side(run.get("ai_side"))

    meta = _get_value(engine_state, "meta", {})
    if isinstance(meta, Mapping):
        scenario_ai = meta.get("ai")
        if isinstance(scenario_ai, Mapping) and scenario_ai.get("side"):
            return _normalize_side(scenario_ai.get("side"))

    return ""


def _resolve_time_budget(
    *,
    explicit_budget_ms: int | None,
    engine_config: Mapping[str, Any],
    default_budget_ms: int,
) -> int:
    if explicit_budget_ms is not None:
        return int(explicit_budget_ms)
    run = engine_config.get("run")
    if isinstance(run, Mapping) and run.get("time_budget_ms") is not None:
        return int(run.get("time_budget_ms"))
    if engine_config.get("time_budget_ms") is not None:
        return int(engine_config.get("time_budget_ms"))
    return int(default_budget_ms)


__all__ = ["BAIController", "BAIControllerConfig", "BAIControllerResult"]
