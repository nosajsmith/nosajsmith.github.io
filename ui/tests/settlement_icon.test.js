import test from "node:test";
import assert from "node:assert/strict";

import {
  buildSettlementIconPresentation,
  summarizeSettlementLocation,
  summarizeSettlementZoomPolicy,
} from "../src/map/settlementIcon.js";

test("settlement summary derives locality tier and control state from exposed objective data", () => {
  const capital = summarizeSettlementLocation({ name: "Henderson", value: 100, state: "held_allied", side: "ALLIED" });
  const majorEnemy = summarizeSettlementLocation({ name: "Seoul", value: 75, state: "held_axis", side: "AXIS" });
  const contestedTown = summarizeSettlementLocation({ name: "Bloody Ridge", value: 45, state: "unheld", side: "ALLIED" });

  assert.equal(capital.tier, "capital");
  assert.equal(capital.controlState, "friendly");
  assert.equal(capital.importanceMarks, 3);
  assert.equal(majorEnemy.tier, "major_city");
  assert.equal(majorEnemy.controlState, "enemy");
  assert.equal(contestedTown.tier, "town");
  assert.equal(contestedTown.controlState, "contested");
});

test("settlement icon presentation follows the documented zoom behavior", () => {
  const far = buildSettlementIconPresentation({ tier: "city", controlState: "friendly", zoom: 0.78 });
  const operational = buildSettlementIconPresentation({ tier: "city", controlState: "friendly", zoom: 1.1 });
  const close = buildSettlementIconPresentation({ tier: "city", controlState: "friendly", zoom: 1.55 });

  assert.equal(far.zoomTier, "far");
  assert.equal(far.showLabel, false);
  assert.equal(far.showValueMarks, false);
  assert.equal(operational.zoomTier, "operational");
  assert.equal(operational.showLabel, false);
  assert.equal(operational.showValueMarks, true);
  assert.equal(close.zoomTier, "close");
  assert.equal(close.showLabel, true);
  assert.equal(close.showStateText, true);
});

test("settlement zoom policy describes far, operational, and close handling", () => {
  assert.deepEqual(
    summarizeSettlementZoomPolicy().map((entry) => entry.id),
    ["far", "operational", "close"],
  );
});
