import { MAP_OPERATIONAL_OVERLAY_TOKENS, MAP_ZOOM_TIERS, MAP_ZOOM_VISIBILITY, getMapZoomTier } from "../../map/designTokens.js";
import { summarizeHexZoomPresentation } from "../../map/hexTile.js";
import { inferUnitCounterEchelon, isHeadquartersUnit } from "../../map/unitCounterFrame.js";
import {
  buildUnitCounterPalettePresentation,
  inferUnitCounterService,
  inferUnitCounterState,
  normalizeUnitCounterFaction,
} from "../../map/unitCounterPalette.js";
import {
  compareAirfieldControl,
  compareAirfieldDamage,
  compareAirfieldTier,
  summarizeAirfieldLocation,
} from "../../map/airfieldIcon.js";
import {
  compareSettlementControl,
  compareSettlementTier,
  summarizeSettlementLocation,
} from "../../map/settlementIcon.js";
import { inferUnitCounterSymbol } from "../../map/unitCounterSymbol.js";
import { buildUnitCounterOverlayPresentation } from "../../map/unitCounterOverlay.js";
import { summarizeMapLabelPolicy } from "../../map/labelDeclutter.js";

export function abbreviateUnitLabel(unit) {
  const source = String(unit?.name || unit?.id || "UNIT").trim();
  const compact = source
    .replace(/Regiment|Division|Group|Belt|Security/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  const tokens = compact.split(/[\s-]+/).filter(Boolean);
  if (!tokens.length) {
    return "UNIT";
  }
  if (tokens.length === 1) {
    return tokens[0].slice(0, 6).toUpperCase();
  }
  return tokens
    .slice(0, 3)
    .map((token) => token.replace(/[^A-Za-z0-9]/g, "").slice(0, 3).toUpperCase())
    .join(" ");
}

export function humanizeObjectiveState(state) {
  const raw = String(state || "unknown").trim();
  if (!raw) {
    return "Unknown";
  }
  return raw
    .replace(/[_.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function classifyObjectiveVisualState(state) {
  const raw = String(state || "").trim().toLowerCase();
  if (raw.startsWith("held_")) {
    return "held";
  }
  if (raw === "unheld") {
    return "unheld";
  }
  return "unknown";
}

export const MAP_ZOOM_MIN = MAP_ZOOM_TIERS[0].min;
export const MAP_ZOOM_MAX = MAP_ZOOM_TIERS[MAP_ZOOM_TIERS.length - 1].max;

export function clampMapZoom(zoom) {
  const numericZoom = Number(zoom);
  if (!Number.isFinite(numericZoom)) {
    return 1;
  }
  return Math.min(MAP_ZOOM_MAX, Math.max(MAP_ZOOM_MIN, numericZoom));
}

export function clampMapCamera(camera, scene) {
  const width = Number(scene?.width || 1000);
  const height = Number(scene?.height || 620);
  const zoom = clampMapZoom(camera?.zoom ?? 1);
  const scaledWidth = width * zoom;
  const scaledHeight = height * zoom;
  const centerOffsetX = scaledWidth <= width ? (width - scaledWidth) / 2 : null;
  const centerOffsetY = scaledHeight <= height ? (height - scaledHeight) / 2 : null;
  const nextOffsetX = centerOffsetX != null
    ? centerOffsetX
    : Math.min(0, Math.max(width - scaledWidth, Number(camera?.offsetX ?? 0)));
  const nextOffsetY = centerOffsetY != null
    ? centerOffsetY
    : Math.min(0, Math.max(height - scaledHeight, Number(camera?.offsetY ?? 0)));

  return {
    zoom: Number(zoom.toFixed(3)),
    offsetX: Number(nextOffsetX.toFixed(2)),
    offsetY: Number(nextOffsetY.toFixed(2)),
  };
}

export function projectMapCameraPoint(point, camera) {
  const x = Number(point?.x ?? 0);
  const y = Number(point?.y ?? 0);
  const zoom = clampMapZoom(camera?.zoom ?? 1);
  const offsetX = Number(camera?.offsetX ?? 0);
  const offsetY = Number(camera?.offsetY ?? 0);
  return {
    x: Number((x * zoom + offsetX).toFixed(2)),
    y: Number((y * zoom + offsetY).toFixed(2)),
  };
}

export function summarizeMapZoomPresentation(zoom) {
  const clampedZoom = clampMapZoom(zoom);
  const tier = getMapZoomTier(clampedZoom);
  const hexZoom = summarizeHexZoomPresentation(clampedZoom);
  const labelPolicy = summarizeMapLabelPolicy(clampedZoom);

  return {
    tier: tier.id,
    zoom: clampedZoom,
    labelPolicy,
    counterScale: tier.counterScale,
    hexFadeOpacity: hexZoom.fadeOpacity,
    gridMinorOpacity: hexZoom.gridMinorOpacity,
    gridMajorOpacity: hexZoom.gridMajorOpacity,
    showLeaderLines: clampedZoom >= MAP_ZOOM_VISIBILITY.leaderLines,
    showObjectiveState: clampedZoom >= MAP_ZOOM_VISIBILITY.objectiveState,
    showAirfieldLabels: clampedZoom >= MAP_ZOOM_VISIBILITY.airfieldLabels,
    showAirfieldMarkers: clampedZoom >= MAP_ZOOM_VISIBILITY.airfieldMarkers,
    showObjectiveLabels: clampedZoom >= MAP_ZOOM_VISIBILITY.objectiveLabels,
    showObjectiveMarkers: clampedZoom >= MAP_ZOOM_VISIBILITY.objectiveMarkers,
    showUnitLabels: clampedZoom >= MAP_ZOOM_VISIBILITY.unitLabels,
    showSiteLabels: clampedZoom >= MAP_ZOOM_VISIBILITY.siteLabels,
    showOverlayLabels: clampedZoom >= MAP_ZOOM_VISIBILITY.overlayLabels,
  };
}

function humanizeSideLabel(side) {
  const raw = String(side ?? "").trim();
  if (!raw) {
    return "Unspecified Side";
  }
  return raw
    .replace(/[_:.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function hasCoord(item) {
  return item && typeof item.x === "number" && typeof item.y === "number";
}

function hasFeatureGeometry(item) {
  if (hasCoord(item)) {
    return true;
  }
  return Array.isArray(item?.points) && item.points.some(hasCoord);
}

function collectPoints(snapshot) {
  const allUnits = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const units = allUnits.filter(hasCoord);
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives.filter(hasCoord) : [];
  const airfields = Array.isArray(snapshot?.airfields) ? snapshot.airfields.filter(hasCoord) : [];
  const ports = Array.isArray(snapshot?.ports) ? snapshot.ports.filter(hasCoord) : [];
  const namedFeatures = Array.isArray(snapshot?.named_features) ? snapshot.named_features.filter(hasFeatureGeometry) : [];
  const namedFeaturePoints = namedFeatures.flatMap((feature) => {
    const points = Array.isArray(feature?.points) ? feature.points.filter(hasCoord) : [];
    return hasCoord(feature) ? [feature, ...points] : points;
  });
  const trackedUnits = allUnits.length;
  const trackedObjectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives.length : 0;
  const trackedAirfields = Array.isArray(snapshot?.airfields) ? snapshot.airfields.length : 0;
  const trackedPorts = Array.isArray(snapshot?.ports) ? snapshot.ports.length : 0;
  const trackedNamedFeatures = Array.isArray(snapshot?.named_features) ? snapshot.named_features.length : 0;
  return {
    allUnits,
    units,
    objectives,
    airfields,
    ports,
    namedFeatures,
    points: [...units, ...objectives, ...airfields, ...ports, ...namedFeaturePoints],
    trackedUnits,
    trackedObjectives,
    trackedAirfields,
    trackedPorts,
    trackedNamedFeatures,
  };
}

function buildViewport(points) {
  if (!points.length) {
    return { minX: 0, maxX: 12, minY: 0, maxY: 8 };
  }

  const xs = points.map((item) => item.x);
  const ys = points.map((item) => item.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(6, maxX - minX || 1);
  const spanY = Math.max(4, maxY - minY || 1);
  const padX = Math.max(1.5, spanX * 0.18);
  const padY = Math.max(1.5, spanY * 0.18);

  return {
    minX: minX - padX,
    maxX: maxX + padX,
    minY: minY - padY,
    maxY: maxY + padY,
  };
}

function projectPoint(x, y, viewport, width, height, inset) {
  const spanX = Math.max(1, viewport.maxX - viewport.minX);
  const spanY = Math.max(1, viewport.maxY - viewport.minY);
  const px = inset + ((x - viewport.minX) / spanX) * (width - inset * 2);
  const py = inset + ((y - viewport.minY) / spanY) * (height - inset * 2);
  return {
    x: Number(px.toFixed(2)),
    y: Number(py.toFixed(2)),
  };
}

export function projectScenePoint(point, scene) {
  return projectPoint(
    Number(point?.x ?? 0),
    Number(point?.y ?? 0),
    scene?.viewport || buildViewport([]),
    Number(scene?.width || 1000),
    Number(scene?.height || 620),
    Number(scene?.inset || 56),
  );
}

export function unprojectScenePoint(point, scene) {
  const viewport = scene?.viewport || buildViewport([]);
  const width = Number(scene?.width || 1000);
  const height = Number(scene?.height || 620);
  const inset = Number(scene?.inset || 56);
  const spanX = Math.max(1, viewport.maxX - viewport.minX);
  const spanY = Math.max(1, viewport.maxY - viewport.minY);
  const x = Number(point?.x ?? 0);
  const y = Number(point?.y ?? 0);
  const normalizedX = (x - inset) / Math.max(1, width - inset * 2);
  const normalizedY = (y - inset) / Math.max(1, height - inset * 2);
  return {
    x: Number((viewport.minX + normalizedX * spanX).toFixed(4)),
    y: Number((viewport.minY + normalizedY * spanY).toFixed(4)),
  };
}

function markerSortKey(marker) {
  const typeRank = marker.kind === "objective"
    ? "0"
    : marker.kind === "airfield"
      ? "1"
      : marker.kind === "port"
        ? "2"
        : "3";
  const side = String(marker.side ?? "").trim().toUpperCase();
  const name = String(marker.name ?? "").trim().toUpperCase();
  const id = String(marker.id ?? "").trim().toUpperCase();
  return [typeRank, side, name, id].join("|");
}

function clusterSortKey(marker) {
  return [
    String(marker.baseAnchor?.y ?? 0).padStart(12, "0"),
    String(marker.baseAnchor?.x ?? 0).padStart(12, "0"),
    markerSortKey(marker),
  ].join("|");
}

function distanceBetween(left, right) {
  const dx = Number(left?.x ?? 0) - Number(right?.x ?? 0);
  const dy = Number(left?.y ?? 0) - Number(right?.y ?? 0);
  return Math.hypot(dx, dy);
}

function buildDeclutteredMarkers(units, objectives, airfields, ports, viewport, width, height, inset) {
  const markers = [
    ...objectives.map((objective) => ({
      ...objective,
      kind: "objective",
      baseAnchor: projectPoint(objective.x, objective.y, viewport, width, height, inset),
    })),
    ...airfields.map((airfield) => ({
      ...airfield,
      kind: "airfield",
      baseAnchor: projectPoint(airfield.x, airfield.y, viewport, width, height, inset),
    })),
    ...ports.map((port) => ({
      ...port,
      kind: "port",
      baseAnchor: projectPoint(port.x, port.y, viewport, width, height, inset),
    })),
    ...units.map((unit) => ({
      ...unit,
      kind: "unit",
      baseAnchor: projectPoint(unit.x, unit.y, viewport, width, height, inset),
    })),
  ];
  const ordered = [...markers].sort((left, right) => clusterSortKey(left).localeCompare(clusterSortKey(right)));
  const threshold = 36;
  const clusters = [];

  for (const marker of ordered) {
    const cluster = clusters.find((candidate) => distanceBetween(candidate.anchor, marker.baseAnchor) <= threshold);
    if (cluster) {
      cluster.items.push(marker);
      continue;
    }
    clusters.push({
      anchor: marker.baseAnchor,
      items: [marker],
    });
  }

  const slotOffsets = [
    { x: -16, y: -22 },
    { x: 16, y: -12 },
    { x: -18, y: 16 },
    { x: 18, y: 16 },
    { x: 0, y: 25 },
    { x: 0, y: -31 },
    { x: -28, y: 2 },
    { x: 28, y: 2 },
  ];

  return clusters.flatMap((cluster) => {
    const ranked = [...cluster.items].sort((left, right) => markerSortKey(left).localeCompare(markerSortKey(right)));
    return ranked.map((marker, index) => {
      const offset = ranked.length > 1 ? slotOffsets[index % slotOffsets.length] : { x: 0, y: 0 };
      const displayAnchor = {
        x: Number((marker.baseAnchor.x + offset.x).toFixed(2)),
        y: Number((marker.baseAnchor.y + offset.y).toFixed(2)),
      };
      const leaderOffset = {
        x: Number((marker.baseAnchor.x - displayAnchor.x).toFixed(2)),
        y: Number((marker.baseAnchor.y - displayAnchor.y).toFixed(2)),
      };
      const hasLeader = Math.hypot(leaderOffset.x, leaderOffset.y) >= 10;

      if (marker.kind === "objective") {
        const labelAnchor = offset.x > 8 ? "end" : "start";
        const labelX = offset.x > 8 ? -12 : 12;
        return {
          ...marker,
          anchor: marker.baseAnchor,
          displayAnchor,
          hasLeader,
          leaderOffset,
          labelX,
          labelY: offset.y <= 0 ? -12 : -11,
          labelAnchor,
          stateX: labelX,
          stateY: offset.y <= 0 ? 14 : 13,
          stateAnchor: labelAnchor,
        };
      }

      const sideLabel = Math.abs(offset.x) >= 12;

      if (marker.kind === "airfield" || marker.kind === "port") {
        return {
          ...marker,
          anchor: marker.baseAnchor,
          displayAnchor,
          hasLeader,
          leaderOffset,
          labelOffsetX: sideLabel ? (offset.x > 0 ? -22 : 22) : 0,
          labelOffsetY: sideLabel ? 4 : (offset.y <= 0 ? 16 : -12),
          labelAnchor: sideLabel ? (offset.x > 0 ? "end" : "start") : "middle",
        };
      }

      return {
        ...marker,
        anchor: marker.baseAnchor,
        displayAnchor,
        hasLeader,
        leaderOffset,
        labelOffsetX: sideLabel ? (offset.x > 0 ? -24 : 24) : 0,
        labelOffsetY: sideLabel ? 4 : (offset.y <= 0 ? 17 : -12),
        labelAnchor: sideLabel ? (offset.x > 0 ? "end" : "start") : "middle",
      };
    });
  });
}

function buildSideSlots(units) {
  const knownSides = new Set();
  let hasUnknown = false;

  for (const unit of units) {
    const key = String(unit?.side ?? "").trim().toUpperCase();
    if (!key || key === "UNKNOWN") {
      hasUnknown = true;
      continue;
    }
    knownSides.add(key);
  }

  const slots = ["primary", "secondary"];
  const sideToSlot = {};
  const legend = [];
  const orderedSides = Array.from(knownSides).sort((left, right) => left.localeCompare(right));

  for (const side of orderedSides) {
    const slot = slots.shift() || "neutral";
    sideToSlot[side] = slot;
    legend.push({
      side,
      label: humanizeSideLabel(side),
      slot,
    });
  }

  sideToSlot.UNKNOWN = "neutral";
  sideToSlot[""] = "neutral";

  if (hasUnknown) {
    legend.push({
      side: "UNKNOWN",
      label: "Unspecified Side",
      slot: "neutral",
    });
  }

  if (!legend.length) {
    legend.push({
      side: "UNKNOWN",
      label: "Unknown",
      slot: "neutral",
    });
  }
  return { sideToSlot, legend };
}

const LEGEND_SYMBOL_PRIORITY = [
  "headquarters",
  "mechanized",
  "infantry_marine",
  "infantry",
  "recon",
  "artillery",
  "engineer",
  "armor",
  "anti_tank",
  "support",
  "formation",
];

function inferUnitLegendSymbol(unit) {
  const entry = inferUnitCounterSymbol(unit);
  if (!entry) {
    return null;
  }

  if (entry.id === "infantry" && /marine/i.test(String(unit?.name ?? ""))) {
    return { id: "infantry_marine", symbol: "infantry", label: "Marine / infantry" };
  }

  return {
    id: entry.id,
    symbol: entry.id,
    label: entry.label,
  };
}

function buildUnitLegendRows(units) {
  const entries = new Map();

  for (const unit of units) {
    const entry = inferUnitLegendSymbol(unit);
    if (entry && !entries.has(entry.id)) {
      entries.set(entry.id, {
        id: entry.id,
        kind: "unit",
        symbol: entry.symbol,
        label: entry.label,
      });
    }
  }

  return Array.from(entries.values()).sort(
    (left, right) => LEGEND_SYMBOL_PRIORITY.indexOf(left.id) - LEGEND_SYMBOL_PRIORITY.indexOf(right.id),
  );
}

function buildMarkLegendRows(objectives, airfields, ports, units, markers) {
  const rows = [];
  const settlements = objectives.map((objective) => summarizeSettlementLocation(objective));
  const summarizedAirfields = airfields.map((airfield) => summarizeAirfieldLocation(airfield, { objectives, units }));
  const seenControlStates = Array.from(new Set(settlements.map((entry) => entry.controlState))).sort(compareSettlementControl);
  const highestTier = [...settlements]
    .sort((left, right) => compareSettlementTier(left.tier, right.tier))
    .at(0);

  if (highestTier?.isKeyObjective) {
    rows.push({
      id: `settlement-tier-${highestTier.tier}`,
      kind: "settlement",
      tier: highestTier.tier,
      controlState: highestTier.controlState,
      label: highestTier.tier === "capital" ? "Key objective locality" : "Major objective locality",
    });
  }

  for (const controlState of seenControlStates) {
    rows.push({
      id: `settlement-control-${controlState}`,
      kind: "settlement",
      tier: controlState === "contested" ? "city" : "town",
      controlState,
      label: controlState === "friendly"
        ? "Friendly-controlled locality"
        : controlState === "enemy"
          ? "Enemy-controlled locality"
          : controlState === "contested"
            ? "Contested locality"
            : controlState === "neutral"
              ? "Neutral locality"
              : "Unconfirmed locality",
    });
  }

  if (summarizedAirfields.length) {
    const highestAirfieldTier = [...summarizedAirfields]
      .sort((left, right) => compareAirfieldTier(left.tier, right.tier))
      .at(0);
    const airfieldDamage = [...summarizedAirfields]
      .sort((left, right) => compareAirfieldDamage(left.damageState, right.damageState))
      .at(0);
    const airfieldControl = Array.from(new Set(summarizedAirfields.map((entry) => entry.controlState))).sort(compareAirfieldControl)[0] ?? "unknown";

    rows.push({
      id: "airfield",
      kind: "airfield",
      tier: highestAirfieldTier?.tier ?? "operational_airfield",
      controlState: airfieldControl,
      damageState: airfieldDamage?.damageState ?? "ready",
      sortieActive: summarizedAirfields.some((entry) => entry.sortieActive),
      readinessBand: highestAirfieldTier?.readinessBand ?? "unknown",
      label: highestAirfieldTier?.tier === "major_airbase" ? "Major airbase" : "Airfield",
    });
  }

  if (ports.length) {
    rows.push({
      id: "port",
      kind: "port",
      label: "Port / shore point",
    });
  }

  if (markers.some((marker) => marker.hasLeader)) {
    rows.push({
      id: "leader",
      kind: "leader",
      label: "Leader line",
    });
  }

  return rows;
}

function buildLegendSections(units, objectives, airfields, ports, markers, sideLegend) {
  const sections = [];
  const forceRows = sideLegend.map((entry) => ({
    id: `force-${entry.side || entry.slot}`,
    kind: "force",
    slot: entry.slot,
    label: `${entry.label} formations`,
  }));
  const unitRows = buildUnitLegendRows(units);
  const markRows = buildMarkLegendRows(objectives, airfields, ports, units, markers);

  if (forceRows.length) {
    sections.push({
      id: "forces",
      title: "Forces",
      rows: forceRows,
    });
  }

  if (unitRows.length) {
    sections.push({
      id: "symbols",
      title: "Symbols",
      rows: unitRows,
    });
  }

  if (markRows.length) {
    sections.push({
      id: "marks",
      title: "Map Marks",
      rows: markRows,
    });
  }

  return sections;
}

function resolveScenarioUnderlay(snapshot) {
  const scenarioId = String(snapshot?.scenario?.id ?? "").trim().toLowerCase();
  const scenarioName = String(snapshot?.scenario?.name ?? "").trim().toLowerCase();
  const isLungaSlice = scenarioId === "lunga_point_slice_1942"
    || scenarioId === "00_lunga_point_slice_1942"
    || scenarioName.includes("lunga point")
    || scenarioName.includes("henderson");

  if (!isLungaSlice) {
    return {
      available: false,
      id: null,
      label: null,
    };
  }

  return {
    available: true,
    id: "lunga_point_henderson",
    label: "Lunga Point / Henderson Field geographic underlay",
  };
}

export function buildMapScene(snapshot, options = {}) {
  const width = Number(options.width || 1000);
  const height = Number(options.height || 620);
  const inset = Number(options.inset || 56);
  const {
    allUnits,
    units,
    objectives,
    airfields,
    ports,
    namedFeatures,
    points,
    trackedUnits,
    trackedObjectives,
    trackedAirfields,
    trackedPorts,
    trackedNamedFeatures,
  } = collectPoints(snapshot);
  const viewport = buildViewport(points);
  const sideSlots = buildSideSlots(units);
  const declutteredMarkers = buildDeclutteredMarkers(units, objectives, airfields, ports, viewport, width, height, inset);
  const objectivesById = new Map(
    declutteredMarkers.filter((marker) => marker.kind === "objective").map((marker) => [marker.id, marker]),
  );
  const airfieldsById = new Map(
    declutteredMarkers.filter((marker) => marker.kind === "airfield").map((marker) => [marker.id, marker]),
  );
  const portsById = new Map(
    declutteredMarkers.filter((marker) => marker.kind === "port").map((marker) => [marker.id, marker]),
  );
  const unitsById = new Map(
    declutteredMarkers.filter((marker) => marker.kind === "unit").map((marker) => [marker.id, marker]),
  );
  const missingUnitCoords = Math.max(0, trackedUnits - units.length);
  const missingObjectiveCoords = Math.max(0, trackedObjectives - objectives.length);
  const missingAirfieldCoords = Math.max(0, trackedAirfields - airfields.length);
  const missingPortCoords = Math.max(0, trackedPorts - ports.length);
  const missingNamedFeatureCoords = Math.max(0, trackedNamedFeatures - namedFeatures.length);
  let emptyState = null;
  if (trackedUnits > 0 && units.length === 0) {
    emptyState = "Tracked units are present, but view.snapshot does not include plottable x/y coordinates for them.";
  } else if (trackedUnits === 0 && trackedObjectives === 0 && trackedAirfields === 0 && trackedPorts === 0 && trackedNamedFeatures === 0) {
    emptyState = "No unit, objective, or infrastructure markers are available in the current command snapshot.";
  } else if (!points.length && (missingObjectiveCoords > 0 || missingAirfieldCoords > 0 || missingPortCoords > 0 || missingNamedFeatureCoords > 0)) {
    emptyState = "The current command snapshot has markers, but none expose plottable coordinates.";
  }
  const namedFeatureRows = buildNamedFeatureSceneRows(snapshot, viewport, width, height, inset);

  return {
    width,
    height,
    inset,
    viewport,
    underlay: resolveScenarioUnderlay(snapshot),
    legend: buildLegendSections(units, objectives, airfields, ports, declutteredMarkers, sideSlots.legend),
    units: units.map((unit) => {
      const counterAppearance = buildUnitCounterPalettePresentation({
        side: unit?.side,
        service: inferUnitCounterService(unit),
        faction: normalizeUnitCounterFaction(unit?.side),
        ...inferUnitCounterState(unit),
      });

      return {
        ...unit,
        ...unitsById.get(unit.id),
        visualSlot: sideSlots.sideToSlot[String(unit.side ?? "").trim().toUpperCase()] || "neutral",
        shortLabel: abbreviateUnitLabel(unit),
        counterSymbol: inferUnitCounterSymbol(unit),
        counterFrame: {
          echelon: inferUnitCounterEchelon(unit),
          isHeadquarters: isHeadquartersUnit(unit),
        },
        counterAppearance,
        counterStatusOverlay: buildUnitCounterOverlayPresentation(unit, {
          disabled: counterAppearance.disabled,
          outOfCommand: counterAppearance.outOfCommand,
        }),
      };
    }),
    objectives: objectives.map((objective) => ({
      ...objective,
      ...objectivesById.get(objective.id),
      visualState: classifyObjectiveVisualState(objective.state),
      stateLabel: humanizeObjectiveState(objective.state),
      settlement: summarizeSettlementLocation(objective),
      objectiveOverlay: summarizeObjectiveOverlay(objective, { airfields, ports }),
    })),
    airfields: airfields.map((airfield) => ({
      ...airfield,
      ...airfieldsById.get(airfield.id),
      airfield: summarizeAirfieldLocation(airfield, { objectives, units: allUnits }),
    })),
    ports: ports.map((port) => ({
      ...port,
      ...portsById.get(port.id),
    })),
    namedFeatures: namedFeatureRows,
    stats: {
      trackedUnits,
      visibleUnits: units.length,
      missingUnitCoords,
      trackedObjectives,
      visibleObjectives: objectives.length,
      missingObjectiveCoords,
      trackedAirfields,
      visibleAirfields: airfields.length,
      missingAirfieldCoords,
      trackedPorts,
      visiblePorts: ports.length,
      missingPortCoords,
      trackedNamedFeatures,
      visibleNamedFeatures: namedFeatureRows.length,
      missingNamedFeatureCoords,
    },
    emptyState,
  };
}

function buildLocMarkers(scene) {
  return (Array.isArray(scene?.units) ? scene.units : [])
    .map((unit) => {
      const loc = unit?.inspector?.operational_state?.loc;
      const state = String(loc?.state ?? "").trim().toLowerCase();
      if (!unit?.displayAnchor || !["connected", "threatened", "broken"].includes(state)) {
        return null;
      }
      return {
        id: unit.id,
        name: unit.name || unit.id || "Formation",
        x: unit.displayAnchor.x,
        y: unit.displayAnchor.y,
        state,
        detail: typeof loc?.detail === "string" && loc.detail.trim() ? loc.detail.trim() : "LOC state detail unavailable",
      };
    })
    .filter(Boolean);
}

function buildArtilleryMarkers(scene) {
  return (Array.isArray(scene?.units) ? scene.units : [])
    .map((unit) => {
      const artillery = unit?.inspector?.branch_specific?.artillery;
      if (!artillery || !unit?.displayAnchor) {
        return null;
      }
      return {
        id: unit.id,
        name: unit.name || unit.id || "Formation",
        x: unit.displayAnchor.x,
        y: unit.displayAnchor.y,
        firePolicy: artillery.fire_policy || null,
      };
    })
    .filter(Boolean);
}

function metricNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function lowerText(value) {
  return String(value ?? "").trim().toLowerCase();
}

function upperText(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeOverlayFaction(side) {
  const faction = normalizeUnitCounterFaction(side);
  if (faction === "friendly" || faction === "partner") {
    return "friendly";
  }
  if (faction === "enemy") {
    return "enemy";
  }
  if (faction === "neutral") {
    return "neutral";
  }
  return "unknown";
}

function normalizeLocationName(value) {
  return upperText(value)
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeSearchText(value) {
  return lowerText(value)
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function joinSearchText(...values) {
  return normalizeSearchText(values.filter(Boolean).join(" "));
}

function severityRank(severity) {
  const raw = lowerText(severity);
  if (raw === "critical") {
    return 3;
  }
  if (raw === "warning" || raw === "warn") {
    return 2;
  }
  if (raw === "info" || raw === "notice") {
    return 1;
  }
  return 0;
}

function distanceBetweenCoords(left, right) {
  if (!hasCoord(left) || !hasCoord(right)) {
    return Number.POSITIVE_INFINITY;
  }
  return distanceBetween(left, right);
}

function nearestByDistance(candidates, anchor, maxDistance = Number.POSITIVE_INFINITY) {
  if (!anchor) {
    return null;
  }
  return [...candidates]
    .map((candidate) => ({
      candidate,
      distance: distanceBetween(candidate?.anchor ?? candidate, anchor),
    }))
    .filter((entry) => Number.isFinite(entry.distance) && entry.distance <= maxDistance)
    .sort((left, right) => left.distance - right.distance)[0]?.candidate ?? null;
}

function collectOperationalReports(snapshot) {
  return (Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : [])
    .map((report) => ({
      id: String(report?.id || ""),
      title: String(report?.title || "Report"),
      summary: String(report?.summary || "Operational update."),
      severity: String(report?.severity || "info"),
      severityRank: severityRank(report?.severity),
      time: metricNumber(report?.time),
      localAreaId: typeof report?.local_area_id === "string" ? report.local_area_id : null,
      searchText: joinSearchText(report?.title, report?.summary, report?.kind),
    }));
}

function buildReportsByLocalArea(snapshot) {
  const rows = collectOperationalReports(snapshot);
  const byArea = new Map();
  for (const report of rows) {
    if (!report.localAreaId) {
      continue;
    }
    const bucket = byArea.get(report.localAreaId) ?? [];
    bucket.push(report);
    byArea.set(report.localAreaId, bucket);
  }
  return byArea;
}

function normalizeNamedFeatureKind(kind) {
  return String(kind || "feature")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

function normalizeVisibilityRule(value, fallback = "operational") {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return fallback;
  }
  return ["always", "far", "operational", "close", "selected_only", "hidden"].includes(normalized)
    ? normalized
    : fallback;
}

function buildNamedFeatureSceneRows(snapshot, viewport, width, height, inset) {
  return (Array.isArray(snapshot?.named_features) ? snapshot.named_features : [])
    .map((feature) => {
      const geometryType = String(feature?.geometry_type || (Array.isArray(feature?.points) && feature.points.length ? "line" : "point"))
        .trim()
        .toLowerCase() || "point";
      const scenePoints = (Array.isArray(feature?.points) ? feature.points : [])
        .filter(hasCoord)
        .map((point) => projectPoint(point.x, point.y, viewport, width, height, inset));
      let anchor = hasCoord(feature)
        ? projectPoint(feature.x, feature.y, viewport, width, height, inset)
        : null;
      if (!anchor && scenePoints.length) {
        const totals = scenePoints.reduce(
          (summary, point) => ({
            x: summary.x + point.x,
            y: summary.y + point.y,
          }),
          { x: 0, y: 0 },
        );
        anchor = {
          x: Number((totals.x / scenePoints.length).toFixed(2)),
          y: Number((totals.y / scenePoints.length).toFixed(2)),
        };
      }
      if (!anchor) {
        return null;
      }
      const kindKey = normalizeNamedFeatureKind(feature?.kind);
      const aliasNames = (Array.isArray(feature?.aliases) ? feature.aliases : [])
        .map((alias) => String(alias?.name || "").trim())
        .filter(Boolean);
      return {
        ...feature,
        geometryType,
        kindKey,
        anchor,
        points: scenePoints,
        labelAnchor: "middle",
        labelOffsetX: 0,
        labelOffsetY: geometryType === "point" ? -10 : 0,
        visibility: normalizeVisibilityRule(feature?.visibility),
        important: Number(feature?.label_priority || 1) >= 3 || kindKey === "sector" || kindKey === "phase_line",
        searchText: joinSearchText(feature?.label, feature?.historical_name, feature?.modern_name, aliasNames.join(" ")),
      };
    })
    .filter(Boolean);
}

function objectiveOverlayCategory(objective, scene) {
  const authoredType = lowerText(objective?.objective_type || objective?.category);
  if (authoredType === "political") {
    return "political";
  }
  if (["primary", "secondary", "supply", "strategic"].includes(authoredType)) {
    return authoredType;
  }
  const objectiveValue = metricNumber(objective?.value) ?? 0;
  const nearbyAirfield = (Array.isArray(scene?.airfields) ? scene.airfields : []).some((airfield) => (
    distanceBetweenCoords(objective, airfield) <= 1.45
      || normalizeLocationName(airfield?.name) === normalizeLocationName(objective?.name)
  ));
  const nearbyPort = (Array.isArray(scene?.ports) ? scene.ports : []).some((port) => (
    distanceBetweenCoords(objective, port) <= 1.45
      || normalizeLocationName(port?.name) === normalizeLocationName(objective?.name)
  ));

  if (objectiveValue >= 95) {
    return "strategic";
  }
  if (nearbyAirfield || nearbyPort) {
    return "supply";
  }
  if (objectiveValue >= 70) {
    return "primary";
  }
  return "secondary";
}

function summarizeObjectiveOverlay(objective, scene) {
  const category = objectiveOverlayCategory(objective, scene);
  const value = metricNumber(objective?.value) ?? 0;
  const authoredTier = metricNumber(objective?.importance_tier);
  return {
    category,
    contested: lowerText(objective?.state) === "unheld" || lowerText(objective?.settlement?.controlState) === "contested",
    importanceTier: authoredTier ?? (category === "strategic" || category === "political" ? 3 : category === "primary" || category === "supply" ? 2 : value >= 45 ? 1 : 0),
    label: category === "strategic"
      ? "Strategic objective"
      : category === "political"
        ? "Political objective"
      : category === "supply"
        ? "Supply objective"
        : category === "primary"
          ? "Primary objective"
          : "Secondary objective",
  };
}

function inferPortControlState(port, scene) {
  const nearObjective = (Array.isArray(scene?.objectives) ? scene.objectives : [])
    .filter((objective) => objective?.anchor && port?.anchor)
    .map((objective) => ({
      objective,
      distance: distanceBetween(objective.anchor, port.anchor),
    }))
    .sort((left, right) => left.distance - right.distance)
    .find((entry) => entry.distance <= 42)?.objective;

  if (nearObjective?.settlement?.controlState) {
    return nearObjective.settlement.controlState;
  }

  const nameKey = normalizeLocationName(port?.name);
  const matchedObjective = (Array.isArray(scene?.objectives) ? scene.objectives : []).find((objective) => (
    nameKey && normalizeLocationName(objective?.name) === nameKey
  ));
  if (matchedObjective?.settlement?.controlState) {
    return matchedObjective.settlement.controlState;
  }

  return "unknown";
}

function summarizeSupplyState(unit) {
  const supplyPct = metricNumber(unit?.inspector?.supply?.supply_pct);
  const supplyDays = metricNumber(unit?.inspector?.supply?.supply_days_current);
  const locState = lowerText(unit?.inspector?.operational_state?.loc?.state);

  if (locState === "broken") {
    return "isolated";
  }
  if (
    (supplyPct != null && supplyPct <= 30)
    || (supplyDays != null && supplyDays <= 1.5)
  ) {
    return "critical";
  }
  if (
    (supplyPct != null && supplyPct <= 50)
    || (supplyDays != null && supplyDays <= 2.5)
  ) {
    return "low";
  }
  if (
    locState === "threatened"
    || (supplyPct != null && supplyPct <= 70)
    || (supplyDays != null && supplyDays <= 3.5)
  ) {
    return "strained";
  }
  if (supplyPct != null || supplyDays != null || locState === "connected") {
    return "well";
  }
  return "unavailable";
}

function buildSupplySources(scene) {
  const airfields = (Array.isArray(scene?.airfields) ? scene.airfields : []).map((airfield) => ({
    id: `airfield:${airfield.id}`,
    sourceId: airfield.id,
    kind: "airfield",
    name: airfield.name,
    anchor: airfield.anchor,
    side: airfield.airfield?.controlState ?? "unknown",
  }));
  const ports = (Array.isArray(scene?.ports) ? scene.ports : []).map((port) => ({
    id: `port:${port.id}`,
    sourceId: port.id,
    kind: "port",
    name: port.name,
    anchor: port.anchor,
    side: inferPortControlState(port, scene),
  }));

  return [...ports, ...airfields].filter((node) => node.anchor);
}

function buildSupplyOverlayState(scene) {
  const sources = buildSupplySources(scene);
  const plottedUnits = Array.isArray(scene?.units) ? scene.units : [];
  const markers = plottedUnits
    .map((unit) => {
      const state = summarizeSupplyState(unit);
      if (!unit?.anchor || state === "unavailable") {
        return null;
      }
      const faction = normalizeOverlayFaction(unit?.side);
      const matchingSources = sources.filter((source) => (
        source.side === faction || source.side === "unknown"
      ));
      const nearestSource = [...matchingSources]
        .sort((left, right) => distanceBetween(left.anchor, unit.anchor) - distanceBetween(right.anchor, unit.anchor))
        .at(0) ?? null;

      return {
        id: unit.id,
        name: unit.name || unit.id || "Formation",
        anchor: unit.anchor,
        state,
        faction,
        locState: lowerText(unit?.inspector?.operational_state?.loc?.state) || null,
        source: nearestSource,
      };
    })
    .filter(Boolean);

  const counts = markers.reduce(
    (summary, marker) => {
      summary[marker.state] += 1;
      return summary;
    },
    { well: 0, strained: 0, low: 0, critical: 0, isolated: 0 },
  );

  return {
    label: "Supply",
    available: Boolean(markers.length || sources.length),
    status: markers.length
      ? `${counts.well} well • ${counts.strained} strained • ${counts.low + counts.critical + counts.isolated} degraded`
      : "Unavailable",
    detail: markers.length
      ? "Supply bands come from exposed unit supply-day, supply-percent, and LOC fields. Corridor lines are proximity links to the nearest plotted same-side source node because explicit trace geometry is not exposed."
      : "Authoritative supply overlay geometry is not exposed on the current shell path.",
    markers,
    sources,
    corridors: markers
      .filter((marker) => marker.source)
      .map((marker) => ({
        id: `${marker.source.id}:${marker.id}`,
        from: marker.source.anchor,
        to: marker.anchor,
        state: marker.state === "well"
          ? "primary"
          : marker.state === "strained"
            ? "strained"
            : marker.state === "isolated"
              ? "isolated"
              : "degraded",
      })),
  };
}

function buildCommandOverlayState(scene) {
  const units = Array.isArray(scene?.units) ? scene.units : [];
  const unitsById = new Map(units.map((unit) => [String(unit.id), unit]));
  const hqs = units
    .filter((unit) => unit?.anchor && (unit?.counterFrame?.isHeadquarters || (unit?.inspector?.command?.subordinates?.length ?? 0) > 0))
    .map((unit) => ({
      id: unit.id,
      name: unit.name || unit.id || "HQ",
      anchor: unit.anchor,
      faction: normalizeOverlayFaction(unit?.side),
      echelon: unit?.counterFrame?.echelon ?? "battalion",
      radius: MAP_OPERATIONAL_OVERLAY_TOKENS.commandRadiusByEchelon[unit?.counterFrame?.echelon ?? "battalion"] || 56,
      subordinateIds: (unit?.inspector?.command?.subordinates ?? [])
        .map((entry) => String(entry?.id || "").trim())
        .filter(Boolean),
    }));

  const links = units
    .map((unit) => {
      const superiorId = String(
        unit?.inspector?.command?.superior?.id
        || unit?.inspector?.command?.hq_unit_id
        || "",
      ).trim();
      const superior = superiorId ? unitsById.get(superiorId) : null;
      if (!unit?.anchor || !superior?.anchor || superior.id === unit.id) {
        return null;
      }
      return {
        id: `${superior.id}:${unit.id}`,
        superiorId: superior.id,
        subordinateId: unit.id,
        from: superior.anchor,
        to: unit.anchor,
        degraded: Boolean(unit?.counterAppearance?.outOfCommand || unit?.counterStatusOverlay?.outOfCommand),
        faction: normalizeOverlayFaction(unit?.side),
      };
    })
    .filter(Boolean)
    .filter((link, index, list) => index === list.findIndex((entry) => entry.id === link.id));

  return {
    label: "Command",
    available: Boolean(hqs.length || links.length),
    status: hqs.length ? `${hqs.length} HQs • ${links.length} links` : "Unavailable",
    detail: hqs.length
      ? "Influence radii scale by echelon as a command-visibility aid only. Link lines follow exposed superior/subordinate relationships and mark degraded command connections when units are out of command."
      : "Authoritative command relationships are not exposed for currently plotted formations.",
    hqs,
    links,
  };
}

function buildPressureAreaAnchors(snapshot, scene) {
  const objectivesById = new Map((scene?.objectives ?? []).map((objective) => [String(objective.id), objective]));
  const airfieldsById = new Map((scene?.airfields ?? []).map((airfield) => [upperText(airfield.id), airfield]));
  const portsById = new Map((scene?.ports ?? []).map((port) => [upperText(port.id), port]));

  return (Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [])
    .map((area) => {
      let anchor = hasCoord(area) ? projectScenePoint(area, scene) : null;
      if (!anchor && area?.objective_id) {
        anchor = objectivesById.get(String(area.objective_id))?.anchor ?? null;
      }
      if (!anchor && area?.location_id) {
        const locationId = upperText(area.location_id);
        anchor = airfieldsById.get(locationId)?.anchor ?? portsById.get(locationId)?.anchor ?? null;
      }
      if (!anchor) {
        return null;
      }
      return {
        ...area,
        anchor,
        label: String(area?.label || area?.id || "Local Area").trim() || "Local Area",
      };
    })
    .filter(Boolean);
}

function inferBarrierFeature(area) {
  const text = [
    area?.label,
    area?.kind,
    area?.defensive_preparation?.obstacle_state,
    area?.defensive_preparation?.fortification_state,
  ].map(lowerText).join(" ");

  if (/(bridge|crossing|ford)/.test(text)) {
    return "crossing";
  }
  if (/(river|forks)/.test(text)) {
    return "majorRiver";
  }
  if (/(creek|stream)/.test(text)) {
    return "minorRiver";
  }
  if (/(ridge|escarpment|slope|cliff)/.test(text)) {
    return "escarpment";
  }
  if (/(wire|obstacle|impassable|blocked|mine)/.test(text)) {
    return "impassable";
  }
  return null;
}

function buildBarrierOverlayState(snapshot, scene) {
  const features = buildPressureAreaAnchors(snapshot, scene)
    .map((area) => {
      const type = inferBarrierFeature(area);
      if (!type) {
        return null;
      }
      return {
        id: area.id,
        label: area.label,
        anchor: area.anchor,
        type,
      };
    })
    .filter(Boolean);

  const waterFeatures = features
    .filter((feature) => feature.type === "majorRiver" || feature.type === "minorRiver")
    .sort((left, right) => left.anchor.x - right.anchor.x);

  const segments = waterFeatures.flatMap((feature, index) => {
    const next = waterFeatures[index + 1];
    if (!next || distanceBetween(feature.anchor, next.anchor) > 180) {
      return [];
    }
    return [{
      id: `${feature.id}:${next.id}`,
      type: feature.type === "majorRiver" || next.type === "majorRiver" ? "majorRiver" : "minorRiver",
      from: feature.anchor,
      to: next.anchor,
    }];
  });

  return {
    label: "Barriers",
    available: Boolean(features.length || segments.length),
    status: features.length
      ? `${features.filter((feature) => feature.type.includes("River")).length} water barriers • ${features.filter((feature) => feature.type === "crossing").length} crossings`
      : "Unavailable",
    detail: features.length
      ? "Barrier cues derive from named local areas and exposed obstacle-preparation text. Full riverbank and terrain-edge geometry is not exposed on the current shell path."
      : "Barrier geometry is not exposed on the current shell path.",
    features,
    segments,
  };
}

function buildInfrastructureOverlayState(snapshot, scene) {
  const pressureAreas = buildPressureAreaAnchors(snapshot, scene);
  const crossings = pressureAreas
    .filter((area) => /(bridge|crossing|ford)/i.test(String(area.label)))
    .map((area) => ({
      id: area.id,
      label: area.label,
      anchor: area.anchor,
      kind: "crossing",
      interdicted: /damaged|interdict|blocked/i.test(String(area?.defensive_preparation?.obstacle_state || "")),
    }));

  const ports = (scene?.ports ?? []).map((port) => ({
    id: port.id,
    label: port.name,
    anchor: port.anchor,
    kind: "port",
    interdicted: false,
  }));
  const airfields = (scene?.airfields ?? []).map((airfield) => ({
    id: airfield.id,
    label: airfield.name,
    anchor: airfield.anchor,
    kind: "airfield",
    interdicted: airfield?.airfield?.damageState === "damaged" || airfield?.airfield?.damageState === "destroyed",
  }));

  return {
    label: "Infrastructure",
    available: Boolean(ports.length || airfields.length || crossings.length),
    status: `${ports.length} port${ports.length === 1 ? "" : "s"} • ${airfields.length} airfield${airfields.length === 1 ? "" : "s"}`,
    detail: crossings.length
      ? "Ports, airfields, and crossing nodes are plotted from the current shell path. Authored road and rail geometry are not yet exposed, so only bridge/crossing points can be shown live."
      : "Ports and airfields are plotted from the current shell path. Authored road and rail geometry are not yet exposed.",
    primaryRoads: [],
    secondaryRoads: [],
    railLines: [],
    nodes: [...ports, ...airfields, ...crossings],
  };
}

function buildObjectiveOverlayState(scene) {
  const objectives = Array.isArray(scene?.objectives) ? scene.objectives : [];
  const counts = objectives.reduce(
    (summary, objective) => {
      const category = objective?.objectiveOverlay?.category ?? "secondary";
      summary[category] += 1;
      if (objective?.objectiveOverlay?.contested) {
        summary.contested += 1;
      }
      return summary;
    },
    { primary: 0, secondary: 0, supply: 0, political: 0, strategic: 0, contested: 0 },
  );

  return {
    label: "Objectives",
    available: Boolean(objectives.length),
    status: objectives.length
      ? `${counts.primary + counts.strategic + counts.political} primary • ${counts.secondary} secondary • ${counts.supply} supply`
      : "Unavailable",
    detail: objectives.length
      ? counts.contested
        ? `${counts.contested} objective locality${counts.contested === 1 ? " is" : "ies are"} currently contested or unheld. Objective tiers use authored objective metadata when present, otherwise they fall back to exposed value, ownership state, and collocated port / airfield context.`
        : "Objective tiers use authored objective metadata when present, otherwise they fall back to exposed value, ownership state, and collocated port / airfield context."
      : "No plotted objectives are available on the current shell path.",
    counts,
  };
}

function inferMovementIntent(unit) {
  const searchText = joinSearchText(
    unit?.inspector?.orders?.action,
    unit?.inspector?.orders?.status,
    unit?.inspector?.orders?.lifecycle_state,
    unit?.inspector?.orders?.note,
    unit?.inspector?.operational_state?.posture,
    unit?.status,
  );

  if (!searchText) {
    return null;
  }
  if (/(counterattack|attack|assault|strike)/.test(searchText)) {
    return "attack";
  }
  if (/(advance|exploit|pursuit)/.test(searchText)) {
    return "advance";
  }
  if (/(retreat|fallback|withdraw|delay)/.test(searchText)) {
    return "fallback";
  }
  if (/(move|march|redeploy|reposition|approach|assembly|shift|reserve)/.test(searchText)) {
    return "move";
  }
  return null;
}

function inferMovementCommitment(unit, intent) {
  const searchText = joinSearchText(
    unit?.inspector?.orders?.action,
    unit?.inspector?.orders?.status,
    unit?.inspector?.orders?.lifecycle_state,
    unit?.inspector?.orders?.note,
  );
  if (!searchText) {
    return intent === "attack" ? "planned" : "committed";
  }
  if (/(queued|prepare|planning|await|assembly|forming|reserve|start line)/.test(searchText)) {
    return "planned";
  }
  if (/(execut|engag|moving|committed|active|contact|advancing)/.test(searchText)) {
    return "committed";
  }
  return intent === "attack" || intent === "advance" ? "planned" : "committed";
}

function buildMovementPathWaypoints(from, to, intent, commitment, unitId) {
  const dx = Number(to?.x ?? 0) - Number(from?.x ?? 0);
  const dy = Number(to?.y ?? 0) - Number(from?.y ?? 0);
  const distance = Math.hypot(dx, dy);
  if (!Number.isFinite(distance) || distance < 52) {
    return [];
  }

  const direction = ((String(unitId).length % 2) * 2) - 1 || 1;
  const offsetMagnitude = Math.min(22, Math.max(10, distance * (intent === "fallback" ? 0.08 : 0.06)));
  const normalX = distance ? (-dy / distance) * offsetMagnitude * direction : 0;
  const normalY = distance ? (dx / distance) * offsetMagnitude * direction : 0;
  const primaryMid = {
    x: Number((from.x + dx * 0.52 + normalX).toFixed(2)),
    y: Number((from.y + dy * 0.52 + normalY).toFixed(2)),
  };

  if (commitment === "planned" && distance > 120 && intent !== "attack") {
    return [
      {
        x: Number((from.x + dx * 0.32 + normalX * 0.7).toFixed(2)),
        y: Number((from.y + dy * 0.32 + normalY * 0.7).toFixed(2)),
      },
      {
        x: Number((from.x + dx * 0.68 + normalX * 0.35).toFixed(2)),
        y: Number((from.y + dy * 0.68 + normalY * 0.35).toFixed(2)),
      },
    ];
  }

  return intent === "attack" ? [] : [primaryMid];
}

function matchMovementTargetByText(searchText, candidates) {
  if (!searchText) {
    return null;
  }
  return candidates.find((candidate) => candidate.searchText && searchText.includes(candidate.searchText)) ?? null;
}

function buildMovementIntentOverlayState(snapshot, scene) {
  const pressureAreas = buildPressureAreaAnchors(snapshot, scene);
  const units = (Array.isArray(scene?.units) ? scene.units : []).filter((unit) => {
    const kind = lowerText(unit?.kind);
    return !kind.includes("air") && !kind.includes("naval") && !kind.includes("sea");
  });
  const unitsById = new Map(units.map((unit) => [String(unit.id), unit]));
  const objectives = (Array.isArray(scene?.objectives) ? scene.objectives : []).map((objective) => ({
    id: objective.id,
    label: objective.name,
    anchor: objective.anchor,
    faction: normalizeOverlayFaction(objective?.side),
    contested: Boolean(objective?.objectiveOverlay?.contested),
    strategic: objective?.objectiveOverlay?.category === "strategic",
    searchText: normalizeSearchText(objective?.name),
    kind: "objective",
  }));
  const sources = buildSupplySources(scene).map((source) => ({
    ...source,
    label: source.name,
    searchText: normalizeSearchText(source?.name),
    faction: normalizeOverlayFaction(source?.side),
  }));
  const hqs = units
    .filter((unit) => unit?.anchor && unit?.counterFrame?.isHeadquarters)
    .map((unit) => ({
      id: unit.id,
      label: unit.name,
      anchor: unit.anchor,
      faction: normalizeOverlayFaction(unit?.side),
      searchText: normalizeSearchText(unit?.name),
      kind: "hq",
    }));
  const namedCandidates = [
    ...pressureAreas.map((area) => ({
      id: area.id,
      label: area.label,
      anchor: area.anchor,
      faction: "unknown",
      searchText: normalizeSearchText(area?.label),
      kind: "pressure",
    })),
    ...objectives,
    ...sources,
    ...hqs,
  ];

  const paths = units
    .map((unit) => {
      const intent = inferMovementIntent(unit);
      if (!intent || !unit?.anchor) {
        return null;
      }

      const commitment = inferMovementCommitment(unit, intent);
      const searchText = joinSearchText(
        unit?.inspector?.orders?.action,
        unit?.inspector?.orders?.status,
        unit?.inspector?.orders?.lifecycle_state,
        unit?.inspector?.orders?.note,
      );
      const faction = normalizeOverlayFaction(unit?.side);
      const directTarget = matchMovementTargetByText(searchText, namedCandidates);
      let target = directTarget;

      if (!target && (intent === "attack" || intent === "advance")) {
        target = nearestByDistance(
          [
            ...pressureAreas.filter((area) => area?.anchor),
            ...objectives.filter((objective) => objective.contested || (objective.faction !== faction && objective.faction !== "unknown")),
          ],
          unit.anchor,
          260,
        );
      }
      if (!target && intent === "fallback") {
        const superiorId = String(unit?.inspector?.command?.superior?.id || unit?.inspector?.command?.hq_unit_id || "").trim();
        target = (superiorId ? unitsById.get(superiorId) : null) ?? nearestByDistance(
          [...sources.filter((source) => source.faction === faction || source.faction === "unknown"), ...hqs.filter((hq) => hq.faction === faction)],
          unit.anchor,
          260,
        );
      }
      if (!target) {
        target = nearestByDistance(
          [...pressureAreas.filter((area) => area?.anchor), ...objectives],
          unit.anchor,
          220,
        );
      }
      if (!target?.anchor || distanceBetween(unit.anchor, target.anchor) < 26) {
        return null;
      }

      const waypoints = buildMovementPathWaypoints(unit.anchor, target.anchor, intent, commitment, unit.id);
      const route = [unit.anchor, ...waypoints, target.anchor];
      const movementState = lowerText(unit?.inspector?.movement?.remaining);

      return {
        id: unit.id,
        unitId: unit.id,
        unitName: unit.name || unit.id || "Formation",
        from: unit.anchor,
        to: target.anchor,
        targetLabel: target.label || "Operational axis",
        intent,
        commitment,
        route,
        waypoints,
        queuedWaypoints: [],
        movementState: movementState || null,
      };
    })
    .filter(Boolean);

  const counts = paths.reduce(
    (summary, path) => {
      summary[path.intent] += 1;
      summary[path.commitment] += 1;
      return summary;
    },
    { move: 0, attack: 0, advance: 0, fallback: 0, planned: 0, committed: 0 },
  );

  return {
    label: "Movement / Orders",
    available: Boolean(paths.length),
    status: paths.length
      ? `${counts.move + counts.advance} movement • ${counts.attack} attack • ${counts.fallback} fallback`
      : "Unavailable",
    detail: paths.length
      ? `${counts.planned} planned • ${counts.committed} committed. Exact route geometry and queued waypoints are not exposed, so axes infer direction from current order text plus the nearest relevant plotted objective, pressure area, HQ, or source node.`
      : "No plotted formation currently exposes enough order state to infer a movement or attack axis.",
    paths,
  };
}

function buildFrontlineOverlayState(snapshot, scene) {
  const pressureAreas = buildPressureAreaAnchors(snapshot, scene);
  const reportsByArea = buildReportsByLocalArea(snapshot);
  const objectivesById = new Map((Array.isArray(scene?.objectives) ? scene.objectives : []).map((objective) => [String(objective.id), objective]));

  const sectors = pressureAreas.map((area) => {
    const reports = reportsByArea.get(area.id) ?? [];
    const reportSeverity = reports.reduce((highest, report) => Math.max(highest, report.severityRank), 0);
    const pressureText = joinSearchText(area?.label, area?.kind, ...(area?.pressure_reasons ?? []), reports.map((report) => report.searchText).join(" "));
    const objective = area?.objective_id ? objectivesById.get(String(area.objective_id)) ?? null : null;
    const atRiskObjective = objective && normalizeOverlayFaction(objective?.side) === "friendly" && lowerText(objective?.state) === "unheld";
    const defensiveText = joinSearchText(
      area?.defensive_preparation?.state,
      area?.defensive_preparation?.fortification_state,
      area?.defensive_preparation?.obstacle_state,
      area?.defensive_preparation?.engineer_state,
    );
    const hot = reportSeverity >= 2 || atRiskObjective || /(attack|counterattack|artillery|engagement|assault|infiltration|pressure)/.test(pressureText);
    const quiet = !hot && !reports.length && defensiveText.length > 0;
    const state = hot ? "hot" : quiet ? "quiet" : "contested";
    const stress = hot && atRiskObjective
      ? "breakthrough"
      : hot && !defensiveText
        ? "thin"
        : null;

    return {
      id: area.id,
      label: area.label,
      anchor: area.anchor,
      state,
      stress,
      objectiveId: area?.objective_id ?? null,
      reportCount: reports.length,
      radius: Number((MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.frontSector + (hot ? 10 : quiet ? -4 : 0)).toFixed(2)),
    };
  });

  const orderedSectors = [...sectors].sort((left, right) => left.anchor.x - right.anchor.x || left.anchor.y - right.anchor.y);
  const segments = orderedSectors.flatMap((sector, index) => {
    const next = orderedSectors[index + 1];
    if (!next || distanceBetween(sector.anchor, next.anchor) > 220) {
      return [];
    }
    const state = sector.state === "hot" || next.state === "hot"
      ? "hot"
      : sector.state === "quiet" && next.state === "quiet"
        ? "quiet"
        : "contested";
    return [{
      id: `${sector.id}:${next.id}`,
      from: sector.anchor,
      to: next.anchor,
      state,
    }];
  });

  const counts = sectors.reduce(
    (summary, sector) => {
      summary[sector.state] += 1;
      if (sector.stress === "breakthrough") {
        summary.breakthrough += 1;
      }
      if (sector.stress === "thin") {
        summary.thin += 1;
      }
      return summary;
    },
    { hot: 0, contested: 0, quiet: 0, breakthrough: 0, thin: 0 },
  );

  return {
    label: "Front / Sectors",
    available: Boolean(sectors.length),
    status: sectors.length
      ? `${counts.hot} hot • ${counts.contested} contested • ${counts.quiet} quiet`
      : "Unavailable",
    detail: sectors.length
      ? `${counts.breakthrough} breakthrough-risk • ${counts.thin} thin-sector markers. Frontage is inferred from named pressure areas and local dispatch severity only; no authored front-line geometry is exposed.`
      : "No local pressure areas are exposed for front-line inference on the current shell path.",
    sectors,
    segments,
  };
}

function buildFogIntelOverlayState(snapshot, scene) {
  const currentHours = metricNumber(snapshot?.time?.current_hours);
  const pressureAreas = buildPressureAreaAnchors(snapshot, scene);
  const reportsByArea = buildReportsByLocalArea(snapshot);
  const objectivesById = new Map((Array.isArray(scene?.objectives) ? scene.objectives : []).map((objective) => [String(objective.id), objective]));

  const contacts = pressureAreas
    .map((area) => {
      const reports = [...(reportsByArea.get(area.id) ?? [])].sort((left, right) => (right.time ?? -1) - (left.time ?? -1));
      const latest = reports[0] ?? null;
      const objective = area?.objective_id ? objectivesById.get(String(area.objective_id)) ?? null : null;
      const atRiskObjective = objective && lowerText(objective?.state) === "unheld";
      const intelText = joinSearchText(area?.label, area?.kind, latest?.title, latest?.summary, ...(area?.pressure_reasons ?? []));
      const ageHours = currentHours != null && latest?.time != null ? Math.max(0, currentHours - latest.time) : null;

      let state = null;
      if (/(hidden|concealed|masked)/.test(intelText)) {
        state = "hidden";
      } else if (ageHours != null && ageHours > 12) {
        state = "stale";
      } else if (latest && (latest.severityRank >= 2 || atRiskObjective)) {
        state = "confirmed";
      } else if (latest) {
        state = "spotted";
      } else if ((area?.pressure_reasons ?? []).length || atRiskObjective) {
        state = "uncertain";
      }

      if (!state) {
        return null;
      }

      return {
        id: area.id,
        label: area.label,
        anchor: area.anchor,
        state,
        uncertainStrength: state === "uncertain" || /(unknown|uncertain|possible|probable|contact)/.test(intelText),
        ageHours,
      };
    })
    .filter(Boolean);

  const counts = contacts.reduce(
    (summary, contact) => {
      summary[contact.state] += 1;
      return summary;
    },
    { stale: 0, spotted: 0, confirmed: 0, uncertain: 0, hidden: 0 },
  );

  return {
    label: "Fog / Intel",
    available: true,
    status: contacts.length
      ? `${counts.confirmed} confirmed • ${counts.spotted + counts.uncertain} tentative`
      : "Wash only",
    detail: contacts.length
      ? `${counts.stale} stale • ${counts.hidden} hidden-like cues. Unseen areas remain under the wash; contact confidence is inferred from exposed local report recency, severity, and named pressure areas only.`
      : "No dedicated recon geometry is exposed. The layer currently uses a restrained unseen wash and waits for local report or pressure-area cues to place contact confidence markers.",
    contacts,
  };
}

function isRecord(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function readWeatherText(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function humanizeWeatherText(value) {
  const raw = readWeatherText(value);
  if (!raw) {
    return null;
  }
  return raw
    .replace(/[_.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function normalizedHourOfDay(currentHours) {
  if (typeof currentHours !== "number" || !Number.isFinite(currentHours)) {
    return null;
  }
  const raw = ((currentHours % 24) + 24) % 24;
  return Math.floor(raw);
}

function timeOfDayState(currentHours) {
  const hour = normalizedHourOfDay(currentHours);
  if (hour == null) {
    return "Time unavailable";
  }
  if (hour >= 5 && hour < 7) {
    return "Dawn";
  }
  if (hour >= 7 && hour < 18) {
    return "Daylight";
  }
  if (hour >= 18 && hour < 20) {
    return "Dusk";
  }
  return "Night";
}

function currentForecastRow(snapshot, weather) {
  const forecast = Array.isArray(weather?.forecast) ? weather.forecast : [];
  if (!forecast.length) {
    return null;
  }

  const currentHours = typeof snapshot?.time?.current_hours === "number" ? snapshot.time.current_hours : null;
  if (currentHours != null) {
    const exact = forecast.find((entry) => {
      if (!isRecord(entry)) {
        return false;
      }
      return entry.hour === currentHours || entry.time === currentHours;
    });
    if (isRecord(exact)) {
      return exact;
    }
  }

  if (forecast.length === 1 && isRecord(forecast[0])) {
    return forecast[0];
  }

  const zeroHour = forecast.find((entry) => {
    if (!isRecord(entry)) {
      return false;
    }
    return entry.hour === 0 || entry.time === 0;
  });
  return isRecord(zeroHour) ? zeroHour : null;
}

export function buildWeatherImpactState(snapshot) {
  const weather = isRecord(snapshot?.weather) ? snapshot.weather : null;
  const currentHours = typeof snapshot?.time?.current_hours === "number" ? snapshot.time.current_hours : null;
  const timeState = timeOfDayState(currentHours);
  const condition = humanizeWeatherText(weather?.condition);
  const summary = readWeatherText(weather?.summary);
  const ground = humanizeWeatherText(weather?.ground);
  const forecast = currentForecastRow(snapshot, weather);
  const visibility = humanizeWeatherText(forecast?.visibility);
  const localContext = Array.isArray(snapshot?.local_pressure_areas) && snapshot.local_pressure_areas.length > 0;
  const lowLight = timeState === "Night" || timeState === "Dawn" || timeState === "Dusk";

  if (!condition) {
    return {
      available: false,
      current: "Weather unavailable",
      timeState,
      operations: "Unavailable",
      visibility: "Not exposed",
      nightOperations: "Not modeled",
      air: "Not exposed",
      groundMovement: "Not exposed",
      note: "Authoritative weather impact is not exposed on the current shell path.",
    };
  }

  let operations = "Weather cue only";
  if (summary) {
    operations = "Summary exposed";
  } else if (ground || visibility) {
    operations = "Context exposed";
  }

  let note = summary;
  if (!note && ground && visibility) {
    note = `Weather impact uses current condition plus exposed ground state ${ground} and visibility ${visibility} only.`;
  } else if (!note && ground) {
    note = `Weather impact uses current condition plus exposed ground state ${ground} only.`;
  } else if (!note && visibility) {
    note = `Weather impact uses current condition plus exposed visibility ${visibility} only.`;
  } else if (!note && lowLight && localContext) {
    note = `${timeState} conditions are visible over the Henderson/Lunga perimeter, but separate low-visibility operational effects are not exposed beyond the current weather state.`;
  } else if (!note && lowLight) {
    note = `${timeState} conditions are visible from the theatre clock, but separate low-visibility operational effects are not exposed beyond the current weather state.`;
  } else if (!note && localContext) {
    note = `${condition} is the only current operational weather signal tied to the Henderson/Lunga fight. Visibility, ground-movement, air-support, and combat-readiness effects are not separately exposed.`;
  } else if (!note) {
    note = `${condition} is the only current operational weather signal on the shell path. Visibility, ground-movement, air-support, and combat-readiness effects are not separately exposed.`;
  }

  return {
    available: true,
    current: condition,
    timeState,
    operations,
    visibility: visibility || "Not exposed",
    nightOperations: "Not modeled",
    air: "Weather cue only",
    groundMovement: ground || "Not exposed",
    note,
  };
}

export function buildOperationalOverlayState(snapshot, scene) {
  const resolvedScene = scene || buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const locMarkers = buildLocMarkers(resolvedScene);
  const artilleryMarkers = buildArtilleryMarkers(resolvedScene);
  const weatherImpact = buildWeatherImpactState(snapshot);
  const supply = buildSupplyOverlayState(resolvedScene);
  const command = buildCommandOverlayState(resolvedScene);
  const barriers = buildBarrierOverlayState(snapshot, resolvedScene);
  const infrastructure = buildInfrastructureOverlayState(snapshot, resolvedScene);
  const movementIntent = buildMovementIntentOverlayState(snapshot, resolvedScene);
  const frontline = buildFrontlineOverlayState(snapshot, resolvedScene);
  const objectives = buildObjectiveOverlayState(resolvedScene);
  const fogIntel = buildFogIntelOverlayState(snapshot, resolvedScene);
  const locCounts = locMarkers.reduce(
    (counts, marker) => {
      counts[marker.state] += 1;
      return counts;
    },
    { connected: 0, threatened: 0, broken: 0 },
  );

  return {
    historicalUnderlay: {
      label: "Historical underlay",
      available: Boolean(resolvedScene?.underlay?.available),
      status: resolvedScene?.underlay?.available ? "Ready" : "Unavailable",
      detail: resolvedScene?.underlay?.available
        ? resolvedScene.underlay.label || "Historical map underlay is available for this slice."
        : "No scenario-specific historical underlay is available for the current slice.",
    },
    terrainEmphasis: {
      label: "Terrain emphasis",
      available: true,
      status: resolvedScene?.underlay?.available ? "Underlay tuned" : "Field wash only",
      detail: resolvedScene?.underlay?.available
        ? "Adds a restrained contour and hatch wash above the terrain field so the underlay reads more clearly without overtaking counters."
        : "Adds a restrained contour wash above the terrain field when no historical underlay is present.",
    },
    grid: {
      label: "Hex grid",
      available: true,
      status: "Available",
      detail: "Zoom-aware major and minor grid strokes remain on the centralized layer system so board readability can be tuned without changing gameplay positions.",
    },
    weatherImpact,
    weatherWash: {
      label: "Weather wash",
      available: weatherImpact.available,
      status: weatherImpact.operations,
      detail: weatherImpact.note,
    },
    objectives,
    supply,
    supplyLoc: {
      label: "Supply / LOC",
      available: locMarkers.length > 0,
      status: locMarkers.length > 0 ? `${locMarkers.length} tracked` : "Unavailable",
      detail: locMarkers.length > 0
        ? `${locCounts.connected} connected, ${locCounts.threatened} threatened, ${locCounts.broken} broken.`
        : "Authoritative LOC overlay data is not exposed on the current shell path.",
      markers: locMarkers,
    },
    command,
    movementIntent,
    frontline,
    barriers,
    infrastructure,
    fogIntel,
    reconIntel: {
      label: "Recon / Intel",
      available: false,
      status: "Not exposed",
      detail: "Operational reconnaissance overlay data is not exposed on the current shell path.",
    },
    airInfluence: {
      label: "Air Influence",
      available: false,
      status: "Not exposed",
      detail: "Authoritative air range and air influence geometry is not exposed on the current shell path.",
    },
    navalSupport: {
      label: "Naval Support",
      available: false,
      status: "Not exposed",
      detail: "Authoritative sea-reach and naval support overlay data is not exposed on the current shell path.",
    },
    artillery: {
      label: "Artillery / Fire Support",
      available: artilleryMarkers.length > 0,
      status: artilleryMarkers.length > 0 ? `${artilleryMarkers.length} formations` : "Unavailable",
      detail: artilleryMarkers.length > 0
        ? "Highlights formations that already expose branch-specific artillery support records."
        : "No artillery-support overlay records are exposed for currently plotted formations.",
      markers: artilleryMarkers,
    },
  };
}
