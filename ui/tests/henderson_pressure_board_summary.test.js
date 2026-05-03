import test from "node:test";
import assert from "node:assert/strict";

import { summarizeHendersonPressureBoard } from "../src/components/shell/henderson_pressure_board_summary.js";

test("henderson pressure board summarizes perimeter pressure from local objectives, reasons, and reports only", () => {
  const snapshot = {
    scenario: { id: "00_lunga_point_slice_1942", name: "Lunga Point 1942 (Vertical Slice)" },
    time: { turn: 4, current_hours: 12 },
    weather: { condition: "Humid Overcast" },
    local_pressure_areas: [
      {
        id: "henderson-field",
        label: "Henderson Field",
        kind: "objective",
        location_id: "HENDERSON_FIELD",
        objective_id: "o1",
        pressure_reasons: ["henderson_perimeter_alert"],
        defensive_preparation: {
          state: "Prepared",
          fortification_state: "Airfield perimeter positions and command-post works are in place.",
          obstacle_state: "Wire and field obstacles cover the main approaches.",
          engineer_state: "Engineer maintenance remains active around the field.",
        },
      },
      {
        id: "lunga-point",
        label: "Lunga Point",
        kind: "anchor",
        location_id: "LUNGA_POINT",
        objective_id: "o2",
        pressure_reasons: [],
        defensive_preparation: {
          state: "Developing",
          fortification_state: "Beachhead defensive positions cover the logistics anchor.",
          obstacle_state: null,
          engineer_state: "Engineer labor is split between dumps, shore point, and perimeter upkeep.",
        },
      },
      {
        id: "alligator-creek",
        label: "Alligator Creek",
        kind: "approach",
        location_id: "ALLIGATOR_CREEK",
        objective_id: "o3",
        pressure_reasons: ["alligator_creek_contact"],
        defensive_preparation: {
          state: "Prepared",
          fortification_state: "Creek-line fighting positions reinforce the eastern wire.",
          obstacle_state: "Creek bank and wire obstacles cover the crossing points.",
          engineer_state: "Engineer strengthening is reported along the eastern wire.",
        },
      },
      {
        id: "bloody-ridge",
        label: "Bloody Ridge",
        kind: "objective",
        location_id: "BLOODY_RIDGE",
        objective_id: "o4",
        pressure_reasons: ["bloody_ridge_contact", "henderson_perimeter_alert"],
        defensive_preparation: {
          state: "Developing",
          fortification_state: "Ridge foxholes and firing positions are established but still thin.",
          obstacle_state: "Natural slopes and limited wire delay the southern approach.",
          engineer_state: "Local engineer strengthening is still underway on the ridge line.",
        },
      },
      {
        id: "matanikau-forks",
        label: "Matanikau Forks",
        kind: "approach",
        location_id: "MATANIKAU_FORKS",
        objective_id: "o5",
        pressure_reasons: ["matanikau_pressure"],
        defensive_preparation: {
          state: "Light",
          fortification_state: "Forward screening positions only.",
          obstacle_state: null,
          engineer_state: null,
        },
      },
    ],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 0, y: 0 }],
    ports: [{ id: "LUNGA_POINT", name: "Lunga Point", x: -1, y: 1 }],
    naval_support_windows: [],
    units: [
      {
        id: "u1",
        name: "5th Marines",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "KUKUM",
        inspector: {
          operational_state: { posture: "DEFEND", readiness: 72, fatigue: 10, loc: { state: "connected", detail: "Connected to HQ" } },
          supply: { supply_pct: 85, supply_days_current: 4.2, ammo: null, fuel: null, rations: null },
          movement: { remaining: "mobile", km_remaining: 12 },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
      {
        id: "u2",
        name: "7th Marines",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "ALLIGATOR_CREEK",
        inspector: {
          operational_state: { posture: "DEFEND", readiness: 68, fatigue: 12, loc: { state: "connected", detail: "Connected to HQ" } },
          supply: { supply_pct: 82, supply_days_current: null, ammo: null, fuel: "limited", rations: null },
          movement: { remaining: "restricted", km_remaining: 6 },
          attachments_support: { attachments: ["11th Marines"], support: null, detached: null },
        },
      },
      {
        id: "u3",
        name: "1st Marines",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "BLOODY_RIDGE",
        inspector: {
          operational_state: { posture: "DEFEND", readiness: 45, fatigue: 37, loc: { state: "threatened", detail: "Threatened on supply route" } },
          supply: { supply_pct: 48, supply_days_current: 2.4, ammo: null, fuel: null, rations: null },
          movement: { remaining: "restricted", km_remaining: 2 },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
      {
        id: "u4",
        name: "1st Marine Division HQ",
        side: "ALLIED",
        unit_type: "HEADQUARTERS",
        location_id: "HENDERSON_FIELD",
        inspector: {
          operational_state: { posture: "DEFEND", readiness: 74, fatigue: 6, loc: { state: "connected", detail: "Connected to HQ" } },
          supply: { supply_pct: 90, supply_days_current: null, ammo: null, fuel: null, rations: null },
          movement: { remaining: null, km_remaining: null },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
    ],
    objectives: [
      { id: "o1", name: "Henderson Field", side: "ALLIED", state: "held_allied", value: 100 },
      { id: "o2", name: "Lunga Point", side: "ALLIED", state: "held_allied", value: 75 },
      { id: "o3", name: "Alligator Creek", side: "ALLIED", state: "held_allied", value: 60 },
      { id: "o4", name: "Bloody Ridge", side: "ALLIED", state: "held_allied", value: 60 },
      { id: "o5", name: "Matanikau Forks", side: "AXIS", state: "unheld", value: 45 },
    ],
    pressure: {
      reasons: ["bloody_ridge_contact", "henderson_perimeter_alert"],
    },
    reports: {
      recent: [
        {
          id: "r2",
          title: "East Wire",
          summary: "Eastern wire reports Japanese probing fire and infiltration pressure near Alligator Creek.",
          severity: "warning",
          local_area_id: "alligator-creek",
        },
        {
          id: "r1",
          title: "Perimeter Alarm",
          summary: "Patrols south of Henderson report heavier movement toward Bloody Ridge; perimeter reserves are alerted.",
          severity: "warning",
          local_area_id: "bloody-ridge",
        },
      ],
    },
  };
  const summary = summarizeHendersonPressureBoard(snapshot, [
    {
      id: "lunga_point_slice_1942:offensive:o4",
      scenarioId: "00_lunga_point_slice_1942",
      name: "Watchtower Counterstroke",
      type: "offensive",
      objectiveId: "o4",
      objectiveName: "Bloody Ridge",
      leadHq: "1st Marine Division HQ",
      participants: [{ unitId: "u2", name: "7th Marines", roleId: "main_effort" }],
      airRole: "cas",
      navalRole: "shore_support",
      tempo: "standard",
      estimatedPrepHours: 6,
      approvedAtTurn: 4,
      approvedAtHours: 8,
    },
  ]);

  assert.equal(summary.available, true);
  assert.equal(summary.operationsOverview.title, "Watchtower Counterstroke");
  assert.equal(summary.operationsOverview.activeOperation, "Watchtower Counterstroke • Moving to Start Line");
  assert.equal(summary.operationsOverview.objectiveSituation, "Bloody Ridge • Held Allied");
  assert.match(summary.operationsOverview.localBattle, /Under Pressure/i);
  assert.match(summary.operationsOverview.immediateConcern, /Bloody Ridge/);
  assert.match(summary.operationsOverview.note, /before launch/i);
  assert.equal(summary.perimeterStatus[0].value, "Under Pressure");
  assert.match(summary.perimeterStatus[1].value, /Bloody Ridge/);
  assert.match(summary.perimeterStatus[2].value, /south of Henderson/i);
  assert.equal(summary.pressureAxes[0].label, "Henderson Field");
  assert.equal(summary.pressureAxes[0].status, "Under Pressure");
  assert.equal(summary.pressureAxes[0].kindLabel, "Objective");
  assert.equal(summary.pressureAxes[1].label, "Alligator Creek");
  assert.equal(summary.pressureAxes[1].kindLabel, "Approach");
  assert.match(summary.engagementSummary.summary, /Bloody Ridge/);
  assert.match(summary.engagementSummary.summary, /Alligator Creek/);
  assert.match(summary.engagementSummary.note, /current formations located at those same exposed local positions/i);
  assert.equal(summary.engagementSummary.hotspotsSummary, "Bloody Ridge • Alligator Creek • Henderson Field");
  assert.equal(summary.engagementSummary.formationSummary, "1st Marines • 7th Marines");
  assert.deepEqual(summary.engagementSummary.hotspots.map((area) => area.label), ["Bloody Ridge", "Alligator Creek", "Henderson Field"]);
  assert.equal(summary.engagementSummary.hotspots[0].status, "In Contact");
  assert.match(summary.engagementSummary.hotspots[0].detail, /Bloody Ridge/i);
  assert.equal(summary.engagementSummary.hotspots[1].status, "In Contact");
  assert.deepEqual(summary.engagementSummary.formations.map((unit) => unit.name), ["1st Marines", "7th Marines"]);
  assert.equal(summary.engagementSummary.formations[0].status, "Strained");
  assert.match(summary.engagementSummary.formations[0].detail, /45 readiness/i);
  assert.match(summary.engagementSummary.formations[0].detail, /LOC threatened/i);
  assert.equal(summary.engagementSummary.formations[1].status, "Holding");
  assert.match(summary.engagementSummary.formations[1].detail, /82% supply/i);
  assert.match(summary.reserveStatus, /reserves are alerted/i);
  assert.equal(summary.responseReadiness.summary, "2 ready • 0 limited • 1 spent or committed");
  assert.deepEqual(summary.responseReadiness.units.map((unit) => unit.name), ["5th Marines", "7th Marines", "1st Marines"]);
  assert.equal(summary.responseReadiness.units[0].readiness, "Ready");
  assert.equal(summary.responseReadiness.units[0].location, "Kukum");
  assert.equal(summary.responseReadiness.units[2].readiness, "Spent");
  assert.equal(summary.counterattackPlanning.summary, "1 ready • 1 limited • 1 not ready");
  assert.match(summary.counterattackPlanning.note, /not a combat-odds estimate/i);
  assert.match(summary.counterattackPlanning.bestCandidate, /5th Marines/);
  assert.deepEqual(summary.counterattackPlanning.candidates.map((unit) => unit.name), ["5th Marines", "7th Marines", "1st Marines"]);
  assert.equal(summary.counterattackPlanning.candidates[0].status, "Ready");
  assert.match(summary.counterattackPlanning.candidates[0].factors, /12 km remaining/i);
  assert.equal(summary.counterattackPlanning.candidates[1].status, "Limited");
  assert.match(summary.counterattackPlanning.candidates[1].note, /Movement restricted/i);
  assert.equal(summary.counterattackPlanning.candidates[2].status, "Not Ready");
  assert.match(summary.counterattackPlanning.candidates[2].locDetail, /Threatened on supply route/i);
  assert.equal(summary.defensePreparation.fortificationState, "Mixed");
  assert.equal(summary.defensePreparation.obstacles, "3 local areas reported");
  assert.equal(summary.defensePreparation.engineer, "4 local areas reported");
  assert.equal(summary.defensePreparation.mostPrepared, "Henderson Field (Prepared)");
  assert.equal(summary.defensePreparation.leastPrepared, "Matanikau Forks (Light)");
  assert.match(summary.defensePreparation.note, /scenario-authored local fortification/i);
  assert.deepEqual(
    summary.defensePreparation.areas.map((area) => area.label),
    ["Henderson Field", "Alligator Creek", "Lunga Point", "Bloody Ridge", "Matanikau Forks"],
  );
  assert.equal(summary.defensePreparation.areas[0].state, "Prepared");
  assert.match(summary.defensePreparation.areas[0].fortification, /command-post works/i);
  assert.equal(summary.defensePreparation.areas[4].state, "Light");
  assert.match(summary.defensePreparation.areas[4].engineer, /not separately exposed/i);
  assert.equal(summary.localSustainment.status, "Critical");
  assert.match(summary.localSustainment.resources[0].value, /average/i);
  assert.equal(summary.localSustainment.resources[2].value, "1 formation tracked");
  assert.equal(summary.localSustainment.resources[4].value, "1 formation tracked");
  assert.equal(summary.localSustainment.atRisk[0].name, "1st Marines");
  assert.match(summary.localSustainment.atRisk[0].detail, /48% supply/i);
  assert.match(summary.localSustainment.concerns[0], /below 50% supply/i);
  assert.equal(summary.airSupport.availability, "Not exposed");
  assert.equal(summary.airSupport.sortiePosture, "Sortie posture not exposed");
  assert.match(summary.airSupport.constraint, /Humid Overcast/);
  assert.match(summary.airSupport.supportingFormation, /No locally based air formation/i);
  assert.equal(summary.navalSupport.availability, "Context exposed");
  assert.equal(summary.navalSupport.supportPosture, "Port anchor only");
  assert.match(summary.navalSupport.note, /Lunga Point/);
  assert.match(summary.navalSupport.constraint, /Lunga Point is the only currently exposed shore-support anchor/i);
  assert.deepEqual(summary.recentContacts.map((row) => row.id), ["r1", "r2"]);
});

test("henderson pressure board stays truthful when the local perimeter picture is unavailable", () => {
  const summary = summarizeHendersonPressureBoard({
    scenario: { id: "inchon_mvp", name: "Inchon" },
    local_pressure_areas: [],
    units: [],
    objectives: [{ id: "o1", name: "KIMPO", side: "ALLIED", state: "held_allied", value: 50 }],
    pressure: { reasons: ["enemy_pressure_north"] },
    reports: { recent: [] },
  });

  assert.equal(summary.available, false);
  assert.equal(summary.title, "Inchon Landing Front");
  assert.match(summary.note, /inchon \/ seoul axis pressure is unavailable/i);
  assert.equal(summary.reserveStatus, "Not exposed on the current shell path.");
  assert.equal(summary.engagementSummary.summary, "No current engagement summary is exposed.");
  assert.match(summary.engagementSummary.note, /does not expose local inchon \/ seoul axis battle areas/i);
  assert.equal(summary.engagementSummary.hotspotsSummary, "No named local engagement focus is exposed.");
  assert.equal(summary.engagementSummary.formationSummary, "No formation is directly tied to the exposed local fight.");
  assert.deepEqual(summary.engagementSummary.hotspots, []);
  assert.deepEqual(summary.engagementSummary.formations, []);
  assert.equal(summary.responseReadiness.summary, "No current response-readiness data.");
  assert.match(summary.responseReadiness.note, /does not expose local inchon \/ seoul axis battle areas/i);
  assert.deepEqual(summary.responseReadiness.units, []);
  assert.equal(summary.counterattackPlanning.summary, "No current counterattack-planning data.");
  assert.match(summary.counterattackPlanning.note, /does not expose local inchon \/ seoul axis battle areas/i);
  assert.equal(summary.counterattackPlanning.bestCandidate, "No best-positioned local counterattack formation is exposed.");
  assert.deepEqual(summary.counterattackPlanning.candidates, []);
  assert.equal(summary.defensePreparation.fortificationState, "Unavailable");
  assert.equal(summary.defensePreparation.obstacles, "Not exposed");
  assert.equal(summary.defensePreparation.engineer, "Not exposed");
  assert.equal(summary.defensePreparation.mostPrepared, "No prepared local objective exposed.");
  assert.equal(summary.defensePreparation.leastPrepared, "No lightly prepared local objective exposed.");
  assert.match(summary.defensePreparation.note, /does not expose local inchon \/ seoul axis battle areas/i);
  assert.deepEqual(summary.defensePreparation.areas, []);
  assert.equal(summary.localSustainment.status, "Unavailable");
  assert.match(summary.localSustainment.note, /does not expose the inchon \/ seoul axis picture/i);
  assert.equal(summary.airSupport.availability, "Unavailable");
  assert.match(summary.airSupport.note, /does not expose the inchon \/ seoul axis picture/i);
  assert.equal(summary.navalSupport.availability, "Unavailable");
  assert.match(summary.navalSupport.note, /does not expose the inchon \/ seoul axis picture/i);
  assert.deepEqual(summary.pressureAxes, []);
});

test("henderson pressure board uses snapshot objective truth and by-objective pressure when local reasons are quiet", () => {
  const summary = summarizeHendersonPressureBoard({
    scenario: { id: "00_lunga_point_slice_1942", name: "Lunga Point 1942 (Vertical Slice)" },
    time: { turn: 4, current_hours: 12 },
    weather: { condition: "Humid Overcast" },
    local_pressure_areas: [
      {
        id: "bloody-ridge",
        label: "Bloody Ridge",
        kind: "objective",
        location_id: "BLOODY_RIDGE",
        objective_id: "o1",
        pressure_reasons: [],
      },
    ],
    units: [],
    objectives: [
      {
        id: "o1",
        name: "Bloody Ridge",
        side: "ALLIED",
        state: "held_allied",
        value: 60,
        objective_truth_key: "ALLIED:BLOODY_RIDGE",
      },
    ],
    objective_truth: {
      "ALLIED:BLOODY_RIDGE": { status: "contested", controller_side: "AXIS" },
    },
    pressure: {
      reasons: [],
      by_objective: {
        "ALLIED:BLOODY_RIDGE": {
          location_id: "BLOODY_RIDGE",
          objective_status: "contested",
          pressure_state: "degraded",
          pressure_score: 35,
        },
      },
      total_pressure_score: 35,
    },
    reports: { recent: [] },
  });

  assert.equal(summary.available, true);
  assert.equal(summary.perimeterStatus[0].value, "At Risk");
  assert.equal(summary.perimeterStatus[1].value, "Bloody Ridge At Risk");
  assert.equal(summary.pressureAxes[0].label, "Bloody Ridge");
  assert.equal(summary.pressureAxes[0].status, "At Risk");
  assert.match(summary.pressureAxes[0].detail, /Objective pressure degraded/i);
  assert.equal(summary.engagementSummary.hotspots[0].label, "Bloody Ridge");
  assert.equal(summary.engagementSummary.hotspots[0].status, "At Risk");
  assert.match(summary.engagementSummary.hotspots[0].detail, /score 35/i);
});
