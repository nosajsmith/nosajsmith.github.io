import React, { useMemo } from "react";
import { axialToPixel, hexPolygonPoints } from "../lib/hex.js";

export default function HexGrid({ meta = {} }) {
  const hexSize = Number(meta.hexSize ?? 22);
  const padX = Number(meta.padX ?? 60);
  const padY = Number(meta.padY ?? 80);

  // Fallback world size if scenario doesn't define it yet
  const width = Number(meta.width ?? 30);
  const height = Number(meta.height ?? 20);

  const polys = useMemo(() => {
    const out = [];
    for (let r = 0; r < height; r++) {
      for (let q = 0; q < width; q++) {
        const p = axialToPixel(q, r, hexSize);
        const cx = p.x + padX;
        const cy = p.y + padY;
        out.push({
          key: `${q},${r}`,
          points: hexPolygonPoints(cx, cy, hexSize),
        });
      }
    }
    return out;
  }, [hexSize, padX, padY, width, height]);

  return (
    <g className="mwe-hex-grid">
      {polys.map((h) => (
        <polygon
          key={h.key}
          points={h.points}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1"
        />
      ))}
    </g>
  );
}
