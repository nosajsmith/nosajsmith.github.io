import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { MAP_READABILITY_STYLE_TOKENS } from "../src/map/designTokens.js";
import {
  MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE,
  MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE,
  MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE,
  MAP_KOREA_OPERATIONAL_CAPTURE_SPECS,
  MAP_KOREA_OPERATIONAL_READINESS_CHECKLIST,
  MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST,
  MAP_READABILITY_BENCHMARK_PRESET,
  MAP_READABILITY_BENCHMARK_SUITE,
  MAP_KOREA_PHYSICAL_BENCHMARK_SUITE,
  MAP_KOREA_PHYSICAL_CAPTURE_SPECS,
  MAP_KOREA_PHYSICAL_READINESS_CHECKLIST,
  MAP_READABILITY_DEBUG_DEFAULTS,
  MAP_READABILITY_ACCEPTANCE_CHECKLIST,
  MAP_READABILITY_CAPTURE_SPECS,
  MAP_READABILITY_REGRESSION_CAPTURE_IDS,
  MAP_READABILITY_ZOOM_PRESETS,
  assertValidBenchmarkReadinessCapture,
  assertValidReadabilityCapture,
  benchmarkLockMismatches,
  benchmarkMatchesLockedState,
  captureHasTerrainBearingRender,
  captureHasReadabilityDebugArtifacts,
  clampReadabilityTuning,
  resolveReadabilityQaBookmarks,
  resolveReadabilityQaViewport,
} from "../src/map/readabilityQaConfig.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const qaBundle = JSON.parse(
  readFileSync(path.resolve(__dirname, "../public/map_tiles/guadalcanal_1942/qa_bundle.json"), "utf8"),
);
const finalOperationalCapture = readFileSync(
  path.resolve(__dirname, "../../docs/ui/map_readability_final/map_readability_final_operational_zoom.svg"),
  "utf8",
);
const restoredOperationalCapture = readFileSync(
  path.resolve(__dirname, "../../docs/ui/map_readability_baselines/map_readability_operational_zoom.svg"),
  "utf8",
);
const brokenBenchmarkCapture = readFileSync(
  path.resolve(__dirname, "../../docs/ui/map_benchmark_basemap_regression/map_benchmark_lunga_point_broken.svg"),
  "utf8",
);
const benchmarkReadinessManifest = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../docs/ui/map_benchmark_readiness/manifest.json"), "utf8"),
);
const benchmarkSuiteManifest = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../docs/ui/map_benchmark_suite/manifest.json"), "utf8"),
);

