import {
  MAP_LABEL_DECLUTTER_TOKENS,
  MAP_LABEL_VISIBILITY_POLICY,
  getMapZoomTier,
} from "./designTokens.js";

function normalizeZoom(zoom) {
  const numericZoom = Number(zoom);
  return Number.isFinite(numericZoom) ? numericZoom : 1;
}

function normalizeAnchor(anchor) {
  return anchor === "end" || anchor === "middle" ? anchor : "start";
}

function estimatedWidth(text, kind, scale) {
  const content = String(text || "").trim();
  const fontSize = (MAP_LABEL_DECLUTTER_TOKENS.fontSizePx[kind] || 7) * scale;
  const widthFactor = MAP_LABEL_DECLUTTER_TOKENS.widthFactor[kind] || 0.58;
  return Math.max(fontSize * 1.75, content.length * fontSize * widthFactor);
}

function estimatedHeight(kind, scale) {
  return (MAP_LABEL_DECLUTTER_TOKENS.lineHeightPx[kind] || 8.75) * scale;
}

function estimateTextRect(candidate) {
  const kind = candidate.kind || "unitLabel";
  const scale = Number(candidate.scale || 1);
  const padding = MAP_LABEL_DECLUTTER_TOKENS.paddingPx[kind] || 4;
  const width = estimatedWidth(candidate.text, kind, scale);
  const height = estimatedHeight(kind, scale);
  const anchor = normalizeAnchor(candidate.textAnchor);
  const x = Number(candidate.x || 0);
  const y = Number(candidate.y || 0);
  const baselineOffset = height * 0.72;
  let left = x;

  if (anchor === "middle") {
    left = x - width / 2;
  } else if (anchor === "end") {
    left = x - width;
  }

  return {
    left: Number((left - padding).toFixed(2)),
    top: Number((y - baselineOffset - padding).toFixed(2)),
    right: Number((left + width + padding).toFixed(2)),
    bottom: Number((y + (height - baselineOffset) + padding).toFixed(2)),
  };
}

function normalizeRect(rect) {
  return {
    left: Number(rect?.left || 0),
    top: Number(rect?.top || 0),
    right: Number(rect?.right || 0),
    bottom: Number(rect?.bottom || 0),
  };
}

function rectsOverlap(left, right, padding = 0) {
  const a = normalizeRect(left);
  const b = normalizeRect(right);
  return !(
    a.right + padding <= b.left
    || a.left >= b.right + padding
    || a.bottom + padding <= b.top
    || a.top >= b.bottom + padding
  );
}

function basePriority(candidate) {
  return MAP_LABEL_DECLUTTER_TOKENS.priority[candidate.kind] || 40;
}

function isImportantObjective(candidate) {
  return candidate.important || candidate.isKeyObjective || candidate.tier === "capital" || candidate.tier === "major_city";
}

function visibilityRuleAllows(candidate, tierId) {
  const visibility = String(candidate?.visibility || "").trim().toLowerCase();
  if (!visibility || visibility === "operational") {
    return tierId !== "far";
  }
  if (visibility === "always" || visibility === "far") {
    return true;
  }
  if (visibility === "close") {
    return tierId === "close";
  }
  if (visibility === "selected_only") {
    return Boolean(candidate.selected || candidate.forceVisible);
  }
  if (visibility === "hidden") {
    return false;
  }
  return true;
}

function shouldShowByTier(candidate, tierId) {
  if (!visibilityRuleAllows(candidate, tierId) && !(candidate.selected || candidate.forceVisible)) {
    return false;
  }
  switch (candidate.kind) {
    case "objectiveLabel":
      if (tierId === "far") {
        return candidate.selected || isImportantObjective(candidate);
      }
      return true;
    case "objectiveState":
      if (tierId === "far") {
        return candidate.selected;
      }
      if (tierId === "operational") {
        return candidate.selected || isImportantObjective(candidate);
      }
      return true;
    case "airfieldLabel":
      if (tierId === "far") {
        return candidate.selected || candidate.important;
      }
      if (tierId === "operational") {
        return candidate.selected || candidate.important;
      }
      return true;
    case "portLabel":
      if (tierId === "far") {
        return candidate.selected;
      }
      if (tierId === "operational") {
        return candidate.selected;
      }
      return true;
    case "unitLabel":
      if (tierId === "far") {
        return candidate.selected;
      }
      if (tierId === "operational") {
        return candidate.selected || candidate.important;
      }
      return true;
    case "featureLabel":
      if (tierId === "far") {
        return candidate.selected || candidate.important;
      }
      if (tierId === "operational") {
        return candidate.selected || candidate.important || candidate.visibility !== "close";
      }
      return true;
    case "regionLabel":
    case "waterLabel":
      if (tierId === "far") {
        return candidate.important;
      }
      return true;
    case "hexLabel":
      return tierId === "close" && (candidate.selected || candidate.important);
    default:
      return candidate.selected || candidate.forceVisible;
  }
}

