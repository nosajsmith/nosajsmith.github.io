import React, { useEffect, useRef, useState } from "react";
import { pixelToAxial, axialRound, axialToPixel } from "../lib/hex.js";

function sideStyle(side) {
  const s = String(side || "").toLowerCase();
  if (s === "blue") return { stroke: "#5aa2ff", fill: "rgba(90,162,255,0.18)" };
  if (s === "red") return { stroke: "#ff5a7a", fill: "rgba(255,90,122,0.18)" };
  return { stroke: "#c0c6d4", fill: "rgba(192,198,212,0.12)" };
}

export default function UnitLayer({
  meta = {},
  units = [],
  selectedId = null,
  onSelect = null,

  // NEW
  onDragStateChange = null, // (bool) => void
  onUnitMove = null,        // (id, {q,r,px,py}) => void
}) {
  const hexSize = Number(meta.hexSize ?? 22);
  const padX = Number(meta.padX ?? 60);
  const padY = Number(meta.padY ?? 80);

  const [dragId, setDragId] = useState(null);
  const [dragPxPy, setDragPxPy] = useState(null);

  // notify pan lock/unlock
  useEffect(() => {
    if (onDragStateChange) onDragStateChange(Boolean(dragId));
  }, [dragId, onDragStateChange]);

  function onMouseDownUnit(e, u) {
    e.stopPropagation();
    e.preventDefault();
    setDragId(u.id);
    setDragPxPy({ px: u.px, py: u.py });
    if (onSelect) onSelect(u);
  }

  function onMouseMove(e) {
    if (!dragId) return;
    // movement in screen coords; simplest: use SVG client coords approximated from mouse.
    // We rely on the existing PanZoomSvg transform keeping things consistent; for now,
    // we just move the label locally (visual), then snap on mouseup.
    setDragPxPy((cur) => {
      if (!cur) return cur;
      return { px: cur.px + e.movementX, py: cur.py + e.movementY };
    });
  }

  function onMouseUp(e) {
    if (!dragId) return;

    const id = dragId;
    const pos = dragPxPy;
    setDragId(null);
    setDragPxPy(null);

    if (!pos) return;

    // snap to nearest hex (px/py -> axial fractional -> round)
    const localX = pos.px - padX;
    const localY = pos.py - padY;

    const frac = pixelToAxial(localX, localY, hexSize);
    const snapped = axialRound(frac.q, frac.r);

    const p = axialToPixel(snapped.q, snapped.r, hexSize);
    const out = {
      q: snapped.q,
      r: snapped.r,
      px: p.x + padX,
      py: p.y + padY,
    };

    if (onUnitMove) onUnitMove(id, out);
  }

  return (
    <g
      className="mwe-unit-layer"
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      {units.map((u) => {
        const isDrag = dragId === u.id;
        const x = Number((isDrag ? dragPxPy?.px : u.px) ?? 0);
        const y = Number((isDrag ? dragPxPy?.py : u.py) ?? 0);

        const isSel = selectedId && u.id === selectedId;
        const base = sideStyle(u.side);
        const r = isSel ? 11 : 9;
        const strokeW = isSel ? 2.5 : 2;

        return (
          <g
            key={u.id}
            transform={`translate(${x},${y})`}
            style={{ cursor: isDrag ? "grabbing" : "grab" }}
            onMouseDown={(e) => onMouseDownUnit(e, u)}
          >
            <circle r={r} fill={base.fill} stroke={base.stroke} strokeWidth={strokeW} />
            <text
              x={14}
              y={4}
              fontSize={12}
              fill="rgba(230,235,245,0.9)"
              style={{ userSelect: "none", pointerEvents: "none" }}
            >
              {u.name}
            </text>
          </g>
        );
      })}
    </g>
  );
}
