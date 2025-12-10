"""
Map model for MWE.

- Terrain enum
- MapTile dataclass
- GameMap container with simple helpers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Terrain(Enum):
    PLAINS = "PLAINS"
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    WATER = "WATER"
    COAST = "COAST"
    URBAN = "URBAN"
    OCEAN = "OCEAN"
    CLEAR = "CLEAR"  # can be used for open, good-going terrain


@dataclass
class MapTile:
    """
    Single map tile / hex.
    """
    tile_id: str
    name: str
    terrain: Terrain
    base_move_cost: int = 1
    is_port: bool = False
    is_airfield: bool = False


@dataclass
class GameMap:
    """
    Lightweight container for map tiles.

    tiles: dict keyed by tile_id.
    neighbors: optional adjacency list (not heavily used yet).
    """
    tiles: Dict[str, MapTile] = field(default_factory=dict)
    neighbors: Dict[str, List[str]] = field(default_factory=dict)

    def get(self, tile_id: str) -> Optional[MapTile]:
        return self.tiles.get(tile_id)

    def get_neighbors(self, tile_id: str) -> List[str]:
        return self.neighbors.get(tile_id, [])

    def to_dict(self) -> Dict[str, Dict[str, object]]:
        """
        Serialize for UI/bridge.
        """
        out: Dict[str, Dict[str, object]] = {}
        for tid, tile in self.tiles.items():
            out[tid] = {
                "id": tile.tile_id,
                "name": tile.name,
                "terrain": tile.terrain.value,
                "base_move_cost": tile.base_move_cost,
                "is_port": tile.is_port,
                "is_airfield": tile.is_airfield,
            }
        return out
