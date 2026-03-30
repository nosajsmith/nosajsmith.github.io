import test from "node:test";
import assert from "node:assert/strict";

import { summarizeGreaseBoard } from "../src/components/shell/grease_board_summary.js";

test("grease board summary uses Inchon mock data when no authoritative brief is exposed yet", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "inchon_mvp", name: "Inchon" },
  });

  assert.equal(summary.available, true);
  assert.equal(summary.source, "mock");
  assert.equal(summary.data?.turn, "TURN 5 — 15 SEP 1950");
  assert.equal(summary.data?.objective, "SEOUL");
  assert.equal(summary.data?.main_effort, "SEOUL AXIS");
  assert.equal(summary.data?.orders.length, 3);
  assert.equal(summary.data?.alerts.length, 2);
  assert.match(summary.data?.staff_notes ?? "", /Road network vulnerable west of Inchon/i);
});

test("grease board summary prefers an explicit snapshot payload over derived live state", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "custom_slice", name: "Custom Slice" },
    time: { turn: 4, current_hours: 18, phase: "night" },
    ai: { last_intent: "hold_henderson" },
    grease_board: {
      turn: "TURN 8",
      objective: "KIMPO",
      front_status: "PRESSING NORTH",
      supply_status: "BEACHHEAD SECURE",
      main_effort: "KIMPO AIRFIELD",
      orders: ["1st Marines pushing inland"],
      alerts: ["Enemy armor reported east of axis"],
      staff_notes: "Reserve fuel intact.",
    },
  });

  assert.equal(summary.available, true);
  assert.equal(summary.source, "snapshot");
  assert.equal(summary.data?.turn, "TURN 8");
  assert.equal(summary.data?.objective, "KIMPO");
  assert.equal(summary.data?.orders[0], "1st Marines pushing inland");
  assert.equal(summary.data?.alerts[0], "Enemy armor reported east of axis");
});

test("grease board summary derives a live command brief from AI, pressure, and unit state", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "00_lunga_point_slice_1942", name: "Lunga Point 1942" },
    time: { turn: 4, current_hours: 30, phase: "night" },
    pressure: {
      active: true,
      reasons: ["bloody_ridge_contact"],
    },
    ai: {
      enabled: true,
      last_intent: "hold_henderson_perimeter",
    },
    bai_report: {
      posture: "DEFENSIVE",
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      reserve_level: 0.3,
      unit_orders: [
        {
          unit_id: "u1",
          action: "hold",
          target_location_id: "HENDERSON_FIELD",
        },
      ],
      summary_lines: ["Hold the perimeter while reserves stay back for local counterattack windows."],
    },
    reports: {
      recent: [
        {
          id: "r1",
          kind: "turn",
          title: "Perimeter Alarm",
          summary: "Japanese probing pressure is building near Bloody Ridge.",
          severity: "warning",
          time: 30,
          sender_label: "Bloody Ridge Outpost",
        },
      ],
    },
    objectives: [
      { id: "o1", name: "Henderson Field", state: "contested", controlled: false, value: 60 },
    ],
    units: [
      {
        id: "u1",
        name: "1st Marines",
        inspector: {
          operational_state: {
            fatigue: 18,
            loc: {
              state: "threatened",
            },
          },
          supply: {
            supply_pct: 58,
            supply_days_current: 3,
          },
        },
      },
      {
        id: "u2",
        name: "2nd Marines",
        inspector: {
          operational_state: {
            fatigue: 41,
            loc: {
              state: "broken",
            },
          },
          supply: {
            supply_pct: 34,
            supply_days_current: 1,
          },
        },
      },
    ],
  });

  assert.equal(summary.available, true);
  assert.equal(summary.source, "derived");
  assert.equal(summary.data?.turn, "TURN 4 — T+30H — NIGHT");
  assert.equal(summary.data?.objective, "Henderson Field");
  assert.equal(summary.data?.front_status, "CONTESTED");
  assert.equal(summary.data?.supply_status, "CRITICAL FORWARD SUPPLY");
  assert.equal(summary.data?.main_effort, "Hold Henderson Perimeter");
  assert.match(summary.data?.orders[0] ?? "", /1st Marines hold Henderson Field/i);
  assert.match(summary.data?.alerts.join(" • ") ?? "", /Bloody Ridge|2nd Marines supply or LOC critical/i);
  assert.match(summary.data?.staff_notes ?? "", /Hold the perimeter while reserves stay back/i);
});

