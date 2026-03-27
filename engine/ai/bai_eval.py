from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping


@dataclass
class ScoreComponent:
    name: str
    value: float
    weight: float
    contribution: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationScore:
    label: str = ""
    base: float = 0.0
    total: float = 0.0
    components: List[ScoreComponent] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    dominant_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "base": self.base,
            "total": self.total,
            "components": [component.to_dict() for component in self.components],
            "reasons": list(self.reasons),
            "dominant_reason": self.dominant_reason,
        }


def clamp(value: Any, low: float, high: float, default: float | None = None) -> float:
    numeric = coerce_float(value, default if default is not None else low)
    return max(low, min(high, numeric))


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_evaluation(
    label: str,
    *,
    components: Iterable[ScoreComponent],
    base: float = 0.0,
) -> EvaluationScore:
    component_list = list(components)
    rounded_base = round(coerce_float(base), 3)
    total = rounded_base + sum(component.contribution for component in component_list)
    ranked = sorted(
        [component for component in component_list if component.reason],
        key=lambda component: (abs(component.contribution), component.name),
        reverse=True,
    )
    reasons = [component.reason for component in ranked[:3]]
    return EvaluationScore(
        label=label,
        base=rounded_base,
        total=round(total, 3),
        components=component_list,
        reasons=reasons,
        dominant_reason=reasons[0] if reasons else "",
    )


def objective_value_component(
    objective_value: Any,
    *,
    weight: float = 1.0,
    scale: float = 100.0,
    label: str = "Objective value",
) -> ScoreComponent:
    raw_value = max(0.0, coerce_float(objective_value))
    normalized = clamp(raw_value / max(1.0, scale), 0.0, 2.5)
    return _component(
        "objective_value",
        normalized,
        weight,
        f"{label} {raw_value:.0f} shapes the decision.",
    )


def terrain_value_for_location(game_map: Any, location_id: str) -> float:
    if not location_id or game_map is None:
        return 0.0

    tile = None
    if hasattr(game_map, "get_tile") and callable(getattr(game_map, "get_tile")):
        tile = game_map.get_tile(location_id)
    elif hasattr(game_map, "get") and callable(getattr(game_map, "get")):
        tile = game_map.get(location_id)
    elif isinstance(game_map, Mapping):
        tile = game_map.get(location_id)

    if tile is None:
        return 0.0

    terrain = str(getattr(getattr(tile, "terrain", None), "value", getattr(tile, "terrain", "")) or "").upper()
    scores = {
        "URBAN": 1.5,
        "MOUNTAIN": 1.4,
        "JUNGLE": 1.2,
        "SWAMP": 1.1,
        "COAST": 0.95,
        "CLEAR": 1.0,
        "PLAINS": 1.0,
        "OCEAN": 0.1,
        "WATER": 0.1,
    }
    defense_bonus = coerce_float(getattr(tile, "defense_bonus", 0))
    return round(scores.get(terrain, 1.0) + (defense_bonus / 10.0), 3)


def terrain_value_component(
    game_map: Any,
    location_id: str,
    *,
    weight: float = 1.0,
    label: str = "Terrain value",
) -> ScoreComponent:
    terrain_value = terrain_value_for_location(game_map, location_id)
    normalized = clamp(terrain_value / 1.5, 0.0, 1.5)
    return _component(
        "terrain_value",
        normalized,
        weight,
        f"{label} at {location_id} rates {terrain_value:.2f}.",
    )


def force_ratio(
    friendly_strength: Any,
    enemy_strength: Any,
) -> float:
    friendly = max(0.0, coerce_float(friendly_strength))
    enemy = max(1.0, coerce_float(enemy_strength, 1.0))
    return round(friendly / enemy, 3)


def force_ratio_component(
    friendly_strength: Any,
    enemy_strength: Any,
    *,
    weight: float = 1.0,
    label: str = "Force ratio",
) -> ScoreComponent:
    ratio = force_ratio(friendly_strength, enemy_strength)
    normalized = clamp(ratio - 1.0, -1.0, 2.0, default=0.0)
    return _component(
        "force_ratio",
        normalized,
        weight,
        f"{label} is {ratio:.2f} to 1 in the local sector.",
    )


