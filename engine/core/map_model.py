from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional, List


class Terrain(str, Enum):
    PLAINS = "PLAINS"
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    URBAN = "URBAN"
    COAST = "COAST"
    OCEAN = "OCEAN"


@dataclass
class MapTile:
    tile_id: str
    name: str = ""
    terrain: Terrain = Terrain.PLAINS

    # Optional gameplay knobs (scenario_loader will pass these if present;
    # harmless if unused by current movement/battle)
    base_move_cost: int = 1
    defense_bonus: int = 0
    supply_bonus: int = 0
    is_airfield: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["terrain"] = self.terrain.value
        return d


class GameMap:
    """
    Minimal map container.

    Required by staff modules:
      - get(tile_id) -> Optional[MapTile]
    """

    def __init__(self) -> None:
        self._tiles: Dict[str, MapTile] = {}

    def add_tile(self, tile: MapTile) -> None:
        self._tiles[tile.tile_id] = tile

    def get(self, tile_id: str, default: Optional[MapTile] = None) -> Optional[MapTile]:
        """
        Dict-like accessor used by staff code (G-3).
        """
        return self._tiles.get(tile_id, default)

    def tiles(self) -> List[MapTile]:
        return list(self._tiles.values())

    def to_dict(self) -> Dict[str, Any]:
        return {tid: tile.to_dict() for tid, tile in self._tiles.items()}
