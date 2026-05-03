import { Fragment, useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent, type PointerEvent, type WheelEvent } from "react";
import type { ViewSnapshot } from "../../types/viewSnapshot";
import lungaPointUnderlayUrl from "../../assets/lunga_point_underlay.svg";
import { axialRound, pixelToAxial } from "../../lib/hex.js";
import { inferScenarioPresentation } from "../../lib/view_snapshot.js";
import { MAP_LABEL_STYLE_TOKENS, MAP_OPERATIONAL_OVERLAY_TOKENS, MAP_SIZE_TOKENS } from "../../map/designTokens.js";
import {
  appendGreaseMarkupPoint,
  createGreaseMarkupItem,
  GREASE_MARKUP_STYLE_OPTIONS,
  GREASE_MARKUP_TOOL_OPTIONS,
  isGreaseMarkupToolContinuous,
  shouldCommitGreaseMarkup,
} from "../../map/greaseMarkup.js";
import { HEX_TILE_PATHS } from "../../map/hexTile.js";
import { buildDeclutteredLabels, buildMarkerObstacleRect } from "../../map/labelDeclutter.js";
import { buildMapOverlayManager, isMapLayerEnabled } from "../../map/overlayManager.js";
import { buildUnitCounterPaletteStyle } from "../../map/unitCounterPalette.js";
import MapDataQAScene from "../../map/dev/MapDataQAScene";
import KoreaOperationalBasemapScene from "../../map/dev/KoreaOperationalBasemapScene";
import InfrastructureGameplayScene from "../../map/dev/InfrastructureGameplayScene";
import ScenarioAuthoringQAScene from "../../map/dev/ScenarioAuthoringQAScene";
import ScenarioOverrideQAScene from "../../map/dev/ScenarioOverrideQAScene";
import VisibilityQAScene from "../../map/dev/VisibilityQAScene";
import {
  collectVisibleBasemapTiles,
  flattenBasemapTiles,
  loadBasemapManifest,
  loadBasemapTiles,
  resolveBasemapPackageTheater,
  summarizeBasemapSourceState,
} from "../../map/runtime/BasemapLoader.js";
import { resolveBasemapStyle } from "../../map/runtime/basemapStyle.js";
import {
  buildInitialMapCamera,
  buildMapScene,
  buildOperationalOverlayState,
  clampMapCamera,
  projectMapCameraPoint,
  projectScenePoint,
  summarizeMapZoomPresentation,
  unprojectScenePoint,
} from "./map_scene.js";
import { summarizeWeatherOverlay } from "./map_weather.js";
import GreaseBoard from "./GreaseBoard";
import GreaseMarkupOverlay from "./GreaseMarkupOverlay";
import GreaseMarkupPalette from "./GreaseMarkupPalette";
import HexTileHarnessPanel from "./HexTileHarnessPanel";
import AirfieldIcon from "./AirfieldIcon";
import AirfieldIconHarnessPanel from "./AirfieldIconHarnessPanel";
import MapLabelHarnessPanel from "./MapLabelHarnessPanel";
import MapOverlayHarnessPanel from "./MapOverlayHarnessPanel";
import MapTokenPreviewPanel from "./MapTokenPreviewPanel";
import NatoLegendSymbol from "./NatoLegendSymbol";
import ObjectiveOverlayBadge from "./ObjectiveOverlayBadge";
import OperationPlannerPanel, { type PlannerWorkbenchTab } from "./OperationPlannerPanel";
import SettlementIcon from "./SettlementIcon";
import SettlementIconHarnessPanel from "./SettlementIconHarnessPanel";
import UnitCounterFrame from "./UnitCounterFrame";
import UnitCounterFrameHarnessPanel from "./UnitCounterFrameHarnessPanel";
import UnitCounterStatusOverlay from "./UnitCounterStatusOverlay";
import { summarizeGreaseBoard } from "./grease_board_summary.js";
import type { InspectorSelection } from "./inspector_types";
import { buildMapCommandPreview, summarizeOperationPlanner, summarizeTrackedOperations } from "./operations_planner.js";
import type { FastCommandPreview, OperationPlannerActions, OperationPlannerState, TrackedDemoOperation } from "./operations_planner_types";

type MapPanelShellProps = {
  snapshot: ViewSnapshot;
  selectedSelection: InspectorSelection | null;
  operations: TrackedDemoOperation[];
  activeLayers: Record<string, boolean>;
  plannerState: OperationPlannerState;
  plannerWorkbenchTab: PlannerWorkbenchTab;
  plannerActions: OperationPlannerActions;
  greaseMarkup: {
    scenarioId: string | null;
    activeTool: string | null;
    activeStyle: string;
    selectedId: string | null;
    items: Array<{
      id: string;
      tool: string;
      style: string;
      points: Array<{ x: number; y: number }>;
      createdAt: number;
    }>;
  };
  greaseMarkupActions: {
    onSetActiveTool: (toolId: string | null) => void;
    onSetActiveStyle: (styleId: string) => void;
    onCommitItem: (item: {
      id: string;
      tool: string;
      style: string;
      points: Array<{ x: number; y: number }>;
      createdAt: number;
    }) => void;
    onSelectItem: (itemId: string | null) => void;
    onRemoveSelectedItem: () => void;
    onClearAll: () => void;
  };
  onToggleLayer: (id: string) => void;
  onSelectPlannerWorkbenchTab: (tab: PlannerWorkbenchTab) => void;
  onCommitFastCommand: (preview: FastCommandPreview | null) => void;
  onSelectSelection: (selection: InspectorSelection) => void;
};

function routePathData(points: Array<{ x: number; y: number }>): string {
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
}

function namedFeatureVisibilityMatches(visibility: string | null | undefined, zoomTier: string): boolean {
  const rule = String(visibility || "operational").trim().toLowerCase();
  if (rule === "always" || rule === "far") {
    return true;
  }
  if (rule === "close") {
    return zoomTier === "close";
  }
  if (rule === "selected_only" || rule === "hidden") {
    return false;
  }
  return zoomTier !== "far";
}

const BASEMAP_HEX_CORNER_OFFSETS = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI / 180) * (60 * index - 30);
  return pixelToAxial(Math.cos(angle), Math.sin(angle), 1);
});

const BASEMAP_NEIGHBOR_DIRECTIONS = [
  [1, 0],
  [1, -1],
  [0, -1],
  [-1, 0],
  [-1, 1],
  [0, 1],
] as const;

function normalizeBasemapTerrainClass(terrainClass: string | null | undefined): string {
  const raw = String(terrainClass || "plains").trim().toLowerCase();
  if (raw === "dense_forest") {
    return "forest";
  }
  if (raw === "urban_built_up") {
    return "urban";
  }
  if (raw === "grass_open" || raw === "cropland") {
    return "plains";
  }
  if (raw === "wetland") {
    return "rough";
  }
  if (raw === "bare_rock") {
    return "mountain";
  }
  return raw || "plains";
}

function basemapHexCoordKey(q: number, r: number): string {
  return `${q}:${r}`;
}

function resolveBasemapCrossingKind(crossingKinds: unknown): string {
  const values = Array.isArray(crossingKinds) ? crossingKinds.map((entry) => String(entry || "").trim().toLowerCase()) : [];
  if (values.includes("bridge")) {
    return "bridge";
  }
  if (values.includes("ford")) {
    return "ford";
  }
  if (values.includes("ferry_terminal")) {
    return "ferry_terminal";
  }
  if (values.includes("port_crossing")) {
    return "port_crossing";
  }
  return "crossing";
}

function resolveBasemapRoadClass(segmentClass: unknown): "primary" | "secondary" {
  return String(segmentClass || "").trim().toLowerCase() === "primary_road" ? "primary" : "secondary";
}

type BasemapRawBounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

type BasemapProjectionContext = {
  rawBounds: BasemapRawBounds;
  rawViewport: BasemapRawBounds;
  containsRawPoint: (point: unknown, pad?: number) => boolean;
  segmentTouchesRawBounds: (segment: { from?: unknown; to?: unknown }, pad?: number) => boolean;
  projectWorldPoint: (point: unknown, featureMeta?: { id?: unknown; name?: unknown }) => { x: number; y: number };
};

const KOREA_AO_BASEMAP_RAW_BOUNDS = Object.freeze({
  minX: -2.45,
  maxX: 0.95,
  minY: 20.9,
  maxY: 22.5,
});

function expandBasemapRawBounds(bounds: BasemapRawBounds, padX: number, padY: number): BasemapRawBounds {
  return {
    minX: bounds.minX - padX,
    maxX: bounds.maxX + padX,
    minY: bounds.minY - padY,
    maxY: bounds.maxY + padY,
  };
}

