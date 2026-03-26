import { MAP_READABILITY_STYLE_TOKENS } from "./designTokens.js";

export const MAP_READABILITY_ZOOM_PRESETS = Object.freeze([
  {
    id: "far",
    label: "Far",
    zoom: 0.8,
    focusFactor: 1,
    note: "Whole-theater scan with minimal local detail.",
  },
  {
    id: "operational",
    label: "Operational",
    zoom: 1,
    focusFactor: 0.46,
    note: "Primary readability target for the theatre screen.",
  },
  {
    id: "close",
    label: "Close",
    zoom: 1.58,
    focusFactor: 0.22,
    note: "Local label and relief stress view for problem sectors.",
  },
]);

export const MAP_READABILITY_CAPTURE_SPECS = Object.freeze([
  { id: "far_zoom", label: "Far Zoom", zoomPresetId: "far", bookmarkId: "overview" },
  { id: "operational_zoom", label: "Operational Zoom", zoomPresetId: "operational", bookmarkId: "overview" },
  { id: "close_zoom", label: "Close Zoom", zoomPresetId: "close", bookmarkId: "dense_labels" },
  { id: "dense_label_area", label: "Dense Label Area", zoomPresetId: "operational", bookmarkId: "dense_labels" },
  { id: "water_barrier_area", label: "Water Barrier Area", zoomPresetId: "operational", bookmarkId: "water_barrier" },
  { id: "hydro_crossing_area", label: "Hydro / Crossing Area", zoomPresetId: "operational", bookmarkId: "hydro_crossing" },
  { id: "mobility_corridor_area", label: "Mobility Corridor Area", zoomPresetId: "operational", bookmarkId: "mobility_corridor" },
  { id: "hydro_settlement_mix", label: "Hydro + Settlement Area", zoomPresetId: "operational", bookmarkId: "hydro_settlement" },
  { id: "relief_heavy_area", label: "Relief Heavy Area", zoomPresetId: "operational", bookmarkId: "relief_mass" },
]);

export const MAP_READABILITY_REGRESSION_CAPTURE_IDS = Object.freeze([
  "far_zoom",
  "operational_zoom",
  "close_zoom",
  "dense_label_area",
  "hydro_crossing_area",
  "relief_heavy_area",
]);

export const MAP_READABILITY_ACCEPTANCE_CHECKLIST = Object.freeze([
  {
    id: "relief_structure",
    label: "Higher ground and ridge structure read quickly",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    note: "Ridges, higher ground, and broken relief should separate before the grid does.",
  },
  {
    id: "major_water_barriers",
    label: "Major water barriers are obvious",
    zoomPresetId: "operational",
    bookmarkId: "water_barrier",
    note: "Coastline and stronger inland barriers should read as operational boundaries.",
  },
  {
    id: "crossing_points",
    label: "Crossing points can be found without opening inspectors",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    note: "Bridge and ford choke points should stand out against nearby hydro.",
  },
  {
    id: "movement_corridors",
    label: "Obvious movement corridors can be scanned at a glance",
    zoomPresetId: "operational",
    bookmarkId: "mobility_corridor",
    note: "Primary roads and corridor geometry should suggest likely movement and supply axes.",
  },
  {
    id: "key_nodes",
    label: "Settlements, airfields, and objectives are legible and distinct",
    zoomPresetId: "operational",
    bookmarkId: "dense_labels",
    note: "Operational nodes should be readable without icon bloat or label flooding.",
  },
  {
    id: "selected_entities",
    label: "Selected and high-priority entities remain immediately readable",
    zoomPresetId: "close",
    bookmarkId: "dense_labels",
    note: "Selection and priority emphasis must survive the softer grid and ghost-label pass.",
  },
]);

export const MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST = Object.freeze([
  {
    id: "coastline_shape",
    label: "Coastline and water barrier shape read immediately",
    zoomPresetId: "operational",
    bookmarkId: "water_barrier",
    note: "The coastline should frame the AOI without overwhelming the landmass.",
  },
  {
    id: "inland_water_obstacles",
    label: "Local inland water obstacles remain visible",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    note: "Local rivers, streams, and short water breaks should still register as movement problems.",
  },
  {
    id: "relief_structure",
    label: "Relief and rougher ground are readable from the land alone",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    note: "Ridges, slope breaks, and rough approaches should read before labels do the work.",
  },
  {
    id: "movement_corridors",
    label: "Likely movement and supply corridors are inferable",
    zoomPresetId: "operational",
    bookmarkId: "mobility_corridor",
    note: "Primary corridors should separate from local roads without bright civilian-map styling.",
  },
  {
    id: "crossings_and_chokepoints",
    label: "Crossings and choke points can be found quickly",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    note: "Bridge and ford nodes should stand out above the nearby barrier line.",
  },
  {
    id: "key_nodes",
    label: "Settlements, airfields, and key nodes remain legible",
    zoomPresetId: "operational",
    bookmarkId: "dense_labels",
    note: "Operational nodes should remain readable without label or icon bloat.",
  },
]);

