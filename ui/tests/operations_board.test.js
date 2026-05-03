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

test("operations board prefers snapshot objective truth and pressure rows over legacy objective state", () => {
  const summary = summarizeOperationsBoard({
    scenario: { id: "test", name: "Test" },
    campaign: { status: "ongoing" },
    time: { turn: 6, time_remaining_hours: 24 },
    reports: { pending_count: 0, recent: [] },
    ai: { last_intent: "hold_reserve" },
    read_first: {
      pressure_summary: "Hill 101 pressure is degraded.",
    },
    objectives: [
      {
        id: "o1",
        name: "Hill 101",
        side: "ALLIED",
        state: "held_allied",
        objective_truth_key: "ALLIED:HILL",
      },
    ],
    objective_truth: {
      "ALLIED:HILL": { status: "contested", controller_side: "AXIS" },
    },
    pressure: {
      summary: "Legacy pressure summary.",
      reasons: [],
      by_objective: {
        "ALLIED:HILL": {
          location_id: "HILL",
          pressure_state: "degraded",
          pressure_score: 35,
        },
      },
      total_pressure_score: 35,
    },
  });

  assert.deepEqual(summary.objectives, [
    {
      id: "o1",
      name: "Hill 101",
      state: "Contested",
      side: "ALLIED",
    },
  ]);
  assert.deepEqual(summary.pressure, {
    summary: "Hill 101 pressure is degraded.",
    reasons: [],
  });
});

test("operations board v0 exposes a compact snapshot-backed operator read", () => {
  const summary = summarizeOperationsBoard({
    contract: { id: "view.snapshot", version: 1, source: "backend_read_model" },
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    operation: { id: "op-chromite", name: "Operation Chromite" },
    campaign: { status: "active", score_by_side: { ALLIED: 12, AXIS: 8 }, win_score: 120 },
    score: { score_by_side: { ALLIED: 60, AXIS: 30 }, win_score: 120 },
    time: { turn: 2, current_hours: 30, phase: "night", time_remaining_hours: 42 },
    read_first: {
      scenario: "Inchon Demo Vertical Slice",
      key_objective: "Kimpo Airfield",
      pressure_summary: "Kimpo pressure is degraded.",
      latest_report: "Kimpo Under Pressure",
    },
    reports: {
      pending_count: 1,
      recent: [
        { id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info", time: 24, sender_label: "G3" },
        { id: "r2", kind: "objective", title: "Kimpo Under Pressure", summary: "Axis resistance stiffening.", severity: "warning", time: 30, sender_label: "G8" },
      ],
    },
    objectives: [
      {
        id: "o-kimpo",
        name: "Kimpo Airfield",
        side: "ALLIED",
        state: "held_allied",
        objective_truth_key: "ALLIED:KIMPO",
      },
      {
        id: "o-seoul",
        name: "Seoul",
        side: "ALLIED",
        state: "unheld",
        objective_truth_key: "ALLIED:SEOUL",
      },
    ],
    objective_truth: {
      "ALLIED:KIMPO": { status: "contested", controller_side: "AXIS" },
      "ALLIED:SEOUL": { status: "held", controller_side: "AXIS" },
    },
    pressure: {
      active: true,
      summary: "Legacy pressure summary.",
      reasons: ["kimpo_screening_force"],
      by_objective: {
        "ALLIED:KIMPO": {
          location_id: "KIMPO",
          objective_status: "contested",
          pressure_state: "degraded",
          pressure_score: 44,
        },
        "ALLIED:SEOUL": {
          location_id: "SEOUL",
          objective_status: "held",
          pressure_state: "none",
          pressure_score: 0,
        },
      },
      total_pressure_score: 44,
    },
    ai: { enabled: true, last_intent: "secure_kimpo_corridor" },
  });

  assert.deepEqual(summary.identity, {
    scenarioId: "inchon_mvp",
    scenarioName: "Inchon Demo Vertical Slice",
    operationId: "op-chromite",
    operationName: "Operation Chromite",
    source: "view.snapshot",
  });
  assert.equal(summary.timing.turnLabel, "Turn 2");
  assert.equal(summary.timing.dayLabel, "Day 2");
  assert.equal(summary.timing.hourLabel, "T+30h");
  assert.equal(summary.score.leader, "Allied leads 60-30");
  assert.deepEqual(summary.objectiveTruth.byState, [
    { state: "Contested", count: 1 },
    { state: "Held Axis", count: 1 },
  ]);
  assert.equal(summary.hotspots[0].label, "KIMPO");
  assert.equal(summary.hotspots[0].state, "Degraded");
  assert.match(summary.hotspots[0].detail, /Pressure 44/);
  assert.equal(summary.command.aiEnabled, true);
  assert.equal(summary.command.aiIntent, "Secure kimpo corridor");
  assert.equal(summary.recent[0].title, "Kimpo Under Pressure");
  assert.equal(summary.recent[0].severity, "WARNING");
});