function numericMapCoord(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function resolveSnapshotPresentationBounds(
  snapshot: ViewSnapshot,
  key: "world_bounds" | "basemap_raw_bounds",
): BasemapRawBounds | null {
  const bounds = snapshot?.map_presentation?.[key];
  if (!bounds) {
    return null;
  }

  const minX = numericMapCoord(bounds.min_x);
  const maxX = numericMapCoord(bounds.max_x);
  const minY = numericMapCoord(bounds.min_y);
  const maxY = numericMapCoord(bounds.max_y);

  if (minX == null || maxX == null || minY == null || maxY == null) {
    return null;
  }
  if (maxX <= minX || maxY <= minY) {
    return null;
  }

  return {
    minX,
    maxX,
    minY,
    maxY,
  };
}

function rawPointX(point: unknown): number | null {
  if (!point || typeof point !== "object") {
    return null;
  }
  const row = point as Record<string, unknown>;
  return numericMapCoord(row.x) ?? numericMapCoord(row.q);
}

function rawPointY(point: unknown): number | null {
  if (!point || typeof point !== "object") {
    return null;
  }
  const row = point as Record<string, unknown>;
  return numericMapCoord(row.y) ?? numericMapCoord(row.r);
}

function normalizeBasemapLookupText(...values: unknown[]): string {
  return values
    .flatMap((value) => {
      if (Array.isArray(value)) {
        return value;
      }
      return [value];
    })
    .map((value) => String(value ?? "").trim().toLowerCase())
    .filter(Boolean)
    .join(" ")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function collectNormalizedMapLabelKeys(...values: unknown[]): string[] {
  return values
    .flatMap((value) => {
      if (Array.isArray(value)) {
        return value;
      }
      return [value];
    })
    .map((value) => normalizeMapLabelKey(value))
    .filter(Boolean);
}

const KOREA_AO_PRIORITY_LABEL_PATTERN = /inchon harbor|incheon harbor|inchon beachhead|inchon|incheon|kimpo airfield|gimpo airfield|kimpo corridor|kimpo|gimpo|yongdungpo|crossings|seoul defensive belt|seoul defensive ring|seoul axis|seoul|han river|han estuary/;
const KOREA_AO_ROUTE_LABEL_PATTERN = /kimpo corridor|yongdungpo|crossings|seoul axis|han river|han estuary/;

function isKoreaAoPriorityLabel(...values: unknown[]): boolean {
  return KOREA_AO_PRIORITY_LABEL_PATTERN.test(normalizeBasemapLookupText(...values));
}

function isKoreaAoRouteLabel(...values: unknown[]): boolean {
  return KOREA_AO_ROUTE_LABEL_PATTERN.test(normalizeBasemapLookupText(...values));
}

function collectSnapshotMapRows(snapshot: ViewSnapshot): Array<Record<string, unknown>> {
  return [
    ...(Array.isArray(snapshot?.objectives) ? snapshot.objectives : []),
    ...(Array.isArray(snapshot?.airfields) ? snapshot.airfields : []),
    ...(Array.isArray(snapshot?.ports) ? snapshot.ports : []),
    ...(Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : []),
    ...(Array.isArray(snapshot?.units) ? snapshot.units : []),
  ].filter((row) => row && typeof row === "object") as Array<Record<string, unknown>>;
}

function findWorldAnchor(snapshot: ViewSnapshot, tokens: string[]): { x: number; y: number } | null {
  const rows = collectSnapshotMapRows(snapshot);
  for (const row of rows) {
    const x = numericMapCoord(row.x);
    const y = numericMapCoord(row.y);
    if (x == null || y == null) {
      continue;
    }
    const searchText = normalizeBasemapLookupText(
      row.id,
      row.name,
      row.label,
      row.location_id,
      row.objective_id,
      row.historical_name,
      row.modern_name,
    );
    if (tokens.some((token) => searchText.includes(token))) {
      return { x, y };
    }
  }
  return null;
}

function buildKoreaAoBasemapProjection(snapshot: ViewSnapshot): BasemapProjectionContext | null {
  const searchText = normalizeBasemapLookupText(
    snapshot?.scenario?.id,
    snapshot?.scenario?.name,
    (snapshot?.objectives || []).map((objective) => objective?.name),
    (snapshot?.airfields || []).map((airfield) => airfield?.name),
    (snapshot?.ports || []).map((port) => port?.name),
  );
  if (!/inchon|incheon|chromite|kimpo|gimpo|seoul/.test(searchText)) {
    return null;
  }

  const seoulWorld = findWorldAnchor(snapshot, ["seoul"]) || { x: 46, y: 36 };
  const inchonWorld = findWorldAnchor(snapshot, ["inchon harbor", "incheon harbor", "inchon", "incheon"]) || { x: 18, y: 58 };
  const kimpoWorld = findWorldAnchor(snapshot, ["kimpo", "gimpo"]) || {
    x: Number((inchonWorld.x + (seoulWorld.x - inchonWorld.x) * 0.46).toFixed(2)),
    y: Number((inchonWorld.y + (seoulWorld.y - inchonWorld.y) * 0.54).toFixed(2)),
  };
  const suwonWorld = findWorldAnchor(snapshot, ["suwon"]) || {
    x: Number((seoulWorld.x + 12.4).toFixed(2)),
    y: Number((seoulWorld.y - 5.5).toFixed(2)),
  };
  const qBasis = {
    x: Number((seoulWorld.x - inchonWorld.x).toFixed(4)),
    y: Number((seoulWorld.y - inchonWorld.y).toFixed(4)),
  };
  const rBasis = {
    x: Number((seoulWorld.x - suwonWorld.x).toFixed(4)),
    y: Number((seoulWorld.y - suwonWorld.y).toFixed(4)),
  };
  const authoredRawBounds = resolveSnapshotPresentationBounds(snapshot, "basemap_raw_bounds");
  const rawBounds = authoredRawBounds ?? KOREA_AO_BASEMAP_RAW_BOUNDS;
  const rawViewport = expandBasemapRawBounds(
    rawBounds,
    authoredRawBounds ? 0.18 : 0.44,
    authoredRawBounds ? 0.16 : 0.38,
  );
  const incheonIntlWorld = {
    x: Number((inchonWorld.x - qBasis.x * 0.22 + rBasis.x * 0.08).toFixed(2)),
    y: Number((inchonWorld.y - qBasis.y * 0.22 + rBasis.y * 0.08).toFixed(2)),
  };
  const overrideRows = [
    { tokens: ["kimpo", "gimpo"], point: kimpoWorld },
    { tokens: ["seoul"], point: seoulWorld },
    { tokens: ["suwon"], point: suwonWorld },
    { tokens: ["inchon harbor", "incheon harbor", "inchon", "incheon"], point: inchonWorld },
    { tokens: ["incheon int l", "incheon intl"], point: incheonIntlWorld },
  ];

  function containsRawPoint(point: unknown, pad = 0): boolean {
    const x = rawPointX(point);
    const y = rawPointY(point);
    if (x == null || y == null) {
      return false;
    }
    return x >= rawBounds.minX - pad
      && x <= rawBounds.maxX + pad
      && y >= rawBounds.minY - pad
      && y <= rawBounds.maxY + pad;
  }

  function segmentTouchesRawBounds(segment: { from?: unknown; to?: unknown }, pad = 0.9): boolean {
    const fromX = rawPointX(segment?.from);
    const fromY = rawPointY(segment?.from);
    const toX = rawPointX(segment?.to);
    const toY = rawPointY(segment?.to);
    if (fromX == null || fromY == null || toX == null || toY == null) {
      return false;
    }
    const minX = Math.min(fromX, toX);
    const maxX = Math.max(fromX, toX);
    const minY = Math.min(fromY, toY);
    const maxY = Math.max(fromY, toY);
    return maxX >= rawBounds.minX - pad
      && minX <= rawBounds.maxX + pad
      && maxY >= rawBounds.minY - pad
      && minY <= rawBounds.maxY + pad;
  }

  function resolveFeatureOverride(featureMeta?: { id?: unknown; name?: unknown }): { x: number; y: number } | null {
    if (!featureMeta) {
      return null;
    }
    const search = normalizeBasemapLookupText(featureMeta.id, featureMeta.name);
    const match = overrideRows.find((row) => row.tokens.some((token) => search.includes(token)));
    return match?.point ?? null;
  }

  function projectWorldPoint(point: unknown, featureMeta?: { id?: unknown; name?: unknown }): { x: number; y: number } {
    const override = resolveFeatureOverride(featureMeta);
    if (override) {
      return override;
    }
    const rawX = rawPointX(point) ?? 0;
    const rawY = rawPointY(point) ?? 22;
    return {
      x: Number((seoulWorld.x + rawX * qBasis.x + (rawY - 22) * rBasis.x).toFixed(2)),
      y: Number((seoulWorld.y + rawX * qBasis.y + (rawY - 22) * rBasis.y).toFixed(2)),
    };
  }

  return {
    rawBounds,
    rawViewport,
    containsRawPoint,
    segmentTouchesRawBounds,
    projectWorldPoint,
  };
}

function normalizeMapLabelKey(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export default function MapPanelShell({
  snapshot,
  selectedSelection,
  operations,
  activeLayers,
  plannerState,
  plannerWorkbenchTab,
  plannerActions,
  greaseMarkup,
  greaseMarkupActions,
  onToggleLayer,
  onSelectPlannerWorkbenchTab,
  onCommitFastCommand,
  onSelectSelection,
}: MapPanelShellProps) {
  const [legendOpen, setLegendOpen] = useState(false);
  const [plannerPinned, setPlannerPinned] = useState(false);
  const [cameraState, setCameraState] = useState({ zoom: 1, offsetX: 0, offsetY: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [commandHoverHex, setCommandHoverHex] = useState<{ q: number; r: number } | null>(null);
  const [stageSize, setStageSize] = useState({ width: 1000, height: 620 });
  const [greaseDraft, setGreaseDraft] = useState<{
    pointerId: number;
    tool: string;
    style: string;
    worldPoints: Array<{ x: number; y: number }>;
    scenePoints: Array<{ x: number; y: number }>;
  } | null>(null);
  const [basemapManifest, setBasemapManifest] = useState<Record<string, unknown> | null>(null);
  const [basemapTiles, setBasemapTiles] = useState<Array<Record<string, unknown>>>([]);
  const [basemapError, setBasemapError] = useState<string | null>(null);
  const qaWorkbenchVisible = import.meta.env.DEV;
  const stageRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const cameraAutoFitKeyRef = useRef<string | null>(null);
  const cameraInteractedRef = useRef(false);
  const dragStateRef = useRef<{
    pointerId: number;
    clientX: number;
    clientY: number;
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const mapReadabilityStyle = useMemo(() => ({
    "--shell-map-label-ghost-opacity": String(MAP_LABEL_STYLE_TOKENS.opacity.basemapGhost),
    "--shell-map-label-basemap-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.basemapGhost}px`,
    "--shell-map-label-basemap-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.basemapGhost}px`,
    "--shell-map-label-objective-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.objective}px`,
    "--shell-map-label-objective-meta-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.objectiveMeta}px`,
    "--shell-map-label-objective-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.objective}px`,
    "--shell-map-label-objective-meta-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.objectiveMeta}px`,
    "--shell-map-label-feature-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.feature}px`,
    "--shell-map-label-feature-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.feature}px`,
    "--shell-map-label-site-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.site}px`,
    "--shell-map-label-site-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.site}px`,
    "--shell-map-label-unit-size": `${MAP_LABEL_STYLE_TOKENS.fontSizePx.unit}px`,
    "--shell-map-label-unit-halo-width": `${MAP_LABEL_STYLE_TOKENS.haloWidthPx.unit}px`,
  }) as CSSProperties, []);
  const sceneOptions = useMemo(() => {
    const width = stageSize.width > 0 ? Math.round(stageSize.width) : 1000;
    const height = stageSize.height > 0 ? Math.round(stageSize.height) : 620;
    const inset = Math.max(48, Math.round(Math.min(width, height) * 0.095));
    return { width, height, inset };
  }, [stageSize]);
  const scene = useMemo(() => buildMapScene(snapshot, sceneOptions), [snapshot, sceneOptions]);
  const presentation = useMemo(() => inferScenarioPresentation(snapshot), [snapshot]);
  const camera = useMemo(() => clampMapCamera(cameraState, scene), [cameraState, scene]);
  const zoomPresentation = useMemo(() => summarizeMapZoomPresentation(camera.zoom), [camera.zoom]);
  const basemapStyle = useMemo(() => resolveBasemapStyle(camera.zoom), [camera.zoom]);
  const basemapProjection = useMemo(
    () => (resolveBasemapPackageTheater(snapshot) === "korea_peninsula_coarse_v1" ? buildKoreaAoBasemapProjection(snapshot) : null),
    [snapshot],
  );
  const overlayState = useMemo(() => buildOperationalOverlayState(snapshot, scene), [snapshot, scene]);
  const plannerSummary = useMemo(() => summarizeOperationPlanner(snapshot, scene, plannerState), [snapshot, scene, plannerState]);
  const trackedOperations = useMemo(() => summarizeTrackedOperations(snapshot, operations, { scene }), [snapshot, operations, scene]);
  const greaseBoard = useMemo(() => summarizeGreaseBoard(snapshot, operations), [snapshot, operations]);
  const weatherOverlay = summarizeWeatherOverlay(snapshot);
  const selectedUnitId = selectedSelection?.kind === "unit" ? selectedSelection.id : null;
  const selectedObjectiveId = selectedSelection?.kind === "objective" ? selectedSelection.id : null;
  const selectedAirfieldId = selectedSelection?.kind === "airfield" ? selectedSelection.id : null;
  const selectedPortId = selectedSelection?.kind === "port" ? selectedSelection.id : null;
  const basemapTheaterId = useMemo(() => resolveBasemapPackageTheater(snapshot), [snapshot]);
  const basemapTileScene = useMemo(
    () => (basemapProjection ? { ...scene, viewport: basemapProjection.rawViewport } : scene),
    [basemapProjection, scene],
  );
  const basemapPackageExpected = Boolean(basemapTheaterId);
  const hasHistoricalUnderlay = scene.underlay?.available && scene.underlay.id === "lunga_point_henderson";
  const resolvedLayerToggles = useMemo(() => {
    const next = { ...activeLayers };
    next.greasePlanning = plannerState.greaseEnabled
      ? (Object.prototype.hasOwnProperty.call(activeLayers, "greasePlanning") ? activeLayers.greasePlanning : true)
      : false;
    const availability = {
      basemap: basemapPackageExpected,
      historicalUnderlay: hasHistoricalUnderlay,
      weatherWash: overlayState.weatherWash.available,
      barriers: overlayState.barriers.available,
      infrastructure: overlayState.infrastructure.available,
      supply: overlayState.supply.available,
      command: overlayState.command.available,
      movementIntent: overlayState.movementIntent.available,
      frontline: overlayState.frontline.available,
      artillery: overlayState.artillery.available,
      objectives: overlayState.objectives.available,
    };

    Object.entries(availability).forEach(([id, available]) => {
      if (!available) {
        next[id] = false;
      }
    });
    return next;
  }, [activeLayers, basemapPackageExpected, hasHistoricalUnderlay, overlayState, plannerState.greaseEnabled]);
  const overlayManager = useMemo(() => buildMapOverlayManager({
    toggles: {
      ...resolvedLayerToggles,
      historicalUnderlay: hasHistoricalUnderlay ? resolvedLayerToggles.historicalUnderlay ?? true : false,
      greasePlanning: plannerState.greaseEnabled && (resolvedLayerToggles.greasePlanning ?? false),
      terrainField: true,
      units: true,
      labels: true,
      ui: true,
    },
  }), [resolvedLayerToggles, hasHistoricalUnderlay, plannerState.greaseEnabled]);
  const basemapLayerVisible = isMapLayerEnabled(overlayManager, "basemap");
  const underlayLayerVisible = isMapLayerEnabled(overlayManager, "historicalUnderlay");
  const terrainFieldLayerVisible = isMapLayerEnabled(overlayManager, "terrainField");
  const terrainEmphasisLayerVisible = isMapLayerEnabled(overlayManager, "terrainEmphasis");
  const gridLayerVisible = isMapLayerEnabled(overlayManager, "grid");
  const weatherLayerVisible = isMapLayerEnabled(overlayManager, "weatherWash");
  const barrierLayerVisible = isMapLayerEnabled(overlayManager, "barriers");
  const artilleryLayerVisible = isMapLayerEnabled(overlayManager, "artillery");
  const supplyLayerVisible = isMapLayerEnabled(overlayManager, "supply");
  const commandLayerVisible = isMapLayerEnabled(overlayManager, "command");
  const movementIntentLayerVisible = isMapLayerEnabled(overlayManager, "movementIntent");
  const frontlineLayerVisible = isMapLayerEnabled(overlayManager, "frontline");
  const fogIntelLayerVisible = isMapLayerEnabled(overlayManager, "fogIntel");
  const greasePlanningLayerVisible = isMapLayerEnabled(overlayManager, "greasePlanning");
  const objectivesLayerVisible = isMapLayerEnabled(overlayManager, "objectives");
  const infrastructureLayerVisible = isMapLayerEnabled(overlayManager, "infrastructure");
  const unitsLayerVisible = isMapLayerEnabled(overlayManager, "units");
  const labelsLayerVisible = isMapLayerEnabled(overlayManager, "labels");
  const terrainTransform = `translate(${camera.offsetX} ${camera.offsetY}) scale(${camera.zoom})`;
  const objectiveSelectionActive = plannerState.greaseEnabled && (plannerState.selectingObjective || (plannerState.plannerOpen && !plannerState.approved));
  const greaseToolArmed = Boolean(plannerState.greaseEnabled && greasePlanningLayerVisible && greaseMarkup.activeTool && !objectiveSelectionActive);
  const quickCommandPreview = useMemo(() => {
    if (!selectedUnitId || !commandHoverHex || greaseToolArmed || objectiveSelectionActive) {
      return null;
    }
    return buildMapCommandPreview(snapshot, selectedUnitId, commandHoverHex);
  }, [snapshot, selectedUnitId, commandHoverHex, greaseToolArmed, objectiveSelectionActive]);
  const transformedQuickCommandPreview = useMemo(() => {
    if (!quickCommandPreview?.available) {
      return null;
    }
    return {
      ...quickCommandPreview,
      cameraRoute: quickCommandPreview.route.map((point) => projectMapCameraPoint(projectScenePoint(point, scene), camera)),
      cameraTarget: projectMapCameraPoint(
        projectScenePoint({ x: quickCommandPreview.targetHex.q, y: quickCommandPreview.targetHex.r }, scene),
        camera,
      ),
    };
  }, [quickCommandPreview, scene, camera]);
  const topControlInset = plannerState.plannerOpen
    ? "calc(min(348px, calc(100vw - 24px)) + clamp(10px, 1vw, 16px))"
    : "calc(188px + clamp(10px, 1vw, 16px))";

  const transformedObjectives = useMemo(
    () => scene.objectives.map((objective) => ({
      ...objective,
      cameraAnchor: projectMapCameraPoint(objective.anchor, camera),
      cameraDisplayAnchor: projectMapCameraPoint(objective.displayAnchor, camera),
    })),
    [scene.objectives, camera],
  );
  const transformedAirfields = useMemo(
    () => scene.airfields.map((airfield) => ({
      ...airfield,
      cameraAnchor: projectMapCameraPoint(airfield.anchor, camera),
      cameraDisplayAnchor: projectMapCameraPoint(airfield.displayAnchor, camera),
    })),
    [scene.airfields, camera],
  );
  const transformedPorts = useMemo(
    () => scene.ports.map((port) => ({
      ...port,
      cameraAnchor: projectMapCameraPoint(port.anchor, camera),
      cameraDisplayAnchor: projectMapCameraPoint(port.displayAnchor, camera),
    })),
    [scene.ports, camera],
  );
  const transformedNamedFeatures = useMemo(
    () => scene.namedFeatures.map((feature) => ({
      ...feature,
      cameraAnchor: projectMapCameraPoint(feature.anchor, camera),
      cameraPoints: (Array.isArray(feature.points) ? feature.points : []).map((point) => projectMapCameraPoint(point, camera)),
    })),
    [scene.namedFeatures, camera],
  );
  const transformedUnits = useMemo(
    () => scene.units.map((unit) => ({
      ...unit,
      cameraAnchor: projectMapCameraPoint(unit.anchor, camera),
      cameraDisplayAnchor: projectMapCameraPoint(unit.displayAnchor, camera),
    })),
    [scene.units, camera],
  );
  const transformedUnitsById = useMemo(
    () => new Map(transformedUnits.map((unit) => [String(unit.id), unit])),
    [transformedUnits],
  );
  const visibleBasemapTileRefs = useMemo(
    () => collectVisibleBasemapTiles(basemapManifest, basemapTileScene, basemapStyle.tileTier),
    [basemapManifest, basemapTileScene, basemapStyle.tileTier],
  );
  const visibleBasemapTileKey = useMemo(
    () => visibleBasemapTileRefs.map((tile) => `${tile.tileId}:${tile.tx}:${tile.ty}`).join("|"),
    [visibleBasemapTileRefs],
  );
  const basemapFeatures = useMemo(
    () => flattenBasemapTiles(basemapTiles),
    [basemapTiles],
  );
  const basemapRuntimeState = useMemo(
    () => summarizeBasemapSourceState({
      expected: basemapPackageExpected,
      manifest: basemapManifest,
      tilePayloads: basemapTiles,
      visibleTileCount: visibleBasemapTileRefs.length,
      error: basemapError,
      fallbackAvailable: hasHistoricalUnderlay,
    }),
    [basemapError, basemapManifest, basemapPackageExpected, basemapTiles, hasHistoricalUnderlay, visibleBasemapTileRefs.length],
  );
  const basemapFallbackUnderlayActive = basemapRuntimeState.fallbackMode === "historical_underlay";
  const effectiveUnderlayLayerVisible = underlayLayerVisible || basemapFallbackUnderlayActive;
  const basemapLayerSummary = useMemo(() => {
    if (!basemapPackageExpected) {
      return {
        label: "Packaged basemap",
        available: false,
        status: "Unavailable",
        detail: "No packaged runtime basemap is registered for the current scenario family.",
      };
    }
    if (basemapRuntimeState.sourceStatus === "error") {
      return {
        label: "Packaged basemap",
        available: true,
        status: basemapFallbackUnderlayActive ? "Load error / fallback" : "Load error",
        detail: basemapFallbackUnderlayActive
          ? `${basemapRuntimeState.developerMessage} Switched to the historical underlay fallback for this slice.`
          : basemapRuntimeState.developerMessage,
      };
    }
    if (basemapRuntimeState.sourceStatus === "loading") {
      return {
        label: "Packaged basemap",
        available: true,
        status: "Loading",
        detail: "Loading packaged terrain, hydro, transport, and node tiles for the current theater.",
      };
    }
    if (!basemapRuntimeState.terrainReady) {
      return {
        label: "Packaged basemap",
        available: true,
        status: "Invalid",
        detail: basemapRuntimeState.developerMessage,
      };
    }
    return {
      label: "Packaged basemap",
      available: true,
      status: `Ready (${basemapTiles.length} tile${basemapTiles.length === 1 ? "" : "s"} in view)`,
      detail: `${presentation.basemapLabel} tiles are aligned beneath the current theater overlays and grid.`,
    };
  }, [basemapFallbackUnderlayActive, basemapPackageExpected, basemapRuntimeState, basemapTiles.length, presentation.basemapLabel]);
  const overlayLayerCatalog = useMemo(() => ({
    basemap: basemapLayerSummary,
    historicalUnderlay: overlayState.historicalUnderlay,
    terrainEmphasis: overlayState.terrainEmphasis,
    grid: overlayState.grid,
    weatherWash: overlayState.weatherWash,
    barriers: overlayState.barriers,
    infrastructure: overlayState.infrastructure,
    supply: overlayState.supply,
    command: overlayState.command,
    movementIntent: overlayState.movementIntent,
    frontline: overlayState.frontline,
    artillery: overlayState.artillery,
    fogIntel: overlayState.fogIntel,
    greasePlanning: {
      label: "Planning markup",
      available: true,
      status: plannerState.greaseEnabled
        ? `${greaseMarkup.items.length} mark${greaseMarkup.items.length === 1 ? "" : "s"}`
        : "Planner off",
      detail: plannerState.greaseEnabled
        ? `${greaseMarkup.items.length} local grease mark${greaseMarkup.items.length === 1 ? "" : "s"} stored for this scenario.`
        : "Enable grease overlay from the planner to draw markup on the map.",
    },
    objectives: overlayState.objectives,
  }), [basemapLayerSummary, overlayState, plannerState.greaseEnabled, greaseMarkup.items.length]);
  const overlayControlEntries = useMemo(
    () => overlayManager.registry
      .filter((layer) => layer.toggleable)
      .map((layer) => {
        const summary = overlayLayerCatalog[layer.id] || {
          label: layer.label,
          available: true,
          status: "Available",
          detail: `${layer.label} is registered in the centralized overlay manager.`,
        };
        const active = isMapLayerEnabled(overlayManager, layer.id);
        return {
          id: layer.id,
          label: summary.label || layer.label,
          detail: summary.detail,
          status: summary.status,
          toggleable: layer.toggleable && summary.available !== false,
          active,
          stateLabel: layer.id === "basemap" ? summary.status : active ? "On" : summary.status,
        };
      }),
    [overlayManager, overlayLayerCatalog],
  );
  const activeOverlayCount = useMemo(
    () => overlayControlEntries.filter((entry) => entry.active).length,
    [overlayControlEntries],
  );
  const plannerActiveToolLabel = useMemo(() => {
    if (!greaseMarkup.activeTool) {
      return "Navigate";
    }
    return GREASE_MARKUP_TOOL_OPTIONS.find((tool) => tool.id === greaseMarkup.activeTool)?.label ?? "Custom";
  }, [greaseMarkup.activeTool]);
  const plannerActiveStyleLabel = useMemo(
    () => GREASE_MARKUP_STYLE_OPTIONS.find((style) => style.id === greaseMarkup.activeStyle)?.label ?? "Amber",
    [greaseMarkup.activeStyle],
  );
  const plannerVisibilityLabel = plannerState.greaseEnabled
    ? greasePlanningLayerVisible ? "Visible" : "Hidden"
    : "Off";
  const plannerLayerCountLabel = `${activeOverlayCount} on`;
  const plannerMapControlGroups = useMemo(() => ([
    {
      id: "terrain",
      label: "Terrain / Base",
      entries: overlayControlEntries.filter((entry) => (
        entry.id === "basemap"
        || entry.id === "historicalUnderlay"
        || entry.id === "terrainEmphasis"
        || entry.id === "grid"
      )),
    },
    {
      id: "operations",
      label: "Operational Layers",
      entries: overlayControlEntries.filter((entry) => (
        entry.id === "weatherWash"
        || entry.id === "barriers"
        || entry.id === "infrastructure"
        || entry.id === "supply"
        || entry.id === "command"
        || entry.id === "movementIntent"
        || entry.id === "frontline"
        || entry.id === "artillery"
        || entry.id === "fogIntel"
        || entry.id === "greasePlanning"
      )),
    },
    {
      id: "markers",
      label: "Markers / Labels",
      entries: overlayControlEntries.filter((entry) => entry.id === "objectives"),
    },
  ].filter((group) => group.entries.length)), [overlayControlEntries]);
  const transformedBasemap = useMemo(() => {
    const mapBasemapWorldPoint = (point: unknown, featureMeta?: { id?: unknown; name?: unknown }) => (
      basemapProjection?.projectWorldPoint(point, featureMeta)
      ?? {
        x: rawPointX(point) ?? 0,
        y: rawPointY(point) ?? 0,
      }
    );
    const hexLookup = new Map(
      (basemapFeatures.hexes || []).map((hexRecord) => [basemapHexCoordKey(Number(hexRecord.q), Number(hexRecord.r)), hexRecord]),
    );
    const contourMajorModulo = basemapStyle.tileTier === "close" ? 4 : basemapStyle.tileTier === "operational" ? 2 : 1;

    const contourHexIds = new Set(
      (basemapFeatures.hexes || [])
        .filter((hexRecord) => {
          if (!hexRecord.contourBand || hexRecord.contourBand <= 0) {
            return false;
          }
          return BASEMAP_NEIGHBOR_DIRECTIONS.some(([dq, dr]) => {
            const neighbor = hexLookup.get(basemapHexCoordKey(Number(hexRecord.q) + dq, Number(hexRecord.r) + dr));
            return Boolean(neighbor) && Number(neighbor.contourBand) !== Number(hexRecord.contourBand);
          });
        })
        .map((hexRecord) => String(hexRecord.hexId)),
    );

    return {
      hexes: (basemapFeatures.hexes || [])
        .filter((hexRecord) => hexRecord.zoomRelevance?.[basemapStyle.tileTier] !== false)
        .filter((hexRecord) => !basemapProjection || basemapProjection.containsRawPoint(hexRecord, 0.84))
        .map((hexRecord) => {
          const q = Number(hexRecord.q);
          const r = Number(hexRecord.r);
          const center = projectScenePoint(mapBasemapWorldPoint({ x: q, y: r }), scene);
          return {
            ...hexRecord,
            center,
            points: BASEMAP_HEX_CORNER_OFFSETS
              .map((offset) => mapBasemapWorldPoint({ x: q + offset.q, y: r + offset.r }))
              .map((point) => projectScenePoint(point, scene))
              .map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`)
              .join(" "),
            terrainClass: normalizeBasemapTerrainClass(hexRecord.terrainClass),
            showContour: contourHexIds.has(String(hexRecord.hexId)),
            majorContour: Number(hexRecord.contourBand || 0) % contourMajorModulo === 0,
          };
        }),
      settlements: (basemapFeatures.settlements || [])
        .filter((settlement) => !basemapProjection || basemapProjection.containsRawPoint(settlement, 0.68))
        .map((settlement) => ({
          ...settlement,
          point: projectScenePoint(
            mapBasemapWorldPoint({ x: Number(settlement.q), y: Number(settlement.r) }, settlement),
            scene,
          ),
        })),
      airfields: (basemapFeatures.airfields || [])
        .filter((airfield) => !basemapProjection || basemapProjection.containsRawPoint(airfield, 0.68))
        .map((airfield) => ({
          ...airfield,
          point: projectScenePoint(
            mapBasemapWorldPoint({ x: Number(airfield.q), y: Number(airfield.r) }, airfield),
            scene,
          ),
        })),
      roadSegments: (basemapFeatures.roadSegments || [])
        .filter((segment) => !basemapProjection || basemapProjection.segmentTouchesRawBounds(segment, 1.05))
        .map((segment) => ({
          ...segment,
          from: projectScenePoint(mapBasemapWorldPoint(segment.from), scene),
          to: projectScenePoint(mapBasemapWorldPoint(segment.to), scene),
        })),
      railSegments: (basemapFeatures.railSegments || [])
        .filter((segment) => !basemapProjection || basemapProjection.segmentTouchesRawBounds(segment, 1.05))
        .map((segment) => ({
          ...segment,
          from: projectScenePoint(mapBasemapWorldPoint(segment.from), scene),
          to: projectScenePoint(mapBasemapWorldPoint(segment.to), scene),
        })),
    };
  }, [basemapFeatures, basemapProjection, basemapStyle.tileTier, scene]);

  useEffect(() => {
    let cancelled = false;
    setBasemapManifest(null);
    setBasemapTiles([]);
    setBasemapError(null);

    if (!basemapTheaterId) {
      return undefined;
    }

    loadBasemapManifest(basemapTheaterId)
      .then((manifest) => {
        if (!cancelled) {
          setBasemapManifest(manifest as Record<string, unknown>);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setBasemapError(error instanceof Error ? error.message : "Unable to load packaged basemap manifest.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [basemapTheaterId]);

  useEffect(() => {
    let cancelled = false;

    if (!basemapTheaterId || !basemapManifest || !visibleBasemapTileRefs.length) {
      setBasemapTiles([]);
      return undefined;
    }

    loadBasemapTiles(basemapTheaterId, visibleBasemapTileRefs, basemapStyle.tileTier)
      .then((tiles) => {
        if (!cancelled) {
          setBasemapTiles(tiles as Array<Record<string, unknown>>);
          setBasemapError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setBasemapError(error instanceof Error ? error.message : "Unable to load packaged basemap tiles.");
          setBasemapTiles([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [basemapManifest, basemapStyle.tileTier, basemapTheaterId, visibleBasemapTileKey, visibleBasemapTileRefs]);
  const labelObstacles = useMemo(() => {
    const scale = zoomPresentation.counterScale;
    return [
      ...transformedObjectives.map((objective) => buildMarkerObstacleRect({
        id: `objective:${objective.id}`,
        kind: "objective",
        x: objective.cameraDisplayAnchor.x,
        y: objective.cameraDisplayAnchor.y,
        width: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.5,
        height: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.5,
        scale,
      })),
      ...transformedAirfields.map((airfield) => buildMarkerObstacleRect({
        id: `airfield:${airfield.id}`,
        kind: "airfield",
        x: airfield.cameraDisplayAnchor.x,
        y: airfield.cameraDisplayAnchor.y,
        width: MAP_SIZE_TOKENS.airfieldIcon.widthPx,
        height: MAP_SIZE_TOKENS.airfieldIcon.heightPx,
        scale,
      })),
      ...transformedPorts.map((port) => buildMarkerObstacleRect({
        id: `port:${port.id}`,
        kind: "port",
        x: port.cameraDisplayAnchor.x,
        y: port.cameraDisplayAnchor.y,
        width: 20,
        height: 16,
        scale,
      })),
      ...transformedUnits.map((unit) => buildMarkerObstacleRect({
        id: `unit:${unit.id}`,
        kind: "unit",
        x: unit.cameraDisplayAnchor.x,
        y: unit.cameraDisplayAnchor.y,
        width: MAP_SIZE_TOKENS.unitIconBox.widthPx,
        height: MAP_SIZE_TOKENS.unitIconBox.heightPx + 4,
        scale,
      })),
    ];
  }, [transformedObjectives, transformedAirfields, transformedPorts, transformedUnits, zoomPresentation.counterScale]);
  const labelDeclutter = useMemo(() => {
    const scale = zoomPresentation.counterScale;
    const koreaFocusedLabeling = /korea|inchon|seoul/.test(`${presentation.shellTitle} ${presentation.theaterLabel}`.toLowerCase());
    const basemapSettlementLabelMin = basemapStyle.tier === "close" ? 4 : koreaFocusedLabeling ? 4 : 6;
    const basemapAirfieldLabelMin = basemapStyle.tier === "close" ? 2 : koreaFocusedLabeling ? 2 : 4;
    const objectiveLabelKeys = new Set(
      transformedObjectives.flatMap((objective) => collectNormalizedMapLabelKeys(
        objective.map_label,
        objective.displayName,
        objective.name,
        objective.historical_name,
        objective.modern_name,
      )),
    );
    const objectiveLocationIds = new Set(
      transformedObjectives.map((objective) => String(objective.location_id || "").trim()).filter(Boolean),
    );
    const authoredMapLabelKeys = new Set([
      ...transformedObjectives.flatMap((objective) => collectNormalizedMapLabelKeys(
        objective.map_label,
        objective.displayName,
        objective.name,
        objective.historical_name,
        objective.modern_name,
      )),
      ...transformedAirfields.flatMap((airfield) => collectNormalizedMapLabelKeys(airfield.map_label, airfield.name)),
      ...transformedPorts.flatMap((port) => collectNormalizedMapLabelKeys(port.map_label, port.name)),
    ].filter(Boolean));
    const candidates = [
      ...transformedBasemap.settlements
        .filter((settlement) => String(settlement.name || "").trim())
        .filter((settlement) => Number(settlement.importance || 0) >= basemapSettlementLabelMin)
        .filter((settlement) => !authoredMapLabelKeys.has(normalizeMapLabelKey(settlement.name)))
        .map((settlement) => {
          const ownerId = `basemap:settlement:${settlement.id}`;
          const importance = Number(settlement.importance || 0);
          return {
            id: `${ownerId}:label`,
            ownerId,
            kind: "featureLabel",
            text: settlement.name,
            x: settlement.point.x + 7.5 * scale,
            y: settlement.point.y - 6.5 * scale,
            textAnchor: "start",
            scale,
            important: importance >= basemapSettlementLabelMin + 2 || ["major_city", "capital"].includes(String(settlement.tier || "")),
            visibility: basemapStyle.tier === "close" ? "close" : "operational",
            priorityBoost: importance * 5,
          };
        }),
      ...transformedBasemap.airfields
        .filter((airfield) => String(airfield.name || "").trim())
        .filter((airfield) => Number(airfield.importance || 0) >= basemapAirfieldLabelMin)
        .filter((airfield) => !authoredMapLabelKeys.has(normalizeMapLabelKey(airfield.name)))
        .map((airfield) => {
          const ownerId = `basemap:airfield:${airfield.id}`;
          const importance = Number(airfield.importance || 0);
          return {
            id: `${ownerId}:label`,
            ownerId,
            kind: "airfieldLabel",
            text: airfield.name,
            x: airfield.point.x + 8 * scale,
            y: airfield.point.y - 6 * scale,
            textAnchor: "start",
            scale,
            important: importance >= basemapAirfieldLabelMin + 1 || String(airfield.tier || "") === "major_airbase",
            visibility: basemapStyle.tier === "close" ? "close" : "operational",
            priorityBoost: importance * 4,
          };
        }),
      ...transformedObjectives.flatMap((objective) => {
        const ownerId = `objective:${objective.id}`;
        const importanceTier = Number(objective.objectiveOverlay?.importanceTier || 0);
        const koreaAxisObjective = koreaFocusedLabeling
          && isKoreaAoPriorityLabel(objective.displayName || objective.name, objective.id, objective.location_id);
        const important = objective.settlement?.tier === "capital"
          || objective.settlement?.tier === "major_city"
          || importanceTier >= 2
          || koreaAxisObjective;
        const selected = selectedObjectiveId === objective.id;
        const forceVisible = koreaAxisObjective && importanceTier >= 3;
        return [
          {
            id: `${ownerId}:label`,
            ownerId,
            ownerObstacleId: ownerId,
            kind: "objectiveLabel",
            text: objective.map_label || objective.displayName || objective.name,
            x: objective.cameraDisplayAnchor.x + objective.labelX * scale,
            y: objective.cameraDisplayAnchor.y + objective.labelY * scale,
            textAnchor: objective.labelAnchor,
            scale,
            important,
            selected,
            forceVisible: selected || forceVisible,
            visibility: objective.visibility,
            tier: objective.settlement?.tier,
            priorityBoost: importanceTier * 6 + (koreaAxisObjective ? 22 : 0),
          },
          {
            id: `${ownerId}:state`,
            ownerId,
            ownerObstacleId: ownerId,
            kind: "objectiveState",
            text: objective.stateLabel,
            x: objective.cameraDisplayAnchor.x + objective.stateX * scale,
            y: objective.cameraDisplayAnchor.y + objective.stateY * scale,
            textAnchor: objective.stateAnchor,
            scale,
            important,
            selected,
            forceVisible: selected,
            visibility: objective.visibility,
            tier: objective.settlement?.tier,
            priorityBoost: importanceTier * 4 + (koreaAxisObjective ? 14 : 0),
          },
        ];
      }),
      ...transformedAirfields.map((airfield) => {
        const ownerId = `airfield:${airfield.id}`;
        const selected = selectedAirfieldId === airfield.id;
        const koreaAxisAirfield = koreaFocusedLabeling && isKoreaAoPriorityLabel(airfield.name, airfield.id);
        const duplicatesObjective = objectiveLocationIds.has(String(airfield.location_id || "").trim())
          || collectNormalizedMapLabelKeys(airfield.map_label, airfield.name).some((key) => objectiveLabelKeys.has(key));
        return {
          id: `${ownerId}:label`,
          ownerId,
          ownerObstacleId: ownerId,
          kind: "airfieldLabel",
          text: airfield.map_label || airfield.name,
          x: airfield.cameraDisplayAnchor.x + airfield.labelOffsetX * scale,
          y: airfield.cameraDisplayAnchor.y + airfield.labelOffsetY * scale,
          textAnchor: airfield.labelAnchor,
          scale,
          important: airfield.airfield?.tier === "major_airbase" || koreaAxisAirfield,
          selected,
          forceVisible: selected || (koreaAxisAirfield && !duplicatesObjective),
          priorityBoost: koreaAxisAirfield ? 18 : 0,
        };
      }),
      ...transformedPorts.map((port) => {
        const ownerId = `port:${port.id}`;
        const selected = selectedPortId === port.id;
        const koreaAxisPort = koreaFocusedLabeling && isKoreaAoPriorityLabel(port.name, port.id);
        const duplicatesObjective = objectiveLocationIds.has(String(port.location_id || "").trim())
          || collectNormalizedMapLabelKeys(port.map_label, port.name).some((key) => objectiveLabelKeys.has(key));
        return {
          id: `${ownerId}:label`,
          ownerId,
          ownerObstacleId: ownerId,
          kind: "portLabel",
          text: port.map_label || port.name,
          x: port.cameraDisplayAnchor.x + port.labelOffsetX * scale,
          y: port.cameraDisplayAnchor.y + port.labelOffsetY * scale,
          textAnchor: port.labelAnchor,
          scale,
          selected,
          important: koreaAxisPort,
          forceVisible: selected || (koreaAxisPort && !duplicatesObjective),
          priorityBoost: koreaAxisPort ? 20 : 0,
        };
      }),
      ...transformedNamedFeatures.map((feature) => {
        const ownerId = `feature:${feature.id}`;
        const koreaAxisFeature = koreaFocusedLabeling && isKoreaAoPriorityLabel(feature.label, feature.id);
        const koreaRouteFeature = koreaFocusedLabeling
          && isKoreaAoRouteLabel(feature.label, feature.id)
          && (feature.kindKey === "phase_line" || feature.kindKey === "corridor" || feature.kindKey === "choke_point" || feature.kindKey === "waterway");
        return {
          id: `${ownerId}:label`,
          ownerId,
          kind: "featureLabel",
          text: feature.map_label || feature.label,
          x: feature.cameraAnchor.x + feature.labelOffsetX * scale,
          y: feature.cameraAnchor.y + feature.labelOffsetY * scale,
          textAnchor: feature.labelAnchor,
          scale,
          important: Boolean(feature.important || koreaAxisFeature),
          visibility: feature.visibility,
          forceVisible: koreaRouteFeature,
          priorityBoost: (Math.max(1, Number(feature.label_priority || 1)) - 1) * 8 + (koreaAxisFeature ? 18 : 0) + (koreaRouteFeature ? 20 : 0),
        };
      }),
      ...transformedUnits.map((unit) => {
        const ownerId = `unit:${unit.id}`;
        const selected = selectedUnitId === unit.id;
        return {
          id: `${ownerId}:label`,
          ownerId,
          ownerObstacleId: ownerId,
          kind: "unitLabel",
          text: unit.map_label || unit.name,
          x: unit.cameraDisplayAnchor.x + unit.labelOffsetX * scale,
          y: unit.cameraDisplayAnchor.y + unit.labelOffsetY * scale,
          textAnchor: unit.labelAnchor,
          scale,
          important: Boolean(unit.labelImportant),
          selected,
          forceVisible: selected || Boolean(unit.labelForceVisible),
          priorityBoost: Number(unit.labelPriorityBoost || 0),
        };
      }),
    ];

    return buildDeclutteredLabels(candidates, labelObstacles, { zoom: camera.zoom });
  }, [
    transformedObjectives,
    transformedAirfields,
    transformedPorts,
    transformedNamedFeatures,
    transformedBasemap,
    transformedUnits,
    labelObstacles,
    selectedObjectiveId,
    selectedAirfieldId,
    selectedPortId,
    selectedUnitId,
    basemapStyle.tier,
    zoomPresentation.counterScale,
    camera.zoom,
    presentation,
  ]);
  const visibleLabelIds = labelDeclutter.visibleIds;
  const visibleLabelOwners = labelDeclutter.visibleOwners;
  const transformedSupplyOverlay = useMemo(
    () => ({
      markers: overlayState.supply.markers.map((marker) => {
        const unit = transformedUnitsById.get(String(marker.id));
        return {
          ...marker,
          cameraPoint: unit?.cameraDisplayAnchor ?? projectMapCameraPoint(marker.anchor, camera),
        };
      }),
      sources: overlayState.supply.sources.map((source) => ({
        ...source,
        cameraPoint: projectMapCameraPoint(source.anchor, camera),
      })),
      corridors: overlayState.supply.corridors.map((corridor) => ({
        ...corridor,
        cameraFrom: projectMapCameraPoint(corridor.from, camera),
        cameraTo: projectMapCameraPoint(corridor.to, camera),
      })),
    }),
    [overlayState.supply, transformedUnitsById, camera],
  );
  const commandFocus = useMemo(() => {
    if (!selectedUnitId) {
      return {
        focusHqId: null,
        subordinateIds: new Set<string>(),
        focusedLinkIds: new Set<string>(),
      };
    }

    const selectedUnit = scene.units.find((unit) => unit.id === selectedUnitId) ?? null;
    if (!selectedUnit) {
      return {
        focusHqId: null,
        subordinateIds: new Set<string>(),
        focusedLinkIds: new Set<string>(),
      };
    }

    const focusHqId = selectedUnit.counterFrame?.isHeadquarters
      ? selectedUnit.id
      : String(selectedUnit?.inspector?.command?.superior?.id || selectedUnit?.inspector?.command?.hq_unit_id || "").trim() || null;
    const focusHq = focusHqId ? overlayState.command.hqs.find((hq) => hq.id === focusHqId) ?? null : null;
    const subordinateIds = new Set((focusHq?.subordinateIds ?? []).map((id) => String(id)));
    const focusedLinkIds = new Set(
      overlayState.command.links
        .filter((link) => link.superiorId === focusHqId || link.subordinateId === selectedUnitId || subordinateIds.has(link.subordinateId))
        .map((link) => link.id),
    );

    return {
      focusHqId,
      subordinateIds,
      focusedLinkIds,
    };
  }, [scene.units, overlayState.command.hqs, overlayState.command.links, selectedUnitId]);
  const transformedCommandOverlay = useMemo(
    () => ({
      hqs: overlayState.command.hqs.map((hq) => ({
        ...hq,
        cameraPoint: transformedUnitsById.get(String(hq.id))?.cameraDisplayAnchor ?? projectMapCameraPoint(hq.anchor, camera),
        radiusPx: Number((hq.radius * camera.zoom).toFixed(2)),
        focused: hq.id === commandFocus.focusHqId,
      })),
      links: overlayState.command.links.map((link) => ({
        ...link,
        cameraFrom: transformedUnitsById.get(String(link.superiorId))?.cameraDisplayAnchor ?? projectMapCameraPoint(link.from, camera),
        cameraTo: transformedUnitsById.get(String(link.subordinateId))?.cameraDisplayAnchor ?? projectMapCameraPoint(link.to, camera),
        focused: commandFocus.focusedLinkIds.has(link.id),
      })),
      subordinateHighlights: Array.from(commandFocus.subordinateIds)
        .map((id) => transformedUnitsById.get(id))
        .filter(Boolean)
        .map((unit) => ({
          id: unit.id,
          cameraPoint: unit.cameraDisplayAnchor,
          degraded: Boolean(unit.counterAppearance?.outOfCommand || unit.counterStatusOverlay?.outOfCommand),
        })),
    }),
    [overlayState.command, transformedUnitsById, camera, commandFocus],
  );
  const transformedMovementOverlay = useMemo(
    () => overlayState.movementIntent.paths.map((path) => ({
      ...path,
      cameraFrom: transformedUnitsById.get(String(path.unitId))?.cameraDisplayAnchor ?? projectMapCameraPoint(path.from, camera),
      cameraTo: projectMapCameraPoint(path.to, camera),
      cameraWaypoints: path.waypoints.map((waypoint) => projectMapCameraPoint(waypoint, camera)),
      cameraRoute: path.route.map((point, index) => (
        index === 0
          ? transformedUnitsById.get(String(path.unitId))?.cameraDisplayAnchor ?? projectMapCameraPoint(point, camera)
          : projectMapCameraPoint(point, camera)
      )),
      selected: selectedUnitId === path.unitId,
    })),
    [overlayState.movementIntent.paths, transformedUnitsById, camera, selectedUnitId],
  );
  const transformedFrontlineOverlay = useMemo(
    () => ({
      sectors: overlayState.frontline.sectors.map((sector) => ({
        ...sector,
        cameraPoint: projectMapCameraPoint(sector.anchor, camera),
        radiusPx: Number((sector.radius * camera.zoom).toFixed(2)),
      })),
      segments: overlayState.frontline.segments.map((segment) => ({
        ...segment,
        cameraFrom: projectMapCameraPoint(segment.from, camera),
        cameraTo: projectMapCameraPoint(segment.to, camera),
      })),
    }),
    [overlayState.frontline, camera],
  );
  const transformedBarrierOverlay = useMemo(
    () => ({
      features: overlayState.barriers.features.map((feature) => ({
        ...feature,
        cameraPoint: projectMapCameraPoint(feature.anchor, camera),
      })),
      segments: overlayState.barriers.segments.map((segment) => ({
        ...segment,
        cameraFrom: projectMapCameraPoint(segment.from, camera),
        cameraTo: projectMapCameraPoint(segment.to, camera),
      })),
    }),
    [overlayState.barriers, camera],
  );
  const transformedInfrastructureNodes = useMemo(
    () => overlayState.infrastructure.nodes.map((node) => ({
      ...node,
      cameraPoint: projectMapCameraPoint(node.anchor, camera),
    })),
    [overlayState.infrastructure.nodes, camera],
  );
  const transformedArtilleryMarkers = useMemo(
    () => overlayState.artillery.markers.map((marker) => ({
      ...marker,
      cameraPoint: projectMapCameraPoint(marker, camera),
    })),
    [overlayState.artillery.markers, camera],
  );
  const transformedFogIntelContacts = useMemo(
    () => overlayState.fogIntel.contacts.map((contact) => ({
      ...contact,
      cameraPoint: projectMapCameraPoint(contact.anchor, camera),
    })),
    [overlayState.fogIntel.contacts, camera],
  );
  const transformedTrackedOperations = useMemo(
    () => trackedOperations.rows.map((operation) => ({
      ...operation,
      cameraMarker: operation.marker ? {
        ...operation.marker,
        ...projectMapCameraPoint(operation.marker, camera),
      } : null,
    })),
    [trackedOperations.rows, camera],
  );
  const transformedPlannerObjectiveMarker = useMemo(
    () => (plannerSummary.objectiveArea.marker ? {
      ...plannerSummary.objectiveArea.marker,
      ...projectMapCameraPoint(plannerSummary.objectiveArea.marker, camera),
    } : null),
    [plannerSummary.objectiveArea.marker, camera],
  );
  const transformedGreaseItems = useMemo(
    () => greaseMarkup.items.map((item) => ({
      ...item,
      points: item.points.map((point) => projectMapCameraPoint(projectScenePoint(point, scene), camera)),
    })),
    [greaseMarkup.items, scene, camera],
  );
  const transformedGreaseDraft = useMemo(
    () => (greaseDraft ? {
      id: "__draft__",
      tool: greaseDraft.tool,
      style: greaseDraft.style,
      points: greaseDraft.worldPoints.map((point) => projectMapCameraPoint(projectScenePoint(point, scene), camera)),
    } : null),
    [greaseDraft, scene, camera],
  );

  useEffect(() => {
    setIsPanning(false);
    setGreaseDraft(null);
    setCommandHoverHex(null);
    dragStateRef.current = null;
    cameraInteractedRef.current = false;
    cameraAutoFitKeyRef.current = null;
  }, [snapshot.scenario?.id]);

  useEffect(() => {
    const autoFitKey = `${String(snapshot.scenario?.id ?? "unknown")}:${scene.width}:${scene.height}`;
    if (cameraInteractedRef.current || cameraAutoFitKeyRef.current === autoFitKey) {
      return;
    }
    setCameraState(buildInitialMapCamera(snapshot, scene));
    cameraAutoFitKeyRef.current = autoFitKey;
  }, [snapshot, scene]);

  useEffect(() => {
    if (!selectedUnitId || greaseToolArmed || objectiveSelectionActive || isPanning) {
      setCommandHoverHex(null);
    }
  }, [selectedUnitId, greaseToolArmed, objectiveSelectionActive, isPanning]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) {
      return undefined;
    }

    function updateStageSize(width: number, height: number) {
      const nextWidth = Math.max(1, Math.round(width));
      const nextHeight = Math.max(1, Math.round(height));
      setStageSize((current) => (
        current.width === nextWidth && current.height === nextHeight
          ? current
          : { width: nextWidth, height: nextHeight }
      ));
    }

    const initialBounds = stage.getBoundingClientRect();
    updateStageSize(initialBounds.width, initialBounds.height);

    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      updateStageSize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!plannerState.plannerOpen) {
      setPlannerPinned(false);
    }
  }, [plannerState.plannerOpen]);

  useEffect(() => {
    if (!plannerState.greaseEnabled || !greasePlanningLayerVisible) {
      setGreaseDraft(null);
    }
  }, [plannerState.greaseEnabled, greasePlanningLayerVisible]);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      setCommandHoverHex(null);
      setGreaseDraft(null);
    }

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  function pointerToScenePoint(clientX: number, clientY: number) {
    const svg = svgRef.current;
    if (!svg) {
      return null;
    }
    const bounds = svg.getBoundingClientRect();
    if (!bounds.width || !bounds.height) {
      return null;
    }
    return {
      x: ((clientX - bounds.left) / bounds.width) * scene.width,
      y: ((clientY - bounds.top) / bounds.height) * scene.height,
    };
  }

  function pointerToWorldPoint(clientX: number, clientY: number) {
    const scenePoint = pointerToScenePoint(clientX, clientY);
    if (!scenePoint) {
      return null;
    }
    const worldScenePoint = {
      x: (scenePoint.x - camera.offsetX) / camera.zoom,
      y: (scenePoint.y - camera.offsetY) / camera.zoom,
    };
    return {
      scenePoint,
      worldPoint: unprojectScenePoint(worldScenePoint, scene),
    };
  }

  function setZoomAtPoint(targetZoom: number, focusPoint: { x: number; y: number }) {
    const nextZoom = Number(targetZoom);
    const worldX = (focusPoint.x - camera.offsetX) / camera.zoom;
    const worldY = (focusPoint.y - camera.offsetY) / camera.zoom;
    cameraInteractedRef.current = true;
    setCameraState(
      clampMapCamera(
        {
          zoom: nextZoom,
          offsetX: focusPoint.x - worldX * nextZoom,
          offsetY: focusPoint.y - worldY * nextZoom,
        },
        scene,
      ),
    );
  }

  function resetCamera() {
    cameraInteractedRef.current = false;
    setCameraState(buildInitialMapCamera(snapshot, scene));
  }

  function handleMapWheel(event: WheelEvent<SVGSVGElement>) {
    const focusPoint = pointerToScenePoint(event.clientX, event.clientY);
    if (!focusPoint) {
      return;
    }
    event.preventDefault();
    const zoomFactor = Math.exp(-event.deltaY * 0.0015);
    setZoomAtPoint(camera.zoom * zoomFactor, focusPoint);
  }

  function handleMapPointerDown(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) {
      return;
    }
    if (!(event.target instanceof Element)) {
      return;
    }
    if (event.target.closest(".shell-map__grease-item")) {
      return;
    }
    if (!greaseToolArmed && event.target.closest(".shell-map__unit, .shell-map__objective, .shell-map__site")) {
      return;
    }
    if (!greaseToolArmed && greaseMarkup.selectedId) {
      greaseMarkupActions.onSelectItem(null);
    }
    const pointerPoint = pointerToWorldPoint(event.clientX, event.clientY);
    if (!pointerPoint) {
      return;
    }
    if (greaseToolArmed && greaseMarkup.activeTool) {
      const initialScenePoints = [pointerPoint.scenePoint];
      const initialWorldPoints = [pointerPoint.worldPoint];
      setGreaseDraft({
        pointerId: event.pointerId,
        tool: greaseMarkup.activeTool,
        style: greaseMarkup.activeStyle,
        scenePoints: initialScenePoints,
        worldPoints: initialWorldPoints,
      });
      event.currentTarget.setPointerCapture(event.pointerId);
      event.preventDefault();
      return;
    }
    dragStateRef.current = {
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      offsetX: camera.offsetX,
      offsetY: camera.offsetY,
    };
    cameraInteractedRef.current = true;
    setIsPanning(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handleMapPointerMove(event: PointerEvent<SVGSVGElement>) {
    if (greaseDraft && greaseDraft.pointerId === event.pointerId) {
      const pointerPoint = pointerToWorldPoint(event.clientX, event.clientY);
      if (!pointerPoint) {
        return;
      }
      setGreaseDraft((current) => {
        if (!current || current.pointerId !== event.pointerId) {
          return current;
        }
        if (isGreaseMarkupToolContinuous(current.tool)) {
          return {
            ...current,
            scenePoints: appendGreaseMarkupPoint(current.scenePoints, pointerPoint.scenePoint, 4),
            worldPoints: appendGreaseMarkupPoint(current.worldPoints, pointerPoint.worldPoint, 0.08),
          };
        }
        return {
          ...current,
          scenePoints: [current.scenePoints[0], pointerPoint.scenePoint],
          worldPoints: [current.worldPoints[0], pointerPoint.worldPoint],
        };
      });
      return;
    }
    const dragState = dragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      if (!selectedUnitId || greaseToolArmed || objectiveSelectionActive) {
        return;
      }
      const pointerPoint = pointerToWorldPoint(event.clientX, event.clientY);
      if (!pointerPoint) {
        return;
      }
      const nextHex = axialRound(pointerPoint.worldPoint.x, pointerPoint.worldPoint.y);
      setCommandHoverHex((current) => (current?.q === nextHex.q && current?.r === nextHex.r ? current : nextHex));
      return;
    }
    const svg = svgRef.current;
    if (!svg) {
      return;
    }
    const bounds = svg.getBoundingClientRect();
    if (!bounds.width || !bounds.height) {
      return;
    }
    const scaleX = scene.width / bounds.width;
    const scaleY = scene.height / bounds.height;
    setCameraState(
      clampMapCamera(
        {
          zoom: camera.zoom,
          offsetX: dragState.offsetX + (event.clientX - dragState.clientX) * scaleX,
          offsetY: dragState.offsetY + (event.clientY - dragState.clientY) * scaleY,
        },
        scene,
      ),
    );
  }

  function endMapPointer(event: PointerEvent<SVGSVGElement>) {
    if (greaseDraft && greaseDraft.pointerId === event.pointerId) {
      const committedDraft = greaseDraft;
      if (shouldCommitGreaseMarkup(committedDraft.tool, committedDraft.scenePoints)) {
        const nextItem = createGreaseMarkupItem({
          tool: committedDraft.tool,
          style: committedDraft.style,
          points: committedDraft.worldPoints,
        });
        if (nextItem) {
          greaseMarkupActions.onCommitItem(nextItem);
        }
      }
      setGreaseDraft(null);
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      return;
    }
    const dragState = dragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }
    dragStateRef.current = null;
    setIsPanning(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleMapPointerLeave() {
    if (!isPanning) {
      setCommandHoverHex(null);
    }
  }

  function resolveFastCommandObjectiveHex(event: MouseEvent<SVGSVGElement>) {
    const eventTarget = event.target instanceof Element ? event.target : null;
    const objectiveId = eventTarget?.closest(".shell-map__objective")?.getAttribute("data-objective-id");
    if (!objectiveId) {
      return null;
    }

    const objective = scene.objectives.find((row) => row.id === objectiveId) ?? null;
    if (!objective) {
      return null;
    }

    return axialRound(objective.x, objective.y);
  }

  function handleMapContextMenu(event: MouseEvent<SVGSVGElement>) {
    if (!selectedUnitId || greaseToolArmed || objectiveSelectionActive) {
      return;
    }
    event.preventDefault();
    const objectiveTargetHex = resolveFastCommandObjectiveHex(event);
    const pointerPoint = objectiveTargetHex ? null : pointerToWorldPoint(event.clientX, event.clientY);
    const targetHex = objectiveTargetHex ?? (pointerPoint ? axialRound(pointerPoint.worldPoint.x, pointerPoint.worldPoint.y) : null);
    if (!targetHex) {
      return;
    }
    const preview = buildMapCommandPreview(snapshot, selectedUnitId, targetHex);
    if (!preview?.available) {
      return;
    }
    setCommandHoverHex(targetHex);
    onCommitFastCommand(preview);
  }

  const plannerPlanWorkbench = (
    <>
      {greaseBoard.available && greaseBoard.data ? (
        <section className="shell-map__planner-section">
          <div className="shell-map__planner-section-title">Command Brief</div>
          <GreaseBoard data={greaseBoard.data} embedded />
        </section>
      ) : null}
      <section className="shell-map__planner-section">
        <div className="shell-map__planner-section-title">Markup Workbench</div>
        <GreaseMarkupPalette
          activeTool={greaseMarkup.activeTool}
          activeStyle={greaseMarkup.activeStyle}
          selectedId={greaseMarkup.selectedId}
          visible={greasePlanningLayerVisible}
          onToggleVisibility={() => onToggleLayer("greasePlanning")}
          onSelectTool={greaseMarkupActions.onSetActiveTool}
          onSelectStyle={greaseMarkupActions.onSetActiveStyle}
          onEraseSelected={greaseMarkupActions.onRemoveSelectedItem}
          onClearAll={greaseMarkupActions.onClearAll}
        />
        <div className="shell-map__planner-note">
          Markup now lives inside the planner so the map stays clear until you deliberately enter planning mode.
        </div>
      </section>
    </>
  );

  const plannerMapWorkbench = (
    <>
      <section className="shell-map__planner-section">
        <div className="shell-map__planner-section-title">Map State</div>
        <div className="shell-map__planner-grid">
          <div className="shell-map__planner-field">
            <span>Zoom</span>
            <strong>{Math.round(camera.zoom * 100)}%</strong>
          </div>
          <div className="shell-map__planner-field">
            <span>View</span>
            <strong>{camera.zoom < 0.9 ? "Broad" : zoomPresentation.showSiteLabels ? "Close" : "Operational"}</strong>
          </div>
          <div className="shell-map__planner-field">
            <span>Basemap</span>
            <strong>{basemapLayerSummary.status}</strong>
          </div>
          <div className="shell-map__planner-field">
            <span>Layers On</span>
            <strong>{plannerLayerCountLabel}</strong>
          </div>
        </div>
        <div className="shell-map__planner-note">{basemapLayerSummary.detail}</div>
        <div className="shell-map__planner-note">
          Detailed map and overlay controls live here. The header Layers control remains a quick status entry point only.
        </div>
      </section>

      <section className="shell-map__planner-section">
        <div className="shell-map__planner-section-title">Quick Controls</div>
        <div className="shell-map__planner-chip-row">
          <button
            type="button"
            className="shell-button shell-button--secondary"
            onClick={() => setZoomAtPoint(camera.zoom * 0.88, { x: scene.width / 2, y: scene.height / 2 })}
          >
            Broader
          </button>
          <button type="button" className="shell-button shell-button--secondary" onClick={resetCamera}>
            Standard
          </button>
          <button
            type="button"
            className="shell-button shell-button--secondary"
            onClick={() => setZoomAtPoint(camera.zoom * 1.12, { x: scene.width / 2, y: scene.height / 2 })}
          >
            Closer
          </button>
          <button
            type="button"
            className={"shell-button shell-button--secondary" + (gridLayerVisible ? " is-active" : "")}
            onClick={() => onToggleLayer("grid")}
            aria-pressed={gridLayerVisible}
          >
            Grid {gridLayerVisible ? "On" : "Off"}
          </button>
          <button
            type="button"
            className={"shell-button shell-button--secondary" + (objectivesLayerVisible ? " is-active" : "")}
            onClick={() => onToggleLayer("objectives")}
            aria-pressed={objectivesLayerVisible}
          >
            Objectives {objectivesLayerVisible ? "On" : "Off"}
          </button>
        </div>
      </section>

      {plannerMapControlGroups.map((group) => (
        <section className="shell-map__planner-section" key={group.id}>
          <div className="shell-map__planner-section-title">{group.label}</div>
          <div className="shell-map__planner-control-list">
            {group.entries.map((entry) => (
              <div className="shell-map__planner-control" key={entry.id}>
                <button
                  type="button"
                  className={"shell-map__control-menu-item" + (entry.active ? " is-active" : "") + (!entry.toggleable ? " is-unavailable" : "")}
                  onClick={() => onToggleLayer(entry.id)}
                  disabled={!entry.toggleable}
                  aria-pressed={entry.toggleable ? entry.active : undefined}
                  title={entry.detail}
                >
                  <span className="shell-map__control-menu-label">{entry.label}</span>
                  <span className="shell-map__control-menu-state">{entry.stateLabel}</span>
                </button>
                <div className="shell-map__control-menu-note">{entry.detail}</div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );

  const plannerQaWorkbench = qaWorkbenchVisible ? (
    <details className="shell-map__planner-devpanel">
      <summary className="shell-map__planner-devsummary">
        Dev / QA Workbench
      </summary>
      <div className="shell-map__planner-note">
        Debug surfaces are intentionally tucked inside the planner so they do not compete with the operational map.
      </div>
      <div className="shell-map__planner-qa-stack">
        <MapDataQAScene theaterId={basemapTheaterId} snapshot={snapshot} />
        <KoreaOperationalBasemapScene />
        <InfrastructureGameplayScene theaterId={basemapTheaterId} />
        <VisibilityQAScene theaterId={basemapTheaterId} />
        <ScenarioAuthoringQAScene theaterId={basemapTheaterId} />
        <ScenarioOverrideQAScene theaterId={basemapTheaterId} />
        <MapTokenPreviewPanel />
        <MapOverlayHarnessPanel />
        <HexTileHarnessPanel />
        <AirfieldIconHarnessPanel />
        <SettlementIconHarnessPanel />
        <MapLabelHarnessPanel />
        <UnitCounterFrameHarnessPanel />
      </div>
    </details>
  ) : null;

  return (
    <section className="shell-map" style={mapReadabilityStyle}>
      <div
        ref={stageRef}
        className={"shell-map__stage" + (effectiveUnderlayLayerVisible ? " shell-map__stage--underlay" : "")}
      >
        <div className="shell-map__grid" aria-hidden="true" />
        {weatherLayerVisible ? (
          <div className={"shell-map__weather-overlay " + weatherOverlay.tone} aria-hidden="true">
          </div>
        ) : null}
        <svg
          ref={svgRef}
          className={"shell-map__svg" + (isPanning ? " is-panning" : "") + (greaseToolArmed ? " is-grease-armed" : "")}
          viewBox={`0 0 ${scene.width} ${scene.height}`}
          role="img"
          aria-label={`${presentation.scenarioLabel} theatre map`}
          onWheel={handleMapWheel}
          onPointerDown={handleMapPointerDown}
          onPointerMove={handleMapPointerMove}
          onPointerUp={endMapPointer}
          onPointerCancel={endMapPointer}
          onPointerLeave={handleMapPointerLeave}
          onContextMenu={handleMapContextMenu}
        >
          <defs>
            <pattern id="map-grid-major" width="96" height="83.14" patternUnits="userSpaceOnUse">
              <path d={HEX_TILE_PATHS.gridMajor} fill="none" className="shell-map__major-line" />
            </pattern>
            <pattern id="map-grid-minor" width="48" height="41.57" patternUnits="userSpaceOnUse">
              <path d={HEX_TILE_PATHS.gridMinor} fill="none" className="shell-map__minor-line" />
            </pattern>
            <pattern id="map-terrain-emphasis" width="108" height="54" patternUnits="userSpaceOnUse">
              <path d="M0 16 Q18 4 36 16 T72 16 T108 16" className="shell-map__terrain-emphasis-line" />
              <path d="M-6 36 Q18 26 42 36 T90 36 T138 36" className="shell-map__terrain-emphasis-line is-soft" />
            </pattern>
            <pattern id="map-paper-grain" width="168" height="168" patternUnits="userSpaceOnUse">
              <circle cx="18" cy="22" r="0.85" className="shell-map__paper-grain-dot" />
              <circle cx="74" cy="46" r="0.72" className="shell-map__paper-grain-dot" />
              <circle cx="138" cy="28" r="0.8" className="shell-map__paper-grain-dot" />
              <circle cx="42" cy="118" r="0.78" className="shell-map__paper-grain-dot" />
              <circle cx="116" cy="132" r="0.88" className="shell-map__paper-grain-dot" />
              <circle cx="150" cy="96" r="0.68" className="shell-map__paper-grain-dot" />
              <path d="M-8 62 Q34 54 74 62 T156 62 T238 62" className="shell-map__paper-grain-fiber" />
              <path d="M-16 108 Q24 101 64 108 T144 108 T224 108" className="shell-map__paper-grain-fiber is-soft" />
            </pattern>
            <pattern id="map-water-texture" width="168" height="88" patternUnits="userSpaceOnUse">
              <path d="M-18 18 Q12 10 42 18 T102 18 T162 18" className="shell-map__water-texture-line" />
              <path d="M0 44 Q28 36 56 44 T112 44 T168 44" className="shell-map__water-texture-line is-soft" />
              <path d="M-12 70 Q16 60 44 70 T100 70 T156 70" className="shell-map__water-texture-line" />
            </pattern>
            <pattern id="map-fog-hatch" width="22" height="22" patternUnits="userSpaceOnUse" patternTransform="rotate(24)">
              <path d="M0 0 V22" className="shell-map__fog-line" />
            </pattern>
            <marker id="map-path-arrow-move" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path className="shell-map__movement-arrowhead is-move" d="M0 0 L8 4 L0 8 Z" />
            </marker>
            <marker id="map-path-arrow-attack" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path className="shell-map__movement-arrowhead is-attack" d="M0 0 L8 4 L0 8 Z" />
            </marker>
            <marker id="map-path-arrow-advance" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path className="shell-map__movement-arrowhead is-advance" d="M0 0 L8 4 L0 8 Z" />
            </marker>
            <marker id="map-path-arrow-fallback" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path className="shell-map__movement-arrowhead is-fallback" d="M0 0 L8 4 L0 8 Z" />
            </marker>
          </defs>

          <g className="shell-map__terrain-layer" transform={terrainTransform} aria-hidden="true">
            {effectiveUnderlayLayerVisible && hasHistoricalUnderlay ? (
              <image
                className="shell-map__underlay-image"
                href={lungaPointUnderlayUrl}
                x="0"
                y="0"
                width={scene.width}
                height={scene.height}
                preserveAspectRatio="none"
              />
            ) : null}

            {terrainFieldLayerVisible ? (
              <rect
                x="0"
                y="0"
                width={scene.width}
                height={scene.height}
                className={"shell-map__field" + (effectiveUnderlayLayerVisible ? " has-underlay" : "")}
              />
            ) : null}

            {basemapLayerVisible && basemapRuntimeState.terrainReady && transformedBasemap.hexes.length ? (
              <g className="shell-map__basemap-layer">
                {transformedBasemap.hexes.map((hexRecord) => (
                  <Fragment key={hexRecord.hexId}>
                    <polygon
                      points={hexRecord.points}
                      className={`shell-map__basemap-hex-fill is-${hexRecord.terrainClass}`}
                      style={{
                        opacity: Number((
                          basemapStyle.terrainOpacity
                          * (hexRecord.terrainClass === "water"
                            ? basemapStyle.waterFillOpacityFactor
                            : hexRecord.terrainClass === "coast"
                              ? basemapStyle.coastFillOpacityFactor
                              : 1)
                        ).toFixed(3)),
                      }}
                    />
                    <polygon
                      points={hexRecord.points}
                      className={`shell-map__basemap-hex-tint is-${String(hexRecord.reliefBand || "lowland")}`}
                      style={{ opacity: basemapStyle.hypsometricOpacity }}
                    />
                    <polygon
                      points={hexRecord.points}
                      className="shell-map__basemap-hex-relief"
                      style={{
                        opacity: Number((
                          basemapStyle.reliefOpacity
                          * (basemapStyle.reliefShadeMix.base + Number(hexRecord.reliefShade || 0) * basemapStyle.reliefShadeMix.gain)
                        ).toFixed(3)),
                      }}
                    />
                    {hexRecord.terrainClass === "water" || hexRecord.terrainClass === "coast" ? (
                      <polygon
                        points={hexRecord.points}
                        className={`shell-map__basemap-hex-texture is-${hexRecord.terrainClass}`}
                        fill="url(#map-water-texture)"
                        style={{
                          opacity: Number((
                            basemapStyle.waterTextureOpacity
                            * (hexRecord.terrainClass === "coast" ? 0.72 : 1)
                          ).toFixed(3)),
                        }}
                      />
                    ) : null}
                    {hexRecord.riverClass ? (
                      <>
                        <polygon
                          points={hexRecord.points}
                          className={`shell-map__basemap-river-casing is-${hexRecord.riverClass}`}
                          style={{
                            opacity: Number((basemapStyle.hydroOpacity * basemapStyle.riverCasingOpacityFactor).toFixed(3)),
                            strokeWidth: `${basemapStyle.lineWidthPx.riverCasing}px`,
                          }}
                        />
                        <polygon
                          points={hexRecord.points}
                          className={`shell-map__basemap-river-ring is-${hexRecord.riverClass}`}
                          style={{
                            opacity: basemapStyle.hydroOpacity,
                            strokeWidth: `${hexRecord.riverClass === "major" ? basemapStyle.lineWidthPx.riverMajor : basemapStyle.lineWidthPx.riverMinor}px`,
                          }}
                        />
                      </>
                    ) : null}
                    {hexRecord.coastline ? (
                      <>
                        <polygon
                          points={hexRecord.points}
                          className="shell-map__basemap-coast-casing"
                          style={{
                            opacity: Number((basemapStyle.hydroOpacity * basemapStyle.coastCasingOpacityFactor).toFixed(3)),
                            strokeWidth: `${basemapStyle.lineWidthPx.coastCasing}px`,
                          }}
                        />
                        <polygon
                          points={hexRecord.points}
                          className="shell-map__basemap-coast-ring"
                          style={{
                            opacity: Number((basemapStyle.hydroOpacity * basemapStyle.coastOpacityFactor).toFixed(3)),
                            strokeWidth: `${basemapStyle.lineWidthPx.coast}px`,
                          }}
                        />
                      </>
                    ) : null}
                    {basemapStyle.showContours && hexRecord.showContour ? (
                      <polygon
                        points={hexRecord.points}
                        className={`shell-map__basemap-contour ${hexRecord.majorContour ? "is-major" : "is-minor"}`}
                        style={{
                          opacity: basemapStyle.contourOpacity,
                          strokeWidth: `${hexRecord.majorContour ? basemapStyle.lineWidthPx.contourMajor : basemapStyle.lineWidthPx.contourMinor}px`,
                        }}
                      />
                    ) : null}
                    {basemapStyle.showCrossings && hexRecord.crossingKinds.length ? (
                      <g
                        className={`shell-map__basemap-crossing is-${resolveBasemapCrossingKind(hexRecord.crossingKinds)}`}
                        transform={`translate(${hexRecord.center.x}, ${hexRecord.center.y})`}
                      >
                        <circle
                          r={basemapStyle.markerSizePx.crossing + 1.7}
                          className="shell-map__basemap-crossing-halo"
                          style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingHaloOpacityFactor).toFixed(3)) }}
                        />
                        <circle
                          r={basemapStyle.markerSizePx.crossing}
                          className="shell-map__basemap-crossing-ring"
                          style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingOpacityFactor).toFixed(3)) }}
                        />
                        <circle
                          r={Math.max(1.1, basemapStyle.markerSizePx.crossing * 0.36)}
                          className="shell-map__basemap-crossing-core"
                          style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingOpacityFactor).toFixed(3)) }}
                        />
                        {resolveBasemapCrossingKind(hexRecord.crossingKinds) === "bridge" ? (
                          <path
                            d="M-3.5 0 H3.5 M-2.3 -2.3 V2.3 M2.3 -2.3 V2.3"
                            className="shell-map__basemap-crossing-mark"
                            style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingOpacityFactor).toFixed(3)) }}
                          />
                        ) : resolveBasemapCrossingKind(hexRecord.crossingKinds) === "ford" ? (
                          <path
                            d="M-3.1 0 H3.1 M-1.9 -1.7 L0 0 L1.9 1.7"
                            className="shell-map__basemap-crossing-mark"
                            style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingOpacityFactor).toFixed(3)) }}
                          />
                        ) : (
                          <path
                            d="M-3.1 0 H3.1 M0 -3.1 V3.1"
                            className="shell-map__basemap-crossing-mark"
                            style={{ opacity: Number(Math.min(1, basemapStyle.nodeOpacity * basemapStyle.crossingOpacityFactor).toFixed(3)) }}
                          />
                        )}
                      </g>
                    ) : null}
                  </Fragment>
                ))}
                {basemapStyle.showRoads ? transformedBasemap.roadSegments.map((segment) => {
                  const roadClass = resolveBasemapRoadClass(segment.class);
                  const roadOpacityFactor = roadClass === "primary"
                    ? basemapStyle.roadPrimaryOpacityFactor
                    : basemapStyle.roadSecondaryOpacityFactor;
                  return (
                    <Fragment key={segment.id}>
                      <line
                        className={`shell-map__basemap-segment-casing is-road is-${segment.class}`}
                        x1={segment.from.x}
                        y1={segment.from.y}
                        x2={segment.to.x}
                        y2={segment.to.y}
                        style={{
                          opacity: Number((basemapStyle.transportOpacity * basemapStyle.transportCasingOpacityFactor * roadOpacityFactor).toFixed(3)),
                          strokeWidth: `${roadClass === "primary" ? basemapStyle.lineWidthPx.roadPrimaryCasing : basemapStyle.lineWidthPx.roadSecondaryCasing}px`,
                        }}
                      />
                      <line
                        className={`shell-map__basemap-segment is-road is-${segment.class}`}
                        x1={segment.from.x}
                        y1={segment.from.y}
                        x2={segment.to.x}
                        y2={segment.to.y}
                        style={{
                          opacity: Number((basemapStyle.transportOpacity * roadOpacityFactor).toFixed(3)),
                          strokeWidth: `${roadClass === "primary" ? basemapStyle.lineWidthPx.roadPrimary : basemapStyle.lineWidthPx.roadSecondary}px`,
                        }}
                      />
                    </Fragment>
                  );
                }) : null}
                {basemapStyle.showRail ? transformedBasemap.railSegments.map((segment) => (
                  <Fragment key={segment.id}>
                    <line
                      className={`shell-map__basemap-segment-casing is-rail is-${segment.class}`}
                      x1={segment.from.x}
                      y1={segment.from.y}
                      x2={segment.to.x}
                      y2={segment.to.y}
                      style={{
                        opacity: Number((basemapStyle.transportOpacity * basemapStyle.transportCasingOpacityFactor * basemapStyle.railOpacityFactor).toFixed(3)),
                        strokeWidth: `${basemapStyle.lineWidthPx.railCasing}px`,
                      }}
                    />
                    <line
                      className={`shell-map__basemap-segment is-rail is-${segment.class}`}
                      x1={segment.from.x}
                      y1={segment.from.y}
                      x2={segment.to.x}
                      y2={segment.to.y}
                      style={{
                        opacity: Number((basemapStyle.transportOpacity * basemapStyle.railOpacityFactor).toFixed(3)),
                        strokeWidth: `${basemapStyle.lineWidthPx.rail}px`,
                      }}
                    />
                  </Fragment>
                )) : null}
                {basemapStyle.showSettlements ? transformedBasemap.settlements.map((settlement) => (
                  <g
                    key={settlement.id}
                    className={`shell-map__basemap-settlement is-${settlement.tier}`}
                    transform={`translate(${settlement.point.x}, ${settlement.point.y})`}
                    style={{ opacity: basemapStyle.nodeOpacity }}
                  >
                    <circle
                      r={basemapStyle.markerSizePx.settlement + Math.min(2.4, Math.max(0, Number(settlement.importance || 0) - 4) * 0.22)}
                      className="shell-map__basemap-settlement-core"
                    />
                    {labelsLayerVisible && basemapStyle.showSettlementNames && visibleLabelIds.has(`basemap:settlement:${settlement.id}:label`) ? (
                      <text className="shell-map__basemap-node-label" x="6" y="-5">
                        {settlement.name}
                      </text>
                    ) : null}
                  </g>
                )) : null}
                {basemapStyle.showAirfields ? transformedBasemap.airfields.map((airfield) => (
                  <g
                    key={airfield.id}
                    className={`shell-map__basemap-airfield is-${airfield.tier}`}
                    transform={`translate(${airfield.point.x}, ${airfield.point.y})`}
                    style={{ opacity: basemapStyle.nodeOpacity }}
                  >
                    <rect
                      x={-basemapStyle.markerSizePx.airfield}
                      y={-basemapStyle.markerSizePx.airfield * 0.42}
                      width={basemapStyle.markerSizePx.airfield * 2}
                      height={basemapStyle.markerSizePx.airfield * 0.84}
                      rx="1.4"
                      className="shell-map__basemap-airfield-runway"
                    />
                    <path
                      d={`M0 ${(-basemapStyle.markerSizePx.airfield * 0.92).toFixed(2)} V ${(basemapStyle.markerSizePx.airfield * 0.92).toFixed(2)}`}
                      className="shell-map__basemap-airfield-spine"
                    />
                    {labelsLayerVisible && basemapStyle.showSettlementNames && visibleLabelIds.has(`basemap:airfield:${airfield.id}:label`) ? (
                      <text className="shell-map__basemap-node-label" x="8" y="-6">
                        {airfield.name}
                      </text>
                    ) : null}
                  </g>
                )) : null}
              </g>
            ) : null}
            {terrainEmphasisLayerVisible ? (
              <rect
                x="0"
                y="0"
                width={scene.width}
                height={scene.height}
                className="shell-map__terrain-emphasis"
                fill="url(#map-terrain-emphasis)"
                style={{ opacity: basemapStyle.terrainWashOpacity }}
              />
            ) : null}
            <rect
              x="0"
              y="0"
              width={scene.width}
              height={scene.height}
              className="shell-map__paper-grain"
              fill="url(#map-paper-grain)"
              style={{ opacity: basemapStyle.paperGrainOpacity }}
            />
            {gridLayerVisible ? <rect x="0" y="0" width={scene.width} height={scene.height} fill="url(#map-grid-minor)" opacity={zoomPresentation.gridMinorOpacity} /> : null}
            {gridLayerVisible ? <rect x="0" y="0" width={scene.width} height={scene.height} fill="url(#map-grid-major)" opacity={zoomPresentation.gridMajorOpacity} /> : null}
          </g>

          {fogIntelLayerVisible ? (
            <g className="shell-map__fog-overlay" aria-hidden="true">
              <rect x="0" y="0" width={scene.width} height={scene.height} className="shell-map__fog-wash" />
              <rect x="0" y="0" width={scene.width} height={scene.height} fill="url(#map-fog-hatch)" className="shell-map__fog-hatch" />
            </g>
          ) : null}

          {barrierLayerVisible ? (
            <g className="shell-map__barrier-overlay" aria-hidden="true">
              {transformedBarrierOverlay.segments.map((segment) => (
                <line
                  key={segment.id}
                  className={`shell-map__barrier-segment is-${segment.type}`}
                  x1={segment.cameraFrom.x}
                  y1={segment.cameraFrom.y}
                  x2={segment.cameraTo.x}
                  y2={segment.cameraTo.y}
                />
              ))}
              {transformedBarrierOverlay.features.map((feature) => (
                <g
                  key={feature.id}
                  className={`shell-map__barrier-feature is-${feature.type}`}
                  transform={`translate(${feature.cameraPoint.x}, ${feature.cameraPoint.y})`}
                >
                  {feature.type === "crossing" ? (
                    <>
                      <circle className="shell-map__barrier-crossing-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.barrierCrossing} />
                      <path className="shell-map__barrier-crossing-mark" d="M-5 0 H5 M0 -5 V5" />
                    </>
                  ) : null}
                  {feature.type === "escarpment" ? (
                    <path className="shell-map__barrier-escarpment-mark" d="M-8 6 L-2 -6 L4 6 M2 6 L8 -6" />
                  ) : null}
                  {feature.type === "impassable" ? (
                    <path className="shell-map__barrier-impassable-mark" d="M-6 -6 L6 6 M6 -6 L-6 6" />
                  ) : null}
                </g>
              ))}
            </g>
          ) : null}

          {infrastructureLayerVisible ? (
            <g className="shell-map__infrastructure-overlay" aria-hidden="true">
              {transformedInfrastructureNodes.map((node) => (
                <g
                  key={`${node.kind}:${node.id}`}
                  className={`shell-map__infrastructure-node is-${node.kind}${node.interdicted ? " is-interdicted" : ""}`}
                  transform={`translate(${node.cameraPoint.x}, ${node.cameraPoint.y}) scale(${zoomPresentation.counterScale})`}
                >
                  <circle
                    className="shell-map__infrastructure-node-ring"
                    r={node.kind === "crossing"
                      ? MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureCrossing
                      : MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureNode}
                  />
                  {node.kind === "crossing" ? (
                    <path className="shell-map__infrastructure-node-mark" d="M-6 0 H6 M0 -6 V6" />
                  ) : (
                    <circle className="shell-map__infrastructure-node-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureCore} />
                  )}
                </g>
              ))}
            </g>
          ) : null}

          {supplyLayerVisible ? (
            <g className="shell-map__supply-overlay" aria-hidden="true">
              {transformedSupplyOverlay.corridors.map((corridor) => (
                <line
                  key={corridor.id}
                  className={`shell-map__supply-corridor is-${corridor.state}`}
                  x1={corridor.cameraFrom.x}
                  y1={corridor.cameraFrom.y}
                  x2={corridor.cameraTo.x}
                  y2={corridor.cameraTo.y}
                />
              ))}
              {transformedSupplyOverlay.sources.map((source) => (
                <g
                  key={source.id}
                  className={`shell-map__supply-source is-${source.kind} is-${source.side ?? "unknown"}`}
                  transform={`translate(${source.cameraPoint.x}, ${source.cameraPoint.y})`}
                >
                  <circle className="shell-map__supply-source-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplySource} />
                  <circle className="shell-map__supply-source-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplySourceCore} />
                </g>
              ))}
              {transformedSupplyOverlay.markers.map((marker) => (
                <g
                  key={marker.id}
                  className={`shell-map__supply-marker is-${marker.state}`}
                  transform={`translate(${marker.cameraPoint.x}, ${marker.cameraPoint.y}) scale(${zoomPresentation.counterScale})`}
                >
                  <circle className="shell-map__supply-marker-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplyMarker} />
                  <circle className="shell-map__supply-marker-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplyMarkerCore} />
                </g>
              ))}
            </g>
          ) : null}

          {commandLayerVisible ? (
            <g className="shell-map__command-overlay" aria-hidden="true">
              {transformedCommandOverlay.hqs.map((hq) => (
                <circle
                  key={hq.id}
                  className={"shell-map__command-radius" + (hq.focused ? " is-focused" : "")}
                  cx={hq.cameraPoint.x}
                  cy={hq.cameraPoint.y}
                  r={hq.radiusPx}
                />
              ))}
              {transformedCommandOverlay.links.map((link) => (
                <line
                  key={link.id}
                  className={"shell-map__command-link" + (link.degraded ? " is-degraded" : "") + (link.focused ? " is-focused" : "")}
                  x1={link.cameraFrom.x}
                  y1={link.cameraFrom.y}
                  x2={link.cameraTo.x}
                  y2={link.cameraTo.y}
                />
              ))}
              {transformedCommandOverlay.subordinateHighlights.map((unit) => (
                <circle
                  key={unit.id}
                  className={"shell-map__command-subordinate" + (unit.degraded ? " is-degraded" : "")}
                  cx={unit.cameraPoint.x}
                  cy={unit.cameraPoint.y}
                  r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.commandSubordinate * zoomPresentation.counterScale}
                />
              ))}
            </g>
          ) : null}

          {frontlineLayerVisible ? (
            <g className="shell-map__front-overlay" aria-hidden="true">
              {transformedFrontlineOverlay.sectors.map((sector) => (
                <g
                  key={sector.id}
                  className={`shell-map__front-sector is-${sector.state}${sector.stress ? ` has-${sector.stress}` : ""}`}
                  transform={`translate(${sector.cameraPoint.x}, ${sector.cameraPoint.y})`}
                >
                  <circle className="shell-map__front-sector-fill" r={sector.radiusPx} />
                  <circle className="shell-map__front-sector-ring" r={sector.radiusPx} />
                  {sector.stress === "breakthrough" ? (
                    <path className="shell-map__front-sector-stress is-breakthrough" d="M-7 0 H7 M0 -7 V7" />
                  ) : null}
                  {sector.stress === "thin" ? (
                    <path className="shell-map__front-sector-stress is-thin" d="M-7 -5 L7 5 M7 -5 L-7 5" />
                  ) : null}
                </g>
              ))}
              {transformedFrontlineOverlay.segments.map((segment) => (
                <line
                  key={segment.id}
                  className={`shell-map__front-segment is-${segment.state}`}
                  x1={segment.cameraFrom.x}
                  y1={segment.cameraFrom.y}
                  x2={segment.cameraTo.x}
                  y2={segment.cameraTo.y}
                />
              ))}
            </g>
          ) : null}

          {movementIntentLayerVisible ? (
            <g className="shell-map__movement-overlay" aria-hidden="true">
              {transformedMovementOverlay.map((path) => {
                const pathClass = `shell-map__movement-path is-${path.intent} is-${path.commitment}${path.selected ? " is-selected" : ""}`;
                const markerEnd = path.intent === "attack"
                  ? "url(#map-path-arrow-attack)"
                  : path.intent === "advance"
                    ? "url(#map-path-arrow-advance)"
                  : path.intent === "fallback"
                    ? "url(#map-path-arrow-fallback)"
                    : "url(#map-path-arrow-move)";
                return (
                  <g key={path.id} className={pathClass}>
                    <path className="shell-map__movement-stroke" d={routePathData(path.cameraRoute)} markerEnd={markerEnd} />
                    {path.intent === "advance" ? <path className="shell-map__movement-axis" d={routePathData(path.cameraRoute)} /> : null}
                    {path.cameraWaypoints.map((waypoint, index) => (
                      <circle
                        key={`${path.id}:waypoint:${index}`}
                        className="shell-map__movement-waypoint"
                        cx={waypoint.x}
                        cy={waypoint.y}
                        r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.movementWaypoint}
                      />
                    ))}
                  </g>
                );
              })}
            </g>
          ) : null}

          {transformedQuickCommandPreview ? (
            <g className={`shell-map__quickcommand is-${transformedQuickCommandPreview.previewTone}`} aria-hidden="true">
              <path
                className="shell-map__quickcommand-path"
                d={routePathData(transformedQuickCommandPreview.cameraRoute)}
                markerEnd={transformedQuickCommandPreview.commandIntent === "attack" ? "url(#map-path-arrow-attack)" : "url(#map-path-arrow-move)"}
              />
              <circle
                className="shell-map__quickcommand-target"
                cx={transformedQuickCommandPreview.cameraTarget.x}
                cy={transformedQuickCommandPreview.cameraTarget.y}
                r={9 * zoomPresentation.counterScale}
              />
              <circle
                className="shell-map__quickcommand-core"
                cx={transformedQuickCommandPreview.cameraTarget.x}
                cy={transformedQuickCommandPreview.cameraTarget.y}
                r={3.2 * zoomPresentation.counterScale}
              />
            </g>
          ) : null}

          {artilleryLayerVisible ? (
            <g className="shell-map__artillery-overlay" aria-hidden="true">
              {transformedArtilleryMarkers.map((marker) => (
                <g
                  key={marker.id}
                  className="shell-map__artillery-marker"
                  transform={`translate(${marker.cameraPoint.x}, ${marker.cameraPoint.y}) scale(${zoomPresentation.counterScale})`}
                >
                  <circle className="shell-map__artillery-ring" r="30" />
                  <path className="shell-map__artillery-bracket" d="M-9 -20 L-9 -13 L-16 -13 M9 -20 L9 -13 L16 -13 M-9 20 L-9 13 L-16 13 M9 20 L9 13 L16 13" />
                </g>
              ))}
            </g>
          ) : null}

          {greasePlanningLayerVisible && (transformedGreaseItems.length || transformedGreaseDraft) ? (
            <GreaseMarkupOverlay
              idPrefix="map"
              items={transformedGreaseDraft ? [...transformedGreaseItems, transformedGreaseDraft] : transformedGreaseItems}
              selectedId={greaseMarkup.selectedId}
              draftId={transformedGreaseDraft ? transformedGreaseDraft.id : null}
              onSelectItem={(itemId) => greaseMarkupActions.onSelectItem(itemId)}
            />
          ) : null}

          {greasePlanningLayerVisible && trackedOperations.available ? (
            <g className="shell-map__grease-operations" aria-hidden="true">
              {transformedTrackedOperations.map((operation) => (
                operation.cameraMarker ? (
                  <g className="shell-map__grease-objective is-approved" key={operation.id}>
                    <circle
                      className="shell-map__grease-ring"
                      cx={operation.cameraMarker.x}
                      cy={operation.cameraMarker.y}
                      r={operation.cameraMarker.radius * zoomPresentation.counterScale}
                    />
                    <circle className="shell-map__grease-core" cx={operation.cameraMarker.x} cy={operation.cameraMarker.y} r={8 * zoomPresentation.counterScale} />
                  </g>
                ) : null
              ))}
            </g>
          ) : null}

          {greasePlanningLayerVisible && transformedPlannerObjectiveMarker && !plannerState.approved ? (
            <g className={"shell-map__grease-objective is-" + transformedPlannerObjectiveMarker.status} aria-hidden="true">
              <circle
                className="shell-map__grease-ring"
                cx={transformedPlannerObjectiveMarker.x}
                cy={transformedPlannerObjectiveMarker.y}
                r={transformedPlannerObjectiveMarker.radius * zoomPresentation.counterScale}
              />
              <circle
                className="shell-map__grease-core"
                cx={transformedPlannerObjectiveMarker.x}
                cy={transformedPlannerObjectiveMarker.y}
                r={8 * zoomPresentation.counterScale}
              />
            </g>
          ) : null}

          {fogIntelLayerVisible ? (
            <g className="shell-map__intel-overlay" aria-hidden="true">
              {transformedFogIntelContacts.map((contact) => (
                <g
                  key={contact.id}
                  className={`shell-map__intel-contact is-${contact.state}${contact.uncertainStrength ? " has-uncertain-strength" : ""}`}
                  transform={`translate(${contact.cameraPoint.x}, ${contact.cameraPoint.y})`}
                >
                  <circle className="shell-map__intel-contact-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelContact} />
                  <circle className="shell-map__intel-contact-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelCore} />
                  {contact.uncertainStrength ? (
                    <path className="shell-map__intel-contact-uncertain" d="M0 -6.2 C2.1 -6.2 3.7 -5.1 3.7 -3.3 C3.7 -1.5 2.4 -0.8 1 0.2 C0 0.9 -0.5 1.7 -0.5 2.6 M0 5.6 H0.1" />
                  ) : null}
                </g>
              ))}
            </g>
          ) : null}

          {labelsLayerVisible && zoomPresentation.showOverlayLabels ? (
            <g className="shell-map__named-features" aria-hidden="true">
              {transformedNamedFeatures.map((feature) => (
                namedFeatureVisibilityMatches(feature.visibility, zoomPresentation.tier) ? (
                  <g
                    key={feature.id}
                    className={`shell-map__named-feature shell-map__named-feature--${feature.kindKey}`}
                  >
                    {feature.geometryType === "line" && feature.cameraPoints.length >= 2 ? (
                      <path
                        className="shell-map__named-feature-line"
                        d={routePathData(feature.cameraPoints)}
                      />
                    ) : null}
                    {feature.geometryType === "zone" && feature.cameraPoints.length >= 3 ? (
                      <polygon
                        className="shell-map__named-feature-zone"
                        points={feature.cameraPoints.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ")}
                      />
                    ) : null}
                    {feature.geometryType === "point" ? (
                      <circle
                        className="shell-map__named-feature-marker"
                        cx={feature.cameraAnchor.x}
                        cy={feature.cameraAnchor.y}
                        r={3.2}
                      />
                    ) : null}
                    {visibleLabelIds.has(`feature:${feature.id}:label`) ? (
                      <text
                        className="shell-map__named-feature-label"
                        x={feature.cameraAnchor.x + feature.labelOffsetX}
                        y={feature.cameraAnchor.y + feature.labelOffsetY}
                        textAnchor={feature.labelAnchor}
                      >
                        {feature.map_label || feature.label}
                      </text>
                    ) : null}
                  </g>
                ) : null
              ))}
            </g>
          ) : null}

          {objectivesLayerVisible ? transformedObjectives.map((objective) => (
            <Fragment key={objective.id}>
              {labelsLayerVisible && objective.hasLeader && zoomPresentation.showLeaderLines && visibleLabelOwners.has(`objective:${objective.id}`) ? (
                <line
                  className="shell-map__leader shell-map__leader--objective"
                  x1={objective.cameraAnchor.x}
                  y1={objective.cameraAnchor.y}
                  x2={objective.cameraDisplayAnchor.x}
                  y2={objective.cameraDisplayAnchor.y}
                />
              ) : null}
              <g
                className={
                  `shell-map__objective is-${objective.visualState}`
                  + ` is-${objective.settlement?.controlState ?? "unknown"}`
                  + ` is-${objective.settlement?.tier ?? "town"}`
                  + ` is-${objective.objectiveOverlay?.category ?? "secondary"}`
                  + (objective.axisFocus ? " is-axis-focus" : "")
                  + (objectiveSelectionActive ? " is-plannable" : "")
                  + (plannerSummary.objectiveArea.marker?.id === objective.id ? " is-planned" : "")
                  + (selectedObjectiveId === objective.id ? " is-selected" : "")
                }
                transform={`translate(${objective.cameraDisplayAnchor.x}, ${objective.cameraDisplayAnchor.y}) scale(${zoomPresentation.counterScale})`}
                role="button"
                tabIndex={0}
                data-objective-id={objective.id}
                aria-pressed={!objectiveSelectionActive ? selectedObjectiveId === objective.id : undefined}
                aria-label={objectiveSelectionActive ? `Mark ${objective.name} as the operation objective area` : `Inspect ${objective.name}`}
                onClick={objectiveSelectionActive
                  ? () => plannerActions.onSelectObjectiveArea(objective.id)
                  : () => onSelectSelection({ kind: "objective", id: objective.id })}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    if (objectiveSelectionActive) {
                      plannerActions.onSelectObjectiveArea(objective.id);
                    } else {
                      onSelectSelection({ kind: "objective", id: objective.id });
                    }
                  }
                }}
              >
                {objective.axisFocus || Number(objective.objectiveOverlay?.importanceTier || 0) >= 2 ? (
                  <g
                    className={
                      "shell-map__objective-emphasis"
                      + ` is-${objective.objectiveOverlay?.category ?? "secondary"}`
                      + (objective.objectiveOverlay?.contested ? " is-contested" : "")
                      + (objective.axisFocus ? " is-axis-focus" : "")
                    }
                    aria-hidden="true"
                  >
                    <circle
                      className="shell-map__objective-emphasis-ring"
                      r={objective.axisFocus ? 23 : Number(objective.objectiveOverlay?.importanceTier || 0) >= 3 ? 19.4 : 18}
                    />
                    {objective.axisFocus ? (
                      <circle
                        className="shell-map__objective-emphasis-core"
                        r={objective.objectiveOverlay?.category === "strategic" ? 16.2 : 14.2}
                      />
                    ) : null}
                  </g>
                ) : null}
                <ObjectiveOverlayBadge
                  category={objective.objectiveOverlay?.category}
                  importanceTier={objective.objectiveOverlay?.importanceTier}
                  contested={objective.objectiveOverlay?.contested}
                  zoom={camera.zoom}
                />
                <SettlementIcon
                  tier={objective.settlement?.tier}
                  controlState={objective.settlement?.controlState}
                  damaged={objective.settlement?.damaged}
                  supplyHub={objective.settlement?.supplyHub}
                  showValueMarks={zoomPresentation.showObjectiveMarkers}
                  zoom={camera.zoom}
                />
                {labelsLayerVisible && visibleLabelIds.has(`objective:${objective.id}:label`) ? (
                  <text
                    className={
                      `shell-map__objective-label is-${objective.settlement?.controlState ?? "unknown"}`
                      + (objective.axisFocus ? " is-axis-focus" : "")
                    }
                    x={objective.labelX}
                    y={objective.labelY}
                    textAnchor={objective.labelAnchor}
                  >
                    {objective.map_label || objective.displayName || objective.name}
                  </text>
                ) : null}
                {labelsLayerVisible && visibleLabelIds.has(`objective:${objective.id}:state`) ? (
                  <text
                    className={
                      `shell-map__objective-state is-${objective.settlement?.controlState ?? "unknown"}`
                      + (objective.axisFocus ? " is-axis-focus" : "")
                    }
                    x={objective.stateX}
                    y={objective.stateY}
                    textAnchor={objective.stateAnchor}
                  >
                    {objective.stateLabel}
                  </text>
                ) : null}
              </g>
            </Fragment>
          )) : null}

          {infrastructureLayerVisible ? transformedAirfields.map((airfield) => (
            <Fragment key={airfield.id}>
              {labelsLayerVisible && airfield.hasLeader && zoomPresentation.showLeaderLines && visibleLabelOwners.has(`airfield:${airfield.id}`) ? (
                <line
                  className="shell-map__leader shell-map__leader--unit"
                  x1={airfield.cameraAnchor.x}
                  y1={airfield.cameraAnchor.y}
                  x2={airfield.cameraDisplayAnchor.x}
                  y2={airfield.cameraDisplayAnchor.y}
                />
              ) : null}
              <g
                className={
                  "shell-map__site shell-map__site--airfield"
                  + ` is-${airfield.airfield?.controlState ?? "unknown"}`
                  + ` is-${airfield.airfield?.tier ?? "operational_airfield"}`
                  + ` is-${airfield.airfield?.damageState ?? "ready"}`
                  + (airfield.airfield?.sortieActive ? " is-sortie-active" : "")
                  + (selectedAirfieldId === airfield.id ? " is-selected" : "")
                }
                transform={`translate(${airfield.cameraDisplayAnchor.x}, ${airfield.cameraDisplayAnchor.y}) scale(${zoomPresentation.counterScale})`}
                role="button"
                tabIndex={0}
                aria-label={`Inspect ${airfield.name}`}
                aria-pressed={selectedAirfieldId === airfield.id}
                onClick={() => onSelectSelection({ kind: "airfield", id: airfield.id })}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectSelection({ kind: "airfield", id: airfield.id });
                  }
                }}
              >
                <AirfieldIcon
                  tier={airfield.airfield?.tier}
                  controlState={airfield.airfield?.controlState}
                  damageState={airfield.airfield?.damageState}
                  readinessBand={airfield.airfield?.readinessBand}
                  sortieActive={airfield.airfield?.sortieActive}
                  zoom={camera.zoom}
                />
                {labelsLayerVisible && visibleLabelIds.has(`airfield:${airfield.id}:label`) ? (
                  <text className="shell-map__site-label" x={airfield.labelOffsetX} y={airfield.labelOffsetY} textAnchor={airfield.labelAnchor}>
                    {airfield.map_label || airfield.name}
                  </text>
                ) : null}
              </g>
            </Fragment>
          )) : null}

          {infrastructureLayerVisible ? transformedPorts.map((port) => (
            <Fragment key={port.id}>
              {labelsLayerVisible && port.hasLeader && zoomPresentation.showLeaderLines && visibleLabelOwners.has(`port:${port.id}`) ? (
                <line
                  className="shell-map__leader shell-map__leader--unit"
                  x1={port.cameraAnchor.x}
                  y1={port.cameraAnchor.y}
                  x2={port.cameraDisplayAnchor.x}
                  y2={port.cameraDisplayAnchor.y}
                />
              ) : null}
              <g
                className={"shell-map__site shell-map__site--port" + (selectedPortId === port.id ? " is-selected" : "")}
                transform={`translate(${port.cameraDisplayAnchor.x}, ${port.cameraDisplayAnchor.y}) scale(${zoomPresentation.counterScale})`}
                role="button"
                tabIndex={0}
                aria-label={`Inspect ${port.name}`}
                aria-pressed={selectedPortId === port.id}
                onClick={() => onSelectSelection({ kind: "port", id: port.id })}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectSelection({ kind: "port", id: port.id });
                  }
                }}
              >
                <rect x="-10" y="-8" width="20" height="16" rx="3" className="shell-map__site-body" />
                <text className="shell-map__site-code" x="0" y="4" textAnchor="middle">PT</text>
                {labelsLayerVisible && visibleLabelIds.has(`port:${port.id}:label`) ? (
                  <text className="shell-map__site-label" x={port.labelOffsetX} y={port.labelOffsetY} textAnchor={port.labelAnchor}>
                    {port.map_label || port.name}
                  </text>
                ) : null}
              </g>
            </Fragment>
          )) : null}

          {unitsLayerVisible ? transformedUnits.map((unit) => (
            <Fragment key={unit.id}>
              {labelsLayerVisible && unit.hasLeader && zoomPresentation.showLeaderLines && visibleLabelOwners.has(`unit:${unit.id}`) ? (
                <line
                  className="shell-map__leader shell-map__leader--unit"
                  x1={unit.cameraAnchor.x}
                  y1={unit.cameraAnchor.y}
                  x2={unit.cameraDisplayAnchor.x}
                  y2={unit.cameraDisplayAnchor.y}
                />
              ) : null}
              <g
                className={
                  `shell-map__unit is-${unit.visualSlot}`
                  + ` is-faction-${unit.counterAppearance?.faction ?? "unknown"}`
                  + ` is-service-${unit.counterAppearance?.service ?? "army"}`
                  + ` is-${unit.counterFrame?.echelon ?? "battalion"}`
                  + (unit.counterAppearance?.disabled ? " is-disabled" : "")
                  + (unit.counterAppearance?.outOfCommand ? " is-out-of-command" : "")
                  + (unit.counterFrame?.isHeadquarters ? " is-headquarters" : "")
                  + (selectedUnitId === unit.id ? " is-selected" : "")
                }
                transform={`translate(${unit.cameraDisplayAnchor.x}, ${unit.cameraDisplayAnchor.y}) scale(${zoomPresentation.counterScale})`}
                style={buildUnitCounterPaletteStyle(unit.counterAppearance ?? {}) as CSSProperties}
                role="button"
                tabIndex={0}
                aria-label={`Select ${unit.name}`}
                aria-pressed={selectedUnitId === unit.id}
                onClick={() => onSelectSelection({ kind: "unit", id: unit.id })}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectSelection({ kind: "unit", id: unit.id });
                  }
                }}
              >
                <UnitCounterFrame
                  echelon={unit.counterFrame?.echelon ?? "battalion"}
                  isHeadquarters={unit.counterFrame?.isHeadquarters}
                  symbol={unit.counterSymbol?.id ?? null}
                  code={unit.shortLabel}
                  zoom={camera.zoom}
                />
                <UnitCounterStatusOverlay
                  overlay={unit.counterStatusOverlay}
                  echelon={unit.counterFrame?.echelon ?? "battalion"}
                  isHeadquarters={unit.counterFrame?.isHeadquarters}
                  zoom={camera.zoom}
                />
                {labelsLayerVisible && visibleLabelIds.has(`unit:${unit.id}:label`) ? (
                  <text className="shell-map__unit-name" x={unit.labelOffsetX} y={unit.labelOffsetY} textAnchor={unit.labelAnchor}>
                    {unit.map_label || unit.name}
                  </text>
                ) : null}
              </g>
            </Fragment>
          )) : null}
        </svg>

        {basemapRuntimeState.invalid || scene.emptyState ? (
          <div
            className="shell-map__overlay shell-map__overlay--top"
            style={{ "--shell-map-control-left": topControlInset } as CSSProperties}
          >
            {basemapRuntimeState.invalid ? (
              <div className={"shell-map__status-note shell-map__status-note--error" + (basemapFallbackUnderlayActive ? " has-fallback" : "")}>
                <strong>Packaged basemap invalid.</strong> {basemapLayerSummary.detail}
              </div>
            ) : null}
            {scene.emptyState && import.meta.env.DEV ? <p className="shell-map__status-note">{scene.emptyState}</p> : null}
          </div>
        ) : null}

        {transformedQuickCommandPreview ? (
          <div
            className="shell-map__overlay shell-map__overlay--top"
            style={{ "--shell-map-control-left": topControlInset } as CSSProperties}
          >
            <div className={`shell-map__status-note shell-map__status-note--quickcommand is-${transformedQuickCommandPreview.previewTone}`}>
              <strong>{transformedQuickCommandPreview.title}</strong>
              <span>{transformedQuickCommandPreview.statusLabel}</span>
              <em>{transformedQuickCommandPreview.note}</em>
            </div>
          </div>
        ) : null}

        <aside className={"shell-drawer shell-drawer--planner" + (plannerState.plannerOpen ? " is-open" : "") + (plannerPinned ? " is-pinned" : "")} aria-label="Operations builder drawer">
          {plannerState.plannerOpen ? (
            <div className="shell-drawer__panel" id="shell-planner-drawer-panel">
              <div className="shell-drawer__head">
                <div>
                  <div className="shell-eyebrow">Operations Builder</div>
                  <h2 className="shell-panel__title">{plannerSummary.currentPlan?.headline ?? "Offensive Planning"}</h2>
                  <div className="shell-drawer__subtitle">
                    {trackedOperations.available
                      ? `${trackedOperations.total} approved operation${trackedOperations.total === 1 ? "" : "s"} tracked. ${trackedOperations.headline}.`
                      : plannerSummary.note}
                  </div>
                </div>
                <div className="shell-drawer__actions">
                  <button type="button" className="shell-button shell-button--secondary" onClick={() => setPlannerPinned((current) => !current)}>
                    {plannerPinned ? "Unpin Panel" : "Pin Panel"}
                  </button>
                  <button
                    type="button"
                    className="shell-button shell-button--secondary"
                    onClick={() => {
                      setPlannerPinned(false);
                      plannerActions.onClosePlanner();
                    }}
                  >
                    Close
                  </button>
                </div>
              </div>
              <div className="shell-drawer__body">
                <OperationPlannerPanel
                  summary={plannerSummary}
                  plannerState={plannerState}
                  actions={plannerActions}
                  embedded
                  workbenchTab={plannerWorkbenchTab}
                  onSelectWorkbenchTab={onSelectPlannerWorkbenchTab}
                  showQaTab={qaWorkbenchVisible}
                  plannerStatus={{
                    activeTool: plannerActiveToolLabel,
                    selectedColor: plannerActiveStyleLabel,
                    visibility: plannerVisibilityLabel,
                    layers: plannerLayerCountLabel,
                  }}
                  planWorkbench={plannerPlanWorkbench}
                  mapWorkbench={plannerMapWorkbench}
                  qaWorkbench={plannerQaWorkbench}
                />
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="shell-drawer__handle"
              onClick={() => {
                onSelectPlannerWorkbenchTab("plan");
                plannerActions.onOpenPlanner();
              }}
              aria-expanded={false}
              aria-controls="shell-planner-drawer-panel"
            >
              <span>Planner</span>
              <span>Open</span>
            </button>
          )}
        </aside>

        <div className="shell-map__utility-shelf">
          <div className={"shell-map__legend" + (legendOpen ? " is-open" : "")}>
            <button
              type="button"
              className="shell-map__legend-toggle"
              onClick={() => setLegendOpen((current) => !current)}
              aria-expanded={legendOpen}
              aria-controls="shell-map-legend"
            >
              <span className="shell-map__legend-title">NATO Legend</span>
              <span className="shell-map__legend-state">{legendOpen ? "Hide" : "Show"}</span>
            </button>

            {legendOpen ? (
              <div className="shell-map__legend-body" id="shell-map-legend">
                {scene.legend.map((section) => (
                  <Fragment key={section.id}>
                    <div className="shell-map__legend-subtitle">{section.title}</div>
                    {section.rows.map((entry) => (
                      <div className="shell-map__legend-row" key={entry.id}>
                        {entry.kind === "force" ? <NatoLegendSymbol kind="force" slot={entry.slot} /> : null}
                        {entry.kind === "unit" ? <NatoLegendSymbol kind="unit" symbol={entry.symbol} /> : null}
                        {entry.kind === "settlement" ? <NatoLegendSymbol kind="settlement" tier={entry.tier} controlState={entry.controlState} /> : null}
                        {entry.kind === "airfield" ? (
                          <NatoLegendSymbol
                            kind="airfield"
                            tier={entry.tier}
                            controlState={entry.controlState}
                            damageState={entry.damageState}
                            readinessBand={entry.readinessBand}
                            sortieActive={entry.sortieActive}
                          />
                        ) : null}
                        {entry.kind === "port" ? <NatoLegendSymbol kind="port" /> : null}
                        {entry.kind === "leader" ? <NatoLegendSymbol kind="leader" /> : null}
                        <span>{entry.label}</span>
                      </div>
                    ))}
                  </Fragment>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
