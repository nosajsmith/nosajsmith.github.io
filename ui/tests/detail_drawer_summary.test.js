import test from "node:test";
import assert from "node:assert/strict";

import { summarizeDetailDrawer } from "../src/components/shell/detail_drawer_summary.js";

test("detail drawer summary consolidates essential main-map context", () => {
  const summary = summarizeDetailDrawer({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    campaign: {
      status: "ongoing",
      win_score: 50,
      score_by_side: { ALLIED: 35, AXIS: 12 },
      objective_state: { o1: true, o2: false, o3: true },
    },
    time: { turn: 4, time_remaining_hours: 36 },
    reports: {
      pending_count: 2,
      recent: [{ id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info" }],
    },
    objectives: [{ id: "o1", name: "Inchon Harbor", state: "held_allied", side: "ALLIED" }],
    pressure: { summary: "Enemy pressure rising.", reasons: [], active: true, details: {} },
    ai: { enabled: false, last_intent: "maintain_pressure_north" },
    staff: { summary: "Staff focused on landing tempo.", load: 3 },
    units: [
      { id: "u1", x: 1, y: 1 },
      { id: "u2", x: null, y: null },
    ],
  });

  assert.equal(summary.campaign.status, "Ongoing");
  assert.equal(summary.mapContext.visibleUnits, 1);
  assert.equal(summary.mapContext.hiddenTrackedUnits, 1);
  assert.equal(summary.mapContext.heldObjectives, 2);
  assert.equal(summary.staff.summary, "Staff focused on landing tempo.");
  assert.deepEqual(summary.score.map((row) => row.label), ["Allied", "Axis"]);
});
