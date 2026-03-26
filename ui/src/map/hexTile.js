import {
  MAP_GRID_PRESENTATION_BY_ZOOM_TIER,
  MAP_SIZE_TOKENS,
  MAP_TERRAIN_STYLES,
  getMapZoomTier,
} from "./designTokens.js";

export const HEX_TILE_VIEWBOX = Object.freeze({
  width: 64,
  height: 56,
  viewBox: "0 0 64 56",
});

export const HEX_TILE_PATHS = Object.freeze({
  outer: "M16 2 L48 2 L62 28 L48 54 L16 54 L2 28 Z",
  inner: "M18 5 L46 5 L58 28 L46 51 L18 51 L6 28 Z",
  inset: "M20 8 L44 8 L54 28 L44 48 L20 48 L10 28 Z",
  selectionTicks: "M16 2 V10 M48 2 V10 M16 54 V46 M48 54 V46 M2 28 H10 M62 28 H54",
  movePips: "M24 20 L30 24 L24 28 M40 20 L34 24 L40 28 M24 36 L30 32 L24 28 M40 36 L34 32 L40 28",
  attackCrosshair: "M32 12 V22 M32 34 V44 M16 28 H26 M38 28 H48",
  attackBrackets: "M12 18 H20 V14 M44 14 V18 H52 M12 38 H20 V42 M44 42 V38 H52",
  riverChannel: "M8 12 C16 10,18 18,24 20 S38 24,40 30 S50 42,56 44",
  riverCrossing: "M23 22 L31 28 L23 34 M41 22 L33 28 L41 34",
  gridMinor: "M12 0 L36 0 L48 20.78 L36 41.57 L12 41.57 L0 20.78 Z",
  gridMajor: "M24 0 L72 0 L96 41.57 L72 83.14 L24 83.14 L0 41.57 Z",
});

export const HEX_TILE_REFERENCE_CASES = [
  {
    id: "default",
    label: "Default",
    note: "Base terrain fill with readable grid border.",
    terrain: "plains",
  },
  {
    id: "hovered",
    label: "Hovered",
    note: "Fine dashed halo for transient focus.",
    terrain: "forest",
    hovered: true,
  },
  {
    id: "selected",
    label: "Selected",
    note: "Glow and edge ticks keep selection visible under counters.",
    terrain: "urban",
    selected: true,
  },
  {
    id: "friendly-zoc",
    label: "Friendly ZOC",
    note: "Solid outer ring shows friendly control.",
    terrain: "hills",
    friendlyZoc: true,
  },
  {
    id: "enemy-zoc",
    label: "Enemy ZOC",
    note: "Long-dash ring separates hostile influence from friendly.",
    terrain: "mountain",
    enemyZoc: true,
  },
  {
    id: "contested",
    label: "Contested",
    note: "Broken alert ring carries contested control.",
    terrain: "rough",
    friendlyZoc: true,
    enemyZoc: true,
    contested: true,
  },
  {
    id: "move-target",
    label: "Move Target",
    note: "March dash and pips mark movement destination.",
    terrain: "river",
    moveTarget: true,
  },
  {
    id: "attack-target",
    label: "Attack Target",
    note: "Crosshair and brackets mark attack intent without fill noise.",
    terrain: "water",
    attackTarget: true,
  },
  {
    id: "layered",
    label: "Layered",
    note: "Selected + enemy ZOC + attack target remains readable.",
    terrain: "forest",
    selected: true,
    enemyZoc: true,
    attackTarget: true,
  },
];

export const HEX_TERRAIN_PREVIEW_MAP = [
  { id: "t1", terrain: "water", col: 0, row: 0, label: "Inlet" },
  { id: "t2", terrain: "coast", col: 1, row: 0, label: "Beach" },
  { id: "t3", terrain: "plains", col: 2, row: 0, label: "Plain" },
  { id: "t4", terrain: "urban", col: 3, row: 0, label: "Town" },
  { id: "t5", terrain: "forest", col: 0, row: 1, label: "Forest" },
  { id: "t6", terrain: "hills", col: 1, row: 1, label: "Hills" },
  { id: "t7", terrain: "river", col: 2, row: 1, label: "Crossing" },
  { id: "t8", terrain: "rough", col: 3, row: 1, label: "Rough" },
  { id: "t9", terrain: "mountain", col: 1, row: 2, label: "Mountain" },
  { id: "t10", terrain: "forest", col: 2, row: 2, label: "Woods" },
  { id: "t11", terrain: "urban", col: 3, row: 2, label: "Built-up" },
];

