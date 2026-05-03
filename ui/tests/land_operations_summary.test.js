import test from "node:test";
import assert from "node:assert/strict";

import { summarizeLandOperations } from "../src/components/shell/land_operations_summary.js";

function buildLandSnapshot() {
  return {
    scenario: { id: "lunga_slice", name: "Lunga Point Slice" },
    time: { turn: 4, current_hours: 12 },
    units: [
      {
        id: "hq-1",
        side: "ALLIED",
        name: "Henderson Perimeter HQ",
        kind: "ground",
        unit_type: "HEADQUARTERS",
        inspector: {
          command: {
            hq_unit_id: null,
            superior: null,
            next_superior: null,
            subordinates: [],
            commander: "Maj. Gen. A. A. Vandegrift",
          },
        },
      },
      {
        id: "u1",
        side: "ALLIED",
        name: "1st Marines",
        kind: "ground",
        unit_type: "INFANTRY",
        location_id: "BLOODY_RIDGE",
        readiness: 70,
        inspector: {
          command: {
            hq_unit_id: "hq-1",
            superior: { id: "hq-1", name: "Henderson Perimeter HQ" },
            next_superior: null,
            subordinates: [],
            commander: "Col. Hunt",
          },
          attachments_support: {
            attachments: ["Engineer Detachment"],
            support: ["11th Marines Battalion"],
            detached: [],
          },
          operational_state: {
            posture: "defend",
            readiness: 70,
            fatigue: 16,
            loc: { state: "connected", label: "LOC Connected", detail: "Local corridor holding." },
          },
          supply: { supply_pct: 78, supply_days_current: "4.0 days" },
          orders: { action: "hold", lifecycle_state: "active", status: "queued" },
        },
      },
      {
        id: "u2",
        side: "ALLIED",
        name: "2nd Marines",
        kind: "ground",
        unit_type: "INFANTRY",
        location_id: "KUKUM",
        readiness: 49,
        inspector: {
          command: {
            hq_unit_id: "hq-1",
            superior: { id: "hq-1", name: "Henderson Perimeter HQ" },
            next_superior: null,
            subordinates: [],
            commander: null,
          },
          attachments_support: {
            attachments: [],
            support: [],
            detached: ["Scout Platoon"],
          },
          operational_state: {
            posture: "reserve",
            readiness: 49,
            fatigue: 38,
            loc: { state: "threatened", label: "LOC Threatened", detail: "Supply route under pressure." },
          },
          supply: { supply_pct: 54, supply_days_current: 2.1 },
          orders: { action: "hold", lifecycle_state: "active", status: "queued" },
        },
      },
      {
        id: "u3",
        side: "ALLIED",
        name: "5th Marines",
        kind: "ground",
        unit_type: "INFANTRY",
        location_id: "LUNGA_POINT",
        readiness: 63,
        inspector: {
          command: {
            hq_unit_id: null,
            superior: null,
            next_superior: null,
            subordinates: [],
            commander: "Col. Del Valle",
          },
          attachments_support: {
            attachments: [],
            support: [],
            detached: [],
          },
          operational_state: {
            posture: "defend",
            readiness: 63,
            fatigue: 18,
            loc: { state: "connected", label: "LOC Connected", detail: "Shore route holding." },
          },
          supply: { supply_pct: 71, supply_days_current: 3.6 },
        },
      },
    ],
    objectives: [{ id: "o1", name: "Henderson Field", side: "ALLIED", state: "held_allied", value: 5 }],
  };
}

test("land operations summary stays grounded in exposed command, support, LOC, and operation data", () => {
  const snapshot = buildLandSnapshot();
  const summary = summarizeLandOperations(snapshot, [
    {
      id: "lunga_slice:offensive:o1",
      scenarioId: "lunga_slice",
      name: "Watchtower Counterstroke",
      type: "offensive",
      objectiveId: "o1",
      objectiveName: "Henderson Field",
      leadHq: "Henderson Perimeter HQ",
      participants: [
        { unitId: "u1", name: "1st Marines", roleId: "main_effort" },
        { unitId: "u2", name: "2nd Marines", roleId: "support" },
      ],
      airRole: "cas",
      navalRole: "shore_support",
      tempo: "standard",
      estimatedPrepHours: 6,
      approvedAtTurn: 4,
      approvedAtHours: 12,
    },
  ]);

  assert.equal(summary.available, true);
  assert.equal(summary.overview.metrics[0].value, "3");
  assert.equal(summary.oob.groups[0].label, "Henderson Perimeter HQ");
  assert.deepEqual(summary.oob.groups[0].formations.map((row) => row.name), ["1st Marines", "2nd Marines"]);
  assert.equal(summary.supportAssignments.rows[0].name, "1st Marines");
  assert.match(summary.supportAssignments.rows[0].assignment, /11th Marines Battalion/);
  assert.equal(summary.locAlerts.rows[0].name, "2nd Marines");
  assert.equal(summary.locAlerts.rows[0].status, "LOC Threatened");
  assert.equal(summary.readinessPosture.rows[0].name, "2nd Marines");
  assert.match(summary.readinessPosture.rows[0].condition, /49 readiness/);
  assert.equal(summary.operations.rows.length, 2);
  assert.equal(summary.operations.rows[0].operation, "Watchtower Counterstroke");
  assert.match(summary.operations.rows[0].support, /CAS • Unavailable/);
});

test("land operations summary stays truthful when no visible land formations are exposed", () => {
  const summary = summarizeLandOperations({
    scenario: { id: "empty", name: "No Land Units" },
    units: [{ id: "air-1", side: "ALLIED", name: "Air Wing", kind: "air", unit_type: "AIR" }],
    objectives: [],
  });

  assert.equal(summary.available, false);
  assert.equal(summary.overview.metrics[0].value, "0");
  assert.equal(summary.oob.groups.length, 0);
  assert.equal(summary.supportAssignments.rows.length, 0);
  assert.equal(summary.locAlerts.rows.length, 0);
  assert.equal(summary.readinessPosture.rows.length, 0);
  assert.equal(summary.operations.rows.length, 0);
});

test("land operations summary treats raw unit supply as percent when no sustainment-days detail is exposed", () => {
  const summary = summarizeLandOperations({
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    units: [
      {
        id: "u-fallback",
        side: "ALLIED",
        name: "ROK Marine Regiment",
        kind: "ground",
        unit_type: "INFANTRY",
        supply: 80,
        readiness: 66,
        inspector: {
          operational_state: {
            posture: "move",
            readiness: 66,
            fatigue: 6,
            loc: { state: "connected", label: "Connected", detail: "Port corridor intact." },
          },
          supply: {
            supply_pct: 80,
            supply_display: "80%",
            supply_days_current: null,
          },
        },
      },
    ],
    objectives: [],
  });

  assert.equal(summary.readinessPosture.rows[0].name, "ROK Marine Regiment");
  assert.equal(summary.readinessPosture.rows[0].sustainment, "80% supply • Connected");
});