export function summarizeMapLabelPolicy(zoom) {
  const tier = getMapZoomTier(normalizeZoom(zoom));
  const policy = MAP_LABEL_VISIBILITY_POLICY.find((entry) => entry.id === tier.id) || MAP_LABEL_VISIBILITY_POLICY[1];
  return {
    ...policy,
    zoomTier: tier.id,
    zoomRange: `${tier.min.toFixed(2)}-${tier.max.toFixed(2)}`,
  };
}

export function buildMarkerObstacleRect({ id, kind, x, y, width, height, scale = 1 }) {
  const obstacleScale = Number(scale || 1);
  const extra = MAP_LABEL_DECLUTTER_TOKENS.obstacleClearancePx[kind] || 0;
  const fullWidth = Number(width || 0) * obstacleScale + extra;
  const fullHeight = Number(height || 0) * obstacleScale + extra;
  return {
    id,
    kind,
    rect: {
      left: Number((Number(x || 0) - fullWidth / 2).toFixed(2)),
      top: Number((Number(y || 0) - fullHeight / 2).toFixed(2)),
      right: Number((Number(x || 0) + fullWidth / 2).toFixed(2)),
      bottom: Number((Number(y || 0) + fullHeight / 2).toFixed(2)),
    },
  };
}

export function buildDeclutteredLabels(candidates, obstacles = [], options = {}) {
  const policy = summarizeMapLabelPolicy(options.zoom);
  const visibleCandidates = (Array.isArray(candidates) ? candidates : [])
    .filter((candidate) => candidate && String(candidate.text || "").trim())
    .filter((candidate) => shouldShowByTier(candidate, policy.zoomTier) || candidate.forceVisible)
    .map((candidate) => {
      const rect = estimateTextRect(candidate);
      return {
        ...candidate,
        textAnchor: normalizeAnchor(candidate.textAnchor),
        forceVisible: Boolean(candidate.forceVisible || candidate.selected),
        priority: basePriority(candidate)
          + (candidate.important ? MAP_LABEL_DECLUTTER_TOKENS.importantPriorityBoost : 0)
          + ((candidate.forceVisible || candidate.selected) ? MAP_LABEL_DECLUTTER_TOKENS.selectedPriorityBoost : 0)
          + Number(candidate.priorityBoost || 0),
        padding: MAP_LABEL_DECLUTTER_TOKENS.paddingPx[candidate.kind] || 4,
        rect,
      };
    })
    .sort((left, right) => {
      if (left.forceVisible !== right.forceVisible) {
        return left.forceVisible ? -1 : 1;
      }
      if (left.priority !== right.priority) {
        return right.priority - left.priority;
      }
      if (left.y !== right.y) {
        return left.y - right.y;
      }
      return left.x - right.x;
    });

  const accepted = [];
  const blocked = [];
  const markerObstacles = Array.isArray(obstacles) ? obstacles : [];

  for (const candidate of visibleCandidates) {
    const collidesObstacle = !candidate.forceVisible && markerObstacles.some((obstacle) => {
      if (!obstacle?.rect) {
        return false;
      }
      if (candidate.ownerObstacleId && obstacle.id === candidate.ownerObstacleId) {
        return false;
      }
      return rectsOverlap(candidate.rect, obstacle.rect, candidate.padding);
    });

    const collidesLabel = !candidate.forceVisible && accepted.some((existing) => (
      rectsOverlap(candidate.rect, existing.rect, Math.max(candidate.padding, existing.padding))
    ));

    if (collidesObstacle || collidesLabel) {
      blocked.push({
        ...candidate,
        blockedBy: collidesObstacle ? "obstacle" : "label",
      });
      continue;
    }

    accepted.push(candidate);
  }

  return {
    policy,
    accepted,
    blocked,
    visibleIds: new Set(accepted.map((candidate) => candidate.id)),
    visibleOwners: new Set(accepted.map((candidate) => candidate.ownerId).filter(Boolean)),
  };
}
