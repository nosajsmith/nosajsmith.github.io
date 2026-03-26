import test from "node:test";
import assert from "node:assert/strict";

import {
  MAP_AIRFIELD_TIER_TOKENS,
  MAP_ANIMATION_TOKENS,
  MAP_BASEMAP_TOKENS,
  MAP_BRANCH_PALETTE,
  MAP_COUNTER_OVERLAY_TOKENS,
  MAP_COUNTER_FRAME_TOKENS,
  MAP_COUNTER_LABEL_POLICY,
  MAP_GRID_PRESENTATION_BY_ZOOM_TIER,
  MAP_GREASE_MARKUP_TOKENS,
  MAP_GLOW_TOKENS,
  MAP_LABEL_VISIBILITY_POLICY,
  MAP_LABEL_STYLE_TOKENS,
  MAP_FACTION_PALETTE,
  MAP_OPERATIONAL_OVERLAY_TOKENS,
  MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER,
  MAP_READABILITY_STYLE_TOKENS,
  MAP_RELIEF_BAND_PALETTE,
  MAP_SIGNAL_COLORS,
  MAP_STROKE_WIDTH_BY_ZOOM_TIER,
  MAP_SETTLEMENT_TIER_TOKENS,
  MAP_SIZE_TOKENS,
  MAP_STATE_TOKENS,
  MAP_TERRAIN_STYLES,
  MAP_ZOOM_TIERS,
} from "../src/map/designTokens.js";

test("map design tokens define the core faction and state language", () => {
  assert.deepEqual(
    MAP_FACTION_PALETTE.map((token) => token.id),
    ["friendly", "enemy", "neutral"],
  );
  assert.deepEqual(
    MAP_STATE_TOKENS.map((token) => token.id),
    ["hovered", "selected", "contested", "disabled", "zoc-friendly", "zoc-enemy", "zoc-contested", "move-target", "attack-target"],
  );
  assert.deepEqual(
    MAP_BRANCH_PALETTE.map((token) => token.id),
    ["army", "marines", "air_force", "navy", "partner", "enemy", "neutral", "unknown"],
  );
});

test("map design tokens define documented zoom tiers with target pixel sizes", () => {
  assert.deepEqual(
    MAP_ZOOM_TIERS.map((tier) => tier.id),
    ["far", "operational", "close"],
  );
  for (const tier of MAP_ZOOM_TIERS) {
    assert.ok(typeof tier.min === "number" && typeof tier.max === "number");
    assert.ok(typeof tier.targetUnitBoxPx === "string" && tier.targetUnitBoxPx.length > 0);
    assert.ok(typeof tier.targetCityIconPx === "number" && tier.targetCityIconPx > 0);
    assert.ok(typeof tier.targetOverlayPx === "number" && tier.targetOverlayPx > 0);
    assert.ok(typeof tier.labelDensity === "string" && tier.labelDensity.length > 0);
  }
});