const TERRAIN_ALIAS_MAP = Object.freeze(
  MAP_TERRAIN_STYLES.reduce((lookup, terrain) => {
    for (const alias of terrain.aliases) {
      lookup[alias] = terrain.id;
    }
    lookup[terrain.id] = terrain.id;
    return lookup;
  }, { river: "plains", "river-crossing": "plains" }),
);

export function normalizeHexTerrain(terrain) {
  const raw = String(terrain || "plains").trim().toLowerCase();
  return TERRAIN_ALIAS_MAP[raw] || "plains";
}

export function summarizeHexZoomPresentation(zoom) {
  const tier = getMapZoomTier(zoom);
  return {
    tier: tier.id,
    ...(MAP_GRID_PRESENTATION_BY_ZOOM_TIER[tier.id] || MAP_GRID_PRESENTATION_BY_ZOOM_TIER.operational),
  };
}

export function resolveHexTileFlags(options = {}) {
  const hovered = Boolean(options.hovered);
  const selected = Boolean(options.selected);
  const friendlyZoc = Boolean(options.friendlyZoc);
  const enemyZoc = Boolean(options.enemyZoc);
  const contested = Boolean(options.contested) || (friendlyZoc && enemyZoc);
  const moveTarget = Boolean(options.moveTarget);
  const attackTarget = Boolean(options.attackTarget);
  const disabled = Boolean(options.disabled);

  return {
    hovered,
    selected,
    friendlyZoc,
    enemyZoc,
    contested,
    moveTarget,
    attackTarget,
    disabled,
  };
}

