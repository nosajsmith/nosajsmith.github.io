import test from "node:test";
import assert from "node:assert/strict";

import { buildDeclutteredLabels, buildMarkerObstacleRect, summarizeMapLabelPolicy } from "../src/map/labelDeclutter.js";

test("label declutter exposes zoom-tier policy bands", () => {
  const far = summarizeMapLabelPolicy(0.78);
  const operational = summarizeMapLabelPolicy(1.08);
  const close = summarizeMapLabelPolicy(1.55);

  assert.equal(far.zoomTier, "far");
  assert.match(far.settlementLabels, /selected and key objective/i);
  assert.equal(operational.zoomTier, "operational");
  assert.match(operational.unitLabels, /selected and HQ/i);
  assert.equal(close.zoomTier, "close");
  assert.match(close.airfieldLabels, /visible/i);
});

test("label declutter keeps selected labels visible even in far-view density", () => {
  const result = buildDeclutteredLabels([
    {
      id: "objective:henderson:label",
      ownerId: "objective:henderson",
      ownerObstacleId: "objective:henderson",
      kind: "objectiveLabel",
      text: "Henderson Field",
      x: 36,
      y: 42,
      textAnchor: "start",
      scale: 1,
      important: true,
    },
    {
      id: "unit:marines:label",
      ownerId: "unit:marines",
      ownerObstacleId: "unit:marines",
      kind: "unitLabel",
      text: "1st Marines",
      x: 156,
      y: 54,
      textAnchor: "start",
      scale: 1,
      selected: true,
      forceVisible: true,
    },
    {
      id: "unit:reserve:label",
      ownerId: "unit:reserve",
      ownerObstacleId: "unit:reserve",
      kind: "unitLabel",
      text: "Reserve Battalion",
      x: 88,
      y: 58,
      textAnchor: "start",
      scale: 1,
    },
  ], [], { zoom: 0.78 });

  assert.equal(result.policy.zoomTier, "far");
  assert.equal(result.visibleIds.has("objective:henderson:label"), true);
  assert.equal(result.visibleIds.has("unit:marines:label"), true);
  assert.equal(result.visibleIds.has("unit:reserve:label"), false);
});

test("label declutter suppresses lower-priority overlaps and obstacle collisions", () => {
  const obstacles = [
    buildMarkerObstacleRect({
      id: "objective:henderson",
      kind: "objective",
      x: 100,
      y: 80,
      width: 24,
      height: 24,
      scale: 1,
    }),
    buildMarkerObstacleRect({
      id: "port:lunga",
      kind: "port",
      x: 170,
      y: 110,
      width: 20,
      height: 16,
      scale: 1,
    }),
  ];

  const result = buildDeclutteredLabels([
    {
      id: "objective:henderson:label",
      ownerId: "objective:henderson",
      ownerObstacleId: "objective:henderson",
      kind: "objectiveLabel",
      text: "Henderson Field",
      x: 118,
      y: 68,
      textAnchor: "start",
      scale: 1,
      important: true,
    },
    {
      id: "airfield:field:label",
      ownerId: "airfield:field",
      ownerObstacleId: "airfield:field",
      kind: "airfieldLabel",
      text: "Fighter Strip",
      x: 150,
      y: 64,
      textAnchor: "start",
      scale: 1,
    },
    {
      id: "unit:hq:label",
      ownerId: "unit:hq",
      ownerObstacleId: "unit:hq",
      kind: "unitLabel",
      text: "Americal HQ",
      x: 170,
      y: 110,
      textAnchor: "middle",
      scale: 1,
      important: true,
    },
  ], obstacles, { zoom: 1.55 });

  assert.equal(result.visibleIds.has("objective:henderson:label"), true);
  assert.equal(result.visibleIds.has("airfield:field:label"), false);
  assert.equal(result.blocked.find((entry) => entry.id === "airfield:field:label")?.blockedBy, "label");
  assert.equal(result.visibleIds.has("unit:hq:label"), false);
  assert.equal(result.blocked.find((entry) => entry.id === "unit:hq:label")?.blockedBy, "obstacle");
});