test("map design tokens define shared size and animation standards", () => {
  assert.equal(MAP_SIZE_TOKENS.unitIconBox.widthPx, 36);
  assert.equal(MAP_SIZE_TOKENS.unitIconBox.heightPx, 20);
  assert.equal(MAP_SIZE_TOKENS.cityIcon.diameterPx, 16);
  assert.equal(MAP_SIZE_TOKENS.airfieldIcon.widthPx, 20);
  assert.deepEqual(
    MAP_AIRFIELD_TIER_TOKENS.map((entry) => entry.id),
    ["major_airbase", "operational_airfield", "minor_airstrip"],
  );
  assert.equal(MAP_SIZE_TOKENS.overlayMarkers.locRingRadiusPx, 24);
  assert.deepEqual(
    MAP_SETTLEMENT_TIER_TOKENS.map((entry) => entry.id),
    ["capital", "major_city", "city", "town", "village"],
  );
  assert.equal(MAP_COUNTER_FRAME_TOKENS.company.widthPx < MAP_COUNTER_FRAME_TOKENS.corps.widthPx, true);
  assert.equal(MAP_COUNTER_FRAME_TOKENS.division.treatment, "double frame + header rule");
  assert.deepEqual(MAP_COUNTER_OVERLAY_TOKENS.priority, ["critical", "engaged", "moving", "idle"]);
  assert.deepEqual(MAP_COUNTER_LABEL_POLICY.map((entry) => entry.id), ["far", "operational", "close"]);
  assert.deepEqual(MAP_LABEL_VISIBILITY_POLICY.map((entry) => entry.id), ["far", "operational", "close"]);
  assert.deepEqual(MAP_SIGNAL_COLORS.map((entry) => entry.id), ["supply", "command", "fog", "weather"]);
  assert.deepEqual(MAP_GLOW_TOKENS.map((entry) => entry.id), ["selection", "engaged", "planning"]);
  assert.equal(MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplyMarker > MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplySourceCore, true);
  assert.ok(MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelContact > MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelCore);
  assert.deepEqual(Object.keys(MAP_OPERATIONAL_OVERLAY_TOKENS.movement), ["move", "advance", "attack", "fallback", "committed", "planned", "waypoint"]);
  assert.deepEqual(Object.keys(MAP_OPERATIONAL_OVERLAY_TOKENS.frontline), ["line", "contested", "hot", "quiet", "segmentHot", "segmentContested", "segmentQuiet", "breakthrough", "thin"]);
  assert.deepEqual(Object.keys(MAP_OPERATIONAL_OVERLAY_TOKENS.objectives), ["primary", "secondary", "supply", "political", "strategic", "contested"]);
  assert.deepEqual(Object.keys(MAP_OPERATIONAL_OVERLAY_TOKENS.fogIntel), ["wash", "hatch", "unseen", "stale", "spotted", "confirmed", "uncertain", "hidden"]);
  assert.deepEqual(Object.keys(MAP_GREASE_MARKUP_TOKENS.styles), ["amber", "offwhite", "blue"]);
  assert.deepEqual(Object.keys(MAP_GREASE_MARKUP_TOKENS.lineWidthPx), ["freehand", "straight", "arrow", "front", "circle", "box", "defensive", "fallback", "selection"]);
  assert.equal(MAP_OPERATIONAL_OVERLAY_TOKENS.lineWidthPx.movement > MAP_OPERATIONAL_OVERLAY_TOKENS.lineWidthPx.command, true);
  assert.ok(MAP_GREASE_MARKUP_TOKENS.markerSizePx.arrowHead > 0);
  assert.deepEqual(MAP_STROKE_WIDTH_BY_ZOOM_TIER.map((entry) => entry.id), ["far", "operational", "close"]);
  assert.equal(MAP_BASEMAP_TOKENS.tilePrefetchPadding, 1);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.scene.width >= 500, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.tuningDefaults.hillshadeOpacity > 0, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase2Baseline.transportOpacity < MAP_READABILITY_STYLE_TOKENS.tuningDefaults.transportOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase3Baseline.gridOpacity > MAP_READABILITY_STYLE_TOKENS.tuningDefaults.gridOpacity, true);
  assert.equal(MAP_READABILITY_STYLE_TOKENS.phase3Baseline.ghostLabelOpacity > MAP_READABILITY_STYLE_TOKENS.tuningDefaults.ghostLabelOpacity, true);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.terrainOpacityByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.waterFillOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.coastFillOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.hypsometricOpacityByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.reliefShadeMixByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.coastOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.coastCasingOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.riverCasingOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.transportCasingOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.roadPrimaryOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.roadSecondaryOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.railOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.crossingOpacityFactorByTier), ["far", "operational", "close"]);
  assert.deepEqual(Object.keys(MAP_BASEMAP_TOKENS.crossingHaloOpacityFactorByTier), ["far", "operational", "close"]);
  assert.ok(MAP_BASEMAP_TOKENS.lineWidthPx.roadPrimary.close > MAP_BASEMAP_TOKENS.lineWidthPx.roadPrimary.far);
  assert.ok(MAP_BASEMAP_TOKENS.lineWidthPx.roadPrimary.operational > MAP_BASEMAP_TOKENS.lineWidthPx.roadSecondary.operational);
  assert.ok(MAP_BASEMAP_TOKENS.lineWidthPx.riverMajor.operational > MAP_BASEMAP_TOKENS.lineWidthPx.riverMinor.operational);
  assert.ok(MAP_BASEMAP_TOKENS.lineWidthPx.coast.operational < MAP_BASEMAP_TOKENS.lineWidthPx.coastCasing.operational);
  assert.ok(MAP_BASEMAP_TOKENS.riverCasingOpacityFactorByTier.operational > MAP_BASEMAP_TOKENS.coastCasingOpacityFactorByTier.operational);
  assert.ok(MAP_BASEMAP_TOKENS.roadPrimaryOpacityFactorByTier.operational > MAP_BASEMAP_TOKENS.roadSecondaryOpacityFactorByTier.operational);
  assert.ok(MAP_BASEMAP_TOKENS.crossingOpacityFactorByTier.operational >= MAP_BASEMAP_TOKENS.crossingHaloOpacityFactorByTier.operational);
  assert.ok(MAP_BASEMAP_TOKENS.markerSizePx.airfield.operational > MAP_BASEMAP_TOKENS.markerSizePx.settlement.operational);
  assert.ok(MAP_BASEMAP_TOKENS.markerSizePx.crossing.operational > MAP_BASEMAP_TOKENS.markerSizePx.crossing.far);
  assert.ok(MAP_GRID_PRESENTATION_BY_ZOOM_TIER.operational.gridMajorOpacity < 0.6);
  assert.ok(MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER.operational > MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER.far);
  assert.ok(MAP_LABEL_STYLE_TOKENS.fontSizePx.objective > MAP_LABEL_STYLE_TOKENS.fontSizePx.site);
  assert.deepEqual(MAP_RELIEF_BAND_PALETTE.map((entry) => entry.id), ["sea_level", "coastal_low", "lowland", "rolling", "upland", "ridge"]);
  assert.equal(MAP_ANIMATION_TOKENS.length, 4);
});

test("map design tokens define muted terrain families for hex presentation", () => {
  assert.deepEqual(
    MAP_TERRAIN_STYLES.map((terrain) => terrain.id),
    ["plains", "forest", "rough", "hills", "mountain", "urban", "water", "coast"],
  );
  for (const terrain of MAP_TERRAIN_STYLES) {
    assert.ok(Array.isArray(terrain.aliases) && terrain.aliases.length > 0);
    assert.ok(typeof terrain.texture === "string" && terrain.texture.length > 0);
    assert.ok(typeof terrain.note === "string" && terrain.note.length > 0);
  }
});
