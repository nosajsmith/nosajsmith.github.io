import test from "node:test";
import assert from "node:assert/strict";

import {
  BASEMAP_PACKAGE_REGISTRY,
  buildPackageUrl,
  clearBasemapCaches,
  collectVisibleBasemapTiles,
  flattenBasemapTiles,
  loadBasemapQaBundle,
  resolveBasemapPackageTheater,
  resolveBasemapRoot,
  summarizeBasemapSourceState,
} from "../src/map/runtime/BasemapLoader.js";
import { MAP_BASEMAP_STYLE_SPEC, resolveBasemapStyle } from "../src/map/runtime/basemapStyle.js";

test("basemap loader resolves the packaged guadalcanal theater from current shell scenario ids", () => {
  assert.equal(BASEMAP_PACKAGE_REGISTRY[0].theaterId, "guadalcanal_1942");
  assert.equal(BASEMAP_PACKAGE_REGISTRY[1].theaterId, "korea_peninsula_coarse_v1");
  assert.equal(
    resolveBasemapPackageTheater({ scenario: { id: "00_lunga_point_slice_1942", name: "Lunga Point 1942 (Vertical Slice)" } }),
    "guadalcanal_1942",
  );
  assert.equal(
    resolveBasemapPackageTheater({ scenario: { id: "gc_1942_historical", name: "Guadalcanal 1942 Historical" } }),
    "guadalcanal_1942",
  );
  assert.equal(
    resolveBasemapPackageTheater({ scenario: { id: "inchon_mvp", name: "Inchon" } }),
    "korea_peninsula_coarse_v1",
  );
  assert.equal(
    resolveBasemapPackageTheater({ scenario: { id: "waegwan_crossing", name: "Waegwan Crossing" } }),
    "korea_peninsula_coarse_v1",
  );
  assert.equal(
    resolveBasemapPackageTheater({ scenario: { id: "mwe_unknown", name: "Unknown Theater" } }),
    null,
  );
  assert.equal(
    resolveBasemapPackageTheater({
      scenario: { id: "publisher_demo_slice", name: "Publisher Demo" },
      objectives: [{ id: "o1", name: "Seoul" }],
      ports: [{ id: "p1", name: "Inchon Harbor" }],
    }),
    "korea_peninsula_coarse_v1",
  );
});

test("basemap loader picks only tiles that intersect the current scene viewport plus padding", () => {
  const manifest = {
    bounds: { minX: -4, minY: 0 },
    prefetchTilePadding: 1,
    tiers: {
      operational: {
        tileSpan: 8,
        tiles: [
          { tileId: "0_0", tx: 0, ty: 0 },
          { tileId: "1_0", tx: 1, ty: 0 },
          { tileId: "0_1", tx: 0, ty: 1 },
          { tileId: "1_1", tx: 1, ty: 1 },
          { tileId: "2_2", tx: 2, ty: 2 },
        ],
      },
    },
  };
  const scene = {
    viewport: {
      minX: -1.5,
      maxX: 6.1,
      minY: 2.2,
      maxY: 8.8,
    },
  };

  assert.deepEqual(
    collectVisibleBasemapTiles(manifest, scene, "operational").map((tile) => tile.tileId),
    ["0_0", "1_0", "0_1", "1_1", "2_2"],
  );
});

