# map_overlay.py — adds Plan Validator warning glyphs
from __future__ import annotations
import io, sys, json
from typing import Dict, Any, List, Tuple, Optional
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")

Coord = Tuple[int, int]
_COLORS = {
    "grid": "#e9ecef", "warn": "#f39c12", "err": "#e74c3c",
    "text": "#222", "hq_ring": "rgba(44,62,80,0.15)",
    "unit_blue": "#2b6cb0", "unit_red": "#c53030"
}

def _hex_to_px(x: int, y: int, cell: int) -> Tuple[int,int]:
    return x * cell, y * cell

class MapOverlay:
    def __init__(self, grid_size=(20,20), cell_px=28, out_dir="."):
        self.grid_w, self.grid_h = grid_size
        self.cell = cell_px
        self.out_dir = out_dir

    def render_ascii(self, turn, units):
        grid = [["." for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        for u in units:
            x,y=u.position
            if 0<=x<self.grid_w and 0<=y<self.grid_h:
                grid[y][x]="B" if u.side.upper()=="BLUE" else "R"
        path=f"{self.out_dir}/map_turn{turn}.txt"
        with open(path,"w",encoding="utf-8") as f:
            for row in grid: f.write("".join(row)+"\n")
        return path

    def render_html(self, turn:int, units, plans=None, supply=None,
                    objectives=None, plan_warnings=None, hqs=None,
                    held_units=None) -> str:
        """Render map overlay with plan warning glyphs."""
        cell=self.cell
        W,H=self.grid_w*cell,self.grid_h*cell
        out=f"{self.out_dir}/map_turn{turn}.html"

        def _circle(cx,cy,r,fill,stroke="none",sw=1,op=1.0):
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>'

        def _text(x,y,t,cls="",color="#000"):
            return f'<text x="{x}" y="{y}" font-size="12" fill="{color}" text-anchor="middle">{t}</text>'

        svg=[]
        svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')

        # Grid
        for x in range(self.grid_w+1):
            X=x*cell; svg.append(f'<line x1="{X}" y1="0" x2="{X}" y2="{H}" stroke="#ddd" stroke-width="1"/>')
        for y in range(self.grid_h+1):
            Y=y*cell; svg.append(f'<line x1="0" y1="{Y}" x2="{W}" y2="{Y}" stroke="#ddd" stroke-width="1"/>')

        # Units
        for u in units:
            x,y=u.position; X,Y=_hex_to_px(x,y,cell)
            color=_COLORS["unit_blue"] if u.side.upper()=="BLUE" else _COLORS["unit_red"]
            svg.append(_circle(X+cell/2,Y+cell/2,11,color,"#fff",3))
            svg.append(_text(X+cell/2,Y+cell/2+4,u.unit_id[:6],"","white"))

        # HQ radius / pins (optional)
        if hqs:
            for h in hqs:
                hx,hy=h["pos"]; X,Y=_hex_to_px(hx,hy,cell)
                svg.append(_circle(X+cell/2,Y+cell/2,14,_COLORS["hq_ring"],"#000",1))
                svg.append(_text(X+cell/2,Y+cell/2+5,h["id"],"", "#eee"))

        # --- Plan warning glyphs ---
        if plan_warnings:
            for w in plan_warnings:
                pos=w.get("pos")
                if not pos: continue
                x,y=pos; X,Y=_hex_to_px(x,y,cell)
                lvl=w.get("level","warn")
                msg=w.get("msg","")
                color=_COLORS["err"] if lvl=="error" else _COLORS["warn"]
                # shape + tooltip
                if lvl=="error":
                    svg.append(f'<g><title>{msg}</title>'
                               f'{_circle(X+cell/2,Y+cell/2,10,color)}'
                               f'{_text(X+cell/2,Y+cell/2+4,"!", "", "#fff")}</g>')
                else:
                    pts=[(X+cell/2,Y+4),(X+cell/2-8,Y+cell-4),(X+cell/2+8,Y+cell-4)]
                    pts_s=" ".join(f"{px},{py}" for px,py in pts)
                    svg.append(f'<g><title>{msg}</title>'
                               f'<polygon points="{pts_s}" fill="{color}" />'
                               f'{_text(X+cell/2,Y+cell-8,"⚠","", "#000")}</g>')

        svg.append("</svg>")
        html=f"<html><head><meta charset='utf-8'/><title>Map T{turn}</title></head><body>{''.join(svg)}</body></html>"
        with open(out,"w",encoding="utf-8") as f: f.write(html)
        return out
