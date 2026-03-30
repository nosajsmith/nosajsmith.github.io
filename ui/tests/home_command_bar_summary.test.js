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
  assert.match(summary.operations.detail, /Objective Inchon/);
  assert.match(summary.operations.detail, /assembly before launch/i);
  assert.equal(summary.objectives.total, 1);
  assert.equal("operations" in summary, true);
  assert.equal(summary.air.label, "Air context partial");
  assert.match(summary.air.detail, /airfield context/);
  assert.equal(summary.naval.label, "Naval context partial");
  assert.match(summary.naval.detail, /maritime context/);
  assert.equal(summary.logistics.label, "4.2d sustainment");
  assert.match(summary.logistics.detail, /4.2 days average current tempo/);
  assert.equal(summary.intelligence.label, "2 pending dispatches");
  assert.match(summary.intelligence.detail, /Latest dispatch Player Order Update/);
  assert.match(summary.intelligence.detail, /1st Marines/i);
  assert.match(summary.intelligence.detail, /Inchon/i);
  assert.equal(summary.reports.pending, 2);
});

test("home command bar ignores stale Guadalcanal AI labels when the active slice is Inchon Korea", () => {
  const summary = summarizeHomeCommandBar({
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    campaign: { status: "ongoing" },
    time: { turn: 2, time_remaining_hours: 42, current_hours: 18 },
    objectives: [{ id: "o1", state: "unheld", name: "Seoul", value: 100, side: "ALLIED" }],
    pressure: { summary: "Pressure building on the Seoul corridor.", reasons: [] },
    reports: { pending_count: 0, recent: [] },
    bai_report: {
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      reserve_level: 0.25,
      unit_orders: [],
    },
    ai: { last_intent: "hold_henderson_perimeter" },
    units: [],
    airfields: [],
    ports: [],
    naval_support_windows: [],
  });

  assert.doesNotMatch(summary.operations.status, /Henderson|Lunga|Guadalcanal/i);
  assert.match(summary.operations.detail, /Objective Seoul/);
});

test("home command bar uses live dispatch count when the bridge does not expose a queue count", () => {
  const summary = summarizeHomeCommandBar({
    reports: {
      pending_count: null,
      recent: [
        { id: "r1", kind: "status", title: "Kimpo Update", summary: "Kimpo corridor remains contested.", severity: "info", time: 18 },
      ],
    },
    pressure: { active: true, reasons: ["kimpo_screening_force"] },
    staff: { summary: "Maintain pressure on the Kimpo approach." },
  });

  assert.equal(summary.intelligence.label, "1 live dispatch");
  assert.match(summary.intelligence.detail, /Latest dispatch Kimpo Update/);
});
