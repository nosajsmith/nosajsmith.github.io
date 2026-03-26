import test from "node:test";
import assert from "node:assert/strict";

import {
  buildAirfieldIconPresentation,
  summarizeAirfieldLocation,
  summarizeAirfieldZoomPolicy,
} from "../src/map/airfieldIcon.js";

test("airfield summary derives truthful tier, control, and readiness from exposed map and based-air-unit context", () => {
  const airfield = {
    id: "HENDERSON_FIELD",
    name: "Henderson Field",
    x: 4,
    y: 4,
  };
  const summary = summarizeAirfieldLocation(airfield, {
    objectives: [{ id: "o1", name: "Henderson Field", side: "ALLIED", state: "held_allied", value: 100, x: 4, y: 4 }],
    units: [{
      id: "air-1",
      name: "Cactus Air Wing",
      kind: "air",
      location_id: "HENDERSON_FIELD",
      readiness: 74,
      inspector: { orders: { action: "sortie launch", status: "executing" }, operational_state: { posture: "Sortie" } },
    }],
  });

  assert.equal(summary.tier, "major_airbase");
  assert.equal(summary.controlState, "friendly");
  assert.equal(summary.readinessBand, "ready");
  assert.equal(summary.sortieActive, true);
  assert.equal(summary.basedAirUnits, 1);
});

test("airfield icon presentation follows icon-only, marker, and labeled zoom tiers", () => {
  const far = buildAirfieldIconPresentation({ tier: "minor_airstrip", controlState: "friendly", zoom: 0.78 });
  const operational = buildAirfieldIconPresentation({ tier: "operational_airfield", controlState: "friendly", zoom: 1.08, readinessBand: "limited" });
  const close = buildAirfieldIconPresentation({ tier: "major_airbase", controlState: "friendly", zoom: 1.55, sortieActive: true });

  assert.equal(far.zoomTier, "far");
  assert.equal(far.showLabel, false);
  assert.equal(far.showStatus, false);
  assert.equal(operational.zoomTier, "operational");
  assert.equal(operational.showStatus, true);
  assert.equal(operational.showLabel, false);
  assert.equal(close.zoomTier, "close");
  assert.equal(close.showStatus, true);
  assert.equal(close.showLabel, true);
});

test("airfield zoom policy describes far, operational, and close behavior", () => {
  assert.deepEqual(
    summarizeAirfieldZoomPolicy().map((entry) => entry.id),
    ["far", "operational", "close"],
  );
});
