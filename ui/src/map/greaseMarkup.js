import { MAP_GREASE_MARKUP_TOKENS } from "./designTokens.js";

export const GREASE_MARKUP_STORAGE_PREFIX = "mwe:grease-markup:";
export const GREASE_MARKUP_VERSION = 1;
export const GREASE_MARKUP_DEFAULT_STYLE = "amber";

export const GREASE_MARKUP_TOOL_OPTIONS = [
  { id: "freehand", label: "Freehand", gesture: "drag", continuous: true },
  { id: "straight_line", label: "Line", gesture: "drag", continuous: false },
  { id: "arrow", label: "Arrow", gesture: "drag", continuous: false },
  { id: "front_line", label: "Front", gesture: "drag", continuous: true },
  { id: "objective_circle", label: "Circle", gesture: "drag", continuous: false },
  { id: "zone_box", label: "Zone", gesture: "drag", continuous: false },
  { id: "defensive_line", label: "Defensive", gesture: "drag", continuous: false },
  { id: "fallback_line", label: "Fallback", gesture: "drag", continuous: false },
];

export const GREASE_MARKUP_STYLE_OPTIONS = [
  { id: "amber", label: "Amber" },
  { id: "offwhite", label: "White" },
  { id: "blue", label: "Blue" },
];

const TOOL_IDS = new Set(GREASE_MARKUP_TOOL_OPTIONS.map((tool) => tool.id));
const STYLE_IDS = new Set(GREASE_MARKUP_STYLE_OPTIONS.map((style) => style.id));

function roundCoord(value) {
  return Number(Number(value || 0).toFixed(3));
}

function normalizePoint(point) {
  if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
    return null;
  }
  return {
    x: roundCoord(point.x),
    y: roundCoord(point.y),
  };
}

function distanceBetween(left, right) {
  if (!left || !right) {
    return 0;
  }
  const dx = Number(left.x || 0) - Number(right.x || 0);
  const dy = Number(left.y || 0) - Number(right.y || 0);
  return Math.hypot(dx, dy);
}

function measurePolylineLength(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return 0;
  }
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    total += distanceBetween(points[index - 1], points[index]);
  }
  return total;
}

function uniqueSequentialPoints(points) {
  const normalized = [];
  for (const point of points || []) {
    const next = normalizePoint(point);
    if (!next) {
      continue;
    }
    const previous = normalized[normalized.length - 1];
    if (!previous || previous.x !== next.x || previous.y !== next.y) {
      normalized.push(next);
    }
  }
  return normalized;
}

function buildBounds(points) {
  if (!points.length) {
    return null;
  }
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX: roundCoord(minX),
    maxX: roundCoord(maxX),
    minY: roundCoord(minY),
    maxY: roundCoord(maxY),
    width: roundCoord(maxX - minX),
    height: roundCoord(maxY - minY),
  };
}

function buildGreaseMarkupId() {
  const random = Math.random().toString(36).slice(2, 9);
  return `grease-${Date.now().toString(36)}-${random}`;
}

export function getGreaseMarkupStorageKey(scenarioId) {
  return `${GREASE_MARKUP_STORAGE_PREFIX}${String(scenarioId || "default")}`;
}

export function getGreaseMarkupTool(toolId) {
  return GREASE_MARKUP_TOOL_OPTIONS.find((tool) => tool.id === toolId) || null;
}

export function isGreaseMarkupToolContinuous(toolId) {
  return Boolean(getGreaseMarkupTool(toolId)?.continuous);
}

export function createGreaseMarkupState(scenarioId = null) {
  return {
    version: GREASE_MARKUP_VERSION,
    scenarioId: scenarioId || null,
    activeTool: null,
    activeStyle: GREASE_MARKUP_DEFAULT_STYLE,
    selectedId: null,
    items: [],
  };
}

export function sanitizeGreaseMarkupState(state, scenarioId = null) {
  const baseState = createGreaseMarkupState(scenarioId);
  if (!state || typeof state !== "object") {
    return baseState;
  }

  const items = Array.isArray(state.items)
    ? state.items
      .map((item) => createGreaseMarkupItem(item))
      .filter(Boolean)
    : [];

  const activeTool = TOOL_IDS.has(state.activeTool) ? state.activeTool : null;
  const activeStyle = STYLE_IDS.has(state.activeStyle) ? state.activeStyle : GREASE_MARKUP_DEFAULT_STYLE;
  const selectedId = typeof state.selectedId === "string" && items.some((item) => item.id === state.selectedId)
    ? state.selectedId
    : null;

  return {
    ...baseState,
    activeTool,
    activeStyle,
    selectedId,
    items,
  };
}

