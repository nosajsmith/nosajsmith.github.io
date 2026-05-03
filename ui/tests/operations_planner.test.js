import test from "node:test";
import assert from "node:assert/strict";

import { buildMapScene } from "../src/components/shell/map_scene.js";
import {
  buildMapCommandPreview,
  createApprovedOperation,
  createOperationPlannerState,
  seedPlannerStateFromMapCommand,
  sanitizeOperationPlannerState,
  summarizeOperationPlanner,
  summarizeTrackedOperations,
} from "../src/components/shell/operations_planner.js";

function buildPlannerSnapshot() {
  return {
    scenario: { id: "lunga_slice", name: "Lunga Point Slice" },
    time: { current_hours: 12 },
    weather: {
      condition: "Humid Overcast",
      forecast: [{ id: "wx-1", hour: 12, visibility: "limited" }],
    },
    units: [
      {
        id: "u1",
        name: "1st Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        x: 0,
        y: 0,
        readiness: 72,
        inspector: {
          command: {
            hq_unit_id: "US-HQ-HENDERSON",
            superior: { id: "US-HQ-HENDERSON", name: "Henderson Perimeter HQ" },
          },
          attachments_support: {
            attachments: [],
            support: ["11th Marines Battalion"],
            detached: [],
          },
          operational_state: {
            readiness: 72,
            fatigue: 14,
            loc: { state: "connected", label: "LOC Connected" },
          },
          supply: { supply_pct: 82, supply_days_current: 4.2 },
          movement: { remaining: "free", km_remaining: 8 },
        },
      },
      {
        id: "u2",
        name: "2nd Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        x: 1.2,
        y: 1.2,
        readiness: 54,
        inspector: {
          command: {
            hq_unit_id: "US-HQ-HENDERSON",
            superior: { id: "US-HQ-HENDERSON", name: "Henderson Perimeter HQ" },
          },
          attachments_support: {
            attachments: ["Engineer Detachment"],
            support: [],
            detached: [],
          },
          operational_state: {
            readiness: 54,
            fatigue: 24,
            loc: { state: "threatened", label: "LOC Threatened" },
          },
          supply: { supply_pct: 58, supply_days_current: 2.4 },
          movement: { remaining: "free", km_remaining: 2 },
        },
      },
      {
        id: "u3",
        name: "5th Marines",
        side: "ALLIED",
        kind: "ground",
        unit_type: "INFANTRY",
        x: 4,
        y: 3,
        readiness: 67,
        inspector: {
          command: {
            hq_unit_id: "US-HQ-HENDERSON",
            superior: { id: "US-HQ-HENDERSON", name: "Henderson Perimeter HQ" },
          },
          attachments_support: {
            attachments: [],
            support: [],
            detached: ["Scout Platoon"],
          },
          operational_state: {
            readiness: 67,
            fatigue: 18,
            loc: { state: "connected", label: "LOC Connected" },
          },
          supply: { supply_pct: 76, supply_days_current: 3.6 },
          movement: { remaining: "free", km_remaining: 4 },
        },
      },
      {
        id: "hq-1",
        name: "Henderson HQ",
        side: "ALLIED",
        kind: "ground",
        unit_type: "HEADQUARTERS",
        x: 0.4,
        y: 0.3,
      },
    ],
    objectives: [
      { id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", x: 0.5, y: 0.5 },
    ],
    local_pressure_areas: [
      { id: "henderson-field", label: "Henderson Field", kind: "objective", location_id: "HENDERSON_FIELD", objective_id: "o1", pressure_reasons: [] },
      { id: "lunga-point", label: "Lunga Point", kind: "shore", location_id: "LUNGA_POINT", objective_id: "o1", pressure_reasons: [] },
    ],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 0.5, y: 0.5 }],
    ports: [{ id: "LUNGA_POINT", name: "Lunga Point", x: 2, y: 2 }],
    naval_support_windows: [{ id: "ns-1", label: "Offshore Fires", side: "ALLIED", start_hour: 8, end_hour: 18 }],
  };
}

