import test from "node:test";
import assert from "node:assert/strict";

import { summarizeOperationsBoard } from "../src/components/shell/operations_board.js";

test("operations board summarizes snapshot content conservatively from view.snapshot", () => {
  const summary = summarizeOperationsBoard({
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    campaign: { status: "ongoing" },
    time: { turn: 4, time_remaining_hours: 36 },
    reports: {
      pending_count: 2,
      recent: [
        { id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info" },
        { id: "r2", kind: "objective", title: "Kimpo Under Pressure", summary: "Axis resistance stiffening.", severity: "warning" },
      ],
    },
    objectives: [
      { id: "o1", name: "Inchon Harbor", state: "held_allied", side: "ALLIED" },
      { id: "o2", name: "Kimpo Airfield", state: "unheld", side: "ALLIED" },
    ],
    pressure: { summary: null, reasons: ["enemy_pressure_north"] },
    ai: { last_intent: "maintain_pressure_north" },
  }, [
    {
      id: "shortcut-1",
      scenarioId: "inchon_mvp",
      name: "1st Marines Move • Kimpo",
      type: "offensive",
      objectiveId: "o2",
      objectiveName: "Kimpo Airfield",
      leadHq: "X Corps",
      participants: [{ unitId: "u1", name: "1st Marines", roleId: "main_effort" }],
      airRole: "none",
      navalRole: "none",
      tempo: "standard",
      estimatedPrepHours: 0,
      approvedAtTurn: 4,
      approvedAtHours: 12,
      commandIntent: "move",
      source: "map_shortcut",
      seedUnitId: "u1",
      targetHex: { q: 3, r: 2 },
      targetLabel: "Kimpo",
      enemyTargetId: null,
    },
  ]);

  assert.deepEqual(summary.situation, {
    status: "Ongoing",
    turn: 4,
    timeRemaining: 36,
    pendingReports: 2,
  });
  assert.deepEqual(summary.objectives[0], {
    id: "o1",
    name: "Inchon Harbor",
    state: "Held Allied",
    side: "ALLIED",
  });
  assert.deepEqual(summary.pressure, {
    summary: null,
    reasons: ["Enemy Pressure North"],
  });
  assert.equal(summary.aiIntent, "Maintain pressure north");
  assert.equal(summary.operations.available, true);
  assert.match(summary.operations.headline, /1st Marines Move • Kimpo/i);
  assert.equal(summary.developments[0].title, "AI Command Update");
  assert.equal(summary.developments[1].title, "Player Order Update");
  assert.equal(summary.developments[2].id, "r2");
});

test("operations board uses the same cleaned operator-facing report wording as the feed", () => {
  const summary = summarizeOperationsBoard({
    reports: {
      pending_count: 1,
      recent: [
        {
          id: "r1",
          kind: "status",
          title: "Status",
          summary: "Game started. Operational AI enabled for visible shell progression.",
          severity: "info",
        },
      ],
    },
    objectives: [],
    pressure: { summary: null, reasons: [] },
    ai: { last_intent: null },
    campaign: { status: "ongoing" },
    time: { turn: 1, time_remaining_hours: 72 },
  });

  assert.deepEqual(summary.developments, [
    {
      id: "r1",
      title: "Status",
      summary: "Game started. Operational AI enabled.",
      severity: "INFO",
    },
  ]);
});
