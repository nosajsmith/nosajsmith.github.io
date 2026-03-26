import type { CSSProperties } from "react";
import { buildUnitCounterSymbolPresentation } from "../../map/unitCounterSymbol.js";

type UnitCounterSymbolId =
  | "formation"
  | "infantry"
  | "headquarters"
  | "recon"
  | "artillery"
  | "engineer"
  | "armor"
  | "mechanized"
  | "anti_tank"
  | "support";

type UnitCounterSymbolProps = {
  symbol?: UnitCounterSymbolId | null;
  zoom?: number;
  placement?: "counter" | "legend";
  x?: number;
  y?: number;
};

export default function UnitCounterSymbol({ symbol = null, zoom = 1, placement = "counter", x = 0, y = 0 }: UnitCounterSymbolProps) {
  if (!symbol) {
    return null;
  }

  const presentation = buildUnitCounterSymbolPresentation({ symbol, zoom, placement });
  const style = { "--shell-counter-symbol-stroke": String(presentation.strokeWidth) } as CSSProperties;

  return (
    <g
      className="shell-map__unit-symbol"
      transform={`translate(${x} ${y + presentation.offsetY}) scale(${presentation.scale})`}
      style={style}
      aria-hidden="true"
    >
      {symbol === "formation" ? (
        <path className="shell-map__unit-symbol-stroke" d="M0 -3.8 V3.8 M-5.2 0 H5.2" />
      ) : null}
      {symbol === "infantry" ? (
        <path className="shell-map__unit-symbol-stroke" d="M-5.6 -3.7 L5.6 3.7 M5.6 -3.7 L-5.6 3.7" />
      ) : null}
      {symbol === "headquarters" ? (
        <>
          <path className="shell-map__unit-symbol-stroke" d="M-5 4 V-4" />
          <path className="shell-map__unit-symbol-fill" d="M-4.5 -4 H4.8 L1.8 -1.3 H-4.5 Z" />
        </>
      ) : null}
      {symbol === "recon" ? (
        <path className="shell-map__unit-symbol-stroke" d="M-5.7 3.7 L5.7 -3.7" />
      ) : null}
      {symbol === "artillery" ? (
        <circle className="shell-map__unit-symbol-fill" cx="0" cy="0" r="2.2" />
      ) : null}
      {symbol === "engineer" ? (
        <path className="shell-map__unit-symbol-stroke" d="M-5.2 -3 H5.2 M-4.2 0 H4.2 M-5.2 3 H5.2" />
      ) : null}
      {symbol === "armor" ? (
        <ellipse className="shell-map__unit-symbol-stroke" cx="0" cy="0" rx="6.1" ry="3.45" />
      ) : null}
      {symbol === "mechanized" ? (
        <>
          <ellipse className="shell-map__unit-symbol-stroke" cx="0" cy="0" rx="6.1" ry="3.45" />
          <path className="shell-map__unit-symbol-stroke" d="M-4.8 -3 L4.8 3 M4.8 -3 L-4.8 3" />
        </>
      ) : null}
      {symbol === "anti_tank" ? (
        <path className="shell-map__unit-symbol-stroke" d="M-5.3 -3.6 L5.3 3.6 M5.3 -3.6 L-5.3 3.6 M0 -4.1 V4.1" />
      ) : null}
      {symbol === "support" ? (
        <path className="shell-map__unit-symbol-stroke" d="M0 -3.8 V3.8 M-4.8 0 H4.8" />
      ) : null}
    </g>
  );
}
