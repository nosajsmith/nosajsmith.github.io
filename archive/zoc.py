# -*- coding: utf-8 -*-
from typing import Dict, Tuple, Iterable, Set
Coord=Tuple[int,int]; HEX_DIRS=[(1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1)]
def zoc_map(enemy_positions: Iterable[Coord]) -> Set[Coord]:
    s=set()
    for q,r in enemy_positions:
        s.add((q,r))
        for dq,dr in HEX_DIRS: s.add((q+dq,r+dr))
    return s
def zoc_cost(cell: Coord, zoc: Set[Coord], base: float=1.0)->float: return base if cell in zoc else 0.0
