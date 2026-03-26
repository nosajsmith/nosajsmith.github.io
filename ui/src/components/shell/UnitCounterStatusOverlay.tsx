import type { CSSProperties } from "react";
import { MAP_COUNTER_OVERLAY_TOKENS } from "../../map/designTokens.js";
import { buildUnitCounterFramePresentation } from "../../map/unitCounterFrame.js";

type UnitCounterStatusOverlayProps = {
  overlay?: {
    selected?: boolean;
    disabled?: boolean;
    outOfCommand?: boolean;
    lowSupply?: boolean;
    moving?: boolean;
    engaged?: boolean;
    damaged?: boolean;
    critical?: boolean;
    idle?: boolean;
    edgeState?: "critical" | "engaged" | "moving" | "idle" | null;
    active?: boolean;
  } | null;
  echelon: "company" | "battalion" | "regiment" | "brigade" | "division" | "corps";
  isHeadquarters?: boolean;
  zoom?: number;
};

function buildCriticalCorners(width: number, height: number) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  return [
    `M${(-halfWidth + 4).toFixed(2)} ${(-halfHeight - 1).toFixed(2)} H${(-halfWidth + 11).toFixed(2)}`,
    `M${(-halfWidth + 4).toFixed(2)} ${(-halfHeight - 1).toFixed(2)} V${(-halfHeight + 6).toFixed(2)}`,
    `M${(halfWidth - 11).toFixed(2)} ${(-halfHeight - 1).toFixed(2)} H${(halfWidth - 4).toFixed(2)}`,
    `M${(halfWidth - 4).toFixed(2)} ${(-halfHeight - 1).toFixed(2)} V${(-halfHeight + 6).toFixed(2)}`,
  ].join(" ");
}

function buildMovingArrow(width: number, height: number) {
  const x = -(width / 2) - 8;
  const y = -(height / 2) - 3;
  const arrowWidth = MAP_COUNTER_OVERLAY_TOKENS.movingArrowWidthPx;
  const arrowHeight = MAP_COUNTER_OVERLAY_TOKENS.movingArrowHeightPx;
  const shaft = arrowWidth - 5;
  const midY = y + arrowHeight / 2;
  return [
    `M${x.toFixed(2)} ${midY.toFixed(2)}`,
    `H${(x + shaft).toFixed(2)}`,
    `M${(x + shaft - 4).toFixed(2)} ${(y + 1).toFixed(2)}`,
    `L${(x + shaft + 1).toFixed(2)} ${midY.toFixed(2)}`,
    `L${(x + shaft - 4).toFixed(2)} ${(y + arrowHeight - 1).toFixed(2)}`,
  ].join(" ");
}

function buildIdleBar(height: number) {
  const y = -(height / 2) - MAP_COUNTER_OVERLAY_TOKENS.idleBarOffsetPx / 2;
  const half = MAP_COUNTER_OVERLAY_TOKENS.idleBarWidthPx / 2;
  return `M${(-half).toFixed(2)} ${y.toFixed(2)} H${half.toFixed(2)}`;
}

function buildDamageCorner(width: number, height: number) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  const size = MAP_COUNTER_OVERLAY_TOKENS.damageCornerSizePx;
  return `M${(halfWidth - size - 2).toFixed(2)} ${(-halfHeight + 2).toFixed(2)} H${(halfWidth - 2).toFixed(2)} V${(-halfHeight + size + 2).toFixed(2)} Z`;
}

function buildSupplyMarker(width: number, height: number) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  const size = MAP_COUNTER_OVERLAY_TOKENS.supplyMarkerSizePx;
  return `M${(-halfWidth + 3).toFixed(2)} ${(halfHeight - 2).toFixed(2)} H${(-halfWidth + 3 + size).toFixed(2)} L${(-halfWidth + 3 + size / 2).toFixed(2)} ${(halfHeight - 2 - size).toFixed(2)} Z`;
}

function buildCommandMarker(width: number, height: number) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  const markerWidth = MAP_COUNTER_OVERLAY_TOKENS.commandMarkerWidthPx;
  const markerHeight = MAP_COUNTER_OVERLAY_TOKENS.commandMarkerHeightPx;
  const left = halfWidth - markerWidth - 2;
  const top = halfHeight - markerHeight - 2;
  return {
    badge: `M${left.toFixed(2)} ${top.toFixed(2)} H${(left + markerWidth).toFixed(2)} L${(left + markerWidth - 3).toFixed(2)} ${(top + markerHeight).toFixed(2)} H${(left + 3).toFixed(2)} Z`,
    notch: `M${(left + markerWidth / 2).toFixed(2)} ${(top + 1.2).toFixed(2)} V${(top + markerHeight - 2).toFixed(2)}`,
  };
}

export default function UnitCounterStatusOverlay({ overlay = null, echelon, isHeadquarters = false, zoom = 1 }: UnitCounterStatusOverlayProps) {
  if (!overlay?.active) {
    return null;
  }

  const frame = buildUnitCounterFramePresentation({ echelon, isHeadquarters, zoom });
  const commandMarker = buildCommandMarker(frame.width, frame.height);
  const style = {
    "--shell-counter-status-engaged-stroke": String(MAP_COUNTER_OVERLAY_TOKENS.engagedGlowStrokePx),
    "--shell-counter-status-critical-stroke": String(MAP_COUNTER_OVERLAY_TOKENS.criticalEdgeStrokePx),
  } as CSSProperties;

  return (
    <g className="shell-map__unit-status" style={style} aria-hidden="true">
      {overlay.edgeState === "engaged" ? (
        <path className="shell-map__unit-status-ring is-engaged" d={frame.outerPath} />
      ) : null}
      {overlay.edgeState === "critical" ? (
        <>
          <path className="shell-map__unit-status-ring is-critical" d={frame.outerPath} />
          <path className="shell-map__unit-status-corners is-critical" d={buildCriticalCorners(frame.width, frame.height)} />
        </>
      ) : null}
      {overlay.edgeState === "moving" ? (
        <path className="shell-map__unit-status-arrow" d={buildMovingArrow(frame.width, frame.height)} />
      ) : null}
      {overlay.edgeState === "idle" ? (
        <path className="shell-map__unit-status-idle" d={buildIdleBar(frame.height)} />
      ) : null}
      {overlay.damaged ? (
        <path className="shell-map__unit-status-damage" d={buildDamageCorner(frame.width, frame.height)} />
      ) : null}
      {overlay.lowSupply ? (
        <path className="shell-map__unit-status-supply" d={buildSupplyMarker(frame.width, frame.height)} />
      ) : null}
      {overlay.outOfCommand ? (
        <>
          <path className="shell-map__unit-status-command" d={commandMarker.badge} />
          <path className="shell-map__unit-status-command-notch" d={commandMarker.notch} />
        </>
      ) : null}
    </g>
  );
}