test("operations planner summary stays objective-driven and truthful for the v0 offensive workflow", () => {
  const snapshot = buildPlannerSnapshot();
  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const state = {
    ...createOperationPlannerState(snapshot.scenario.id),
    greaseEnabled: true,
    plannerOpen: true,
    objectiveId: "o1",
    unitRoles: {
      u1: "main_effort",
      u2: "support",
    },
    airRole: "cas",
    navalRole: "shore_support",
    tempo: "night_movement",
    approved: true,
  };

  const summary = summarizeOperationPlanner(snapshot, scene, state);

  assert.equal(summary.identity.type, "Offensive");
  assert.equal(summary.identity.leadHq, "Henderson Perimeter HQ");
  assert.equal(summary.objectiveArea.name, "Henderson Field");
  assert.equal(summary.objectiveArea.marker.status, "approved");
  assert.deepEqual(summary.groundForces.rows.map((row) => row.name), ["1st Marines", "2nd Marines", "5th Marines"]);
  assert.equal(summary.groundForces.rows[0].roleLabel, "Main Effort");
  assert.equal(summary.groundForces.rows[0].assemblyEstimate, "Current-step");
  assert.equal(summary.groundForces.rows[1].roleLabel, "Support");
  assert.equal(summary.groundForces.rows[1].assemblyEstimate, "~6h");
  assert.equal(summary.airSupport.availability, "Not exposed");
  assert.equal(summary.navalSupport.availability, "Available");
  assert.equal(summary.staffEstimate.prepDays, "0.25 day");
  assert(summary.staffEstimate.warnings.some((warning) => /demo request only/i.test(warning)));
  assert(summary.staffEstimate.warnings.some((warning) => /night movement is selected before current night conditions/i.test(warning)));
  assert.equal(summary.approval.ready, true);
  assert.equal(summary.approval.objective, "Henderson Field");
  assert.match(summary.approval.participatingForces[0], /1st Marines \(Main Effort\)/);
  assert.match(summary.approval.supportAssigned[0], /CAS • Not exposed/);
  assert.equal(summary.currentPlan.headline, "Offensive • Henderson Field");
  assert.match(summary.note, /frontend shell state only/i);
});

test("approved demo operations become tracked shell objects with compact lifecycle state", () => {
  const snapshot = buildPlannerSnapshot();
  const approvedOperation = createApprovedOperation(snapshot, {
    ...createOperationPlannerState(snapshot.scenario.id),
    objectiveId: "o1",
    name: "Offensive • Henderson Field",
    unitRoles: {
      u1: "main_effort",
      u2: "support",
    },
    airRole: "cas",
    navalRole: "shore_support",
    tempo: "standard",
    approved: true,
  });

  const tracked = summarizeTrackedOperations(snapshot, [approvedOperation]);

  assert.equal(tracked.available, true);
  assert.equal(tracked.total, 1);
  assert.equal(tracked.lead.status, "Moving to Start Line");
  assert.equal(tracked.lead.prepStatus, "~6h to assembly");
  assert.equal(tracked.lead.leadHq, "Henderson Perimeter HQ");
  assert.match(tracked.lead.participatingForces[0], /1st Marines \(Main Effort\)/);
  assert.match(tracked.lead.supportAssigned[0], /CAS • Not exposed/);
  assert.match(tracked.lead.supportAssigned[1], /Shore Support • Available/);
  assert.match(tracked.note, /frontend demo command objects/i);

  const engagedSnapshot = buildPlannerSnapshot();
  engagedSnapshot.time.current_hours = 18;
  engagedSnapshot.local_pressure_areas[0].pressure_reasons = ["bloody_ridge_contact"];
  engagedSnapshot.reports = {
    recent: [
      {
        id: "r1",
        title: "Henderson Contact",
        summary: "Heavy contact around Henderson Field.",
        severity: "warn",
        local_area_id: "henderson-field",
      },
    ],
  };

  const engaged = summarizeTrackedOperations(engagedSnapshot, [approvedOperation]);
  assert.equal(engaged.lead.status, "Securing Objective");
  assert.match(engaged.lead.statusDetail, /friendly hands/i);
});

