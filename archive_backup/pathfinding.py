# -*- coding: utf-8 -*-
from typing import Dict, Tuple, List, Callable
import heapq
Coord = Tuple[int,int]
HEX_DIRS = [(1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1)]
def neighbors(a: Coord) -> List[Coord]:
    q,r = a; return [(q+dq, r+dr) for dq,dr in HEX_DIRS]
def heuristic(a: Coord, b: Coord) -> float:
    dq = abs(a[0]-b[0]); dr = abs(a[1]-b[1]); ds = abs((-a[0]-a[1]) - (-b[0]-b[1])); return max(dq, dr, ds)
def a_star(start: Coord, goal: Coord, cost_fn: Callable[[Coord,Coord], float], max_iters: int = 5000):
    frontier=[]; heapq.heappush(frontier,(0,start)); came={}; g={start:0.0}
    while frontier and max_iters>0:
        max_iters-=1; _,cur=heapq.heappop(frontier)
        if cur==goal:
            path=[cur]
            while cur in came: cur=came[cur]; path.append(cur)
            path.reverse(); return path,g[goal]
        for n in neighbors(cur):
            step=cost_fn(cur,n)
            if step>=1e9: continue
            new=g[cur]+step
            if n not in g or new<g[n]:
                g[n]=new; came[n]=cur; f=new+heuristic(n,goal); heapq.heappush(frontier,(f,n))
    return None,float('inf')