export const MAP_READABILITY_TUNING_FIELDS = Object.freeze([
  { id: "hillshadeOpacity", label: "Hillshade opacity", format: (value) => value.toFixed(2) },
  { id: "terrainTintStrength", label: "Terrain tint", format: (value) => value.toFixed(2) },
  { id: "terrainContrast", label: "Terrain contrast", format: (value) => `${value.toFixed(2)}x` },
  { id: "hydroOpacity", label: "Hydro opacity", format: (value) => value.toFixed(2) },
  { id: "hydroWidthScale", label: "Hydro width", format: (value) => `${value.toFixed(2)}x` },
  { id: "transportOpacity", label: "Road / rail opacity", format: (value) => value.toFixed(2) },
  { id: "transportWidthScale", label: "Road / rail width", format: (value) => `${value.toFixed(2)}x` },
  { id: "gridOpacity", label: "Grid opacity", format: (value) => value.toFixed(2) },
  { id: "gridWidthScale", label: "Grid width", format: (value) => `${value.toFixed(2)}x` },
  { id: "ghostLabelOpacity", label: "Ghost label opacity", format: (value) => value.toFixed(2) },
  { id: "localLabelScale", label: "Local label scale", format: (value) => `${value.toFixed(2)}x` },
  { id: "settlementIconScale", label: "Settlement icon scale", format: (value) => `${value.toFixed(2)}x` },
  { id: "airfieldIconScale", label: "Airfield icon scale", format: (value) => `${value.toFixed(2)}x` },
  { id: "objectiveIconScale", label: "Objective icon scale", format: (value) => `${value.toFixed(2)}x` },
]);

export const MAP_READABILITY_BENCHMARK_PRESET = Object.freeze({
  compareMode: "corrected",
  layoutMode: "single",
  rawPreviewMode: "hillshade",
  showGrid: true,
  showHydro: true,
  showTransport: true,
  showHistorical: false,
});

export const MAP_READABILITY_DEBUG_DEFAULTS = Object.freeze({
  showExtentFrame: false,
});

export const MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE = Object.freeze({
  showGrid: MAP_READABILITY_BENCHMARK_PRESET.showGrid,
  showHydro: MAP_READABILITY_BENCHMARK_PRESET.showHydro,
  showTransport: MAP_READABILITY_BENCHMARK_PRESET.showTransport,
  showHistorical: MAP_READABILITY_BENCHMARK_PRESET.showHistorical,
});

export const MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE = Object.freeze({
  compareMode: MAP_READABILITY_BENCHMARK_PRESET.compareMode,
  layoutMode: MAP_READABILITY_BENCHMARK_PRESET.layoutMode,
  rawPreviewMode: MAP_READABILITY_BENCHMARK_PRESET.rawPreviewMode,
  showCalibration: false,
  showExtentFrame: MAP_READABILITY_DEBUG_DEFAULTS.showExtentFrame,
  selectedHexId: null,
});

