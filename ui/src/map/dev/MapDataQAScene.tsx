import { Fragment, useEffect, useId, useMemo, useRef, useState, type CSSProperties, type RefObject } from "react";
import AirfieldIcon from "../../components/shell/AirfieldIcon";
import ObjectiveOverlayBadge from "../../components/shell/ObjectiveOverlayBadge";
import SettlementIcon from "../../components/shell/SettlementIcon";
import { buildMapScene, projectScenePoint } from "../../components/shell/map_scene.js";
import type { ViewSnapshot } from "../../types/viewSnapshot";
import { MAP_BASEMAP_TOKENS, MAP_READABILITY_STYLE_TOKENS, MAP_SIZE_TOKENS } from "../designTokens.js";
import { normalizeHexTerrain } from "../hexTile.js";
import { buildDeclutteredLabels, buildMarkerObstacleRect } from "../labelDeclutter.js";
import {
  benchmarkLockMismatches,
  benchmarkMatchesLockedState,
  MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST,
  MAP_READABILITY_BENCHMARK_PRESET,
  MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
  MAP_READABILITY_BENCHMARK_SUITE,
  MAP_READABILITY_DEBUG_DEFAULTS,
  MAP_READABILITY_CAPTURE_SPECS,
  MAP_READABILITY_REGRESSION_CAPTURE_IDS,
  MAP_READABILITY_TUNING_FIELDS,
  MAP_READABILITY_ZOOM_PRESETS,
  captureSpecFilename,
  clampReadabilityTuning,
  resolveReadabilityQaBookmarks,
  resolveReadabilityQaViewport,
} from "../readabilityQaConfig.js";
import { loadBasemapQaBundle } from "../runtime/BasemapLoader.js";

type MapDataQASceneProps = {
  theaterId: string | null;
  snapshot?: ViewSnapshot | null;
  title?: string;
  note?: string;
  benchmarkSuite?: typeof MAP_READABILITY_BENCHMARK_SUITE;
  captureSpecs?: typeof MAP_READABILITY_CAPTURE_SPECS;
  readinessChecklist?: typeof MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST;
};

type QaHexRecord = {
  hex_id: string;
  q: number;
  r: number;
  dominant_terrain_class: string;
  elevation_m: { mean: number; min: number; max: number };
  slope: { mean: number; min: number; max: number; class: string };
  ruggedness: { mean: number; min: number; max: number; class: string };
  terrain_mix_pct: Record<string, number>;
  water_adjacency: { has_any: boolean; adjacent_water_hexes: number };
  river_presence: { major_river: boolean; minor_river: boolean };
  river_crossing_flags: {
    has_any: boolean;
    bridge: boolean;
    ford: boolean;
    ferry_terminal: boolean;
    port_crossing: boolean;
    matched_hydro_classes: string[];
  };
  coastline_flag: boolean;
  road_presence: { has_any: boolean; classes: string[]; length_m: number };
  rail_presence: { has_any: boolean; classes: string[]; length_m: number };
  bridge_crossing_presence: { has_any: boolean; bridge_count: number; tunnel_count: number; crossing_count: number; classes: string[] };
  settlement_tier: { has_any: boolean; class: string | null; importance_rank: number; name: string | null };
  airfield_presence: { has_any: boolean; class: string | null; importance_rank: number; name: string | null };
  movement_cost_seed: number;
  los_visibility_proxy_seed: number;
  supply_weight_seed: number;
  provenance: {
    source_ids: string[];
    source_layers: string[];
    source_feature_ids: Record<string, string[]>;
    bake_job_id: string;
    generated_at: string;
    geometry_hash: string;
  };
};

type QaBundle = {
  schema: string;
  theaterId: string;
  generatedAt: string;
  manifest: {
    bounds: { minX: number; maxX: number; minY: number; maxY: number };
    tierSummaries: Record<string, { tileCount: number; tileSpan: number }>;
  };
  validation: {
    status: string;
    summary: { pass: number; warning: number; fail: number };
    checks: Array<{ id: string; label: string; status: string; summary: string }>;
  };
  historicalOverrides: {
    available: boolean;
    fileCount: number;
    files: string[];
    note: string;
  };
  stats: {
    hexCount: number;
    elevation: { min: number; max: number };
  };
  hexes: QaHexRecord[];
  operationalPreview: {
    settlements: Array<{ id: string; q: number; r: number; tier: string; importance: number; name: string }>;
    airfields: Array<{ id: string; q: number; r: number; tier: string; importance: number; name: string }>;
    roadSegments: Array<{ id: string; class: string; from: { x: number; y: number }; to: { x: number; y: number } }>;
    railSegments: Array<{ id: string; class: string; from: { x: number; y: number }; to: { x: number; y: number } }>;
  };
};

type RawPreviewMode = "dem" | "hillshade" | "color";
type CompareMode = "raw" | "corrected" | "blend";
type LayoutMode = "single" | "before_after";

type ReadabilityObjective = {
  id: string;
  q: number;
  r: number;
  name: string;
  stateLabel: string;
  category: "primary" | "secondary" | "supply" | "political" | "strategic";
  importanceTier: number;
  contested: boolean;
};

const HEX_CORNER_OFFSETS = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI / 180) * (60 * index - 30);
  return {
    q: Math.cos(angle),
    r: Math.sin(angle),
  };
});

