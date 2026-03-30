import test from "node:test";
import assert from "node:assert/strict";

import { renderReadyShellSmoke, renderStateScreenSmoke } from "../src/components/shell/smoke_render.js";

test("ready-state shell render uses operator-facing labels and humanized backend strings", () => {
  const html = renderReadyShellSmoke({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    time: { current_hours: 24 },
    campaign: {
      status: "ongoing",
      score_by_side: { ALLIED: 35, AXIS: 12 },
    },
    pressure: {
      reasons: ["enemy_pressure_north", "rail_congestion_lvov_axis"],
    },
    ai: {
      last_intent: "maintain_pressure_north",
    },
    reports: {
      recent: [{ id: "r1", kind: "player_order", summary: "Marine advance continues." }],
    },
  });

  assert.match(html, /Theater of Operations: Inchon/);
  assert.match(html, /Campaign Ongoing/);
  assert.match(html, /Enemy Pressure North/);
  assert.match(html, /Maintain pressure north/);
  assert.match(html, /Player Order Marine advance continues\./);
  assert.doesNotMatch(html, /Operation Shell|Main Map Panel|Backend source|Map V0/i);
});

test("ready-state shell infers the Inchon slice from live Korea context even when the scenario label is generic", () => {
  const html = renderReadyShellSmoke({
    scenario: { id: "publisher_demo_slice", name: "Publisher Demo" },
    time: { current_hours: 24 },
    campaign: {
      status: "ongoing",
      score_by_side: { ALLIED: 35, AXIS: 12 },
    },
    pressure: {
      reasons: ["seoul_axis_pressure"],
    },
    ai: {
      last_intent: "secure_inchon_corridor",
    },
    reports: {
      recent: [{ id: "r1", kind: "status", summary: "Pressure rising on the Seoul approach." }],
    },
    objectives: [{ id: "o1", name: "Seoul" }],
    ports: [{ id: "p1", name: "Inchon Harbor" }],
    grease_board: {
      objective: "SEOUL",
      main_effort: "INCHON / SEOUL AXIS",
    },
  });

  assert.match(html, /Theater of Operations: Inchon/);
  assert.match(html, /Operation Chromite Vertical Slice/);
  assert.doesNotMatch(html, /Guadalcanal|Henderson|Lunga/i);
});

test("not-ready state render remains explicit and operator-facing", () => {
  const html = renderStateScreenSmoke(
    "Scenario not ready",
    "A scenario has not been started on the active bridge yet.",
  );

  assert.match(html, /Command Post/);
  assert.match(html, /Scenario not ready/);
  assert.match(html, /active bridge/);
});