export const MAP_READABILITY_BENCHMARK_SUITE = Object.freeze([
  {
    id: "lunga_point_overview",
    label: "Lunga Point Overview",
    scenarioId: "guadalcanal_1942",
    sector: "Coastal overview",
    sourceCaptureId: "operational_zoom",
    zoomPresetId: "operational",
    bookmarkId: "overview",
    description: "Primary locked coastal benchmark for overall land-water balance, node placement, and local corridor context.",
    overlayState: MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
    uiState: MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
    checklist: [
      { id: "relief", label: "Relief structure reads from the land first." },
      { id: "hydro_barriers", label: "Coastline and inland hydro barriers frame the AOI clearly." },
      { id: "corridors", label: "Likely movement and supply approaches are inferable." },
      { id: "nodes", label: "Settlements, airfield, and objectives remain legible." },
      { id: "ui_readability", label: "Benchmark UI stays quiet enough that the coastline and nodes do the explanatory work." },
    ],
  },
  {
    id: "inland_relief_sector",
    label: "Inland Relief Sector",
    scenarioId: "guadalcanal_1942",
    sector: "Ridge / rough ground",
    sourceCaptureId: "relief_heavy_area",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    description: "High-ruggedness inland sector used to judge ridge mass, rough approaches, and local barrier visibility.",
    overlayState: MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
    uiState: MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
    checklist: [
      { id: "relief", label: "Ridges, slope breaks, and rougher ground separate quickly." },
      { id: "hydro_barriers", label: "Local water breaks still register against the relief mass." },
      { id: "corridors", label: "Easier approaches are distinguishable from rougher routes." },
      { id: "nodes", label: "Nearby operational anchors stay visible without crowding the terrain." },
      { id: "ui_readability", label: "QA chrome stays subordinate so the inland relief signal remains the primary read." },
    ],
  },
  {
    id: "river_crossing_sector",
    label: "River Crossing Sector",
    scenarioId: "guadalcanal_1942",
    sector: "River crossing / barrier",
    sourceCaptureId: "hydro_crossing_area",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    description: "Crossing benchmark for inland barriers, bridge visibility, and local choke-point judgment.",
    overlayState: MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
    uiState: MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
    checklist: [
      { id: "relief", label: "Ground around the crossing still communicates approach difficulty." },
      { id: "hydro_barriers", label: "Barrier lines and local inland water obstacles are obvious." },
      { id: "corridors", label: "Crossing-linked approaches and corridor breaks read cleanly." },
      { id: "nodes", label: "Nearby settlements and nodes do not bury the crossing." },
      { id: "ui_readability", label: "The benchmark chrome does not compete with the crossing or nearby choke point." },
    ],
  },
  {
    id: "mobility_corridor_sector",
    label: "Mobility Corridor Sector",
    scenarioId: "guadalcanal_1942",
    sector: "Road-led corridor",
    sourceCaptureId: "mobility_corridor_area",
    zoomPresetId: "operational",
    bookmarkId: "mobility_corridor",
    description: "Operational corridor benchmark for reading likely movement and supply routes at a glance.",
    overlayState: MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
    uiState: MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
    checklist: [
      { id: "relief", label: "Terrain still explains why the corridor runs where it does." },
      { id: "hydro_barriers", label: "Water obstacles along the corridor remain easy to spot." },
      { id: "corridors", label: "Primary vs local routes separate without bright linework." },
      { id: "nodes", label: "Corridor-linked nodes are readable as operational anchors." },
      { id: "ui_readability", label: "The standard benchmark UI state leaves the corridor readable without extra clutter." },
    ],
  },
  {
    id: "settlement_airfield_sector",
    label: "Settlement / Airfield Sector",
    scenarioId: "guadalcanal_1942",
    sector: "Settlement and airfield cluster",
    sourceCaptureId: "dense_label_area",
    zoomPresetId: "operational",
    bookmarkId: "dense_labels",
    description: "Operational node benchmark for the Honiara cluster, settlement hierarchy, and airfield readability.",
    overlayState: MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
    uiState: MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
    checklist: [
      { id: "relief", label: "Underlying terrain still reads beneath the node cluster." },
      { id: "hydro_barriers", label: "Nearby water and barrier context stays visible around the nodes." },
      { id: "corridors", label: "Settlement-to-settlement and airfield access routes are inferable." },
      { id: "nodes", label: "Settlement, airfield, and objective hierarchy remains disciplined." },
      { id: "ui_readability", label: "The benchmark UI remains restrained enough that node hierarchy, not chrome, dominates the read." },
    ],
  },
]);

export const MAP_KOREA_PHYSICAL_CAPTURE_SPECS = Object.freeze([
  { id: "korea_broad_theater_view", label: "Broad Theater", zoomPresetId: "far", bookmarkId: "overview" },
  { id: "korea_mountainous_interior", label: "Mountain Interior", zoomPresetId: "operational", bookmarkId: "relief_mass" },
  { id: "korea_river_coastal_area", label: "River / Coastal", zoomPresetId: "operational", bookmarkId: "hydro_crossing" },
]);

export const MAP_KOREA_OPERATIONAL_CAPTURE_SPECS = Object.freeze([
  { id: "korea_broad_theater_view", label: "Broad Theater", zoomPresetId: "far", bookmarkId: "overview" },
  { id: "korea_major_corridor_region", label: "Major Corridor", zoomPresetId: "operational", bookmarkId: "mobility_corridor" },
  { id: "korea_mountainous_interior", label: "Mountain Interior", zoomPresetId: "operational", bookmarkId: "relief_mass" },
  { id: "korea_river_crossing_sector", label: "River Crossing", zoomPresetId: "operational", bookmarkId: "hydro_crossing" },
  { id: "korea_coastal_node_sector", label: "Coastal Node", zoomPresetId: "operational", bookmarkId: "coastal_node" },
]);

export const MAP_KOREA_PHYSICAL_READINESS_CHECKLIST = Object.freeze([
  {
    id: "peninsula_extent",
    label: "Peninsula extent reads as one coherent landmass",
    zoomPresetId: "far",
    bookmarkId: "overview",
    note: "The coast should frame the whole peninsula without runtime fallback gaps.",
  },
  {
    id: "mountain_structure",
    label: "Mountain mass and rough interior ground are readable",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    note: "The inland benchmark should make rougher approaches and higher ground obvious without extra overlays.",
  },
  {
    id: "river_and_coast_barriers",
    label: "Coastal and inland water barriers remain visible",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    note: "Major rivers, estuaries, and nearby coast should read as movement constraints in the same frame.",
  },
  {
    id: "terrain_bearing_runtime",
    label: "Packaged basemap remains terrain-bearing at all three checkpoints",
    zoomPresetId: "far",
    bookmarkId: "overview",
    note: "The QA bundle and runtime package must not degrade to an empty fallback field.",
  },
]);