test("map readability QA config defines the expected zoom tiers and capture set", () => {
  assert.deepEqual(
    MAP_READABILITY_ZOOM_PRESETS.map((preset) => preset.id),
    ["far", "operational", "close"],
  );
  assert.deepEqual(
    MAP_READABILITY_CAPTURE_SPECS.map((capture) => capture.id),
    ["far_zoom", "operational_zoom", "close_zoom", "dense_label_area", "water_barrier_area", "hydro_crossing_area", "mobility_corridor_area", "hydro_settlement_mix", "relief_heavy_area"],
  );
  assert.equal(MAP_READABILITY_STYLE_TOKENS.scene.width > 0, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase1Baseline.hillshadeOpacity < MAP_READABILITY_STYLE_TOKENS.tuningDefaults.hillshadeOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase2Baseline.hydroOpacity < MAP_READABILITY_STYLE_TOKENS.tuningDefaults.hydroOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase3Baseline.gridOpacity > MAP_READABILITY_STYLE_TOKENS.tuningDefaults.gridOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase3Baseline.ghostLabelOpacity > MAP_READABILITY_STYLE_TOKENS.tuningDefaults.ghostLabelOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.tuningDefaults.transportOpacity > 0, true);
  assert.deepEqual(MAP_READABILITY_REGRESSION_CAPTURE_IDS, [
    "far_zoom",
    "operational_zoom",
    "close_zoom",
    "dense_label_area",
    "hydro_crossing_area",
    "relief_heavy_area",
  ]);
  assert.deepEqual(MAP_READABILITY_ACCEPTANCE_CHECKLIST.map((item) => item.id), [
    "relief_structure",
    "major_water_barriers",
    "crossing_points",
    "movement_corridors",
    "key_nodes",
    "selected_entities",
  ]);
  assert.deepEqual(MAP_READABILITY_BENCHMARK_READINESS_CHECKLIST.map((item) => item.id), [
    "coastline_shape",
    "inland_water_obstacles",
    "relief_structure",
    "movement_corridors",
    "crossings_and_chokepoints",
    "key_nodes",
  ]);
  assert.deepEqual(MAP_READABILITY_BENCHMARK_SUITE.map((item) => item.id), [
    "lunga_point_overview",
    "inland_relief_sector",
    "river_crossing_sector",
    "mobility_corridor_sector",
    "settlement_airfield_sector",
  ]);
  assert.equal(MAP_READABILITY_BENCHMARK_SUITE.every((item) => item.zoomPresetId === "operational"), true);
  assert.equal(MAP_READABILITY_BENCHMARK_SUITE.every((item) => item.scenarioId === "guadalcanal_1942"), true);
  assert.equal(
    MAP_READABILITY_BENCHMARK_SUITE.every((item) => JSON.stringify(item.overlayState) === JSON.stringify(MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE)),
    true,
  );
  assert.equal(
    MAP_READABILITY_BENCHMARK_SUITE.every((item) => JSON.stringify(item.uiState) === JSON.stringify(MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE)),
    true,
  );
  assert.equal(
    MAP_READABILITY_BENCHMARK_SUITE.every((item) => (
      Array.isArray(item.checklist)
      && item.checklist.length === 5
      && item.checklist.map((check) => check.id).join(",") === "relief,hydro_barriers,corridors,nodes,ui_readability"
    )),
    true,
  );
  assert.deepEqual(MAP_KOREA_PHYSICAL_CAPTURE_SPECS.map((capture) => capture.id), [
    "korea_broad_theater_view",
    "korea_mountainous_interior",
    "korea_river_coastal_area",
  ]);
  assert.deepEqual(MAP_KOREA_OPERATIONAL_CAPTURE_SPECS.map((capture) => capture.id), [
    "korea_broad_theater_view",
    "korea_major_corridor_region",
    "korea_mountainous_interior",
    "korea_river_crossing_sector",
    "korea_coastal_node_sector",
  ]);
  assert.deepEqual(MAP_KOREA_PHYSICAL_BENCHMARK_SUITE.map((item) => item.id), [
    "korea_peninsula_overview",
    "korea_mountainous_interior",
    "korea_river_coastal_sector",
  ]);
  assert.deepEqual(MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE.map((item) => item.id), [
    "korea_peninsula_overview",
    "korea_major_corridor_region",
    "korea_mountainous_interior",
    "korea_river_crossing_sector",
    "korea_coastal_node_sector",
  ]);
  assert.equal(MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE.every((item) => item.scenarioId === "korea_peninsula_coarse_v1"), true);
  assert.equal(MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE.every((item) => item.checklist.length >= 5), true);
  assert.equal(MAP_KOREA_PHYSICAL_BENCHMARK_SUITE.every((item) => item.scenarioId === "korea_peninsula_coarse_v1"), true);
  assert.equal(MAP_KOREA_PHYSICAL_BENCHMARK_SUITE.every((item) => item.checklist.length >= 5), true);
  assert.deepEqual(MAP_KOREA_PHYSICAL_READINESS_CHECKLIST.map((item) => item.id), [
    "peninsula_extent",
    "mountain_structure",
    "river_and_coast_barriers",
    "terrain_bearing_runtime",
  ]);
  assert.deepEqual(MAP_KOREA_OPERATIONAL_READINESS_CHECKLIST.map((item) => item.id), [
    "peninsula_extent",
    "corridor_readability",
    "mountain_structure",
    "river_crossings",
    "coastal_nodes",
    "key_nodes",
  ]);
  assert.deepEqual(MAP_READABILITY_BENCHMARK_PRESET, {
    compareMode: "corrected",
    layoutMode: "single",
    rawPreviewMode: "hillshade",
    showGrid: true,
    showHydro: true,
    showTransport: true,
    showHistorical: false,
  });
  assert.deepEqual(MAP_READABILITY_DEBUG_DEFAULTS, {
    showExtentFrame: false,
  });
  assert.equal(MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.selectedHexId, null);
});

