import React from "react";

function sideStyle(side) {
  const s = String(side || "").toLowerCase();
  if (s === "blue") return { stroke: "#5aa2ff", fill: "rgba(90,162,255,0.18)" };
  if (s === "red") return { stroke: "#ff5a7a", fill: "rgba(255,90,122,0.18)" };
  return { stroke: "#c0c6d4", fill: "rgba(192,198,212,0.12)" };
}

export default function UnitLayer({
  units = [],
  selectedId = null,
  onSelect = null,
}) {
  function onMouseDownUnit(e, u) {
    e.stopPropagation();
    e.preventDefault();
    if (onSelect) onSelect(u);
  }

  return (
    <g className="mwe-unit-layer">
      {units.map((u) => {
        const x = Number(u.px ?? 0);
        const y = Number(u.py ?? 0);

        const isSel = selectedId && u.id === selectedId;
        const base = sideStyle(u.side);
        const r = isSel ? 11 : 9;
        const strokeW = isSel ? 2.5 : 2;

        return (
          <g
            key={u.id}
            transform={`translate(${x},${y})`}
            style={{ cursor: "pointer" }}
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