test("operations planner sanitizes stale demo planner state against the current snapshot", () => {
  const snapshot = buildPlannerSnapshot();
  const sanitized = sanitizeOperationPlannerState(snapshot, {
    ...createOperationPlannerState(snapshot.scenario.id),
    greaseEnabled: true,
    plannerOpen: true,
    selectingObjective: true,
    objectiveId: "missing-objective",
    unitRoles: { ghost: "main_effort", u1: "invalid-role" },
    airRole: "invalid-air-role",
    navalRole: "invalid-naval-role",
    tempo: "warp",
    approved: true,
  });

  assert.equal(sanitized.objectiveId, null);
  assert.deepEqual(sanitized.unitRoles, {});
  assert.equal(sanitized.airRole, "none");
  assert.equal(sanitized.navalRole, "none");
  assert.equal(sanitized.tempo, "standard");
  assert.equal(sanitized.approved, false);
});

test("map move shortcuts stay objective-driven when the clicked target lands on the objective hex", () => {
  const snapshot = buildPlannerSnapshot();
  const preview = buildMapCommandPreview(snapshot, "u1", { q: 1, r: 0 });
  assert.ok(preview);
  assert.equal(preview.commandIntent, "move");
  assert.equal(preview.mode, "immediate");
  assert.equal(preview.targetLabel, "Henderson Field");

  const seeded = seedPlannerStateFromMapCommand(snapshot, createOperationPlannerState(snapshot.scenario.id), preview);
  assert.equal(seeded.commandSource, "map_shortcut");
  assert.equal(seeded.commandIntent, "move");
  assert.equal(seeded.seedUnitId, "u1");
  assert.deepEqual(seeded.targetHex, { q: 1, r: 0 });
  assert.equal(seeded.targetLabel, "Henderson Field");
  assert.equal(seeded.objectiveId, "o1");
  assert.equal(seeded.unitRoles.u1, "main_effort");
  assert.equal(seeded.approved, true);
});

test("map move shortcuts do not guess a named objective from a nearby hex", () => {
  const snapshot = buildPlannerSnapshot();
  const preview = buildMapCommandPreview(snapshot, "u1", { q: 2, r: 0 });
  assert.ok(preview);
  assert.equal(preview.commandIntent, "move");
  assert.equal(preview.mode, "planner_review");
  assert.equal(preview.targetLabel, "Hex 2, 0");
  assert.equal(preview.objectiveId, null);
  assert.equal(preview.objectiveName, null);
  assert.match(preview.note, /deliberate objective review/i);

  const seeded = seedPlannerStateFromMapCommand(snapshot, createOperationPlannerState(snapshot.scenario.id), preview);
  assert.equal(seeded.commandSource, "map_shortcut");
  assert.equal(seeded.commandIntent, "move");
  assert.equal(seeded.seedUnitId, "u1");
  assert.deepEqual(seeded.targetHex, { q: 2, r: 0 });
  assert.equal(seeded.targetLabel, "Hex 2, 0");
  assert.equal(seeded.objectiveId, null);
  assert.equal(seeded.selectingObjective, true);
  assert.equal(seeded.approved, false);
});

test("map attack shortcuts stay deterministic and use the same planner seed path", () => {
  const snapshot = buildPlannerSnapshot();
  snapshot.units.push({
    id: "e1",
    name: "Sendai Regiment",
    side: "AXIS",
    kind: "ground",
    unit_type: "INFANTRY",
    x: 1,
    y: 0,
  });

  const preview = buildMapCommandPreview(snapshot, "u1", { q: 1, r: 0 });
  assert.ok(preview);
  assert.equal(preview.commandIntent, "attack");
  assert.equal(preview.mode, "immediate");
  assert.equal(preview.enemyTargetId, "e1");
  assert.equal(preview.targetLabel, "Sendai Regiment");

  const seeded = seedPlannerStateFromMapCommand(snapshot, createOperationPlannerState(snapshot.scenario.id), preview);
  assert.equal(seeded.commandIntent, "attack");
  assert.equal(seeded.commandSource, "map_shortcut");
  assert.equal(seeded.enemyTargetId, "e1");
  assert.equal(seeded.tempo, "immediate");
  assert.equal(seeded.unitRoles.u1, "main_effort");
});