export const MAP_KOREA_OPERATIONAL_READINESS_CHECKLIST = Object.freeze([
  {
    id: "peninsula_extent",
    label: "Peninsula extent remains terrain-bearing at far zoom",
    zoomPresetId: "far",
    bookmarkId: "overview",
    note: "The peninsula should still load as a coherent landmass once operational overlays are added.",
  },
  {
    id: "corridor_readability",
    label: "Major movement and supply corridors are inferable",
    zoomPresetId: "operational",
    bookmarkId: "mobility_corridor",
    note: "Primary roads and rail corridors should read cleanly above the physical map without drowning it.",
  },
  {
    id: "mountain_structure",
    label: "Mountain mass still explains harder approaches",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    note: "The added transport lines must not flatten the rough interior ground signal.",
  },
  {
    id: "river_crossings",
    label: "River barriers and crossings can be scanned quickly",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    note: "Hydro, crossings, and nearby corridors should read as one coherent obstacle picture.",
  },
  {
    id: "coastal_nodes",
    label: "Coastal nodes remain legible without swamping the shoreline",
    zoomPresetId: "operational",
    bookmarkId: "coastal_node",
    note: "Coastal settlements or airfields should sit on top of the shoreline, not replace it.",
  },
  {
    id: "key_nodes",
    label: "Settlements and airfields are visible but controlled",
    zoomPresetId: "operational",
    bookmarkId: "dense_labels",
    note: "Operational nodes should be readable without turning the peninsula map into a label field.",
  },
]);

export const MAP_KOREA_PHYSICAL_BENCHMARK_SUITE = Object.freeze([
  {
    id: "korea_peninsula_overview",
    label: "Broad Theater",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Peninsula extent",
    sourceCaptureId: "far_zoom",
    zoomPresetId: "far",
    bookmarkId: "overview",
    description: "Whole-peninsula framing used to validate coastline alignment, relief presence, and terrain-bearing runtime load.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: false,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "extent", label: "Peninsula extent renders without fallback gaps." },
      { id: "coast", label: "Coastline shape is coherent at theater scale." },
      { id: "relief", label: "Large mountain structure still reads at far zoom." },
      { id: "hydro", label: "Major coastal and river barriers remain visible." },
      { id: "local_readability", label: "The view feels like a physical map, not a tinted blank field." },
    ],
  },
  {
    id: "korea_mountainous_interior",
    label: "Mountain Interior",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Ridge / rough interior",
    sourceCaptureId: "relief_heavy_area",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    description: "Interior mountain benchmark for hillshade, tint separation, and rough-ground readability.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: false,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "relief", label: "Mountain mass and slope structure separate quickly." },
      { id: "terrain", label: "Flatter vs rougher ground is inferable from the land alone." },
      { id: "hydro", label: "Interior water features still register against the relief." },
      { id: "readability", label: "Operational zoom remains legible without heavy labels." },
      { id: "runtime", label: "The packaged style stack loads cleanly in this interior sector." },
    ],
  },
  {
    id: "korea_river_coastal_sector",
    label: "River / Coastal",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "River + littoral barrier",
    sourceCaptureId: "hydro_crossing_area",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    description: "Barrier benchmark for major river/coast interaction and local obstacle readability.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: false,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "hydro", label: "River and littoral barrier geometry read immediately." },
      { id: "coast", label: "Sea fill stays subordinate to the land and shoreline." },
      { id: "relief", label: "Nearby land still explains the approach ground." },
      { id: "barrier", label: "Local obstacle reading survives without transport overlays." },
      { id: "runtime", label: "The view remains terrain-bearing and aligned." },
    ],
  },
]);

