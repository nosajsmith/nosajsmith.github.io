# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Dict, Tuple, List, Callable
from pathfinding import a_star
from zoc import zoc_map
Coord=Tuple[int,int]
@dataclass
class CombatEvent:
    attacker:str; defender:str; location:Coord; odds:float; result:str; atk_losses:int; def_losses:int; defender_retreat_path:List[Coord]
def terrain_defense_bonus(t:str)->float: return {'clear':1.0,'hills':1.2,'woods':1.3,'urban':1.5,'fort':1.6}.get(t,1.0)
def resolve_combat(attacker,defender,location,terrain_at,ground_at,enemy_positions):
    atk=attacker.get('strength',100); df=defender.get('strength',80); terr=terrain_at(location); bonus=terrain_defense_bonus(terr); odds=(atk/max(1,df*bonus))
    if odds>=1.5: result='attacker_win'; atk_loss=int(atk*0.05); def_loss=int(df*0.3)
    elif odds>=1.0: result='stalemate'; atk_loss=int(atk*0.12); def_loss=int(df*0.12)
    else: result='defender_hold'; atk_loss=int(atk*0.2); def_loss=int(df*0.08)
    retreat=[]; 
    if result=='attacker_win':
        zoc=zoc_map(enemy_positions); aq,ar=attacker['pos']; dq,dr=defender['pos']; target=(dq+(dq-aq),dr+(dr-ar)); path,_=a_star((dq,dr),target,lambda a,b:1.0 if b not in zoc else 5.0); retreat=path or []
    return CombatEvent(attacker['id'],defender['id'],location,round(odds,2),result,atk_loss,def_loss,retreat)
