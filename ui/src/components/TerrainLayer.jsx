import React from "react";
import { axialToPixel, hexPolygonPoints } from "../lib/hex.js";

const TERRAIN_FILL = {
  hill: "rgba(170, 140, 90, 0.28)",
  forest: "rgba(70, 120, 70, 0.28)",
  woods: "rgba(70, 120, 70, 0.28)",
  urban: "rgba(120, 120, 135, 0.28)",
  city: "rgba(120, 120, 135, 0.28)",
  water: "rgba(70, 120, 190, 0.34)",
  river: "rgba(70, 120, 190, 0.26)",
  beach: "rgba(190, 180, 120, 0.26)",
};

export default function TerrainLayer({ meta = {}, terrain = {} }) {
  const hexSize = Number(meta.hexSize ?? 22);
  const padX = Number(meta.padX ?? 60);
  const padY = Number(meta.padY ?? 80);
  const tiles = Array.isArray(terrain?.tiles) ? terrain.tiles : [];

  return (
    <g className="terrain-layer">
      {tiles.map((tile, idx) => {
        const q = Number(tile?.q ?? tile?.x ?? tile?.position?.[0]);
        const r = Number(tile?.r ?? tile?.y ?? tile?.position?.[1]);
        if (!Number.isFinite(q) || !Number.isFinite(r)) {
          return null;
        }
        const kind = String(tile?.type ?? tile?.terrain ?? "plain").toLowerCase();
        const p = axialToPixel(q, r, hexSize);
        return (
          <polygon
            key={`${q},${r},${idx}`}
            className="terrain-hex"
            points={hexPolygonPoints(p.x + padX, p.y + padY, hexSize)}
            fill={TERRAIN_FILL[kind] ?? "rgba(255,255,255,0.04)"}
            stroke="rgba(255,255,255,0.04)"
            strokeWidth="1"
          />
        );
      })}
    </g>
  );
}
