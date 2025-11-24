# terrain.py
from __future__ import annotations
from typing import Dict, Tuple, List, Optional
import json, os

Coord = Tuple[int, int]

class TerrainMap:
    def __init__(self, path: str = "terrain.json"):
        self.path = path
        self.width = 0
        self.height = 0
        self.tiles: Dict[Coord, str] = {}   # (x,y)->type
        self.roads: List[List[Coord]] = []  # list of polylines

        self._load(path)

    def _load(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            # empty map
            return
        self.width = int(d.get("width", 20))
        self.height = int(d.get("height", 20))
        for t in d.get("tiles", []):
            x, y = t["pos"]
            self.tiles[(int(x), int(y))] = t.get("type", "clear")
        self.roads = [[(int(x), int(y)) for x, y in seg] for seg in d.get("roads", [])]

    def get(self, x: int, y: int) -> str:
        return self.tiles.get((x, y), "clear")

    def has_road_between(self, a: Coord, b: Coord) -> bool:
        # returns True if any road polyline includes consecutive a->b
        for line in self.roads:
            for p, q in zip(line[:-1], line[1:]):
                if (p == a and q == b) or (p == b and q == a):
                    return True
        return False

    def is_river_between(self, a: Coord, b: Coord) -> bool:
        # Any side with a 'river' tile and NO road directly connecting a<->b counts as river crossing
        if self.has_road_between(a,b):
            return False
        ax, ay = a; bx, by = b
        return self.get(ax, ay) == "river" or self.get(bx, by) == "river"
