# -*- coding: utf-8 -*-
from typing import Dict, Tuple, List, Callable
from dataclasses import dataclass
from pathfinding import a_star
from zoc import zoc_map, zoc_cost
Coord=Tuple[int,int]
@dataclass
class MovementLog:
    unit_id:str; start:Coord; end:Coord; path:List[Coord]; mp_spent:float; blocked:bool=False; reason:str=''
UNIT_MP={'inf':8.0,'arm':12.0,'mech':12.0,'eng':8.0,'arty':6.0}
def default_cost_fn(terrain_cost,ground_mod,zoc_cells):
    def cost(a,b):
        tc=terrain_cost(b); gm=ground_mod(b); zc=zoc_cost(b,zoc_cells,base=1.0); return tc+gm+zc
    return cost
def move_unit(unit,target,terrain_cost,ground_mod,enemy_positions):
    uid=unit['id']; pos=tuple(unit['pos']); mp_total=UNIT_MP.get(unit.get('type','inf'),8.0); zoc_cells=zoc_map(enemy_positions)
    path,total=a_star(pos,target,default_cost_fn(terrain_cost,ground_mod,zoc_cells))
    if not path: return MovementLog(uid,pos,pos,[pos],0.0,True,'no_path')
    spent=0.0; cur=pos; walked=[pos]
    for i in range(1,len(path)):
        step=default_cost_fn(terrain_cost,ground_mod,zoc_cells)(path[i-1],path[i])
        if spent+step>mp_total: break
        spent+=step; cur=path[i]; walked.append(cur)
    blocked=(cur!=target); reason='mp_exhausted' if blocked else ''
    return MovementLog(uid,pos,cur,walked,spent,blocked,reason)
