const DEFAULT_BASEMAP_ROOT = "./map_tiles";

export const BASEMAP_PACKAGE_REGISTRY = Object.freeze([
  {
    theaterId: "guadalcanal_1942",
    aliasTokens: ["guadalcanal", "gc_1942", "lunga", "henderson", "tulagi", "kokumbona"],
  },
  {
    theaterId: "korea_peninsula_coarse_v1",
    aliasTokens: ["korea", "korean war", "waegwan", "naktong", "nakdong", "seoul", "inchon", "pusan"],
  },
]);

const manifestCache = new Map();
const tileCache = new Map();
const qaBundleCache = new Map();

function normalizeSearchText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function packageEntryForSnapshot(snapshot) {
  const searchText = normalizeSearchText(
    `${snapshot?.scenario?.id ?? ""} ${snapshot?.scenario?.name ?? ""}`,
  );
  if (!searchText) {
    return null;
  }
  return BASEMAP_PACKAGE_REGISTRY.find((entry) => entry.aliasTokens.some((token) => searchText.includes(token))) || null;
}

export function resolveBasemapRoot(options = {}) {
  const explicitRoot = typeof options === "string"
    ? options
    : options && typeof options === "object"
      ? options.root
      : null;
  if (explicitRoot) {
    return String(explicitRoot).replace(/\/+$/, "");
  }
  const baseHref = (options && typeof options === "object" && options.baseHref)
    || globalThis.document?.baseURI
    || globalThis.location?.href
    || null;
  if (baseHref) {
    try {
      return new URL("map_tiles", baseHref).toString().replace(/\/+$/, "");
    } catch {
      // Fall through to the portable relative default below.
    }
  }
  return DEFAULT_BASEMAP_ROOT;
}

export function buildPackageUrl(theaterId, suffix, root = null) {
  const normalizedRoot = resolveBasemapRoot(root);
  return `${normalizedRoot}/${theaterId}/${suffix.replace(/^\/+/, "")}`;
}

async function fetchJson(url, fetchImpl) {
  const response = await fetchImpl(url);
  if (!response.ok) {
    throw new Error(`Basemap fetch failed: ${response.status} ${response.statusText} for ${url}`);
  }
  return response.json();
}

export function resolveBasemapPackageTheater(snapshot) {
  return packageEntryForSnapshot(snapshot)?.theaterId || null;
}

export async function loadBasemapManifest(theaterId, options = {}) {
  if (!theaterId) {
    return null;
  }
  const resolvedRoot = resolveBasemapRoot(options);
  const cacheKey = `${resolvedRoot}:${theaterId}`;
  if (manifestCache.has(cacheKey)) {
    return manifestCache.get(cacheKey);
  }
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    throw new Error("Basemap fetch implementation is unavailable");
  }
  const manifest = await fetchJson(buildPackageUrl(theaterId, "manifest.json", resolvedRoot), fetchImpl);
  manifestCache.set(cacheKey, manifest);
  return manifest;
}

export async function loadBasemapQaBundle(theaterId, options = {}) {
  if (!theaterId) {
    return null;
  }
  const resolvedRoot = resolveBasemapRoot(options);
  const cacheKey = `${resolvedRoot}:${theaterId}:qa`;
  if (qaBundleCache.has(cacheKey)) {
    return qaBundleCache.get(cacheKey);
  }
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    throw new Error("Basemap fetch implementation is unavailable");
  }
  const bundle = await fetchJson(buildPackageUrl(theaterId, "qa_bundle.json", resolvedRoot), fetchImpl);
  qaBundleCache.set(cacheKey, bundle);
  return bundle;
}