export const MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE = Object.freeze([
  {
    id: "korea_peninsula_overview",
    label: "Broad Theater",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Peninsula extent",
    sourceCaptureId: "korea_broad_theater_view",
    zoomPresetId: "far",
    bookmarkId: "overview",
    description: "Whole-peninsula operational overview used to validate physical plus corridor layering at theater scale.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: true,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "extent", label: "Peninsula extent remains coherent and terrain-bearing." },
      { id: "coast", label: "Coastline still frames the theater after transport is added." },
      { id: "corridors", label: "Primary national corridors are visible at a glance." },
      { id: "nodes", label: "Major cities and air gateways appear without clutter." },
      { id: "readability", label: "The view still reads as a restrained operational map." },
    ],
  },
  {
    id: "korea_major_corridor_region",
    label: "Major Corridor",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Road / rail corridor",
    sourceCaptureId: "korea_major_corridor_region",
    zoomPresetId: "operational",
    bookmarkId: "mobility_corridor",
    description: "Operational corridor benchmark for primary movement and supply approaches.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: true,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "corridors", label: "Primary roads and rail lines are readable over terrain." },
      { id: "hydro", label: "Nearby barriers still shape the corridor picture." },
      { id: "nodes", label: "Corridor anchor settlements remain visible." },
      { id: "hierarchy", label: "Physical map still sits below transport rather than disappearing under it." },
      { id: "readability", label: "Likely approaches are inferable without bright linework." },
    ],
  },
  {
    id: "korea_mountainous_interior",
    label: "Mountain Interior",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Ridge / rough interior",
    sourceCaptureId: "korea_mountainous_interior",
    zoomPresetId: "operational",
    bookmarkId: "relief_mass",
    description: "Interior mountain benchmark for rough-ground readability after operational overlays are added.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: true,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "relief", label: "Mountain mass and harder approaches still dominate the read." },
      { id: "corridors", label: "Limited corridors through rough ground remain identifiable." },
      { id: "hydro", label: "Interior water obstacles still register against the relief." },
      { id: "nodes", label: "Any local nodes stay secondary to the ground." },
      { id: "readability", label: "Operational zoom remains legible without label dependence." },
    ],
  },
  {
    id: "korea_river_crossing_sector",
    label: "River Crossing",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "River barrier / crossing",
    sourceCaptureId: "korea_river_crossing_sector",
    zoomPresetId: "operational",
    bookmarkId: "hydro_crossing",
    description: "Barrier benchmark for local river obstacles, crossing candidates, and nearby corridors.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: true,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "hydro", label: "Barrier geometry reads immediately." },
      { id: "crossings", label: "Crossing candidates can be found without inspectors." },
      { id: "corridors", label: "Approach corridors to the crossing remain obvious." },
      { id: "terrain", label: "Nearby ground still explains better and worse approaches." },
      { id: "readability", label: "The combined hydro and transport picture stays restrained." },
    ],
  },
  {
    id: "korea_coastal_node_sector",
    label: "Coastal Node",
    scenarioId: "korea_peninsula_coarse_v1",
    sector: "Coastal / port-adjacent node",
    sourceCaptureId: "korea_coastal_node_sector",
    zoomPresetId: "operational",
    bookmarkId: "coastal_node",
    description: "Coastal node benchmark for shoreline, littoral corridor, and node hierarchy readability.",
    overlayState: {
      showGrid: true,
      showHydro: true,
      showTransport: true,
      showHistorical: false,
    },
    uiState: {
      compareMode: "corrected",
      layoutMode: "single",
      rawPreviewMode: "hillshade",
    },
    checklist: [
      { id: "coast", label: "Shoreline remains readable beneath node and corridor overlays." },
      { id: "nodes", label: "Coastal settlement or airfield anchors are easy to spot." },
      { id: "corridors", label: "Littoral corridors read without drowning the coast." },
      { id: "hydro", label: "Local coastal and inland barriers still frame the node." },
      { id: "readability", label: "The view remains serious and restrained." },
    ],
  },
]);

function metricNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function averagePoint(rows) {
  if (!rows.length) {
    return null;
  }
  const totalWeight = rows.reduce((sum, row) => sum + (row.weight || 1), 0) || rows.length;
  return rows.reduce((point, row) => {
    const weight = row.weight || 1;
    point.x += row.x * weight;
    point.y += row.y * weight;
    return point;
  }, { x: 0, y: 0, totalWeight });
}

function distanceSq(left, right) {
  const dx = metricNumber(left?.x) - metricNumber(right?.x);
  const dy = metricNumber(left?.y) - metricNumber(right?.y);
  return dx * dx + dy * dy;
}

function finalizeAverage(point) {
  if (!point || !point.totalWeight) {
    return null;
  }
  return {
    x: point.x / point.totalWeight,
    y: point.y / point.totalWeight,
  };
}

function boundsCenter(bounds) {
  return {
    x: (metricNumber(bounds?.minX) + metricNumber(bounds?.maxX)) / 2,
    y: (metricNumber(bounds?.minY) + metricNumber(bounds?.maxY)) / 2,
  };
}

function rankedCrossingHex(hexes = []) {
  return [...hexes]
    .filter((hexRecord) => Boolean(hexRecord?.river_crossing_flags?.has_any))
    .sort((left, right) => {
      const leftBridge = metricNumber(left?.bridge_crossing_presence?.bridge_count);
      const rightBridge = metricNumber(right?.bridge_crossing_presence?.bridge_count);
      const leftRoad = metricNumber(left?.road_presence?.length_m);
      const rightRoad = metricNumber(right?.road_presence?.length_m);
      return rightBridge - leftBridge || rightRoad - leftRoad || metricNumber(right?.q) - metricNumber(left?.q);
    })[0] || null;
}

function rankedReliefHexes(hexes = []) {
  return [...hexes]
    .sort((left, right) => {
      const leftScore = metricNumber(left?.ruggedness?.mean) * 0.72 + metricNumber(left?.elevation_m?.mean) * 0.08;
      const rightScore = metricNumber(right?.ruggedness?.mean) * 0.72 + metricNumber(right?.elevation_m?.mean) * 0.08;
      return rightScore - leftScore;
    })
    .slice(0, 18);
}

