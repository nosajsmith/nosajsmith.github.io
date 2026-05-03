import test from "node:test";
import assert from "node:assert/strict";

import { summarizeCommunications } from "../src/components/shell/communications_summary.js";

test("communications summary uses available report fields without fabricating metadata", () => {
  const summary = summarizeCommunications({
    pending_count: 2,
    recent: [
      { id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info", time: 4, sender_label: "Beachmaster" },
      { id: "r2", kind: "warning", title: "", summary: "", severity: "warning", time: null },
    ],
  });

  assert.equal(summary.pending, 2);
  assert.equal(summary.latest.id, "r2");
  assert.equal(summary.latest.kind, "Warning");
  assert.equal(summary.latest.body, "Operational update.");
  assert.equal(summary.latest.severity, "warning");
  assert.equal(summary.latest.timeLabel, "Time unavailable");
  assert.equal(summary.history[1].title, "Landing Continues");
  assert.equal(summary.history[1].senderLabel, "Beachmaster");
  assert.equal(summary.history[1].insigniaCode, "B");
  assert.equal(summary.demoExample, null);
});

test("communications summary falls back to demo content only when no live messages are present", () => {
  const summary = summarizeCommunications({
    pending_count: null,
    recent: [],
  });

  assert.equal(summary.latest, null);
  assert.equal(summary.history.length, 0);
  assert.equal(summary.demoExample?.senderLabel, "82nd Airborne");
  assert.equal(summary.demoExample?.insigniaCode, "AA");
  assert.equal(summary.demoExample?.isDemo, true);
});

test("communications summary suppresses demo fallback when a live snapshot exists but the bridge exposes no traffic yet", () => {
  const summary = summarizeCommunications({
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    time: { turn: 1, current_hours: 0 },
    reports: { pending_count: null, recent: [] },
    units: [],
    objectives: [],
  });

  assert.equal(summary.latest, null);
  assert.equal(summary.history.length, 0);
  assert.equal(summary.demoExample, null);
});

test("communications summary prefers view.snapshot reports and read-first before synthesized command context", () => {
  const summary = summarizeCommunications({
    contract: { id: "view.snapshot", version: 1, source: "backend_read_model" },
    scenario: { id: "contract_demo", name: "Contract Demo" },
    time: { turn: 2, current_hours: 24, phase: "day" },
    campaign: { status: "active" },
    read_first: {
      scenario: "Contract Demo",
      turn: 2,
      phase: "day",
      campaign_status: "active",
      key_objective: "Hill 101",
      pressure_summary: "Hill 101 pressure degraded.",
      latest_report: "Objective Update",
    },
    reports: {
      pending_count: 0,
      recent: [
        { id: "r1", kind: "status", title: "Earlier Logistics", summary: "Supply trains clear the road.", severity: "info", time: 18, sender_label: "G4" },
        { id: "r2", kind: "objectives", title: "Objective Update", summary: "Hill 101 remains contested.", severity: "warning", time: 24, sender_label: "G8" },
      ],
    },
    ai: { enabled: true, last_intent: "delay_hill_101" },
    pressure: {
      active: true,
      summary: "Hill 101 pressure degraded.",
      reasons: ["ALLIED:HILL:degraded_by_supply"],
    },
    bai_report: {
      posture: "DEFENSIVE",
      chosen_operation: { name: "Delay Hill 101" },
      unit_orders: [{ unit_id: "u1", action: "hold", target_location_id: "HILL" }],
    },
    units: [{ id: "u1", name: "1st Battalion" }],
  });

  assert.equal(summary.pending, 0);
  assert.equal(summary.latest?.id, "r2");
  assert.equal(summary.latest?.title, "Objective Update");
  assert.equal(summary.history[1]?.title, "Earlier Logistics");
  const readFirst = summary.history.find((message) => message.title === "Current Operational Picture");
  assert.ok(readFirst);
  assert.match(readFirst.summary, /Hill 101 pressure degraded/i);
  const aiUpdateIndex = summary.history.findIndex((message) => message.title === "AI Command Update");
  assert.ok(aiUpdateIndex > 1);
  assert.equal(summary.demoExample, null);
});

test("communications summary synthesizes AI command and order-flow messages from live snapshot state", () => {
  const summary = summarizeCommunications({
    time: { turn: 3, current_hours: 48 },
    ai: { enabled: true, last_intent: "hold_henderson_perimeter" },
    pressure: { active: true, summary: "Pressure persists along the perimeter.", reasons: [] },
    reports: {
      pending_count: 1,
      recent: [
        { id: "r1", kind: "status", title: "Night Contact", summary: "Night contact reported south of Henderson Field.", severity: "warning", time: 48 },
      ],
    },
    bai_report: {
      posture: "DEFENSIVE",
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      reserve_level: 0.3,
      summary_lines: ["Counterattack windows remain limited; reserves stay back unless the line collapses."],
      unit_orders: [
        { unit_id: "u1", action: "hold", target_location_id: "HENDERSON_FIELD" },
      ],
    },
    units: [
      {
        id: "u1",
        name: "1st Marines",
        inspector: {
          supply: { supply_pct: 34, supply_days_current: 1 },
          operational_state: { loc: { state: "broken" } },
        },
      },
    ],
  });

  assert.equal(summary.pending, 1);
  assert.equal(summary.latest?.title, "AI Command Update");
  assert.match(summary.latest?.summary ?? "", /Defensive posture/i);
  assert.ok(summary.history.some((message) => message.title === "Orders Issued"));
  assert.ok(summary.history.some((message) => message.title === "Operational Pressure"));
  assert.ok(summary.history.some((message) => message.title === "Night Contact"));
});

test("communications summary reflects tracked shortcut orders in player-readable language", () => {
  const summary = summarizeCommunications({
    time: { turn: 2, current_hours: 12 },
    reports: { pending_count: 0, recent: [] },
    units: [{ id: "u1", name: "1st Marines" }],
  }, [
    {
      id: "shortcut-1",
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

  assert.equal(summary.latest?.title, "Player Order Update");
  assert.match(summary.latest?.summary ?? "", /Player order 1st Marines move Seoul Axis/i);
});

test("communications summary suppresses stale Guadalcanal dispatch text when the active slice is Inchon Korea", () => {
  const summary = summarizeCommunications({
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    time: { turn: 2, current_hours: 18 },
    reports: {
      pending_count: 2,
      recent: [
        { id: "r1", kind: "status", title: "Beachhead Update", summary: "Kimpo corridor remains contested.", severity: "info", time: 18 },
        { id: "r2", kind: "warning", title: "Night Contact", summary: "Night contact reported south of Henderson Field.", severity: "warning", time: 17 },
      ],
    },
  });

  assert.equal(summary.latest?.title, "Beachhead Update");
  assert.doesNotMatch(summary.latest?.summary ?? "", /Henderson|Lunga|Guadalcanal/i);
  assert.ok(summary.history.every((message) => !/Henderson|Lunga|Guadalcanal/i.test(`${message.title} ${message.summary}`)));
});
