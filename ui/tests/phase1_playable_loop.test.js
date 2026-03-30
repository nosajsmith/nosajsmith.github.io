import test from "node:test";
import assert from "node:assert/strict";

import { summarizeCommunications } from "../src/components/shell/communications_summary.js";
import { summarizeGreaseBoard } from "../src/components/shell/grease_board_summary.js";
import { summarizeInspector } from "../src/components/shell/inspector_summary.js";
import { buildMapScene } from "../src/components/shell/map_scene.js";
import { normalizeSnapshot } from "../src/lib/view_snapshot.ts";

function buildBeforeAdvancePayload() {
  return {
    game: {
      scenario: "Mini Guadalcanal 1942",
      time: { day: 2, phase: "day", weather: "Clear" },
      ai: {
        enabled: true,
        side: "AXIS",
        controller_available: true,
        last_orders: 2,
      },
    },
    pressure: {
      active: true,
      reasons: ["bloody_ridge_contact"],
      summary: "Pressure building against the perimeter.",
    },
    logs: [
      { src: "BAI", turn: 2, phase: "orders", message: "JP-35BDE holds TULAGI and screens the western approach." },
    ],
    reports: {
      recent: [
        {
          id: "r1",
          kind: "status",
          title: "Perimeter Alarm",
          summary: "Japanese probing pressure is building near Bloody Ridge.",
          severity: "warning",
          time: 24,
          sender_label: "Bloody Ridge Outpost",
        },
      ],
    },
    bai_report: {
      posture: "DEFENSIVE",
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      reserve_level: 0.3,
      summary_lines: ["Hold the perimeter while reserves stay back for local counterattack windows."],
      unit_orders: [
        {
          unit_id: "US-1MAR",
          action: "hold",
          target_location_id: "HENDERSON_FIELD",
        },
      ],
    },
    units: [
      {
        id: "US-1MAR",
        name: "1st Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        strength: 82,
        readiness: 71,
        morale: 74,
        fatigue: 18,
        supply: 64,
        posture: "DEFEND",
        location_id: "HENDERSON_FIELD",
        x: 4,
        y: 4,
        inspector: {
          operational_state: {
            posture: "defend",
            readiness: 71,
            fatigue: 18,
            morale: 74,
            cohesion: 69,
            loc: {
              state: "connected",
              label: "LOC Connected",
              detail: "Local corridor is holding.",
            },
          },
          supply: {
            supply_pct: 64,
            supply_days_current: 3,
            supply_display: "3 days",
          },
          orders: {
            action: "hold",
            lifecycle_state: "active",
            status: "issued",
          },
        },
      },
      {
        id: "US-2MAR",
        name: "2nd Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        strength: 68,
        readiness: 52,
        morale: 51,
        fatigue: 39,
        supply: 34,
        posture: "RESERVE",
        location_id: "BLOODY_RIDGE",
        x: 4.6,
        y: 4.2,
        inspector: {
          operational_state: {
            posture: "reserve",
            readiness: 52,
            fatigue: 39,
            morale: 51,
            cohesion: 46,
            loc: {
              state: "broken",
              label: "LOC Broken",
              detail: "Forward route is compromised.",
            },
          },
          supply: {
            supply_pct: 34,
            supply_days_current: 1,
            supply_display: "1 day",
          },
          orders: {
            action: "reserve",
            lifecycle_state: "active",
            status: "issued",
          },
        },
      },
    ],
    objectives: [
      {
        id: "HENDERSON_FIELD",
        name: "Henderson Field",
        side: "ALLIED",
        state: "contested",
        controlled: false,
        value: 60,
        x: 4.1,
        y: 4.05,
      },
    ],
    local_pressure_areas: [
      {
        id: "bloody-ridge",
        label: "Bloody Ridge",
        kind: "approach",
        location_id: "BLOODY_RIDGE",
        objective_id: "HENDERSON_FIELD",
        pressure_reasons: ["bloody_ridge_contact"],
        x: 4.5,
        y: 4.3,
      },
    ],
  };
}

