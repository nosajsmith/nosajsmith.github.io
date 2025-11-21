"""
Map model for MWE.

Very simple start:
- Map is a collection of areas/hexes
- Each tile has terrain and movement cost
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class Terrain(str, Enum):
    OCEAN = "Ocean"
    COAST = "Coast"
    PLAINS = "Plains"
    JUNGLE = "Jungle"
    MOUNTAIN = "Mountain"
    URBAN = "Urban"


@dataclass
class MapTile:
    id: str                 # e.g. hex code or area name
    terrain: Terrain
    base_move_cost: int = 1
    is_port: bool = False
    is_airfield: bool = False


class GameMap:
    """
    Simple container for map tiles.

    Later you can add neighbors, distance calculations, etc.
    """

    def __init__(self) -> None:
        self._tiles: Dict[str, MapTile] = {}

    def add_tile(self, tile: MapTile) -> None:
        self._tiles[tile.id] = tile

    def get(self, tile_id: str) -> Optional[MapTile]:
        return self._tiles.get(tile_id)

    def all_tiles(self):
        return list(self._tiles.values())