test("basemap helpers flatten tile payloads and resolve zoom-tier style rules", () => {
  const merged = flattenBasemapTiles([
    {
      hexes: [{ hexId: "a" }],
      settlements: [{ id: "s1" }],
      airfields: [{ id: "a1" }],
      roadSegments: [{ id: "r1" }],
      railSegments: [],
    },
    {
      hexes: [{ hexId: "b" }],
      settlements: [],
      airfields: [],
      roadSegments: [],
      railSegments: [{ id: "rr1" }],
    },
  ]);

  assert.deepEqual(merged.hexes.map((entry) => entry.hexId), ["a", "b"]);
  assert.deepEqual(merged.settlements.map((entry) => entry.id), ["s1"]);
  assert.deepEqual(merged.airfields.map((entry) => entry.id), ["a1"]);
  assert.deepEqual(merged.roadSegments.map((entry) => entry.id), ["r1"]);
  assert.deepEqual(merged.railSegments.map((entry) => entry.id), ["rr1"]);

  assert.deepEqual(Object.keys(MAP_BASEMAP_STYLE_SPEC), ["far", "operational", "close"]);
  assert.equal(resolveBasemapStyle(0.8).tileTier, "far");
  assert.equal(resolveBasemapStyle(1.0).tileTier, "operational");
  assert.equal(resolveBasemapStyle(1.0).showSettlementNames, true);
  assert.equal(resolveBasemapStyle(1.0).paperGrainOpacity > 0, true);
  assert.equal(resolveBasemapStyle(1.0).terrainWashOpacity > 0, true);
  assert.equal(resolveBasemapStyle(1.0).waterTextureOpacity > 0, true);
  assert.equal(resolveBasemapStyle(1.55).tileTier, "close");

  clearBasemapCaches();
});

test("basemap loader fetches and caches the QA bundle from the packaged root", async () => {
  let fetchCount = 0;
  const fetchImpl = async (url) => {
    fetchCount += 1;
    assert.equal(url, "./map_tiles/guadalcanal_1942/qa_bundle.json");
    return {
      ok: true,
      json: async () => ({ schema: "mwe.map_data_qa_bundle.v1", theaterId: "guadalcanal_1942" }),
    };
  };

  const first = await loadBasemapQaBundle("guadalcanal_1942", { fetchImpl });
  const second = await loadBasemapQaBundle("guadalcanal_1942", { fetchImpl });

  assert.equal(first.schema, "mwe.map_data_qa_bundle.v1");
  assert.equal(second.theaterId, "guadalcanal_1942");
  assert.equal(fetchCount, 1);

  clearBasemapCaches();
});

test("basemap loader resolves packaged asset roots relative to the current app url", () => {
  const originalLocation = globalThis.location;
  Object.defineProperty(globalThis, "location", {
    configurable: true,
    value: { href: "file:///home/jason/dev/mwe/ui/dist/index.html" },
  });

  try {
    assert.equal(
      resolveBasemapRoot(),
      "file:///home/jason/dev/mwe/ui/dist/map_tiles",
    );
    assert.equal(
      buildPackageUrl("guadalcanal_1942", "manifest.json"),
      "file:///home/jason/dev/mwe/ui/dist/map_tiles/guadalcanal_1942/manifest.json",
    );
  } finally {
    if (originalLocation === undefined) {
      delete globalThis.location;
    } else {
      Object.defineProperty(globalThis, "location", {
        configurable: true,
        value: originalLocation,
      });
    }
  }
});

test("basemap runtime state requires a ready source and terrain-bearing render data", () => {
  const ready = summarizeBasemapSourceState({
    expected: true,
    manifest: { tiers: { operational: { tiles: [{ tileId: "0_0" }] } } },
    tilePayloads: [{ hexes: [{ hexId: "a" }] }],
    visibleTileCount: 1,
    fallbackAvailable: true,
  });
  assert.equal(ready.sourceStatus, "ready");
  assert.equal(ready.ready, true);
  assert.equal(ready.terrainReady, true);
  assert.equal(ready.invalid, false);

  const failed = summarizeBasemapSourceState({
    expected: true,
    manifest: { tiers: { operational: { tiles: [{ tileId: "0_0" }] } } },
    tilePayloads: [],
    visibleTileCount: 1,
    error: "Basemap fetch failed: 404 Not Found",
    fallbackAvailable: true,
  });
  assert.equal(failed.sourceStatus, "error");
  assert.equal(failed.ready, false);
  assert.equal(failed.terrainReady, false);
  assert.equal(failed.invalid, true);
  assert.equal(failed.fallbackMode, "historical_underlay");
});