function rankedBarrierHexes(hexes = []) {
  return [...hexes]
    .filter((hexRecord) => (
      Boolean(hexRecord?.coastline_flag)
      || Boolean(hexRecord?.river_presence?.major_river)
      || Boolean(hexRecord?.river_presence?.minor_river)
    ))
    .sort((left, right) => {
      const leftScore = (left?.coastline_flag ? 2.2 : 0) + (left?.river_presence?.major_river ? 2.4 : 0) + (left?.river_presence?.minor_river ? 1.1 : 0);
      const rightScore = (right?.coastline_flag ? 2.2 : 0) + (right?.river_presence?.major_river ? 2.4 : 0) + (right?.river_presence?.minor_river ? 1.1 : 0);
      return rightScore - leftScore;
    })
    .slice(0, 28);
}

function rankedCoastHexes(hexes = []) {
  return [...hexes]
    .filter((hexRecord) => Boolean(hexRecord?.coastline_flag))
    .sort((left, right) => metricNumber(right?.q) - metricNumber(left?.q))
    .slice(0, 28);
}

function roadSegmentWeight(segment) {
  const raw = String(segment?.class || "").trim().toLowerCase();
  if (raw === "primary_road") {
    return 4;
  }
  if (raw === "secondary_road") {
    return 2.4;
  }
  if (raw === "tertiary_road") {
    return 1.8;
  }
  return 1.2;
}

