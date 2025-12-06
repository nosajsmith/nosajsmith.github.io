"""
Map model for MWE engine.

Defines:
- Terrain enum
- MapTile dataclass
- GameMap container with lookup helpers
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

class Terrain(Enum):
    PLAINS = "PLAINS"
    CLEAR = "CLEAR"
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    URBAN = "URBAN"
    COAST = "COAST"
    WATER = "WATER"
    OCEAN = "OCEAN"

    @classmethod
    def _missing_(cls, value):
        """
        Be forgiving with terrain strings from JSON.
        Accept things like "Plains", "plain", "Ocean", etc.
        """
        if isinstance(value, str):
            v = value.strip().upper()

            # Simple aliases
            aliases = {
                "SEA": "OCEAN",
                "JUNG": "JUNGLE",
            }
            if v in aliases:
                return cls[aliases[v]]

            if v in cls.__members__:
                return cls[v]

        raise ValueError(f"{value!r} is not a valid Terrain")


# ---------------------------------------------------------------------------
# Tile + Map
# ---------------------------------------------------------------------------

@dataclass
class MapTile:
    tile_id: str
    terrain: Terrain
    name: str = ""
    is_port: bool = False
    is_airfield: bool = False

    # New: base movement cost used by future pathfinding / ops
    base_move_cost: int = 1


class GameMap:
    """
    Very simple map wrapper for now.

    Internally stores a dict of tile_id -> MapTile.
    """

    def __init__(self, tiles: Dict[str, MapTile]) -> None:
        self.tiles: Dict[str, MapTile] = dict(tiles)

    # Basic lookups ---------------------------------------------------------

    def get(self, tile_id: str) -> Optional[MapTile]:
        """Return the MapTile for a given location_id / tile_id, or None."""
        return self.tiles.get(tile_id)

    def get_title(self, tile_id: str) -> str:
        """Convenience; returns the tile's name or the id if missing."""
        tile = self.tiles.get(tile_id)
        if tile is None:
            return tile_id
        return tile.name or tile.tile_id

    def all_tiles(self) -> List[MapTile]:
        return list(self.tiles.values())

    # Neighbor hooks (stub) -------------------------------------------------

    def neighbors(self, tile_id: str) -> List[str]:
        """
        Placeholder for future hex grid / adjacency logic.
        For now, returns an empty list so callers can safely iterate.
        """
        return []