export function serializeGreaseMarkupState(state) {
  const sanitized = sanitizeGreaseMarkupState(state, state?.scenarioId ?? null);
  return {
    version: GREASE_MARKUP_VERSION,
    scenarioId: sanitized.scenarioId,
    activeTool: sanitized.activeTool,
    activeStyle: sanitized.activeStyle,
    selectedId: sanitized.selectedId,
    items: sanitized.items.map((item) => ({
      id: item.id,
      tool: item.tool,
      style: item.style,
      points: item.points,
      createdAt: item.createdAt,
    })),
  };
}

export function deserializeGreaseMarkupState(rawValue, scenarioId = null) {
  if (typeof rawValue === "string") {
    try {
      return sanitizeGreaseMarkupState(JSON.parse(rawValue), scenarioId);
    } catch (_error) {
      return createGreaseMarkupState(scenarioId);
    }
  }
  return sanitizeGreaseMarkupState(rawValue, scenarioId);
}

export function createGreaseMarkupItem(input) {
  if (!input || typeof input !== "object" || !TOOL_IDS.has(input.tool)) {
    return null;
  }
  const style = STYLE_IDS.has(input.style) ? input.style : GREASE_MARKUP_DEFAULT_STYLE;
  const continuous = isGreaseMarkupToolContinuous(input.tool);
  const normalizedPoints = uniqueSequentialPoints(input.points);
  const points = continuous
    ? normalizedPoints
    : normalizedPoints.length > 1
      ? [normalizedPoints[0], normalizedPoints[normalizedPoints.length - 1]]
      : normalizedPoints;
  if (points.length < 2) {
    return null;
  }

  return {
    id: typeof input.id === "string" && input.id.trim() ? input.id : buildGreaseMarkupId(),
    tool: input.tool,
    style,
    points,
    bounds: buildBounds(points),
    createdAt: Number.isFinite(Number(input.createdAt)) ? Number(input.createdAt) : Date.now(),
  };
}

export function appendGreaseMarkupPoint(points, nextPoint, minimumDistance = 0.6) {
  const normalizedPoint = normalizePoint(nextPoint);
  if (!normalizedPoint) {
    return Array.isArray(points) ? points : [];
  }
  const current = Array.isArray(points) ? points : [];
  const previous = current[current.length - 1];
  if (previous && distanceBetween(previous, normalizedPoint) < minimumDistance) {
    return current;
  }
  return [...current, normalizedPoint];
}

export function shouldCommitGreaseMarkup(toolId, scenePoints) {
  if (!TOOL_IDS.has(toolId)) {
    return false;
  }
  const normalizedPoints = uniqueSequentialPoints(scenePoints);
  if (normalizedPoints.length < 2) {
    return false;
  }

  const bounds = buildBounds(normalizedPoints);
  const minimumDistance = MAP_GREASE_MARKUP_TOKENS.minimumGesturePx[toolId] ?? 12;

  if (toolId === "objective_circle" || toolId === "zone_box") {
    return Boolean(bounds) && (bounds.width >= minimumDistance || bounds.height >= minimumDistance);
  }
  if (toolId === "freehand" || toolId === "front_line") {
    return measurePolylineLength(normalizedPoints) >= minimumDistance;
  }
  return distanceBetween(normalizedPoints[0], normalizedPoints[normalizedPoints.length - 1]) >= minimumDistance;
}

export function clearGreaseMarkupSelection(state) {
  return {
    ...sanitizeGreaseMarkupState(state, state?.scenarioId ?? null),
    selectedId: null,
  };
}

export function removeGreaseMarkupItem(state, itemId) {
  const sanitized = sanitizeGreaseMarkupState(state, state?.scenarioId ?? null);
  return {
    ...sanitized,
    selectedId: sanitized.selectedId === itemId ? null : sanitized.selectedId,
    items: sanitized.items.filter((item) => item.id !== itemId),
  };
}

export function clearGreaseMarkupItems(state) {
  const sanitized = sanitizeGreaseMarkupState(state, state?.scenarioId ?? null);
  return {
    ...sanitized,
    selectedId: null,
    items: [],
  };
}