function buildHexPolygonPoints(
  q: number,
  r: number,
  scene: { viewport: { minX: number; maxX: number; minY: number; maxY: number }; width: number; height: number; inset: number },
): string {
  return HEX_CORNER_OFFSETS
    .map((offset) => projectScenePoint({ x: q + offset.q, y: r + offset.r }, scene))
    .map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`)
    .join(" ");
}

function classifyDemBand(elevationMean: number): string {
  if (elevationMean <= 2) {
    return "sea";
  }
  if (elevationMean < 40) {
    return "coastal";
  }
  if (elevationMean < 120) {
    return "low";
  }
  if (elevationMean < 260) {
    return "rolling";
  }
  if (elevationMean < 500) {
    return "upland";
  }
  return "ridge";
}

function classifyShadeBand(hexRecord: QaHexRecord): string {
  const slope = Number(hexRecord.slope?.mean || 0);
  const ruggedness = Number(hexRecord.ruggedness?.mean || 0);
  const relief = (slope / 24) * 0.52 + (ruggedness / 30) * 0.38 + Math.min(Number(hexRecord.elevation_m?.mean || 0), 900) / 900 * 0.1;
  if (relief < 0.08) {
    return "flat";
  }
  if (relief < 0.18) {
    return "soft";
  }
  if (relief < 0.32) {
    return "mid";
  }
  if (relief < 0.5) {
    return "strong";
  }
  return "hard";
}

function classifyColorBand(hexRecord: QaHexRecord): string {
  return classifyDemBand(Number(hexRecord.elevation_m?.mean || 0));
}

function classifyReliefBand(hexRecord: QaHexRecord): "sea_level" | "coastal_low" | "lowland" | "rolling" | "upland" | "ridge" {
  const elevationMean = Number(hexRecord.elevation_m?.mean || 0);
  if (elevationMean <= 2) {
    return "sea_level";
  }
  if (elevationMean < 40) {
    return "coastal_low";
  }
  if (elevationMean < 120) {
    return "lowland";
  }
  if (elevationMean < 260) {
    return "rolling";
  }
  if (elevationMean < 500) {
    return "upland";
  }
  return "ridge";
}

function normalizeSettlementTier(tier: string | null | undefined): "village" | "town" | "city" | "major_city" | "capital" {
  const raw = String(tier || "").trim().toLowerCase();
  if (raw === "capital" || raw === "key_objective_city") {
    return "capital";
  }
  if (raw === "major_city") {
    return "major_city";
  }
  if (raw === "city") {
    return "city";
  }
  if (raw === "town") {
    return "town";
  }
  return "village";
}

function summarizeValidationTone(status: string): string {
  if (status === "fail") {
    return "is-fail";
  }
  if (status === "warning") {
    return "is-warning";
  }
  return "is-pass";
}

function buildSyntheticObjectives(bundle: QaBundle | null): ReadabilityObjective[] {
  if (!bundle) {
    return [];
  }
  const settlements = [...(bundle.operationalPreview?.settlements || [])].sort((left, right) => right.importance - left.importance);
  const rows = settlements.slice(0, 3).map((settlement, index) => ({
    id: `synthetic-objective:${settlement.id}`,
    q: Number(settlement.q),
    r: Number(settlement.r),
    name: settlement.name,
    stateLabel: index === 0 ? "Key locality" : "Reference node",
    category: index === 0 ? "strategic" : index === 1 ? "primary" : "secondary",
    importanceTier: Math.max(1, Math.min(3, Math.round(settlement.importance / 3))),
    contested: false,
  }) satisfies ReadabilityObjective);
  const supplyAirfield = bundle.operationalPreview?.airfields?.[0];
  if (supplyAirfield) {
    rows.push({
      id: `synthetic-objective:${supplyAirfield.id}`,
      q: Number(supplyAirfield.q),
      r: Number(supplyAirfield.r),
      name: supplyAirfield.name,
      stateLabel: "Air link",
      category: "supply",
      importanceTier: 2,
      contested: false,
    });
  }
  return rows;
}

function downloadSvg(svgElement: SVGSVGElement, filename: string) {
  const blob = new Blob([svgElement.outerHTML], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildStyleVars(tuning: ReturnType<typeof clampReadabilityTuning>, zoomTierId: string): CSSProperties {
  const base = MAP_READABILITY_STYLE_TOKENS;
  const waterFillOpacityFactor = MAP_BASEMAP_TOKENS.waterFillOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.waterFillOpacityFactorByTier.operational;
  const coastFillOpacityFactor = MAP_BASEMAP_TOKENS.coastFillOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.coastFillOpacityFactorByTier.operational;
  const coastOpacityFactor = MAP_BASEMAP_TOKENS.coastOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.coastOpacityFactorByTier.operational;
  const coastCasingOpacityFactor = MAP_BASEMAP_TOKENS.coastCasingOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.coastCasingOpacityFactorByTier.operational;
  const riverCasingOpacityFactor = MAP_BASEMAP_TOKENS.riverCasingOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.riverCasingOpacityFactorByTier.operational;
  const transportCasingOpacityFactor = MAP_BASEMAP_TOKENS.transportCasingOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.transportCasingOpacityFactorByTier.operational;
  const roadPrimaryOpacityFactor = MAP_BASEMAP_TOKENS.roadPrimaryOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.roadPrimaryOpacityFactorByTier.operational;
  const roadSecondaryOpacityFactor = MAP_BASEMAP_TOKENS.roadSecondaryOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.roadSecondaryOpacityFactorByTier.operational;
  const railOpacityFactor = MAP_BASEMAP_TOKENS.railOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.railOpacityFactorByTier.operational;
  const crossingOpacityFactor = MAP_BASEMAP_TOKENS.crossingOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.crossingOpacityFactorByTier.operational;
  const crossingHaloOpacityFactor = MAP_BASEMAP_TOKENS.crossingHaloOpacityFactorByTier[zoomTierId] ?? MAP_BASEMAP_TOKENS.crossingHaloOpacityFactorByTier.operational;
  return {
    "--shell-mapqa-raw-blend-opacity": String(base.blendOpacity.raw),
    "--shell-mapqa-corrected-blend-opacity": String(base.blendOpacity.corrected),
    "--shell-mapqa-selection-width": `${base.strokeWidthPx.selection}px`,
    "--shell-mapqa-grid-width": `${(base.strokeWidthPx.grid * tuning.gridWidthScale).toFixed(3)}px`,
    "--shell-mapqa-grid-opacity": tuning.gridOpacity.toFixed(2),
    "--shell-mapqa-historical-opacity": String(base.opacity.historicalWash),
    "--shell-mapqa-hillshade-opacity": tuning.hillshadeOpacity.toFixed(2),
    "--shell-mapqa-terrain-tint-opacity": tuning.terrainTintStrength.toFixed(2),
    "--shell-mapqa-water-fill-opacity": (tuning.terrainTintStrength * waterFillOpacityFactor).toFixed(2),
    "--shell-mapqa-coast-fill-opacity": (tuning.terrainTintStrength * coastFillOpacityFactor).toFixed(2),
    "--shell-mapqa-terrain-contrast": tuning.terrainContrast.toFixed(2),
    "--shell-mapqa-hypsometric-opacity": (base.opacity.hypsometric * Math.max(0.78, tuning.terrainTintStrength)).toFixed(2),
    "--shell-mapqa-hydro-opacity": tuning.hydroOpacity.toFixed(2),
    "--shell-mapqa-hydro-coast-opacity": (tuning.hydroOpacity * coastOpacityFactor).toFixed(2),
    "--shell-mapqa-hydro-coast-casing-opacity": (tuning.hydroOpacity * coastCasingOpacityFactor).toFixed(2),
    "--shell-mapqa-hydro-river-casing-opacity": (tuning.hydroOpacity * riverCasingOpacityFactor).toFixed(2),
    "--shell-mapqa-hydro-coast-casing-width": `${(base.strokeWidthPx.hydroCoastCasing * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-coast-width": `${(base.strokeWidthPx.hydroCoast * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-major-casing-width": `${(base.strokeWidthPx.hydroMajorCasing * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-major-width": `${(base.strokeWidthPx.hydroMajor * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-minor-casing-width": `${(base.strokeWidthPx.hydroMinorCasing * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-minor-width": `${(base.strokeWidthPx.hydroMinor * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-crossing-halo-opacity": String(Math.min(1, crossingHaloOpacityFactor).toFixed(2)),
    "--shell-mapqa-hydro-crossing-opacity": String(Math.min(1, crossingOpacityFactor).toFixed(2)),
    "--shell-mapqa-hydro-crossing-halo-width": `${(base.strokeWidthPx.hydroCrossingHalo * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-hydro-crossing-ring-width": `${(base.strokeWidthPx.hydroCrossingRing * tuning.hydroWidthScale).toFixed(2)}px`,
    "--shell-mapqa-transport-opacity": tuning.transportOpacity.toFixed(2),
    "--shell-mapqa-transport-casing-opacity": (tuning.transportOpacity * transportCasingOpacityFactor).toFixed(2),
    "--shell-mapqa-transport-primary-opacity": (tuning.transportOpacity * roadPrimaryOpacityFactor).toFixed(2),
    "--shell-mapqa-transport-secondary-opacity": (tuning.transportOpacity * roadSecondaryOpacityFactor).toFixed(2),
    "--shell-mapqa-transport-rail-opacity": (tuning.transportOpacity * railOpacityFactor).toFixed(2),
    "--shell-mapqa-road-primary-casing-width": `${(base.strokeWidthPx.transportPrimaryCasing * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-road-primary-width": `${(base.strokeWidthPx.transportPrimary * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-road-secondary-casing-width": `${(base.strokeWidthPx.transportSecondaryCasing * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-road-secondary-width": `${(base.strokeWidthPx.transportSecondary * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-rail-casing-width": `${(base.strokeWidthPx.transportRailCasing * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-rail-width": `${(base.strokeWidthPx.transportRail * tuning.transportWidthScale).toFixed(2)}px`,
    "--shell-mapqa-ghost-label-opacity": tuning.ghostLabelOpacity.toFixed(2),
    "--shell-mapqa-ghost-label-size": `${(base.labelFontPx.ghost * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-local-label-size": `${(base.labelFontPx.local * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-objective-label-size": `${(base.labelFontPx.objective * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-objective-meta-size": `${(base.labelFontPx.objectiveMeta * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-historical-label-size": `${base.labelFontPx.historical}px`,
    "--shell-mapqa-label-halo-width": `${(base.haloWidthPx.local * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-objective-halo-width": `${(base.haloWidthPx.objective * tuning.localLabelScale).toFixed(2)}px`,
    "--shell-mapqa-settlement-scale": tuning.settlementIconScale.toFixed(2),
    "--shell-mapqa-airfield-scale": tuning.airfieldIconScale.toFixed(2),
    "--shell-mapqa-objective-scale": tuning.objectiveIconScale.toFixed(2),
  } as CSSProperties;
}

export default function MapDataQAScene({
  theaterId,
  snapshot = null,
  title = "Map Readability QA",
  note = "Readability harness uses packaged basemap QA data plus current scenario objectives when available. In the final lock pass the compare view shows the preserved Phase 1 baseline against the current calibrated stack. Calibration-only controls are hidden by default; use the explicit export profiles to keep the regression captures stable.",
  benchmarkSuite = MAP_READABILITY_BENCHMARK_SUITE,
  captureSpecs = MAP_READABILITY_CAPTURE_SPECS,
  readinessChecklist = MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST,
}: MapDataQASceneProps) {
  const [open, setOpen] = useState(false);
  const [bundle, setBundle] = useState<QaBundle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rawPreviewMode, setRawPreviewMode] = useState<RawPreviewMode>("hillshade");
  const [compareMode, setCompareMode] = useState<CompareMode>("corrected");
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("before_after");
  const [zoomPresetId, setZoomPresetId] = useState<string>("operational");
  const [bookmarkId, setBookmarkId] = useState<string>("overview");
  const [showCalibration, setShowCalibration] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [showHydro, setShowHydro] = useState(true);
  const [showTransport, setShowTransport] = useState(true);
  const [showHistorical, setShowHistorical] = useState(false);
  const [showExtentFrame, setShowExtentFrame] = useState(MAP_READABILITY_DEBUG_DEFAULTS.showExtentFrame);
  const [selectedHexId, setSelectedHexId] = useState<string | null>(null);
  const [tuning, setTuning] = useState(() => clampReadabilityTuning(MAP_READABILITY_STYLE_TOKENS.tuningDefaults));
  const tunedSvgRef = useRef<SVGSVGElement | null>(null);
  const sceneDomId = useId();

  useEffect(() => {
    let cancelled = false;

    setBundle(null);
    setLoadError(null);

    if (!open) {
      return undefined;
    }

    if (!theaterId) {
      setLoadError("Benchmark invalid: no packaged basemap is registered for the current scenario family.");
      return undefined;
    }

    loadBasemapQaBundle(theaterId)
      .then((nextBundle) => {
        if (!cancelled) {
          setBundle(nextBundle as QaBundle);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "Unable to load the packaged QA bundle.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, theaterId]);

  const bookmarks = useMemo(() => resolveReadabilityQaBookmarks(bundle), [bundle]);

  useEffect(() => {
    if (!bookmarks.length) {
      return;
    }
    if (!bookmarks.some((entry) => entry.id === bookmarkId)) {
      setBookmarkId(bookmarks[0].id);
    }
  }, [bookmarks, bookmarkId]);

  useEffect(() => {
    if (!bundle) {
      return;
    }
    setSelectedHexId((current) => {
      if (current && bundle.hexes.some((hexRecord) => hexRecord.hex_id === current)) {
        return current;
      }
      return null;
    });
  }, [bundle]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setRawPreviewMode(MAP_READABILITY_BENCHMARK_PRESET.rawPreviewMode as RawPreviewMode);
    setCompareMode(MAP_READABILITY_BENCHMARK_PRESET.compareMode as CompareMode);
    setLayoutMode(MAP_READABILITY_BENCHMARK_PRESET.layoutMode as LayoutMode);
    setShowGrid(MAP_READABILITY_BENCHMARK_PRESET.showGrid);
    setShowHydro(MAP_READABILITY_BENCHMARK_PRESET.showHydro);
    setShowTransport(MAP_READABILITY_BENCHMARK_PRESET.showTransport);
    setShowHistorical(MAP_READABILITY_BENCHMARK_PRESET.showHistorical);
    setShowExtentFrame(MAP_READABILITY_DEBUG_DEFAULTS.showExtentFrame);
    setShowCalibration(false);
    setSelectedHexId(MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.selectedHexId);
  }, [open, theaterId]);

  const qaScene = useMemo(
    () => resolveReadabilityQaViewport(bundle, zoomPresetId, bookmarkId),
    [bundle, zoomPresetId, bookmarkId],
  );

  const projectedHexes = useMemo(() => (
    (bundle?.hexes || []).map((hexRecord) => ({
      ...hexRecord,
      center: projectScenePoint({ x: hexRecord.q, y: hexRecord.r }, qaScene),
      points: buildHexPolygonPoints(hexRecord.q, hexRecord.r, qaScene),
      terrainClass: normalizeHexTerrain(hexRecord.dominant_terrain_class),
      demBand: classifyDemBand(Number(hexRecord.elevation_m?.mean || 0)),
      shadeBand: classifyShadeBand(hexRecord),
      colorBand: classifyColorBand(hexRecord),
      reliefBand: classifyReliefBand(hexRecord),
    }))
  ), [bundle, qaScene]);

  const projectedOperationalPreview = useMemo(() => ({
    settlements: (bundle?.operationalPreview?.settlements || []).map((settlement) => ({
      ...settlement,
      point: projectScenePoint({ x: settlement.q, y: settlement.r }, qaScene),
    })),
    airfields: (bundle?.operationalPreview?.airfields || []).map((airfield) => ({
      ...airfield,
      point: projectScenePoint({ x: airfield.q, y: airfield.r }, qaScene),
    })),
    roadSegments: (bundle?.operationalPreview?.roadSegments || []).map((segment) => ({
      ...segment,
      fromPoint: projectScenePoint(segment.from, qaScene),
      toPoint: projectScenePoint(segment.to, qaScene),
    })),
    railSegments: (bundle?.operationalPreview?.railSegments || []).map((segment) => ({
      ...segment,
      fromPoint: projectScenePoint(segment.from, qaScene),
      toPoint: projectScenePoint(segment.to, qaScene),
    })),
  }), [bundle, qaScene]);

  const scenarioObjectives = useMemo(() => {
    if (!snapshot) {
      return buildSyntheticObjectives(bundle);
    }
    const liveScene = buildMapScene(snapshot, MAP_READABILITY_STYLE_TOKENS.scene);
    const liveObjectives = Array.isArray(liveScene.objectives) ? liveScene.objectives.map((objective) => ({
      id: String(objective.id),
      q: Number(objective.displayAnchor?.x ?? objective.anchor?.x ?? 0),
      r: Number(objective.displayAnchor?.y ?? objective.anchor?.y ?? 0),
      name: objective.name,
      stateLabel: objective.stateLabel,
      category: objective.objectiveOverlay?.category ?? "secondary",
      importanceTier: Math.max(1, Number(objective.objectiveOverlay?.importanceTier || 1)),
      contested: Boolean(objective.objectiveOverlay?.contested),
    }) satisfies ReadabilityObjective) : [];
    return liveObjectives.length ? liveObjectives : buildSyntheticObjectives(bundle);
  }, [bundle, snapshot]);

  const projectedObjectives = useMemo(
    () => scenarioObjectives.map((objective) => ({
      ...objective,
      point: projectScenePoint({ x: objective.q, y: objective.r }, qaScene),
    })),
    [scenarioObjectives, qaScene],
  );

  const selectedHex = useMemo(
    () => projectedHexes.find((hexRecord) => hexRecord.hex_id === selectedHexId) || null,
    [projectedHexes, selectedHexId],
  );

  const showRawBase = compareMode !== "corrected";
  const showCorrectedBase = compareMode !== "raw";
  const historicalAvailable = Boolean(bundle?.historicalOverrides?.available);
  const benchmarkRenderState = useMemo(() => {
    if (!theaterId) {
      return {
        status: "invalid",
        detail: "Benchmark invalid: no packaged basemap is registered for the current scenario family.",
      };
    }
    if (loadError) {
      return {
        status: "error",
        detail: `Benchmark invalid: ${loadError}`,
      };
    }
    if (!bundle) {
      return {
        status: "loading",
        detail: "Loading packaged basemap QA bundle.",
      };
    }
    if (!projectedHexes.length) {
      return {
        status: "invalid",
        detail: "Benchmark invalid: packaged QA bundle loaded but no terrain-bearing hexes were rendered.",
      };
    }
    if (showExtentFrame) {
      return {
        status: "invalid",
        detail: "Benchmark invalid: debug extent framing is enabled. Turn it off before exporting or accepting captures.",
      };
    }
    return {
      status: "ready",
      detail: `${projectedHexes.length} terrain-bearing hexes available for benchmark rendering.`,
    };
  }, [bundle, loadError, projectedHexes.length, showExtentFrame, theaterId]);
  const benchmarkReady = benchmarkRenderState.status === "ready";

  const applyBenchmarkPreset = (nextState: {
    zoomPresetId: string;
    bookmarkId: string;
    uiState?: { compareMode?: string; layoutMode?: string; rawPreviewMode?: string; showCalibration?: boolean; showExtentFrame?: boolean; selectedHexId?: string | null };
    overlayState?: { showGrid?: boolean; showHydro?: boolean; showTransport?: boolean; showHistorical?: boolean };
  }) => {
    setZoomPresetId(nextState.zoomPresetId);
    setBookmarkId(nextState.bookmarkId);
    setRawPreviewMode((nextState.uiState?.rawPreviewMode || MAP_READABILITY_BENCHMARK_PRESET.rawPreviewMode) as RawPreviewMode);
    setCompareMode((nextState.uiState?.compareMode || MAP_READABILITY_BENCHMARK_PRESET.compareMode) as CompareMode);
    setLayoutMode((nextState.uiState?.layoutMode || MAP_READABILITY_BENCHMARK_PRESET.layoutMode) as LayoutMode);
    setShowGrid(nextState.overlayState?.showGrid ?? MAP_READABILITY_BENCHMARK_PRESET.showGrid);
    setShowHydro(nextState.overlayState?.showHydro ?? MAP_READABILITY_BENCHMARK_PRESET.showHydro);
    setShowTransport(nextState.overlayState?.showTransport ?? MAP_READABILITY_BENCHMARK_PRESET.showTransport);
    setShowHistorical(nextState.overlayState?.showHistorical ?? MAP_READABILITY_BENCHMARK_PRESET.showHistorical);
    setShowExtentFrame(nextState.uiState?.showExtentFrame ?? MAP_READABILITY_DEBUG_DEFAULTS.showExtentFrame);
    setShowCalibration(nextState.uiState?.showCalibration ?? false);
    setSelectedHexId(nextState.uiState?.selectedHexId ?? MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.selectedHexId);
    setTuning(clampReadabilityTuning(MAP_READABILITY_STYLE_TOKENS.tuningDefaults));
  };

  const applyCaptureSpec = (captureId: string) => {
    const capture = captureSpecs.find((entry) => entry.id === captureId);
    if (!capture) {
      return;
    }
    applyBenchmarkPreset(capture);
  };

  const applyBenchmarkSuiteSpec = (benchmarkId: string) => {
    const benchmark = benchmarkSuite.find((entry) => entry.id === benchmarkId);
    if (!benchmark) {
      return;
    }
    applyBenchmarkPreset(benchmark);
  };

  const currentBenchmarkState = useMemo(() => ({
    zoomPresetId,
    bookmarkId,
    selectedHexId,
    overlayState: {
      showGrid,
      showHydro,
      showTransport,
      showHistorical,
    },
    uiState: {
      compareMode,
      layoutMode,
      rawPreviewMode,
      showCalibration,
      showExtentFrame,
      selectedHexId,
    },
  }), [
    bookmarkId,
    compareMode,
    layoutMode,
    rawPreviewMode,
    selectedHexId,
    showCalibration,
    showExtentFrame,
    showGrid,
    showHistorical,
    showHydro,
    showTransport,
    zoomPresetId,
  ]);

  const candidateBenchmark = benchmarkSuite.find((entry) => (
    entry.zoomPresetId === zoomPresetId
    && entry.bookmarkId === bookmarkId
  )) || null;
  const matchedBenchmark = benchmarkSuite.find((entry) => benchmarkMatchesLockedState(currentBenchmarkState, entry)) || null;
  const benchmarkLockDrift = candidateBenchmark && !matchedBenchmark
    ? benchmarkLockMismatches(currentBenchmarkState, candidateBenchmark)
    : [];
  const activeBenchmark = matchedBenchmark || candidateBenchmark;

  const sceneLabel = `${qaScene.zoomPreset.label} / ${qaScene.bookmark.label}`;

  const renderScene = (profileId: string, profileTuning: ReturnType<typeof clampReadabilityTuning>, svgRef?: RefObject<SVGSVGElement | null>) => {
    const labelObstacles = [
      ...projectedOperationalPreview.settlements.map((settlement) => buildMarkerObstacleRect({
        id: `settlement:${settlement.id}`,
        kind: "objective",
        x: settlement.point.x,
        y: settlement.point.y,
        width: MAP_SIZE_TOKENS.cityIcon.diameterPx * profileTuning.settlementIconScale,
        height: MAP_SIZE_TOKENS.cityIcon.diameterPx * profileTuning.settlementIconScale,
        scale: 1,
      })),
      ...projectedOperationalPreview.airfields.map((airfield) => buildMarkerObstacleRect({
        id: `airfield:${airfield.id}`,
        kind: "airfield",
        x: airfield.point.x,
        y: airfield.point.y,
        width: MAP_SIZE_TOKENS.airfieldIcon.widthPx * profileTuning.airfieldIconScale,
        height: MAP_SIZE_TOKENS.airfieldIcon.heightPx * profileTuning.airfieldIconScale,
        scale: 1,
      })),
      ...projectedObjectives.map((objective) => buildMarkerObstacleRect({
        id: `objective:${objective.id}`,
        kind: "objective",
        x: objective.point.x,
        y: objective.point.y,
        width: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.7 * profileTuning.objectiveIconScale,
        height: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.7 * profileTuning.objectiveIconScale,
        scale: 1,
      })),
    ];
    const labelDeclutter = buildDeclutteredLabels([
      ...projectedOperationalPreview.settlements.map((settlement) => ({
        id: `settlement:${settlement.id}:label`,
        ownerId: `settlement:${settlement.id}`,
        ownerObstacleId: `settlement:${settlement.id}`,
        kind: "featureLabel",
        text: settlement.name,
        x: settlement.point.x + 8,
        y: settlement.point.y - 6,
        textAnchor: "start",
        scale: profileTuning.localLabelScale,
        important: settlement.importance >= 5 || settlement.tier === "city" || settlement.tier === "major_city" || settlement.tier === "capital",
        visibility: "operational",
        priorityBoost: Math.max(0, Number(settlement.importance || 0) - 3) * 4,
      })),
      ...projectedOperationalPreview.airfields.map((airfield) => ({
        id: `airfield:${airfield.id}:label`,
        ownerId: `airfield:${airfield.id}`,
        ownerObstacleId: `airfield:${airfield.id}`,
        kind: "airfieldLabel",
        text: airfield.name,
        x: airfield.point.x + 10,
        y: airfield.point.y - 8,
        textAnchor: "start",
        scale: profileTuning.localLabelScale,
        important: Number(airfield.importance || 0) >= 4,
        visibility: "operational",
      })),
      ...projectedObjectives.flatMap((objective) => ([
        {
          id: `objective:${objective.id}:label`,
          ownerId: `objective:${objective.id}`,
          ownerObstacleId: `objective:${objective.id}`,
          kind: "objectiveLabel",
          text: objective.name,
          x: objective.point.x + 12,
          y: objective.point.y - 12,
          textAnchor: "start",
          scale: profileTuning.localLabelScale,
          important: objective.importanceTier >= 2,
          visibility: "operational",
          priorityBoost: objective.importanceTier * 8,
        },
        {
          id: `objective:${objective.id}:state`,
          ownerId: `objective:${objective.id}`,
          ownerObstacleId: `objective:${objective.id}`,
          kind: "objectiveState",
          text: objective.stateLabel,
          x: objective.point.x + 12,
          y: objective.point.y + 2,
          textAnchor: "start",
          scale: profileTuning.localLabelScale,
          important: objective.importanceTier >= 2,
          visibility: "operational",
          priorityBoost: objective.importanceTier * 6,
        },
      ])),
    ], labelObstacles, { zoom: qaScene.zoomPreset.zoom });
    const visibleLabelIds = labelDeclutter.visibleIds;
    const ghostLabels = [...labelDeclutter.accepted, ...labelDeclutter.blocked];
    const style = buildStyleVars(profileTuning, qaScene.zoomPreset.id);
    return (
      <div className="shell-mapqa__panel" key={profileId} style={style}>
        <div className="shell-mapqa__panelhead">
          <strong>{profileId === "baseline" ? "Baseline" : "Tuned"}</strong>
          <span>{sceneLabel}</span>
        </div>
        <div className="shell-mapqa__canvaswrap">
          <svg
            ref={svgRef}
            className="shell-mapqa__svg"
            viewBox={`0 0 ${qaScene.width} ${qaScene.height}`}
            role="img"
            aria-label={`Map readability QA scene ${profileId}`}
          >
            <rect className="shell-mapqa__field" x="0" y="0" width={qaScene.width} height={qaScene.height} />
            {showExtentFrame ? (
              <rect
                className="shell-mapqa__extent-frame"
                x="0.5"
                y="0.5"
                width={qaScene.width - 1}
                height={qaScene.height - 1}
                rx="10"
                data-debug-extent="true"
              />
            ) : null}

            {showRawBase ? (
              <g className={"shell-mapqa__rawlayer is-" + rawPreviewMode + (compareMode === "blend" ? " is-blend" : "")}>
                {projectedHexes.map((hexRecord) => (
                  <polygon
                    key={`${profileId}:${hexRecord.hex_id}:raw`}
                    points={hexRecord.points}
                    className={
                      "shell-mapqa__hex "
                      + `shell-mapqa__hex--${rawPreviewMode}-${rawPreviewMode === "dem" ? hexRecord.demBand : rawPreviewMode === "hillshade" ? hexRecord.shadeBand : hexRecord.colorBand}`
                    }
                    onClick={() => setSelectedHexId(hexRecord.hex_id)}
                  />
                ))}
              </g>
            ) : null}

            {showCorrectedBase ? (
              <g className={"shell-mapqa__correctedlayer" + (compareMode === "blend" ? " is-blend" : "")}>
                {projectedHexes.map((hexRecord) => (
                  <Fragment key={`${profileId}:${hexRecord.hex_id}:corrected`}>
                    <polygon
                      points={hexRecord.points}
                      className={`shell-mapqa__hex shell-mapqa__hex--terrain is-${hexRecord.terrainClass}`}
                      onClick={() => setSelectedHexId(hexRecord.hex_id)}
                    />
                    <polygon
                      points={hexRecord.points}
                      className={`shell-mapqa__hex shell-mapqa__hex--hypsometric is-${hexRecord.reliefBand}`}
                      onClick={() => setSelectedHexId(hexRecord.hex_id)}
                    />
                    <polygon
                      points={hexRecord.points}
                      className={`shell-mapqa__hex shell-mapqa__hex--hillshade is-${hexRecord.shadeBand}`}
                      onClick={() => setSelectedHexId(hexRecord.hex_id)}
                    />
                  </Fragment>
                ))}
              </g>
            ) : null}

            {showHydro ? (
              <g className="shell-mapqa__hydro">
                {projectedHexes.map((hexRecord) => {
                  if (!hexRecord.coastline_flag && !hexRecord.river_presence?.major_river && !hexRecord.river_presence?.minor_river && !hexRecord.river_crossing_flags?.has_any) {
                    return null;
                  }
                  return (
                    <g key={`${profileId}:${hexRecord.hex_id}:hydro`} transform={`translate(${hexRecord.center.x} ${hexRecord.center.y})`}>
                      {hexRecord.coastline_flag ? <path className="shell-mapqa__hydro-coast-casing" d="M-10 -2 C-5 -7 5 -7 10 -1" /> : null}
                      {hexRecord.coastline_flag ? <path className="shell-mapqa__hydro-coast" d="M-10 -2 C-5 -7 5 -7 10 -1" /> : null}
                      {hexRecord.river_presence?.major_river ? <path className="shell-mapqa__hydro-river-casing is-major" d="M-8 -7 C-5 -3 2 2 8 7" /> : null}
                      {hexRecord.river_presence?.major_river ? <path className="shell-mapqa__hydro-river is-major" d="M-8 -7 C-5 -3 2 2 8 7" /> : null}
                      {hexRecord.river_presence?.minor_river ? <path className="shell-mapqa__hydro-river-casing is-minor" d="M-7 -6 C-3 -2 2 2 7 6" /> : null}
                      {hexRecord.river_presence?.minor_river ? <path className="shell-mapqa__hydro-river is-minor" d="M-7 -6 C-3 -2 2 2 7 6" /> : null}
                      {hexRecord.river_crossing_flags?.has_any ? <circle className="shell-mapqa__hydro-crossing-halo" cx="0" cy="0" r="3.8" /> : null}
                      {hexRecord.river_crossing_flags?.has_any ? <circle className="shell-mapqa__hydro-crossing" cx="0" cy="0" r="2.8" /> : null}
                      {hexRecord.river_crossing_flags?.has_any ? <circle className="shell-mapqa__hydro-crossing-core" cx="0" cy="0" r="1.15" /> : null}
                    </g>
                  );
                })}
              </g>
            ) : null}

            {showTransport ? (
              <g className="shell-mapqa__transport">
                {projectedOperationalPreview.roadSegments.map((segment) => (
                  <Fragment key={`${profileId}:${segment.id}`}>
                    <line
                      className={`shell-mapqa__transport-line-casing is-road is-${segment.class}`}
                      x1={segment.fromPoint.x}
                      y1={segment.fromPoint.y}
                      x2={segment.toPoint.x}
                      y2={segment.toPoint.y}
                    />
                    <line
                      className={`shell-mapqa__transport-line is-${segment.class}`}
                      x1={segment.fromPoint.x}
                      y1={segment.fromPoint.y}
                      x2={segment.toPoint.x}
                      y2={segment.toPoint.y}
                    />
                  </Fragment>
                ))}
                {projectedOperationalPreview.railSegments.map((segment) => (
                  <Fragment key={`${profileId}:${segment.id}`}>
                    <line
                      className={`shell-mapqa__transport-line-casing is-rail ${segment.class ? `is-${segment.class}` : ""}`}
                      x1={segment.fromPoint.x}
                      y1={segment.fromPoint.y}
                      x2={segment.toPoint.x}
                      y2={segment.toPoint.y}
                    />
                    <line
                      className={`shell-mapqa__transport-line is-rail ${segment.class ? `is-${segment.class}` : ""}`}
                      x1={segment.fromPoint.x}
                      y1={segment.fromPoint.y}
                      x2={segment.toPoint.x}
                      y2={segment.toPoint.y}
                    />
                  </Fragment>
                ))}
              </g>
            ) : null}

            {showCorrectedBase ? (
              <g className="shell-mapqa__nodes">
                {projectedOperationalPreview.settlements.map((settlement) => (
                  <g
                    key={`${profileId}:${settlement.id}:icon`}
                    className="shell-mapqa__node shell-mapqa__node--settlement"
                    transform={`translate(${settlement.point.x} ${settlement.point.y}) scale(var(--shell-mapqa-settlement-scale))`}
                  >
                    <SettlementIcon
                      tier={normalizeSettlementTier(settlement.tier)}
                      controlState="unknown"
                      placement="map"
                      zoom={qaScene.zoomPreset.zoom}
                      showValueMarks={settlement.importance >= 5}
                    />
                  </g>
                ))}
                {projectedOperationalPreview.airfields.map((airfield) => (
                  <g
                    key={`${profileId}:${airfield.id}:icon`}
                    className="shell-mapqa__node shell-mapqa__node--airfield"
                    transform={`translate(${airfield.point.x} ${airfield.point.y}) scale(var(--shell-mapqa-airfield-scale))`}
                  >
                    <AirfieldIcon
                      tier={String(airfield.tier || "").trim().toLowerCase() === "major_airbase" ? "major_airbase" : String(airfield.tier || "").trim().toLowerCase() === "minor_airstrip" ? "minor_airstrip" : "operational_airfield"}
                      controlState="unknown"
                      placement="map"
                      zoom={qaScene.zoomPreset.zoom}
                      readinessBand="unknown"
                      damageState="ready"
                    />
                  </g>
                ))}
                {projectedObjectives.map((objective) => (
                  <g
                    key={`${profileId}:${objective.id}:objective`}
                    className="shell-mapqa__node shell-mapqa__node--objective"
                    transform={`translate(${objective.point.x} ${objective.point.y}) scale(var(--shell-mapqa-objective-scale))`}
                  >
                    <ObjectiveOverlayBadge
                      category={objective.category}
                      importanceTier={objective.importanceTier}
                      contested={objective.contested}
                      zoom={qaScene.zoomPreset.zoom}
                    />
                  </g>
                ))}
              </g>
            ) : null}

            {showCorrectedBase ? (
              <g className="shell-mapqa__labels">
                {ghostLabels.map((label) => (
                  <text
                    key={`${profileId}:${label.id}:ghost`}
                    className={"shell-mapqa__ghost-label" + (label.kind.startsWith("objective") ? " is-objective" : "")}
                    x={label.x}
                    y={label.y}
                    textAnchor={label.textAnchor}
                  >
                    {label.text}
                  </text>
                ))}
                {[...projectedOperationalPreview.settlements, ...projectedOperationalPreview.airfields].map((entry) => {
                  const isSettlement = "tier" in entry && typeof entry.tier === "string";
                  const id = `${isSettlement ? "settlement" : "airfield"}:${entry.id}:label`;
                  if (!visibleLabelIds.has(id)) {
                    return null;
                  }
                  return (
                    <text
                      key={`${profileId}:${id}:local`}
                      className="shell-mapqa__local-label"
                      x={entry.point.x + ("importance" in entry && !isSettlement ? 10 : 8)}
                      y={entry.point.y + (isSettlement ? -6 : -8)}
                      textAnchor="start"
                    >
                      {entry.name}
                    </text>
                  );
                })}
                {projectedObjectives.map((objective) => (
                  <Fragment key={`${profileId}:${objective.id}:labels`}>
                    {visibleLabelIds.has(`objective:${objective.id}:label`) ? (
                      <text className="shell-mapqa__objective-label" x={objective.point.x + 12} y={objective.point.y - 12} textAnchor="start">
                        {objective.name}
                      </text>
                    ) : null}
                    {visibleLabelIds.has(`objective:${objective.id}:state`) ? (
                      <text className="shell-mapqa__objective-state" x={objective.point.x + 12} y={objective.point.y + 2} textAnchor="start">
                        {objective.stateLabel}
                      </text>
                    ) : null}
                  </Fragment>
                ))}
              </g>
            ) : null}

            {showHistorical && historicalAvailable ? (
              <g className="shell-mapqa__historical">
                <rect className="shell-mapqa__historical-wash" x="0" y="0" width={qaScene.width} height={qaScene.height} />
                <text className="shell-mapqa__historical-label" x="50%" y="18" textAnchor="middle">
                  Historical override overlay active
                </text>
              </g>
            ) : null}

            {showGrid ? (
              <g className="shell-mapqa__grid">
                {projectedHexes.map((hexRecord) => (
                  <polygon
                    key={`${profileId}:${hexRecord.hex_id}:grid`}
                    points={hexRecord.points}
                    className="shell-mapqa__grid-hex"
                    onClick={() => setSelectedHexId(hexRecord.hex_id)}
                  />
                ))}
              </g>
            ) : null}

            {selectedHex ? (
              <polygon
                points={selectedHex.points}
                className="shell-mapqa__selection"
                onClick={() => setSelectedHexId(selectedHex.hex_id)}
              />
            ) : null}
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div className={"shell-mapqa" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-mapqa__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls={sceneDomId}
      >
        <span className="shell-map__legend-title">{title}</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-mapqa__body" id={sceneDomId}>
          <div className="shell-mapqa__toolbar">
            <div className="shell-mapqa__chiprow" role="group" aria-label="Readability zoom preset">
              {MAP_READABILITY_ZOOM_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={"shell-mapqa__chip" + (zoomPresetId === preset.id ? " is-active" : "")}
                  onClick={() => setZoomPresetId(preset.id)}
                  title={preset.note}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="shell-mapqa__chiprow" role="group" aria-label="Readability bookmarks">
              {bookmarks.map((bookmark) => (
                <button
                  key={bookmark.id}
                  type="button"
                  className={"shell-mapqa__chip" + (bookmarkId === bookmark.id ? " is-active" : "")}
                  onClick={() => setBookmarkId(bookmark.id)}
                  title={bookmark.description}
                >
                  {bookmark.label}
                </button>
              ))}
            </div>

            <div className="shell-mapqa__chiprow" role="group" aria-label="Benchmark suite">
              {benchmarkSuite.map((benchmark) => (
                <button
                  key={benchmark.id}
                  type="button"
                  className={"shell-mapqa__chip" + (activeBenchmark?.id === benchmark.id ? " is-active" : "")}
                  onClick={() => applyBenchmarkSuiteSpec(benchmark.id)}
                  title={benchmark.description}
                >
                  {benchmark.label}
                </button>
              ))}
            </div>

            {showCalibration ? (
              <div className="shell-mapqa__chiprow" role="group" aria-label="Raw preview mode">
                {[
                  { id: "dem", label: "DEM" },
                  { id: "hillshade", label: "Shade" },
                  { id: "color", label: "Relief" },
                ].map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={"shell-mapqa__chip" + (rawPreviewMode === option.id ? " is-active" : "")}
                    onClick={() => setRawPreviewMode(option.id as RawPreviewMode)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            ) : null}

            <div className="shell-mapqa__chiprow" role="group" aria-label="Raw versus corrected comparison">
              {[
                { id: "raw", label: "Raw" },
                { id: "blend", label: "Blend" },
                { id: "corrected", label: "Final" },
              ].map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={"shell-mapqa__chip" + (compareMode === option.id ? " is-active" : "")}
                  onClick={() => setCompareMode(option.id as CompareMode)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="shell-mapqa__chiprow" role="group" aria-label="Baseline comparison layout">
              {[
                { id: "single", label: "Single" },
                { id: "before_after", label: "Before / After" },
              ].map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={"shell-mapqa__chip" + (layoutMode === option.id ? " is-active" : "")}
                  onClick={() => setLayoutMode(option.id as LayoutMode)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="shell-mapqa__chiprow" role="group" aria-label="QA layer toggles">
              <button type="button" className={"shell-mapqa__chip" + (showGrid ? " is-active" : "")} onClick={() => setShowGrid((current) => !current)}>
                Grid {showGrid ? "On" : "Off"}
              </button>
              <button type="button" className={"shell-mapqa__chip" + (showHydro ? " is-active" : "")} onClick={() => setShowHydro((current) => !current)}>
                Hydro {showHydro ? "On" : "Off"}
              </button>
              <button type="button" className={"shell-mapqa__chip" + (showTransport ? " is-active" : "")} onClick={() => setShowTransport((current) => !current)}>
                Transport {showTransport ? "On" : "Off"}
              </button>
              <button
                type="button"
                className={"shell-mapqa__chip" + (showHistorical ? " is-active" : "")}
                onClick={() => setShowHistorical((current) => !current)}
                disabled={!historicalAvailable}
                title={historicalAvailable ? "Toggle packaged historical overrides." : "No structured historical overrides are packaged for this theater."}
              >
                Historical {historicalAvailable ? (showHistorical ? "On" : "Off") : "N/A"}
              </button>
            </div>

            <div className="shell-mapqa__chiprow" role="group" aria-label="Screenshot workflow">
              {captureSpecs.map((capture) => (
                <button
                  key={capture.id}
                  type="button"
                  className="shell-mapqa__chip"
                  onClick={() => applyCaptureSpec(capture.id)}
                  title={`Apply ${capture.label} baseline framing`}
                >
                  {capture.label}
                </button>
              ))}
            </div>

            <div className="shell-mapqa__actionrow">
              <button
                type="button"
                className={"shell-mapqa__action" + (showCalibration ? " is-active" : "")}
                onClick={() => setShowCalibration((current) => !current)}
              >
                {showCalibration ? "Hide Developer Calibration" : "Developer Calibration"}
              </button>
              {showCalibration ? (
                <button
                  type="button"
                  className={"shell-mapqa__action" + (showExtentFrame ? " is-active" : "")}
                  onClick={() => setShowExtentFrame((current) => !current)}
                >
                  {showExtentFrame ? "Hide Extent Frame" : "Show Extent Frame"}
                </button>
              ) : null}
              {showCalibration ? (
                <button
                  type="button"
                  className="shell-mapqa__action"
                  onClick={() => setTuning(clampReadabilityTuning(MAP_READABILITY_STYLE_TOKENS.tuningDefaults))}
                >
                  Reset Tuning
                </button>
              ) : null}
              <button
                type="button"
                className="shell-mapqa__action"
                disabled={!benchmarkReady}
                onClick={() => {
                  if (benchmarkReady && tunedSvgRef.current) {
                    downloadSvg(tunedSvgRef.current, captureSpecFilename({
                      id: `${zoomPresetId}_${bookmarkId}`,
                      label: "",
                      zoomPresetId,
                      bookmarkId,
                    }));
                  }
                }}
              >
                Export SVG
              </button>
            </div>
          </div>

          <div className="shell-mapqa__note">
            {note}
          </div>

          {benchmarkRenderState.status !== "ready" ? (
            <div className={"shell-mapqa__status" + (benchmarkRenderState.status === "loading" ? "" : " is-error")}>
              {benchmarkRenderState.detail}
            </div>
          ) : null}

          {bundle && benchmarkReady ? (
            <div className="shell-mapqa__layout">
              <div className="shell-mapqa__canvasstack">
                {layoutMode === "before_after" ? (
                  <div className="shell-mapqa__compare">
                    {renderScene("baseline", clampReadabilityTuning(MAP_READABILITY_STYLE_TOKENS.phase1Baseline))}
                    {renderScene("tuned", tuning, tunedSvgRef)}
                  </div>
                ) : (
                  renderScene("tuned", tuning, tunedSvgRef)
                )}
              </div>

              <aside className="shell-mapqa__inspect">
                {showCalibration ? (
                  <div className="shell-mapqa__section">
                    <div className="shell-map__legend-subtitle">Calibration Controls</div>
                    <div className="shell-mapqa__tuning">
                      {MAP_READABILITY_TUNING_FIELDS.map((field) => {
                        const range = MAP_READABILITY_STYLE_TOKENS.tuningRanges[field.id as keyof typeof MAP_READABILITY_STYLE_TOKENS.tuningRanges];
                        const value = tuning[field.id as keyof typeof tuning];
                        return (
                          <label className="shell-mapqa__slider" key={field.id}>
                            <div className="shell-mapqa__sliderhead">
                              <span>{field.label}</span>
                              <strong>{field.format(Number(value))}</strong>
                            </div>
                            <input
                              type="range"
                              min={range.min}
                              max={range.max}
                              step={range.step}
                              value={value}
                              onChange={(event) => {
                                const nextValue = Number(event.target.value);
                                setTuning((current) => clampReadabilityTuning({ ...current, [field.id]: nextValue }));
                              }}
                            />
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ) : null}

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Benchmark Source</div>
                  <div className="shell-mapqa__summary">
                    <span className="shell-mapqa__statuspill is-pass">READY</span>
                    <span>{benchmarkRenderState.detail}</span>
                  </div>
                </div>

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Benchmark Suite</div>
                  <div className="shell-mapqa__capturelist">
                    {benchmarkSuite.map((benchmark) => (
                      <div className="shell-mapqa__capture" key={benchmark.id}>
                        <strong>{benchmark.label}</strong>
                        <span>{benchmark.zoomPresetId} / {benchmark.bookmarkId}</span>
                        <span>{benchmark.sector}</span>
                        {matchedBenchmark?.id === benchmark.id ? (
                          <span className="shell-mapqa__captureflag is-pass">Locked state matched</span>
                        ) : candidateBenchmark?.id === benchmark.id ? (
                          <span className="shell-mapqa__captureflag is-warning">Camera match only</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>

                {activeBenchmark ? (
                  <div className="shell-mapqa__section">
                    <div className="shell-map__legend-subtitle">Locked Benchmark State</div>
                    <div className="shell-mapqa__capturelist">
                      <div className="shell-mapqa__capture">
                        <strong>{activeBenchmark.label}</strong>
                        <span>{activeBenchmark.scenarioId} • {activeBenchmark.sector}</span>
                        <span>Camera {activeBenchmark.zoomPresetId} / {activeBenchmark.bookmarkId}</span>
                        <span>
                          Lock status: {matchedBenchmark?.id === activeBenchmark.id ? "Matched" : "Drifted"}
                        </span>
                        <span>
                          Overlays: Grid {activeBenchmark.overlayState?.showGrid ? "On" : "Off"} •
                          Hydro {activeBenchmark.overlayState?.showHydro ? "On" : "Off"} •
                          Transport {activeBenchmark.overlayState?.showTransport ? "On" : "Off"} •
                          Historical {activeBenchmark.overlayState?.showHistorical ? "On" : "Off"}
                        </span>
                        <span>
                          UI: {activeBenchmark.uiState?.compareMode || "corrected"} •
                          {activeBenchmark.uiState?.layoutMode || "single"} •
                          {activeBenchmark.uiState?.rawPreviewMode || "hillshade"} •
                          Calibration {(activeBenchmark.uiState?.showCalibration ?? false) ? "On" : "Off"} •
                          Extent frame {(activeBenchmark.uiState?.showExtentFrame ?? false) ? "On" : "Off"} •
                          Selected hex {activeBenchmark.uiState?.selectedHexId || "None"}
                        </span>
                        {benchmarkLockDrift.length ? (
                          <span>Drift: {benchmarkLockDrift.join(" | ")}</span>
                        ) : (
                          <span>No benchmark drift detected.</span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Benchmark Checklist</div>
                  <div className="shell-mapqa__capturelist">
                    {(activeBenchmark?.checklist || benchmarkSuite[0].checklist).map((item) => (
                      <div className="shell-mapqa__capture" key={item.id}>
                        <strong>{item.label}</strong>
                        <span>{activeBenchmark?.label || benchmarkSuite[0].label}</span>
                        <code>{item.id}</code>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Regression Captures</div>
                  <div className="shell-mapqa__capturelist">
                    {captureSpecs.map((capture) => (
                      <div className="shell-mapqa__capture" key={capture.id}>
                        <strong>{capture.label}</strong>
                        <span>{capture.zoomPresetId} / {capture.bookmarkId}</span>
                        <code>{captureSpecFilename(capture)}</code>
                        {MAP_READABILITY_REGRESSION_CAPTURE_IDS.includes(capture.id) ? (
                          <span className="shell-mapqa__captureflag">Phase 1 match</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Benchmark Readiness</div>
                  <div className="shell-mapqa__capturelist">
                    {readinessChecklist.map((item) => (
                      <div className="shell-mapqa__capture" key={item.id}>
                        <strong>{item.label}</strong>
                        <span>{item.zoomPresetId} / {item.bookmarkId}</span>
                        <span>{item.note}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Validation</div>
                  <div className="shell-mapqa__summary">
                    <span className={"shell-mapqa__statuspill " + summarizeValidationTone(bundle.validation.status)}>
                      {bundle.validation.status.toUpperCase()}
                    </span>
                    <span>{bundle.validation.summary.pass} pass</span>
                    <span>{bundle.validation.summary.warning} warn</span>
                    <span>{bundle.validation.summary.fail} fail</span>
                  </div>
                  <div className="shell-mapqa__checklist">
                    {bundle.validation.checks.map((check) => (
                      <div className="shell-mapqa__check" key={check.id}>
                        <span className={"shell-mapqa__checkdot " + summarizeValidationTone(check.status)} aria-hidden="true" />
                        <div className="shell-mapqa__checkcopy">
                          <strong>{check.label}</strong>
                          <span>{check.summary}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Selected Hex</div>
                  {selectedHex ? (
                    <div className="shell-mapqa__metagrid">
                      <div className="shell-mapqa__meta"><strong>ID</strong><span>{selectedHex.hex_id}</span></div>
                      <div className="shell-mapqa__meta"><strong>Terrain</strong><span>{selectedHex.dominant_terrain_class}</span></div>
                      <div className="shell-mapqa__meta"><strong>Elevation</strong><span>{selectedHex.elevation_m.mean} m</span></div>
                      <div className="shell-mapqa__meta"><strong>Slope</strong><span>{selectedHex.slope.class}</span></div>
                      <div className="shell-mapqa__meta"><strong>Rugged</strong><span>{selectedHex.ruggedness.class}</span></div>
                      <div className="shell-mapqa__meta"><strong>Movement</strong><span>{selectedHex.movement_cost_seed}</span></div>
                      <div className="shell-mapqa__meta"><strong>Visibility</strong><span>{selectedHex.los_visibility_proxy_seed}</span></div>
                      <div className="shell-mapqa__meta"><strong>Supply</strong><span>{selectedHex.supply_weight_seed}</span></div>
                      <div className="shell-mapqa__meta"><strong>Water</strong><span>{selectedHex.water_adjacency.has_any ? "Adjacent" : "Dry"}</span></div>
                      <div className="shell-mapqa__meta"><strong>Road</strong><span>{selectedHex.road_presence.has_any ? selectedHex.road_presence.classes.join(", ") : "None"}</span></div>
                      <div className="shell-mapqa__meta"><strong>Crossing</strong><span>{selectedHex.bridge_crossing_presence.has_any ? `${selectedHex.bridge_crossing_presence.bridge_count} bridge` : "None"}</span></div>
                      <div className="shell-mapqa__meta"><strong>Settlement</strong><span>{selectedHex.settlement_tier.name || "None"}</span></div>
                      <div className="shell-mapqa__meta"><strong>Airfield</strong><span>{selectedHex.airfield_presence.name || "None"}</span></div>
                    </div>
                  ) : (
                    <div className="shell-mapqa__status">Select a hex to inspect its metadata and provenance.</div>
                  )}
                </div>

                {selectedHex ? (
                  <div className="shell-mapqa__section">
                    <div className="shell-map__legend-subtitle">Provenance</div>
                    <div className="shell-mapqa__provenance">
                      <div className="shell-mapqa__meta"><strong>Layers</strong><span>{selectedHex.provenance.source_layers.join(", ")}</span></div>
                      <div className="shell-mapqa__meta"><strong>Sources</strong><span>{selectedHex.provenance.source_ids.join(", ")}</span></div>
                      <div className="shell-mapqa__meta"><strong>Bake Job</strong><span>{selectedHex.provenance.bake_job_id}</span></div>
                      <div className="shell-mapqa__meta"><strong>Geometry</strong><span>{selectedHex.provenance.geometry_hash}</span></div>
                      {Object.entries(selectedHex.provenance.source_feature_ids || {}).filter(([, ids]) => ids.length).map(([kind, ids]) => (
                        <div className="shell-mapqa__meta" key={kind}>
                          <strong>{kind}</strong>
                          <span>{ids.join(", ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="shell-mapqa__section">
                  <div className="shell-map__legend-subtitle">Correction Layer</div>
                  <div className="shell-mapqa__historicalcopy">
                    <strong>{bundle.historicalOverrides.available ? "Overrides packaged" : "No packaged overrides"}</strong>
                    <span>{bundle.historicalOverrides.note}</span>
                  </div>
                </div>
              </aside>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