test("grease board summary promotes tracked planner-owned orders into active orders and main effort", () => {
  const snapshot = {
    scenario: { id: "inchon_mvp", name: "Operation Chromite" },
    time: { turn: 2, current_hours: 12, phase: "day" },
    objectives: [
      { id: "o-seoul", name: "Seoul", value: 100, state: "unheld", controlled: false, x: 46, y: 36 },
    ],
    units: [
      {
        id: "u1",
        name: "1st Marines",
        inspector: {
          supply: { supply_pct: 74, supply_days_current: 4.5 },
          operational_state: { fatigue: 12, loc: { state: "connected", label: "LOC Connected" } },
        },
      },
    ],
  };

  const summary = summarizeGreaseBoard(snapshot, [
    {
      id: "shortcut-u1-4-4",
      scenarioId: "inchon_mvp",
      name: "1st Marines Move • Seoul Axis",
      type: "offensive",
      objectiveId: "o-seoul",
      objectiveName: "Seoul",
      leadHq: "X Corps",
      participants: [{ unitId: "u1", name: "1st Marines", roleId: "main_effort" }],
      airRole: "none",
      navalRole: "none",
      tempo: "standard",
      estimatedPrepHours: 0,
      approvedAtTurn: 2,
      approvedAtHours: 12,
      commandIntent: "move",
      source: "map_shortcut",
      seedUnitId: "u1",
      targetHex: { q: 4, r: 4 },
      targetLabel: "Seoul Axis",
      enemyTargetId: null,
    },
  ]);

  assert.equal(summary.available, true);
  assert.equal(summary.source, "derived");
  assert.equal(summary.data?.main_effort, "1st Marines Move • Seoul Axis");
  assert.match(summary.data?.orders[0] ?? "", /1st Marines Move .*Seoul Axis/i);
  assert.match(summary.data?.staff_notes ?? "", /Move toward Seoul Axis/i);
});

test("grease board summary suppresses stale South Pacific AI text in Korea slices", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "inchon_mvp", name: "Operation Chromite" },
    time: { turn: 3, current_hours: 18, phase: "day" },
    ai: {
      enabled: true,
      last_intent: "hold_henderson_perimeter",
    },
    bai_report: {
      posture: "OFFENSIVE",
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      reserve_level: 0.45,
      summary_lines: ["Hold Henderson Field while the reserve waits."],
      unit_orders: [
        {
          unit_id: "u1",
          action: "advance",
          target_location_id: "SEOUL",
        },
      ],
    },
    reports: {
      recent: [
        {
          id: "r1",
          kind: "warning",
          title: "Legacy report",
          summary: "Henderson Field remains under pressure.",
          severity: "warning",
          time: 18,
        },
        {
          id: "r2",
          kind: "warning",
          title: "Axis delay",
          summary: "Enemy resistance is strengthening east of Kimpo.",
          severity: "warning",
          time: 18,
        },
      ],
    },
    objectives: [
      { id: "o1", name: "Seoul", value: 100, state: "unheld", controlled: false, x: 46, y: 36 },
      { id: "o2", name: "Inchon Harbor", value: 70, state: "held_allied", controlled: true, x: 18, y: 58 },
    ],
    units: [
      {
        id: "u1",
        name: "1st Marines",
        inspector: {
          supply: {
            supply_pct: 72,
            supply_days_current: 5,
          },
          operational_state: {
            fatigue: 16,
            loc: {
              state: "secure",
            },
          },
        },
      },
    ],
  });

  assert.equal(summary.available, true);
  assert.equal(summary.source, "derived");
  assert.equal(summary.data?.objective, "Seoul");
  assert.equal(summary.data?.main_effort, "Seoul");
  assert.match(summary.data?.orders.join(" • ") ?? "", /1st Marines advance Seoul/i);
  assert.doesNotMatch(summary.data?.orders.join(" • ") ?? "", /henderson|lunga|guadalcanal/i);
  assert.doesNotMatch(summary.data?.alerts.join(" • ") ?? "", /henderson|lunga|guadalcanal/i);
  assert.doesNotMatch(summary.data?.staff_notes ?? "", /henderson|lunga|guadalcanal/i);
});