export function collectVisibleBasemapTiles(manifest, scene, tierId) {
  const tier = manifest?.tiers?.[tierId];
  if (!tier || !scene?.viewport) {
    return [];
  }
  const bounds = manifest.bounds || { minX: 0, minY: 0 };
  const tileSpan = Number(tier.tileSpan || 1);
  const padding = Number(manifest.prefetchTilePadding || 0);
  const minTx = Math.floor((scene.viewport.minX - bounds.minX) / tileSpan) - padding;
  const maxTx = Math.floor((scene.viewport.maxX - bounds.minX) / tileSpan) + padding;
  const minTy = Math.floor((scene.viewport.minY - bounds.minY) / tileSpan) - padding;
  const maxTy = Math.floor((scene.viewport.maxY - bounds.minY) / tileSpan) + padding;

  return (tier.tiles || []).filter((tile) => (
    tile.tx >= minTx
    && tile.tx <= maxTx
    && tile.ty >= minTy
    && tile.ty <= maxTy
  ));
}

export async function loadBasemapTiles(theaterId, tileRefs, tierId, options = {}) {
  if (!theaterId || !tileRefs?.length) {
    return [];
  }
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    throw new Error("Basemap fetch implementation is unavailable");
  }

  const root = resolveBasemapRoot(options);
  return Promise.all(tileRefs.map(async (tileRef) => {
    const cacheKey = `${root}:${theaterId}:${tierId}:${tileRef.tileId}`;
    if (tileCache.has(cacheKey)) {
      return tileCache.get(cacheKey);
    }
    const payload = await fetchJson(buildPackageUrl(theaterId, `${tierId}/${tileRef.tileId}.json`, root), fetchImpl);
    tileCache.set(cacheKey, payload);
    return payload;
  }));
}

export function hasRenderableBasemapTerrain(tilePayloads) {
  return flattenBasemapTiles(tilePayloads).hexes.length > 0;
}

export function summarizeBasemapSourceState(options = {}) {
  const expected = Boolean(options.expected);
  const manifest = options.manifest || null;
  const tilePayloads = Array.isArray(options.tilePayloads) ? options.tilePayloads : [];
  const visibleTileCount = Number(options.visibleTileCount || 0);
  const error = String(options.error || "").trim();
  const fallbackAvailable = Boolean(options.fallbackAvailable);
  const terrainReady = hasRenderableBasemapTerrain(tilePayloads);

  if (!expected) {
    return {
      sourceStatus: "unavailable",
      ready: false,
      terrainReady: false,
      invalid: false,
      fallbackMode: "none",
      developerMessage: "No packaged basemap is registered for the current scenario family.",
    };
  }

  if (error) {
    return {
      sourceStatus: "error",
      ready: false,
      terrainReady: false,
      invalid: true,
      fallbackMode: fallbackAvailable ? "historical_underlay" : "none",
      developerMessage: error,
    };
  }

  if (!manifest) {
    return {
      sourceStatus: "loading",
      ready: false,
      terrainReady: false,
      invalid: false,
      fallbackMode: "none",
      developerMessage: "Loading packaged basemap manifest.",
    };
  }

  if (visibleTileCount > 0 && !terrainReady) {
    return {
      sourceStatus: "loading",
      ready: false,
      terrainReady: false,
      invalid: false,
      fallbackMode: fallbackAvailable ? "historical_underlay" : "none",
      developerMessage: "Packaged basemap tiles did not yield any terrain-bearing render data for the current view.",
    };
  }

  return {
    sourceStatus: "ready",
    ready: terrainReady,
    terrainReady,
    invalid: !terrainReady,
    fallbackMode: "none",
    developerMessage: terrainReady
      ? "Packaged basemap tiles are ready and terrain-bearing features are present."
      : "Packaged basemap manifest loaded but no terrain-bearing data is available.",
  };
}

export function flattenBasemapTiles(tilePayloads) {
  const merged = {
    hexes: [],
    settlements: [],
    airfields: [],
    roadSegments: [],
    railSegments: [],
  };

  for (const tile of tilePayloads || []) {
    merged.hexes.push(...(tile?.hexes || []));
    merged.settlements.push(...(tile?.settlements || []));
    merged.airfields.push(...(tile?.airfields || []));
    merged.roadSegments.push(...(tile?.roadSegments || []));
    merged.railSegments.push(...(tile?.railSegments || []));
  }

  return merged;
}

export function clearBasemapCaches() {
  manifestCache.clear();
  tileCache.clear();
  qaBundleCache.clear();
}
