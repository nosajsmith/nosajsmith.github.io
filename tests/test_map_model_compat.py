from __future__ import annotations

from engine.core.map_model import GameMap, MapTile, Terrain
from mwe_map_model import GameMap as CanonicalGameMap
from mwe_map_model import MapTile as CanonicalMapTile
from mwe_map_model import Terrain as CanonicalTerrain
from server.engine.core.map_model import (
    GameMap as ServerGameMap,
    MapTile as ServerMapTile,
    Terrain as ServerTerrain,
)


def test_server_map_model_reexports_canonical_engine_types() -> None:
    assert Terrain is CanonicalTerrain
    assert MapTile is CanonicalMapTile
    assert GameMap is CanonicalGameMap
    assert ServerTerrain is CanonicalTerrain
    assert ServerMapTile is CanonicalMapTile
    assert ServerGameMap is CanonicalGameMap


def test_terrain_aliases_and_mutable_map_tile_are_stable() -> None:
    assert Terrain.CLEAR is Terrain.PLAINS
    assert Terrain.WATER is Terrain.OCEAN
    assert Terrain.coerce("clear") is Terrain.PLAINS
    assert Terrain.coerce("coast") is Terrain.COAST
    assert Terrain.coerce("water") is Terrain.OCEAN

    tile = MapTile(tile_id="SEA", terrain=Terrain.COAST)
    tile.is_port = True
    tile.terrain = Terrain.OCEAN

    game_map = GameMap()
    game_map.add_tile(tile)

    stored = game_map.get_tile("SEA")
    assert stored is tile
    assert stored.is_port is True
    assert stored.terrain is Terrain.OCEAN