export function resolveReadabilityQaBookmarks(bundle) {
  const bounds = bundle?.manifest?.bounds || { minX: -4, maxX: 31, minY: 0, maxY: 74 };
  const center = boundsCenter(bounds);
  const settlements = Array.isArray(bundle?.operationalPreview?.settlements) ? bundle.operationalPreview.settlements : [];
  const airfields = Array.isArray(bundle?.operationalPreview?.airfields) ? bundle.operationalPreview.airfields : [];
  const hexes = Array.isArray(bundle?.hexes) ? bundle.hexes : [];

  const denseAverage = finalizeAverage(averagePoint([
    ...settlements.map((settlement) => ({
      x: metricNumber(settlement.q),
      y: metricNumber(settlement.r),
      weight: Math.max(1, metricNumber(settlement.importance)),
    })),
    ...airfields.map((airfield) => ({
      x: metricNumber(airfield.q),
      y: metricNumber(airfield.r),
      weight: Math.max(2, metricNumber(airfield.importance) + 1),
    })),
  ]));

  const crossingHex = rankedCrossingHex(hexes);
  const leadingBarrierHex = rankedBarrierHexes(hexes)[0] || null;
  const coastHexes = rankedCoastHexes(hexes);
  const reliefAverage = finalizeAverage(averagePoint(
    rankedReliefHexes(hexes).map((hexRecord) => ({
      x: metricNumber(hexRecord.q),
      y: metricNumber(hexRecord.r),
      weight: Math.max(1, metricNumber(hexRecord.ruggedness?.mean)),
    })),
  ));
  const barrierAverage = finalizeAverage(averagePoint(
    rankedBarrierHexes(hexes).map((hexRecord) => ({
      x: metricNumber(hexRecord.q),
      y: metricNumber(hexRecord.r),
      weight: (hexRecord?.coastline_flag ? 2.2 : 0) + (hexRecord?.river_presence?.major_river ? 2.4 : 0) + (hexRecord?.river_presence?.minor_river ? 1.1 : 0),
    })),
  ));
  const coastAverage = finalizeAverage(averagePoint(
    coastHexes.map((hexRecord) => ({
      x: metricNumber(hexRecord.q),
      y: metricNumber(hexRecord.r),
      weight: 1.6,
    })),
  ));
  const corridorSegments = (() => {
    const roadSegments = Array.isArray(bundle?.operationalPreview?.roadSegments) ? bundle.operationalPreview.roadSegments : [];
    if (!crossingHex) {
      return roadSegments;
    }
    const local = roadSegments.filter((segment) => {
      const midpoint = {
        x: (metricNumber(segment?.from?.x) + metricNumber(segment?.to?.x)) / 2,
        y: (metricNumber(segment?.from?.y) + metricNumber(segment?.to?.y)) / 2,
      };
      return distanceSq(midpoint, { x: metricNumber(crossingHex.q), y: metricNumber(crossingHex.r) }) <= 12 * 12;
    });
    return local.length >= 12 ? local : roadSegments;
  })();
  const corridorAverage = finalizeAverage(averagePoint(
    corridorSegments.map((segment) => ({
      x: (metricNumber(segment?.from?.x) + metricNumber(segment?.to?.x)) / 2,
      y: (metricNumber(segment?.from?.y) + metricNumber(segment?.to?.y)) / 2,
      weight: roadSegmentWeight(segment),
    })),
  ));
  const hydroAnchorPoints = rankedBarrierHexes(hexes).map((hexRecord) => ({ x: metricNumber(hexRecord.q), y: metricNumber(hexRecord.r) }));
  const coastAnchorPoints = coastHexes.map((hexRecord) => ({ x: metricNumber(hexRecord.q), y: metricNumber(hexRecord.r) }));
  const hydroSettlement = settlements
    .map((settlement) => ({
      settlement,
      distance: hydroAnchorPoints.length
        ? Math.min(...hydroAnchorPoints.map((point) => distanceSq(point, { x: metricNumber(settlement.q), y: metricNumber(settlement.r) })))
        : Number.POSITIVE_INFINITY,
    }))
    .sort((left, right) => left.distance - right.distance || metricNumber(right.settlement.importance) - metricNumber(left.settlement.importance))[0];
  const coastalCandidates = [
    ...settlements.map((settlement) => ({
      id: settlement.id,
      x: metricNumber(settlement.q),
      y: metricNumber(settlement.r),
      weight: Math.max(1, metricNumber(settlement.importance)),
      distance: coastAnchorPoints.length
        ? Math.min(...coastAnchorPoints.map((point) => distanceSq(point, { x: metricNumber(settlement.q), y: metricNumber(settlement.r) })))
        : Number.POSITIVE_INFINITY,
    })),
    ...airfields.map((airfield) => ({
      id: airfield.id,
      x: metricNumber(airfield.q),
      y: metricNumber(airfield.r),
      weight: Math.max(2, metricNumber(airfield.importance) + 1),
      distance: coastAnchorPoints.length
        ? Math.min(...coastAnchorPoints.map((point) => distanceSq(point, { x: metricNumber(airfield.q), y: metricNumber(airfield.r) })))
        : Number.POSITIVE_INFINITY,
    })),
  ]
    .sort((left, right) => left.distance - right.distance || right.weight - left.weight)
    .slice(0, 6);
  const coastalNodeAverage = finalizeAverage(averagePoint(coastalCandidates));

  return [
    {
      id: "overview",
      label: "Overview",
      description: "Whole-theater framing for broad readability checks.",
      center,
      spanMultiplier: 1,
    },
    {
      id: "dense_labels",
      label: "Dense Labels",
      description: "Settlements, airfield, and local names around the Honiara cluster.",
      center: denseAverage || center,
      spanMultiplier: 0.58,
    },
    {
      id: "water_barrier",
      label: "Water Barrier",
      description: "Coastline and major-water barrier readability sector.",
      center: barrierAverage || center,
      spanMultiplier: 0.42,
    },
    {
      id: "hydro_crossing",
      label: "Hydro Crossing",
      description: "Bridge and river corridor view for crossing readability.",
      center: crossingHex
        ? { x: metricNumber(crossingHex.q), y: metricNumber(crossingHex.r) }
        : leadingBarrierHex
          ? { x: metricNumber(leadingBarrierHex.q), y: metricNumber(leadingBarrierHex.r) }
          : barrierAverage || center,
      spanMultiplier: 0.4,
    },
    {
      id: "mobility_corridor",
      label: "Mobility Corridor",
      description: "Primary road corridor framing for route and supply readability.",
      center: corridorAverage || center,
      spanMultiplier: 0.38,
    },
    {
      id: "hydro_settlement",
      label: "Hydro Settlement",
      description: "Mixed hydro plus settlement cluster for choke-point readability.",
      center: hydroSettlement ? { x: metricNumber(hydroSettlement.settlement.q), y: metricNumber(hydroSettlement.settlement.r) } : denseAverage || center,
      spanMultiplier: 0.34,
    },
    {
      id: "coastal_node",
      label: "Coastal Node",
      description: "Coastal settlement or airfield cluster near the shoreline.",
      center: coastalNodeAverage || coastAverage || denseAverage || center,
      spanMultiplier: 0.34,
    },
    {
      id: "relief_mass",
      label: "Relief Mass",
      description: "High-ruggedness terrain for hillshade and contour checks.",
      center: reliefAverage || center,
      spanMultiplier: 0.34,
    },
  ];
}

export function resolveReadabilityQaViewport(bundle, zoomPresetId, bookmarkId) {
  const scene = MAP_READABILITY_STYLE_TOKENS.scene;
  const bounds = bundle?.manifest?.bounds || { minX: -4, maxX: 31, minY: 0, maxY: 74 };
  const zoomPreset = MAP_READABILITY_ZOOM_PRESETS.find((preset) => preset.id === zoomPresetId) || MAP_READABILITY_ZOOM_PRESETS[1];
  const bookmarks = resolveReadabilityQaBookmarks(bundle);
  const bookmark = bookmarks.find((entry) => entry.id === bookmarkId) || bookmarks[0];
  const worldWidth = Math.max(8, metricNumber(bounds.maxX) - metricNumber(bounds.minX));
  const worldHeight = Math.max(8, metricNumber(bounds.maxY) - metricNumber(bounds.minY));
  const aspect = scene.width / scene.height;

  let spanX = worldWidth * zoomPreset.focusFactor * bookmark.spanMultiplier;
  let spanY = worldHeight * zoomPreset.focusFactor * bookmark.spanMultiplier;
  spanX = Math.max(spanX, spanY * aspect);
  spanY = Math.max(spanY, spanX / aspect);

  const halfX = spanX / 2;
  const halfY = spanY / 2;
  const clampedCenterX = clamp(bookmark.center.x, metricNumber(bounds.minX) + halfX, metricNumber(bounds.maxX) - halfX);
  const clampedCenterY = clamp(bookmark.center.y, metricNumber(bounds.minY) + halfY, metricNumber(bounds.maxY) - halfY);

  return {
    viewport: {
      minX: clampedCenterX - halfX,
      maxX: clampedCenterX + halfX,
      minY: clampedCenterY - halfY,
      maxY: clampedCenterY + halfY,
    },
    width: scene.width,
    height: scene.height,
    inset: scene.inset,
    zoomPreset,
    bookmark,
  };
}

