import test from "node:test";
import assert from "node:assert/strict";

import {
  MAP_LAYER_REGISTRY,
  buildMapOverlayManager,
  isMapLayerEnabled,
  toggleMapLayer,
} from "../src/map/overlayManager.js";

test("overlay manager keeps a centralized priority-ordered layer registry", () => {
  assert.deepEqual(
    MAP_LAYER_REGISTRY.map((layer) => layer.id),
    [
      "basemap",
      "historicalUnderlay",
      "terrainField",
      "terrainEmphasis",
      "grid",
      "weatherWash",
      "barriers",
      "infrastructure",
      "supply",
      "command",
      "frontline",
      "movementIntent",
      "artillery",
      "fogIntel",
      "greasePlanning",
      "objectives",
      "units",
      "labels",
      "ui",
    ],
  );
  assert.ok(MAP_LAYER_REGISTRY.every((layer, index, list) => index === 0 || list[index - 1].priority <= layer.priority));
});

test("overlay manager resolves default and overridden layer visibility", () => {
  const manager = buildMapOverlayManager({
    toggles: {
      grid: false,
      supply: true,
    },
  });

  assert.equal(isMapLayerEnabled(manager, "terrainField"), true);
  assert.equal(isMapLayerEnabled(manager, "historicalUnderlay"), false);
  assert.equal(isMapLayerEnabled(manager, "grid"), false);
  assert.equal(isMapLayerEnabled(manager, "supply"), true);
  assert.deepEqual(
    manager.orderedLayers.map((layer) => layer.id).includes("grid"),
    false,
  );
});

test("overlay manager toggles layers without losing the registry contract", () => {
  const next = toggleMapLayer({}, "grid");
  const back = toggleMapLayer(next, "grid");

  assert.equal(next.grid, false);
  assert.equal(back.grid, true);
});
