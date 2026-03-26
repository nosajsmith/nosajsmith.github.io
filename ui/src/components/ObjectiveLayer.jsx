import React from "react";
import { axialToPixel } from "../lib/hex.js";

export default function ObjectiveLayer({ meta = {}, objectives = [] }) {
  const hexSize = Number(meta.hexSize ?? 22);
  const padX = Number(meta.padX ?? 60);
  const padY = Number(meta.padY ?? 80);

  return (
    <g className="objective-layer">
      {(objectives || []).map((objective) => {
        const pos = Array.isArray(objective?.position) ? objective.position : null;
        const q = pos?.[0];
        const r = pos?.[1];
        if (!Number.isFinite(q) || !Number.isFinite(r)) {
          return null;
        }
        const p = axialToPixel(q, r, hexSize);
        const controlled = objective?.controlled === true;
        return (
          <g key={objective.id || `${q},${r}`} transform={`translate(${p.x + padX},${p.y + padY})`}>
            <circle
              className="objective-pin"
              r="7"
              fill={controlled ? "rgba(45,212,191,0.9)" : "rgba(251,191,36,0.9)"}
              stroke="rgba(10,15,25,0.9)"
              strokeWidth="2"
            />
            <text className="objective-label" x="12" y="4">
              {objective.label || objective.id || "OBJ"}
            </text>
          </g>
        );
      })}
    </g>
  );
}
