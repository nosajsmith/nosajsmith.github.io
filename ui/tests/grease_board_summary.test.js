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

test("grease board summary prefers an explicit snapshot payload over scenario mock data", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "custom_slice", name: "Custom Slice" },
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

test("grease board stays absent outside Inchon until a command brief payload is exposed", () => {
  const summary = summarizeGreaseBoard({
    scenario: { id: "00_lunga_point_slice_1942", name: "Lunga Point 1942" },
  });

  assert.equal(summary.available, false);
  assert.equal(summary.source, "unavailable");
  assert.match(summary.note ?? "", /Inchon vertical slice/i);
});