test("map readability QA bookmark resolution finds the documented representative sectors", () => {
  const bookmarks = resolveReadabilityQaBookmarks(qaBundle);
  assert.deepEqual(
    bookmarks.map((bookmark) => bookmark.id),
    ["overview", "dense_labels", "water_barrier", "hydro_crossing", "mobility_corridor", "hydro_settlement", "coastal_node", "relief_mass"],
  );
  assert.equal(
    bookmarks[1].center.x !== bookmarks[0].center.x || bookmarks[1].center.y !== bookmarks[0].center.y,
    true,
  );
});

test("map readability QA viewport resolution stays bounded to the packaged theater", () => {
  const scene = resolveReadabilityQaViewport(qaBundle, "operational", "hydro_crossing");
  assert.equal(scene.viewport.minX >= qaBundle.manifest.bounds.minX, true);
  assert.equal(scene.viewport.maxX <= qaBundle.manifest.bounds.maxX, true);
  assert.equal(scene.viewport.minY >= qaBundle.manifest.bounds.minY, true);
  assert.equal(scene.viewport.maxY <= qaBundle.manifest.bounds.maxY, true);
});

test("map readability QA bundle includes terrain-bearing render data for benchmark captures", () => {
  assert.equal(Array.isArray(qaBundle.hexes), true);
  assert.equal(qaBundle.hexes.length > 0, true);
  assert.equal(qaBundle.hexes.some((hexRecord) => typeof hexRecord.dominant_terrain_class === "string" && hexRecord.dominant_terrain_class.length > 0), true);
});

test("map readability QA tuning clamp respects documented slider ranges", () => {
  const tuned = clampReadabilityTuning({
    hillshadeOpacity: 9,
    gridOpacity: -1,
    settlementIconScale: 1.22,
  });
  assert.equal(tuned.hillshadeOpacity, MAP_READABILITY_STYLE_TOKENS.tuningRanges.hillshadeOpacity.max);
  assert.equal(tuned.gridOpacity, MAP_READABILITY_STYLE_TOKENS.tuningRanges.gridOpacity.min);
  assert.equal(tuned.settlementIconScale, 1.22);
});

test("map readability captures reject leaked debug extent artifacts", () => {
  assert.equal(captureHasReadabilityDebugArtifacts('<svg><rect class="frame" /></svg>'), true);
  assert.equal(captureHasReadabilityDebugArtifacts('<svg><rect class="debugExtentFrame" data-debug-extent="true" /></svg>'), true);
  assert.equal(captureHasReadabilityDebugArtifacts('<svg><image class="shell-map__underlay-image" href="lunga_point_underlay.svg" /></svg>'), true);
  assert.equal(captureHasReadabilityDebugArtifacts('<svg><rect class="field" /></svg>'), false);
  assert.throws(
    () => assertValidReadabilityCapture('<svg><rect class="frame" /></svg>'),
    /debug extent artifacts/i,
  );
  assert.throws(
    () => assertValidReadabilityCapture('<svg><image class="shell-map__underlay-image" href="lunga_point_underlay.svg" /></svg>'),
    /debug extent artifacts/i,
  );
});

test("benchmark readiness validator requires both clean and terrain-bearing captures", () => {
  assert.equal(captureHasTerrainBearingRender('<svg><polygon class="hex" /></svg>'), true);
  assert.equal(captureHasTerrainBearingRender('<svg><rect class="field" /></svg>'), false);
  assert.throws(
    () => assertValidBenchmarkReadinessCapture('<svg><rect class="field" /></svg>'),
    /terrain-bearing map content/i,
  );
});

test("restored and current benchmark captures remain valid while broken capture fails", () => {
  assert.throws(
    () => assertValidBenchmarkReadinessCapture(brokenBenchmarkCapture),
    /debug extent artifacts/i,
  );
  assert.doesNotThrow(() => assertValidBenchmarkReadinessCapture(restoredOperationalCapture));
  assert.doesNotThrow(() => assertValidBenchmarkReadinessCapture(finalOperationalCapture));
});

