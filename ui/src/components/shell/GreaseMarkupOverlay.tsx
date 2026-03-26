import { Fragment } from "react";
import { MAP_GREASE_MARKUP_TOKENS } from "../../map/designTokens.js";

type GreasePoint = {
  x: number;
  y: number;
};

type GreaseItem = {
  id: string;
  tool: string;
  style: string;
  points: GreasePoint[];
};

type GreaseMarkupOverlayProps = {
  idPrefix: string;
  items: GreaseItem[];
  selectedId?: string | null;
  draftId?: string | null;
  onSelectItem?: ((id: string) => void) | null;
};

function pathData(points: GreasePoint[]): string {
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
}

function buildBounds(points: GreasePoint[]) {
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    minY,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
  };
}

function buildSegmentMarks(points: GreasePoint[], builder: (from: GreasePoint, to: GreasePoint) => string | null): string[] {
  const marks = [];
  for (let index = 1; index < points.length; index += 1) {
    const mark = builder(points[index - 1], points[index]);
    if (mark) {
      marks.push(mark);
    }
  }
  return marks;
}

function buildDirectionalVectors(from: GreasePoint, to: GreasePoint) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy) || 1;
  const tangent = { x: dx / distance, y: dy / distance };
  const normal = { x: -tangent.y, y: tangent.x };
  const midpoint = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
  return { distance, tangent, normal, midpoint };
}

function buildDefensiveMark(from: GreasePoint, to: GreasePoint) {
  const { distance, normal, midpoint } = buildDirectionalVectors(from, to);
  if (distance < 12) {
    return null;
  }
  const tick = MAP_GREASE_MARKUP_TOKENS.markerSizePx.defensiveTick;
  return `M${(midpoint.x - normal.x * tick * 0.6).toFixed(2)} ${(midpoint.y - normal.y * tick * 0.6).toFixed(2)} L${(midpoint.x + normal.x * tick * 0.6).toFixed(2)} ${(midpoint.y + normal.y * tick * 0.6).toFixed(2)}`;
}

function buildFallbackChevron(from: GreasePoint, to: GreasePoint) {
  const { distance, tangent, normal, midpoint } = buildDirectionalVectors(from, to);
  if (distance < 12) {
    return null;
  }
  const chevron = MAP_GREASE_MARKUP_TOKENS.markerSizePx.fallbackChevron;
  const tip = {
    x: midpoint.x - tangent.x * chevron * 0.7,
    y: midpoint.y - tangent.y * chevron * 0.7,
  };
  const left = {
    x: midpoint.x + normal.x * chevron * 0.55,
    y: midpoint.y + normal.y * chevron * 0.55,
  };
  const right = {
    x: midpoint.x - normal.x * chevron * 0.55,
    y: midpoint.y - normal.y * chevron * 0.55,
  };
  return `M${left.x.toFixed(2)} ${left.y.toFixed(2)} L${tip.x.toFixed(2)} ${tip.y.toFixed(2)} L${right.x.toFixed(2)} ${right.y.toFixed(2)}`;
}

function buildFrontTick(from: GreasePoint, to: GreasePoint) {
  const { distance, tangent, normal, midpoint } = buildDirectionalVectors(from, to);
  if (distance < 14) {
    return null;
  }
  const tick = MAP_GREASE_MARKUP_TOKENS.markerSizePx.frontTick;
  const forward = {
    x: midpoint.x + tangent.x * tick * 0.8,
    y: midpoint.y + tangent.y * tick * 0.8,
  };
  const crest = {
    x: midpoint.x + normal.x * tick * 0.8,
    y: midpoint.y + normal.y * tick * 0.8,
  };
  const rear = {
    x: midpoint.x - tangent.x * tick * 0.8,
    y: midpoint.y - tangent.y * tick * 0.8,
  };
  return `M${rear.x.toFixed(2)} ${rear.y.toFixed(2)} Q${crest.x.toFixed(2)} ${crest.y.toFixed(2)} ${forward.x.toFixed(2)} ${forward.y.toFixed(2)}`;
}

function buildArrowHeadPath(idPrefix: string) {
  return `${idPrefix}-grease-arrowhead`;
}

