import test from "node:test";
import assert from "node:assert/strict";

import {
  buildHexTilePresentation,
  HEX_TILE_PATHS,
  HEX_TILE_REFERENCE_CASES,
  normalizeHexTerrain,
  summarizeHexZoomPresentation,
} from "../src/map/hexTile.js";

test("hex tile zoom presentation keeps far view lighter and close view clearer", () => {
  const far = summarizeHexZoomPresentation(0.78);
  const operational = summarizeHexZoomPresentation(1);
  const close = summarizeHexZoomPresentation(1.6);

  assert.equal(far.tier, "far");
  assert.equal(operational.tier, "operational");
  assert.equal(close.tier, "close");
  assert.ok(far.gridMinorOpacity < operational.gridMinorOpacity);
  assert.ok(operational.gridMajorOpacity < close.gridMajorOpacity);
  assert.ok(far.fadeOpacity < close.fadeOpacity);
});

test("hex tile presentation layers selected and zoc states with non-color pattern differences", () => {
  const tile = buildHexTilePresentation({
    selected: true,
    enemyZoc: true,
    attackTarget: true,
    zoom: 1,
  });

  assert.equal(tile.flags.selected, true);
  assert.equal(tile.flags.enemyZoc, true);
  assert.equal(tile.flags.attackTarget, true);
  assert.deepEqual(
    tile.overlays.map((overlay) => overlay.id),
    ["enemy-zoc", "attack-crosshair", "attack-brackets", "selected-glow", "selected-ring", "selected-ticks"],
  );
  assert.deepEqual(
    tile.overlays.map((overlay) => overlay.pattern),
    ["long-dash-ring", "crosshair", "brackets", "soft-glow", "solid-ring", "edge-ticks"],
  );
});

test("hex tile can hide the base grid without suppressing state overlays", () => {
  const tile = buildHexTilePresentation({
    gridVisible: false,
    moveTarget: true,
    hovered: true,
    zoom: 1.58,
  });

  assert.equal(tile.gridVisible, false);
  assert.equal(tile.minorBorderOpacity, 0);
  assert.equal(tile.majorBorderOpacity, 0);
  assert.deepEqual(
    tile.overlays.map((overlay) => overlay.id),
    ["move-target", "move-pips", "hovered"],
  );
});

test("hex tile normalizes terrain aliases and converts river tiles into crossing treatment", () => {
  assert.equal(normalizeHexTerrain("field"), "plains");
  assert.equal(normalizeHexTerrain("woods"), "forest");
  assert.equal(normalizeHexTerrain("hill"), "hills");
  assert.equal(normalizeHexTerrain("ridge"), "mountain");
  assert.equal(normalizeHexTerrain("sea"), "water");

  const river = buildHexTilePresentation({ terrain: "river", zoom: 1 });
  assert.equal(river.terrain, "plains");
  assert.equal(river.riverCrossing, true);
  assert.deepEqual(
    river.overlays.slice(-3).map((overlay) => overlay.id),
    ["river-channel", "river-banks", "river-crossing"],
  );
});

test("hex tile exports reusable geometry and capture cases for every requested state", () => {
  assert.match(HEX_TILE_PATHS.outer, /^M16 2/);
  assert.deepEqual(
    HEX_TILE_REFERENCE_CASES.map((capture) => capture.id),
    ["default", "hovered", "selected", "friendly-zoc", "enemy-zoc", "contested", "move-target", "attack-target", "layered"],
  );
});