function buildAfterAdvancePayload() {
  return {
    game: {
      scenario: "Mini Guadalcanal 1942",
      time: { day: 3, phase: "night", weather: "Rain" },
      ai: {
        enabled: true,
        side: "AXIS",
        controller_available: true,
        last_orders: 3,
      },
    },
    pressure: {
      active: true,
      reasons: ["bloody_ridge_contact", "supply_route_under_pressure"],
      summary: "Pressure persists along the perimeter and supply route.",
    },
    logs: [
      { src: "BAI", turn: 3, phase: "orders", message: "US-1MAR tightens the Henderson perimeter while reserves remain uncommitted." },
      { src: "ENGINE", turn: 3, phase: "turn", message: "Processed Day 2; now Day 3" },
    ],
    reports: {
      recent: [
        {
          id: "r2",
          kind: "status",
          title: "Night Contact",
          summary: "Night contact reported south of Henderson Field as reserves remain in place.",
          severity: "warning",
          time: 48,
          sender_label: "Henderson Watch",
        },
      ],
    },
    bai_report: {
      posture: "DEFENSIVE",
      main_objective: { name: "Henderson Field" },
      chosen_operation: { name: "Counterattack Local Breach" },
      reserve_level: 0.3,
      summary_lines: ["Counterattack windows remain limited; reserves stay back unless the line collapses."],
      unit_orders: [
        {
          unit_id: "US-1MAR",
          action: "hold",
          target_location_id: "HENDERSON_FIELD",
        },
        {
          unit_id: "US-2MAR",
          action: "reserve",
          target_location_id: "BLOODY_RIDGE",
        },
      ],
    },
    units: [
      {
        id: "US-1MAR",
        name: "1st Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        strength: 80,
        readiness: 69,
        morale: 72,
        fatigue: 24,
        supply: 58,
        posture: "DEFEND",
        location_id: "HENDERSON_FIELD",
        x: 4,
        y: 4,
        inspector: {
          operational_state: {
            posture: "defend",
            readiness: 69,
            fatigue: 24,
            morale: 72,
            cohesion: 66,
            loc: {
              state: "connected",
              label: "LOC Connected",
              detail: "Main corridor remains open.",
            },
          },
          supply: {
            supply_pct: 58,
            supply_days_current: 3,
            supply_display: "3 days",
          },
          orders: {
            action: "hold",
            lifecycle_state: "active",
            status: "issued",
          },
        },
      },
      {
        id: "US-2MAR",
        name: "2nd Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        strength: 66,
        readiness: 50,
        morale: 49,
        fatigue: 42,
        supply: 38,
        posture: "RESERVE",
        location_id: "BLOODY_RIDGE",
        x: 4.6,
        y: 4.2,
        inspector: {
          operational_state: {
            posture: "reserve",
            readiness: 50,
            fatigue: 42,
            morale: 49,
            cohesion: 44,
            loc: {
              state: "threatened",
              label: "LOC Threatened",
              detail: "Forward route remains under pressure.",
            },
          },
          supply: {
            supply_pct: 38,
            supply_days_current: 1,
            supply_display: "1 day",
          },
          orders: {
            action: "reserve",
            lifecycle_state: "active",
            status: "issued",
          },
        },
      },
    ],
    objectives: [
      {
        id: "HENDERSON_FIELD",
        name: "Henderson Field",
        side: "ALLIED",
        state: "contested",
        controlled: false,
        value: 60,
        x: 4.1,
        y: 4.05,
      },
    ],
    local_pressure_areas: [
      {
        id: "bloody-ridge",
        label: "Bloody Ridge",
        kind: "approach",
        location_id: "BLOODY_RIDGE",
        objective_id: "HENDERSON_FIELD",
        pressure_reasons: ["bloody_ridge_contact", "supply_route_under_pressure"],
        x: 4.5,
        y: 4.3,
      },
    ],
  };
}

test("Phase 1 playable loop stays coherent across selection, turn advance, reports, and grease board refresh", () => {
  const before = normalizeSnapshot(buildBeforeAdvancePayload());
  const after = normalizeSnapshot(buildAfterAdvancePayload());

  const mapScene = buildMapScene(before, { width: 520, height: 300, inset: 32 });
  assert.ok(mapScene.units.length >= 2, "expected visible units on the map");
  assert.ok(mapScene.objectives.length >= 1, "expected visible objectives on the map");

  const inspector = summarizeInspector(before, { kind: "unit", id: "US-1MAR" });
  assert.equal(inspector.selected, true);
  assert.equal(inspector.header.title, "1st Marines");
  assert.match(inspector.header.subtitle, /Allied|Formation|Infantry/i);

  const beforeComms = summarizeCommunications(before);
  const afterComms = summarizeCommunications(after);
  assert.ok(beforeComms.latest, "expected initial communications feed");
  assert.ok(afterComms.latest, "expected refreshed communications feed");
  assert.notEqual(afterComms.latest?.summary, beforeComms.latest?.summary);
  assert.equal(afterComms.latest?.title, "AI Command Update");
  assert.match(afterComms.latest?.summary ?? "", /Counterattack Local Breach|Defensive posture/i);
  assert.ok(afterComms.history.some((message) => message.title === "Orders Issued"));
  assert.ok(afterComms.history.some((message) => /Night Contact|Processed Day 2/.test(message.summary)));

  const beforeGrease = summarizeGreaseBoard(before);
  const afterGrease = summarizeGreaseBoard(after);
  assert.equal(beforeGrease.available, true);
  assert.equal(afterGrease.available, true);
  assert.equal(beforeGrease.source, "derived");
  assert.equal(afterGrease.source, "derived");
  assert.notEqual(afterGrease.data?.turn, beforeGrease.data?.turn);
  assert.match(afterGrease.data?.main_effort ?? "", /Counterattack Local Breach/i);
  assert.match(afterGrease.data?.alerts.join(" • ") ?? "", /Night contact|supply route/i);
  assert.match(afterGrease.data?.staff_notes ?? "", /reserves stay back/i);
});