function renderShape(item: GreaseItem, markerEndId: string | null) {
  const bounds = buildBounds(item.points);
  switch (item.tool) {
    case "objective_circle":
      return (
        <>
          <ellipse
            className="shell-map__grease-shape shell-map__grease-shape--fill"
            cx={bounds.centerX}
            cy={bounds.centerY}
            rx={Math.max(8, bounds.width / 2)}
            ry={Math.max(8, bounds.height / 2)}
          />
          <ellipse
            className="shell-map__grease-shape shell-map__grease-shape--stroke"
            cx={bounds.centerX}
            cy={bounds.centerY}
            rx={Math.max(8, bounds.width / 2)}
            ry={Math.max(8, bounds.height / 2)}
          />
        </>
      );
    case "zone_box":
      return (
        <>
          <rect
            className="shell-map__grease-shape shell-map__grease-shape--fill"
            x={bounds.minX}
            y={bounds.minY}
            width={Math.max(12, bounds.width)}
            height={Math.max(12, bounds.height)}
            rx="6"
          />
          <rect
            className="shell-map__grease-shape shell-map__grease-shape--stroke"
            x={bounds.minX}
            y={bounds.minY}
            width={Math.max(12, bounds.width)}
            height={Math.max(12, bounds.height)}
            rx="6"
          />
        </>
      );
    default:
      return (
        <>
          <path className="shell-map__grease-shape shell-map__grease-shape--stroke" d={pathData(item.points)} markerEnd={markerEndId || undefined} />
          {item.tool === "front_line"
            ? buildSegmentMarks(item.points, buildFrontTick).map((mark, index) => (
              <path key={`${item.id}:front:${index}`} className="shell-map__grease-mark shell-map__grease-mark--front" d={mark} />
            ))
            : null}
          {item.tool === "defensive_line"
            ? buildSegmentMarks(item.points, buildDefensiveMark).map((mark, index) => (
              <path key={`${item.id}:def:${index}`} className="shell-map__grease-mark shell-map__grease-mark--defensive" d={mark} />
            ))
            : null}
          {item.tool === "fallback_line"
            ? buildSegmentMarks(item.points, buildFallbackChevron).map((mark, index) => (
              <path key={`${item.id}:fallback:${index}`} className="shell-map__grease-mark shell-map__grease-mark--fallback" d={mark} />
            ))
            : null}
        </>
      );
  }
}

export default function GreaseMarkupOverlay({
  idPrefix,
  items,
  selectedId = null,
  draftId = null,
  onSelectItem = null,
}: GreaseMarkupOverlayProps) {
  const arrowHeadId = buildArrowHeadPath(idPrefix);

  return (
    <g className="shell-map__grease-layer">
      <defs>
        <marker id={arrowHeadId} viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path className="shell-map__grease-arrowhead" d="M0 0 L8 4 L0 8 Z" />
        </marker>
      </defs>
      {items.map((item) => {
        const isSelected = item.id === selectedId;
        const isDraft = item.id === draftId;
        const markerEndId = item.tool === "arrow" ? `url(#${arrowHeadId})` : null;
        const bounds = buildBounds(item.points);
        return (
          <g
            key={item.id}
            className={
              `shell-map__grease-item is-${item.tool} is-${item.style}`
              + (isSelected ? " is-selected" : "")
              + (isDraft ? " is-draft" : "")
            }
            onClick={onSelectItem ? (event) => {
              event.stopPropagation();
              onSelectItem(item.id);
            } : undefined}
          >
            {isSelected ? (
              <Fragment>
                {item.tool === "objective_circle" ? (
                  <ellipse
                    className="shell-map__grease-shape shell-map__grease-shape--selection"
                    cx={bounds.centerX}
                    cy={bounds.centerY}
                    rx={Math.max(10, bounds.width / 2 + 3)}
                    ry={Math.max(10, bounds.height / 2 + 3)}
                  />
                ) : item.tool === "zone_box" ? (
                  <rect
                    className="shell-map__grease-shape shell-map__grease-shape--selection"
                    x={bounds.minX - 3}
                    y={bounds.minY - 3}
                    width={Math.max(18, bounds.width + 6)}
                    height={Math.max(18, bounds.height + 6)}
                    rx="8"
                  />
                ) : (
                  <path className="shell-map__grease-shape shell-map__grease-shape--selection" d={pathData(item.points)} />
                )}
              </Fragment>
            ) : null}
            {renderShape(item, markerEndId)}
          </g>
        );
      })}
    </g>
  );
}