export function buildHexTilePresentation(options = {}) {
  const flags = resolveHexTileFlags(options);
  const zoom = summarizeHexZoomPresentation(options.zoom ?? 1);
  const rawTerrain = String(options.terrain || "plains").trim().toLowerCase() || "plains";
  const terrain = normalizeHexTerrain(rawTerrain);
  const riverCrossing = Boolean(options.riverCrossing) || rawTerrain === "river" || rawTerrain === "river-crossing";
  const gridVisible = options.gridVisible !== false;
  const textureVisible = options.showTexture !== false;
  const baseMinorWidth = MAP_SIZE_TOKENS.hexOutline.minorPx * zoom.strokeScale;
  const baseMajorWidth = MAP_SIZE_TOKENS.hexOutline.majorPx * zoom.strokeScale;
  const selectedWidth = MAP_SIZE_TOKENS.hexOutline.selectedPx * zoom.strokeScale;
  const overlays = [];

  if (flags.friendlyZoc && !flags.contested) {
    overlays.push({
      id: "friendly-zoc",
      shape: "outer",
      strokeVar: "--map-token-zoc-friendly",
      strokeWidth: Number((1.38 * zoom.strokeScale).toFixed(2)),
      opacity: 0.82,
      dashArray: null,
      pattern: "solid-ring",
    });
  }

  if (flags.enemyZoc && !flags.contested) {
    overlays.push({
      id: "enemy-zoc",
      shape: "outer",
      strokeVar: "--map-token-zoc-enemy",
      strokeWidth: Number((1.42 * zoom.strokeScale).toFixed(2)),
      opacity: 0.9,
      dashArray: "8 4",
      pattern: "long-dash-ring",
    });
  }

  if (flags.contested) {
    overlays.push({
      id: "contested",
      shape: "outer",
      strokeVar: "--map-token-zoc-contested",
      strokeWidth: Number((1.58 * zoom.strokeScale).toFixed(2)),
      opacity: 0.92,
      dashArray: "3 2 9 2",
      pattern: "broken-alert-ring",
    });
  }

  if (flags.moveTarget) {
    overlays.push({
      id: "move-target",
      shape: "inner",
      strokeVar: "--map-token-faction-friendly",
      strokeWidth: Number((1.28 * zoom.strokeScale).toFixed(2)),
      opacity: 0.88,
      dashArray: "5 3",
      pattern: "march-dash",
    });
    overlays.push({
      id: "move-pips",
      shape: "movePips",
      strokeVar: "--map-token-faction-friendly",
      strokeWidth: Number((1.12 * zoom.strokeScale).toFixed(2)),
      opacity: 0.9,
      dashArray: null,
      pattern: "movement-pips",
    });
  }

  if (flags.attackTarget) {
    overlays.push({
      id: "attack-crosshair",
      shape: "attackCrosshair",
      strokeVar: "--map-token-zoc-enemy",
      strokeWidth: Number((1.24 * zoom.strokeScale).toFixed(2)),
      opacity: 0.92,
      dashArray: null,
      pattern: "crosshair",
    });
    overlays.push({
      id: "attack-brackets",
      shape: "attackBrackets",
      strokeVar: "--map-token-zoc-enemy",
      strokeWidth: Number((1.14 * zoom.strokeScale).toFixed(2)),
      opacity: 0.9,
      dashArray: null,
      pattern: "brackets",
    });
  }

  if (flags.hovered) {
    overlays.push({
      id: "hovered",
      shape: "inner",
      strokeVar: "--map-token-selection-soft",
      strokeWidth: Number((1.08 * zoom.strokeScale).toFixed(2)),
      opacity: 0.86,
      dashArray: "2 3",
      pattern: "fine-dash-halo",
    });
  }

  if (flags.selected) {
    overlays.push({
      id: "selected-glow",
      shape: "outer",
      strokeVar: "--map-token-selection-glow",
      strokeWidth: Number((selectedWidth + 3.8 * zoom.strokeScale).toFixed(2)),
      opacity: 0.42,
      dashArray: null,
      pattern: "soft-glow",
    });
    overlays.push({
      id: "selected-ring",
      shape: "outer",
      strokeVar: "--map-token-selection-stroke",
      strokeWidth: Number(selectedWidth.toFixed(2)),
      opacity: 0.96,
      dashArray: null,
      pattern: "solid-ring",
    });
    overlays.push({
      id: "selected-ticks",
      shape: "selectionTicks",
      strokeVar: "--map-token-selection-stroke",
      strokeWidth: Number((1.16 * zoom.strokeScale).toFixed(2)),
      opacity: 0.96,
      dashArray: null,
      pattern: "edge-ticks",
    });
  }

  if (riverCrossing) {
    overlays.push({
      id: "river-channel",
      shape: "riverChannel",
      strokeVar: "--map-token-terrain-river",
      strokeWidth: Number((1.64 * zoom.strokeScale).toFixed(2)),
      opacity: 0.88,
      dashArray: null,
      pattern: "river-channel",
    });
    overlays.push({
      id: "river-banks",
      shape: "riverChannel",
      strokeVar: "--map-token-terrain-river-bank",
      strokeWidth: Number((3.9 * zoom.strokeScale).toFixed(2)),
      opacity: 0.34,
      dashArray: null,
      pattern: "river-bank-halo",
    });
    overlays.push({
      id: "river-crossing",
      shape: "riverCrossing",
      strokeVar: "--map-token-text-primary",
      strokeWidth: Number((1.1 * zoom.strokeScale).toFixed(2)),
      opacity: 0.82,
      dashArray: null,
      pattern: "crossing-chevron",
    });
  }

  return {
    terrain,
    rawTerrain,
    riverCrossing,
    zoomTier: zoom.tier,
    fadeOpacity: flags.disabled ? 0.52 : zoom.fadeOpacity,
    gridVisible,
    textureVisible,
    terrainClass: `is-${terrain}`,
    minorBorderWidth: Number(baseMinorWidth.toFixed(2)),
    majorBorderWidth: Number(baseMajorWidth.toFixed(2)),
    minorBorderOpacity: gridVisible ? zoom.gridMinorOpacity : 0,
    majorBorderOpacity: gridVisible ? zoom.gridMajorOpacity : 0,
    overlays,
    flags,
  };
}
