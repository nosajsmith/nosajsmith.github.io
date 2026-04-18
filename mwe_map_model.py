from __future__ import annotations

"""Canonical runtime map model shared by engine and server import paths."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Optional


class Terrain(str, Enum):
    PLAINS = "PLAINS"
    CLEAR = PLAINS
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    URBAN = "URBAN"
    SWAMP = "SWAMP"
    DESERT = "DESERT"
    COAST = "COAST"
    OCEAN = "OCEAN"
    WATER = OCEAN

    @staticmethod
    def coerce(value: str | None) -> "Terrain":
        if value is None:
            return Terrain.PLAINS

        normalized = str(value).strip().upper()
        aliases = {
            "CLEAR": "PLAINS",
            "PLAIN": "PLAINS",
            "OPEN": "PLAINS",
            "FIELD": "PLAINS",
            "FOREST": "JUNGLE",
            "WOODS": "JUNGLE",
            "CITY": "URBAN",
            "TOWN": "URBAN",
            "WATER": "OCEAN",
            "SEA": "OCEAN",
        }
        normalized = aliases.get(normalized, normalized)

        try:
            return Terrain(normalized)
        except ValueError:
            return Terrain.PLAINS


@dataclass
class MapTile:
    """
    Canonical mutable map tile model.

    Older tests and gameplay helpers still patch fields such as `is_port`
    post-construction, so this remains intentionally mutable.
    """

    tile_id: str
    name: str = ""
    terrain: Terrain = Terrain.PLAINS
    base_move_cost: int = 1
    defense_bonus: int = 0
    supply_bonus: int = 0
    is_port: bool = False
    is_airfield: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["terrain"] = self.terrain.value
        return data


class GameMap:
    def __init__(self) -> None:
        self._tiles: Dict[str, MapTile] = {}

    def add_tile(self, tile: MapTile) -> None:
        self._tiles[tile.tile_id] = tile

    def get_tile(self, tile_id: str) -> Optional[MapTile]:
        return self._tiles.get(tile_id)

    def get(self, tile_id: str, default: Optional[MapTile] = None) -> Optional[MapTile]:
        return self._tiles.get(tile_id, default)

    def tiles(self) -> Iterable[MapTile]:
        return self._tiles.values()

    def tile_ids(self) -> Iterable[str]:
        return self._tiles.keys()

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {tile_id: tile.to_dict() for tile_id, tile in self._tiles.items()}


__all__ = ["Terrain", "MapTile", "GameMap"]