export function clampReadabilityTuning(partial = {}) {
  const defaults = MAP_READABILITY_STYLE_TOKENS.tuningDefaults;
  const ranges = MAP_READABILITY_STYLE_TOKENS.tuningRanges;
  const next = { ...defaults };
  for (const [id, range] of Object.entries(ranges)) {
    const raw = Object.prototype.hasOwnProperty.call(partial, id) ? Number(partial[id]) : defaults[id];
    next[id] = clamp(Number.isFinite(raw) ? raw : defaults[id], range.min, range.max);
  }
  return next;
}

export function captureSpecFilename(spec) {
  return `map_readability_${spec.id}.svg`;
}

export function benchmarkSuiteFilename(spec) {
  return `map_benchmark_${spec.id}.svg`;
}

export function benchmarkLockMismatches(currentState, benchmarkSpec) {
  const mismatches = [];
  const expectedOverlayState = benchmarkSpec?.overlayState || {};
  const expectedUiState = benchmarkSpec?.uiState || {};
  const currentOverlayState = currentState?.overlayState || {};
  const currentUiState = currentState?.uiState || {};

  if (currentState?.zoomPresetId !== benchmarkSpec?.zoomPresetId) {
    mismatches.push(`zoom ${currentState?.zoomPresetId || "unset"} != ${benchmarkSpec?.zoomPresetId || "unset"}`);
  }
  if (currentState?.bookmarkId !== benchmarkSpec?.bookmarkId) {
    mismatches.push(`bookmark ${currentState?.bookmarkId || "unset"} != ${benchmarkSpec?.bookmarkId || "unset"}`);
  }

  for (const overlayId of ["showGrid", "showHydro", "showTransport", "showHistorical"]) {
    if ((currentOverlayState?.[overlayId] ?? false) !== (expectedOverlayState?.[overlayId] ?? false)) {
      mismatches.push(`${overlayId} ${currentOverlayState?.[overlayId] ? "on" : "off"} != ${expectedOverlayState?.[overlayId] ? "on" : "off"}`);
    }
  }

  for (const uiId of ["compareMode", "layoutMode", "rawPreviewMode", "showCalibration", "showExtentFrame"]) {
    if ((currentUiState?.[uiId] ?? null) !== (expectedUiState?.[uiId] ?? null)) {
      mismatches.push(`${uiId} ${currentUiState?.[uiId] ?? "unset"} != ${expectedUiState?.[uiId] ?? "unset"}`);
    }
  }

  if ((currentState?.selectedHexId ?? null) !== (expectedUiState?.selectedHexId ?? null)) {
    mismatches.push(`selected hex ${currentState?.selectedHexId || "none"} != ${expectedUiState?.selectedHexId || "none"}`);
  }

  return mismatches;
}

export function benchmarkMatchesLockedState(currentState, benchmarkSpec) {
  return benchmarkLockMismatches(currentState, benchmarkSpec).length === 0;
}

export function captureHasReadabilityDebugArtifacts(svgText) {
  const source = String(svgText || "");
  return /class=(["'])(?:frame|debugExtentFrame)\1/.test(source)
    || source.includes("shell-mapqa__extent-frame")
    || source.includes("data-debug-extent=\"true\"")
    || source.includes("shell-map__underlay-image")
    || source.includes("lunga_point_underlay");
}

export function captureHasTerrainBearingRender(svgText) {
  const source = String(svgText || "");
  return /<polygon class="hex"/.test(source)
    || source.includes("shell-map__basemap-hex-fill")
    || source.includes("shell-mapqa__hex--terrain");
}

export function assertValidReadabilityCapture(svgText) {
  if (captureHasReadabilityDebugArtifacts(svgText)) {
    throw new Error("Readability capture is invalid: debug extent artifacts are enabled.");
  }
}

export function assertValidBenchmarkReadinessCapture(svgText) {
  assertValidReadabilityCapture(svgText);
  if (!captureHasTerrainBearingRender(svgText)) {
    throw new Error("Benchmark capture is invalid: no terrain-bearing map content was rendered.");
  }
}