def supply_feasibility(
    available_supply: Any,
    *,
    floor: float = 45.0,
    ceiling: float = 80.0,
) -> float:
    supply = coerce_float(available_supply)
    span = max(1.0, ceiling - floor)
    return round(clamp((supply - floor) / span, -1.0, 1.5, default=0.0), 3)


def supply_feasibility_component(
    available_supply: Any,
    *,
    floor: float = 45.0,
    ceiling: float = 80.0,
    weight: float = 1.0,
    label: str = "Supply feasibility",
) -> ScoreComponent:
    feasibility = supply_feasibility(available_supply, floor=floor, ceiling=ceiling)
    return _component(
        "supply_feasibility",
        feasibility,
        weight,
        f"{label} is {coerce_float(available_supply):.0f} against floor {coerce_float(floor):.0f}.",
    )


def enemy_threat(
    enemy_strength: Any,
    friendly_strength: Any,
    *,
    contested: bool = False,
) -> float:
    enemy = max(0.0, coerce_float(enemy_strength))
    friendly = max(1.0, coerce_float(friendly_strength, 1.0))
    ratio = enemy / friendly
    contested_bonus = 0.2 if contested else 0.0
    return round(clamp((ratio / 2.0) + contested_bonus, 0.0, 1.5, default=0.0), 3)


def enemy_threat_component(
    enemy_strength: Any,
    friendly_strength: Any,
    *,
    contested: bool = False,
    weight: float = 1.0,
    label: str = "Enemy threat",
) -> ScoreComponent:
    threat = enemy_threat(enemy_strength, friendly_strength, contested=contested)
    return _component(
        "enemy_threat",
        threat,
        weight,
        f"{label} is {threat:.2f} in the current sector.",
    )


def reserve_requirement(
    target_fraction: Any,
    current_fraction: Any,
) -> float:
    target = clamp(target_fraction, 0.0, 1.0, default=0.0)
    current = clamp(current_fraction, 0.0, 1.0, default=0.0)
    return round(clamp((target - current) / 0.5, 0.0, 1.5, default=0.0), 3)


def reserve_requirement_component(
    target_fraction: Any,
    current_fraction: Any,
    *,
    weight: float = 1.0,
    label: str = "Reserve requirement",
) -> ScoreComponent:
    requirement = reserve_requirement(target_fraction, current_fraction)
    return _component(
        "reserve_requirement",
        requirement,
        weight,
        f"{label} gap is {requirement:.2f} against target reserve {clamp(target_fraction, 0.0, 1.0, default=0.0):.2f}.",
    )


def doctrinal_bias_component(
    bias_value: Any,
    *,
    baseline: float = 0.5,
    weight: float = 1.0,
    label: str = "Doctrinal bias",
) -> ScoreComponent:
    bias = clamp(coerce_float(bias_value, baseline) - baseline, -0.5, 0.5, default=0.0)
    raw_value = clamp(bias_value, 0.0, 1.0, default=baseline)
    return _component(
        "doctrinal_bias",
        bias,
        weight,
        f"{label} is {raw_value:.2f} versus baseline {baseline:.2f}.",
    )


def location_strength(units: Iterable[Any], location_id: str, *, field_name: str = "strength") -> float:
    total = 0.0
    for unit in units:
        unit_location = getattr(getattr(unit, "location_id", None), "value", getattr(unit, "location_id", None))
        if str(unit_location or "") != str(location_id or ""):
            continue
        raw_value = getattr(getattr(unit, field_name, 0), "value", getattr(unit, field_name, 0))
        total += max(0.0, coerce_float(raw_value))
    return round(total, 3)


def _component(name: str, value: float, weight: float, reason: str) -> ScoreComponent:
    rounded_value = round(coerce_float(value), 3)
    rounded_weight = round(coerce_float(weight, 1.0), 3)
    return ScoreComponent(
        name=name,
        value=rounded_value,
        weight=rounded_weight,
        contribution=round(rounded_value * rounded_weight, 3),
        reason=reason,
    )


__all__ = [
    "EvaluationScore",
    "ScoreComponent",
    "build_evaluation",
    "clamp",
    "coerce_float",
    "doctrinal_bias_component",
    "enemy_threat",
    "enemy_threat_component",
    "force_ratio",
    "force_ratio_component",
    "location_strength",
    "objective_value_component",
    "reserve_requirement",
    "reserve_requirement_component",
    "supply_feasibility",
    "supply_feasibility_component",
    "terrain_value_component",
    "terrain_value_for_location",
]
