import React from "react";

function sideAccent(side) {
  const normalized = String(side || "").toUpperCase();
  if (normalized === "ALLIED") return "#7fd7c0";
  if (normalized === "AXIS") return "#f08b96";
  return "#d6dee9";
}

export default function SupplyLayer({ supplyNodes = [] }) {
  return (
    <g className="mwe-supply-layer" pointerEvents="none">
      {supplyNodes.map((node) => {
        const accent = sideAccent(node.side);
        return (
          <g key={node.id} transform={`translate(${node.px},${node.py + 24})`}>
            <path
              d="M0,-8 L8,0 L0,8 L-8,0 Z"
              fill="rgba(10, 18, 30, 0.86)"
              stroke={accent}
              strokeWidth={1.5}
            />
            <text x={14} y={4} className="supply-label">
              {node.dailySupply}
            </text>
          </g>
        );
      })}
    </g>
  );
}
