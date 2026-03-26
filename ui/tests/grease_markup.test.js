import test from "node:test";
import assert from "node:assert/strict";

import {
  clearGreaseMarkupItems,
  createGreaseMarkupItem,
  createGreaseMarkupState,
  deserializeGreaseMarkupState,
  removeGreaseMarkupItem,
  serializeGreaseMarkupState,
  shouldCommitGreaseMarkup,
} from "../src/map/greaseMarkup.js";

test("grease markup items normalize tool, style, and point data", () => {
  const item = createGreaseMarkupItem({
    tool: "freehand",
    style: "amber",
    points: [
      { x: 1, y: 2 },
      { x: 1, y: 2 },
      { x: 3.12398, y: 4.67891 },
      { x: 6, y: 7 },
    ],
  });

  assert.ok(item);
  assert.equal(item.tool, "freehand");
  assert.equal(item.style, "amber");
  assert.equal(item.points.length, 3);
  assert.equal(item.points[1].x, 3.124);
  assert.ok(item.bounds.width > 0);
  assert.ok(item.bounds.height > 0);
});

test("grease markup commit thresholds distinguish small gestures from real markup", () => {
  assert.equal(
    shouldCommitGreaseMarkup("straight_line", [{ x: 0, y: 0 }, { x: 4, y: 4 }]),
    false,
  );
  assert.equal(
    shouldCommitGreaseMarkup("straight_line", [{ x: 0, y: 0 }, { x: 24, y: 4 }]),
    true,
  );
  assert.equal(
    shouldCommitGreaseMarkup("zone_box", [{ x: 10, y: 10 }, { x: 16, y: 14 }]),
    false,
  );
  assert.equal(
    shouldCommitGreaseMarkup("zone_box", [{ x: 10, y: 10 }, { x: 34, y: 28 }]),
    true,
  );
});

test("grease markup state serializes and deserializes per scenario", () => {
  const item = createGreaseMarkupItem({
    tool: "arrow",
    style: "offwhite",
    points: [{ x: 1, y: 1 }, { x: 5, y: 4 }],
  });
  const serialized = serializeGreaseMarkupState({
    ...createGreaseMarkupState("lunga"),
    activeTool: "arrow",
    activeStyle: "offwhite",
    selectedId: item.id,
    items: [item],
  });
  const restored = deserializeGreaseMarkupState(JSON.stringify(serialized), "lunga");

  assert.equal(restored.scenarioId, "lunga");
  assert.equal(restored.activeTool, "arrow");
  assert.equal(restored.activeStyle, "offwhite");
  assert.equal(restored.selectedId, item.id);
  assert.equal(restored.items.length, 1);
  assert.equal(restored.items[0].tool, "arrow");
});

test("grease markup removal helpers keep selection clean", () => {
  const item = createGreaseMarkupItem({
    tool: "defensive_line",
    style: "blue",
    points: [{ x: 0, y: 0 }, { x: 6, y: 6 }],
  });
  const populated = {
    ...createGreaseMarkupState("test"),
    selectedId: item.id,
    items: [item],
  };
  const removed = removeGreaseMarkupItem(populated, item.id);
  const cleared = clearGreaseMarkupItems(populated);

  assert.equal(removed.items.length, 0);
  assert.equal(removed.selectedId, null);
  assert.equal(cleared.items.length, 0);
  assert.equal(cleared.selectedId, null);
});
