# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass, asdict
from movement_engine import move_unit, MovementLog
from combat_resolver import resolve_combat, CombatEvent
Coord=Tuple[int,int]
@dataclass
class ExecutionReport: movements:List[MovementLog]; combats:List[CombatEvent]
def execute_orders(orders,units,enemy_units,terrain_cost_fn,terrain_type_fn,ground_mod_fn):
    uid_to={u['id']:u for u in units}; enemy_positions=[tuple(e['pos']) for e in enemy_units]; mlogs=[]; combats=[]
    for o in orders:
        if o['order_type'] in ('attack','probe','redeploy'):
            u=uid_to.get(o['unit_id']); 
            if not u: continue
            tgt=tuple(o['target_hex']) if o.get('target_hex') else tuple(u['pos'])
            log=move_unit(u,tgt,terrain_cost_fn,ground_mod_fn,enemy_positions); mlogs.append(log); u['pos']=list(log.end)
    for o in orders:
        if o['order_type'] in ('attack','probe'):
            atk=uid_to.get(o['unit_id']); 
            if not atk or not o.get('target_hex'): continue
            loc=tuple(o['target_hex'])
            for e in enemy_units:
                if tuple(e['pos'])==loc:
                    ce=resolve_combat(atk,e,loc,terrain_type_fn,lambda _: 'dry',enemy_positions); combats.append(ce); break
    return ExecutionReport(mlogs,combats)
