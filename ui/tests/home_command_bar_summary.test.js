import test from "node:test";
import assert from "node:assert/strict";

import { summarizeHomeCommandBar } from "../src/components/shell/home_command_bar_summary.js";

test("home command bar uses available snapshot data and explicit placeholders", () => {
  const snapshot = {
    campaign: { status: "ongoing" },
    time: { turn: 4, time_remaining_hours: 36, current_hours: 12 },
    objectives: [{ id: "o1", state: "held_allied", name: "Inchon" }],
    pressure: { summary: null, reasons: ["enemy_pressure_north"] },
    staff: { summary: "Staff focused on landing tempo." },
    reports: { pending_count: 2, recent: [{ id: "r1", title: "Landing Continues", kind: "status", summary: "Beachhead expanding.", severity: "info" }] },
    airfields: [{ id: "KIMPO", name: "Kimpo Airfield", x: 7, y: 4 }],
    ports: [{ id: "INCHON", name: "Inchon Harbor", x: 3, y: 5 }],
    naval_support_windows: [{ id: "naval-gunfire", label: "Naval Gunfire", side: "ALLIED", start_hour: 0, end_hour: 24 }],
    units: [
      {
        id: "log-1",
        kind: "logistics",
        inspector: {
          supply: { supply_days_current: 4.2, supply_pct: 78 },
          movement: {},
          toe: {},
          operational_state: {},
          attachments_support: {},
        },
      },
    ],
  };
  const summary = summarizeHomeCommandBar(snapshot, [
    {
      id: "inchon_slice:offensive:o1",
      scenarioId: null,
      name: "Offensive • Inchon",
      type: "offensive",
      objectiveId: "o1",
      objectiveName: "Inchon",
      leadHq: "X Corps",
      participants: [{ unitId: "u1", name: "1st Marines", roleId: "main_effort" }],
      airRole: "cas",
      navalRole: "shore_support",
      tempo: "standard",
      estimatedPrepHours: 6,
      approvedAtTurn: 4,
      approvedAtHours: 12,
    },
  ]);

  assert.equal(summary.theatre.status, "Ongoing");
  assert.equal(summary.theatre.timeRemaining, "36h remaining");
  assert.match(summary.theatre.detail, /Turn 4 • 36h remaining • Moving to Start Line/);
  assert.equal(summary.operations.status, "Offensive • Inchon • Moving to Start Line");
  assert.match(summary.operations.detail, /Inchon • Held Allied/);
  assert.equal(summary.objectives.total, 1);
  assert.equal("operations" in summary, true);
  assert.equal(summary.air.label, "Air context partial");
  assert.match(summary.air.detail, /airfield context/);
  assert.equal(summary.naval.label, "Naval context partial");
  assert.match(summary.naval.detail, /maritime context/);
  assert.equal(summary.logistics.label, "4.2d sustainment");
  assert.match(summary.logistics.detail, /4.2 days average current tempo/);
  assert.equal(summary.intelligence.label, "2 pending");
  assert.match(summary.intelligence.detail, /communications feed and pressure-reason path/);
  assert.equal(summary.reports.pending, 2);
});
