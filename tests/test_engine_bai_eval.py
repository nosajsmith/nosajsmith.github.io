from __future__ import annotations

from engine.ai import (
    build_evaluation,
    doctrinal_bias_component,
    enemy_threat_component,
    force_ratio,
    force_ratio_component,
    objective_value_component,
    reserve_requirement_component,
    supply_feasibility_component,
    terrain_value_component,
    terrain_value_for_location,
)
from engine.core.map_model import GameMap, MapTile, Terrain


def test_bai_eval_helpers_build_reusable_explainable_scores():
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="RIDGE", name="Hill Ridge", terrain=Terrain.MOUNTAIN))
    game_map.add_tile(MapTile(tile_id="PLAIN", name="Open Plain", terrain=Terrain.PLAINS))

    evaluation = build_evaluation(
        "test_attack",
        base=0.1,
        components=[
            objective_value_component(100, weight=1.2, label="Enemy objective"),
            terrain_value_component(game_map, "RIDGE", weight=-0.2, label="Terrain resistance"),
            force_ratio_component(120, 80, weight=0.3, label="Local force ratio"),
            supply_feasibility_component(70, floor=45, weight=0.2, label="Supply feasibility"),
            enemy_threat_component(80, 120, contested=True, weight=-0.1, label="Enemy threat"),
            reserve_requirement_component(0.3, 0.0, weight=-0.2, label="Reserve requirement"),
            doctrinal_bias_component(0.8, weight=0.2, label="Doctrinal aggression"),
        ],
    )

    assert terrain_value_for_location(game_map, "RIDGE") > terrain_value_for_location(game_map, "PLAIN")
    assert force_ratio(120, 80) == 1.5
    assert evaluation.total != 0
    assert evaluation.dominant_reason
    assert len(evaluation.components) == 7
    assert any(component.name == "objective_value" for component in evaluation.components)
    assert evaluation.to_dict()["reasons"]
