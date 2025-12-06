"""
Game Map Model for MWE
Compatible with Phase 8 engine and scenario loader.
"""

from __future__ import annotations
from typing import Dict, Optional
from enum import Enum


class Terrain(Enum):
    """
    Terrain types used by the engine and scenarios.

    Includes both older names (PLAINS, OCEAN) and newer ones so that
    existing scenarios continue to load.
    """
    PLAINS = "PLAINS"
    CLEAR = "CLEAR"
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    WATER = "WATER"
    OCEAN = "OCEAN"


class MapTile:
    """
    A single hex/tile on the map.
    """

    def __init__(
        self,
        tile_id: str,
        terrain: Terrain = Terrain.PLAINS,
        base_move_cost: int = 1,
        is_port: bool = False,
        is_airfield: bool = False,
    ) -> None:
        self.id = tile_id
        self.terrain = terrain
        self.base_move_cost = base_move_cost
        self.is_port = is_port
        self.is_airfield = is_airfield


class GameMap:
    """
    Phase 8-compatible map model:
    GameMap(tiles: Dict[str, MapTile])
    """

    def __init__(self, tiles: Dict[str, MapTile]) -> None:
        self.tiles: Dict[str, MapTile] = tiles

    def get_tile(self, tile_id: str) -> Optional[MapTile]:
        return self.tiles.get(tile_id)

    def neighbors(self, tile_id: str) -> list[str]:
        """
        Placeholder adjacency. You can define neighbors in scenario metadata later.
        For now, return an empty list to avoid errors.
        """
        return []