test("locked final operational readability capture is free of debug extent artifacts", () => {
  assert.equal(captureHasReadabilityDebugArtifacts(finalOperationalCapture), false);
  assert.doesNotThrow(() => assertValidReadabilityCapture(finalOperationalCapture));
});

test("benchmark readiness manifest tracks broken restored and current-final captures", () => {
  assert.equal(benchmarkReadinessManifest.camera.zoomPresetId, "operational");
  assert.equal(benchmarkReadinessManifest.camera.bookmarkId, "overview");
  assert.deepEqual(
    benchmarkReadinessManifest.comparison.map((entry) => entry.id),
    ["broken", "restored", "current_final"],
  );
  assert.equal(benchmarkReadinessManifest.comparison[0].validBenchmark, false);
  assert.equal(benchmarkReadinessManifest.comparison[1].validBenchmark, true);
  assert.equal(benchmarkReadinessManifest.comparison[2].validBenchmark, true);
});

test("benchmark suite manifest tracks the locked multi-sector benchmark pack", () => {
  assert.equal(benchmarkSuiteManifest.theaterId, qaBundle.theaterId);
  assert.deepEqual(
    benchmarkSuiteManifest.suite.map((entry) => entry.id),
    MAP_READABILITY_BENCHMARK_SUITE.map((entry) => entry.id),
  );
  assert.equal(
    benchmarkSuiteManifest.suite.every((entry) => entry.zoomPresetId === "operational" && entry.scenarioId === "guadalcanal_1942"),
    true,
  );
  assert.equal(
    benchmarkSuiteManifest.suite.every((entry) => (
      entry.overlayState?.showGrid === MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE.showGrid
      && entry.overlayState?.showHydro === MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE.showHydro
      && entry.overlayState?.showTransport === MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE.showTransport
      && entry.overlayState?.showHistorical === MAP_READABILITY_BENCHMARK_LOCKED_OVERLAY_STATE.showHistorical
    )),
    true,
  );
  assert.equal(
    benchmarkSuiteManifest.suite.every((entry) => (
      entry.uiState?.compareMode === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.compareMode
      && entry.uiState?.layoutMode === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.layoutMode
      && entry.uiState?.rawPreviewMode === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.rawPreviewMode
      && entry.uiState?.showCalibration === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.showCalibration
      && entry.uiState?.showExtentFrame === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.showExtentFrame
      && entry.uiState?.selectedHexId === MAP_READABILITY_BENCHMARK_LOCKED_UI_STATE.selectedHexId
    )),
    true,
  );
  assert.equal(
    benchmarkSuiteManifest.suite.every((entry) => (
      typeof entry.description === "string"
      && entry.description.length > 0
      && Array.isArray(entry.checklist)
      && entry.checklist.map((item) => item.id).join(",") === "relief,hydro_barriers,corridors,nodes,ui_readability"
    )),
    true,
  );
});

test("benchmark lock matching requires the full camera overlay and UI state", () => {
  const benchmark = MAP_READABILITY_BENCHMARK_SUITE[0];
  const lockedState = {
    zoomPresetId: benchmark.zoomPresetId,
    bookmarkId: benchmark.bookmarkId,
    selectedHexId: benchmark.uiState.selectedHexId,
    overlayState: { ...benchmark.overlayState },
    uiState: { ...benchmark.uiState },
  };
  assert.equal(benchmarkMatchesLockedState(lockedState, benchmark), true);
  assert.deepEqual(benchmarkLockMismatches(lockedState, benchmark), []);

  const driftedState = {
    ...lockedState,
    selectedHexId: "hex:q10:r22",
    uiState: {
      ...lockedState.uiState,
      showCalibration: true,
      selectedHexId: "hex:q10:r22",
    },
  };
  assert.equal(benchmarkMatchesLockedState(driftedState, benchmark), false);
  assert.deepEqual(
    benchmarkLockMismatches(driftedState, benchmark),
    [
      "showCalibration true != false",
      "selected hex hex:q10:r22 != none",
    ],
  );
});
