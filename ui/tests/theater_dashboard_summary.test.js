import test from "node:test";
import assert from "node:assert/strict";

import { summarizeCommunications } from "../src/components/shell/communications_summary.js";
import { summarizeHendersonPressureBoard } from "../src/components/shell/henderson_pressure_board_summary.js";
import { summarizeIntelligenceBranch } from "../src/components/shell/intelligence_branch_summary.js";
import { summarizeReinforcementsBoard } from "../src/components/shell/reinforcements_board_summary.js";
import { summarizeTheaterDashboard } from "../src/components/shell/theater_dashboard_summary.js";

function buildDashboardSnapshot() {
  return {
    scenario: { id: "lunga_slice", name: "Lunga Point Slice" },
    campaign: { status: "ongoing", score_by_side: { ALLIED: 40, AXIS: 18 }, win_score: 100 },
    time: { turn: 4, time_remaining_hours: 36, current_hours: 12 },
    weather: {
      condition: "Humid Overcast",
      ground: "mud",
      forecast: [{ id: "wx-1", hour: 12, visibility: "limited" }],
    },
    pressure: { summary: null, reasons: ["bloody_ridge_contact"], active: true, details: {} },
    reports: {
      pending_count: 2,
      recent: [
        {
          id: "r1",
          kind: "status",
          title: "Bloody Ridge Contact",
          summary: "Japanese probing pressure is building near Bloody Ridge.",
          severity: "warn",
          time: 12,
          sender_label: "Bloody Ridge Outpost",
          local_area_id: "bloody-ridge",
        },
      ],
    },
    staff: { summary: "Operations watch elevated.", load: 3 },
    ai: { enabled: true, last_intent: "maintain_perimeter" },
    units: [
      {
        id: "u1",
        side: "ALLIED",
        name: "1st Marines",
        unit_type: "INFANTRY",
        readiness: 70,
        morale: 74,
        supply: "4.0 days",
        kind: "ground",
        location_id: "BLOODY_RIDGE",
        inspector: {
          command: {
            hq_unit_id: "US-HQ-HENDERSON",
            superior: {
              id: "US-HQ-HENDERSON",
              name: "Henderson Perimeter HQ",
              side: "ALLIED",
              kind: "headquarters",
            },
            next_superior: null,
            subordinates: [],
            commander: "Maj. Gen. A. A. Vandegrift",
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
            morale: 74,
            cohesion: 68,
            loc: { state: "connected", label: "LOC Connected", detail: "Local corridor holding." },
          },
          supply: { supply_pct: 78, supply_days_current: "4.0 days" },
          movement: { remaining: "free", km_remaining: 8 },
        },
      },
      {
        id: "u2",
        side: "ALLIED",
        name: "2nd Marines",
        unit_type: "INFANTRY",
        readiness: 49,
        morale: 46,
        supply: "2.1 days",
        kind: "ground",
        location_id: "KUKUM",
        inspector: {
          command: {
            hq_unit_id: "US-HQ-HENDERSON",
            superior: {
              id: "US-HQ-HENDERSON",
              name: "Henderson Perimeter HQ",
              side: "ALLIED",
              kind: "headquarters",
            },
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
            morale: 46,
            cohesion: 44,
            loc: { state: "threatened", label: "LOC Threatened", detail: "Supply route under pressure." },
          },
          supply: { supply_pct: 54, supply_display: "2.1 days", supply_days_current: 2.1 },
          movement: { remaining: "restricted", km_remaining: 3 },
          orders: { action: "hold", lifecycle_state: "active", status: "queued" },
          replacement_quality: {
            replacement_quality_band: "Regular",
            experience_band: "Green",
            newcomer_pct: 42,
            veteran_core_pct: 39,
            reconstitution_state: "recovering",
            combat_cohesion_state: "degraded",
          },
        },
      },
      { side: "AXIS", readiness: 58, morale: 68, supply: "3.0 days" },
    ],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 4, y: 4 }],
    ports: [{ id: "LUNGA_POINT", name: "Lunga Point", x: 3, y: 4 }],
    naval_support_windows: [{ id: "nsw-1", label: "Offshore Fires", side: "ALLIED", start_hour: 8, end_hour: 18 }],
    force_changes: {
      reinforcements: [
        {
          id: "US-2MAR",
          name: "2nd Marine Regiment",
          side: "ALLIED",
          kind: "INFANTRY",
          day: 2,
          location_id: "LUNGA_POINT",
          hq_unit_id: "I_MARINE_AMPHIBIOUS_CORPS",
          x: 0,
          y: 0,
        },
      ],
      withdrawals: [
        {
          id: "IJN-SCREEN",
          name: "Tokyo Express Screen",
          side: "AXIS",
          kind: "NAVAL",
          day: 3,
          location_id: "LUNGA_POINT",
          hq_unit_id: null,
          x: null,
          y: null,
        },
      ],
      replacement_events: [],
    },
    objectives: [{ id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", value: 5 }],
    local_pressure_areas: [
      {
        id: "bloody-ridge",
        label: "Bloody Ridge",
        kind: "approach",
        location_id: "HENDERSON_FIELD",
        objective_id: "o1",
        pressure_reasons: ["bloody_ridge_contact"],
        defensive_preparation: {
          state: "Prepared",
          fortification_state: "Field positions established.",
          obstacle_state: "Wire obstacles reported.",
          engineer_state: "Engineers reinforcing the line.",
        },
      },
      {
        id: "lunga-point",
        label: "Lunga Point",
        kind: "shore",
        location_id: "LUNGA_POINT",
        objective_id: "o1",
        pressure_reasons: [],
        defensive_preparation: {
          state: "Light",
          fortification_state: "Fieldworks remain light near the shoreline.",
          obstacle_state: "Obstacle detail not separately exposed.",
          engineer_state: "Engineer effort remains limited.",
        },
      },
    ],
  };
}

test("theater dashboard summary stays truthful and uses visible snapshot data only", () => {
  const snapshot = buildDashboardSnapshot();
  const operations = [
    {
      id: "lunga_slice:offensive:o1",
      scenarioId: "lunga_slice",
      name: "Offensive • Henderson Field",
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
  ];
  const summary = summarizeTheaterDashboard(snapshot, null, operations);
  const communications = summarizeCommunications(snapshot, operations);
  const intelligenceBranch = summarizeIntelligenceBranch(snapshot, operations);
  const reinforcementsBoard = summarizeReinforcementsBoard(snapshot);

  assert.equal(summary.land.totalUnits, 3);
  assert.equal(summary.land.alliedUnits, 2);
  assert.equal(summary.land.axisUnits, 1);
  assert.equal(summary.land.averageReadiness, 59);
  assert.equal(summary.logistics.supplyAverage, 3);
  assert.equal(summary.campaignPicture.available, true);
  assert.equal(summary.campaignPicture.objectiveProgress, "Held Allied 1");
  assert.equal(summary.campaignPicture.keyObjective, "Henderson Field (Held Allied)");
  assert.equal(summary.campaignPicture.scoreSummary, "Allied 40 • Axis 18");
  assert.equal(summary.campaignPicture.pressureSummary, "Bloody Ridge Contact");
  assert.equal(summary.intelligence.latestTitle, "AI Command Update");
  assert.equal(summary.staff.ai, "Enabled");
  assert.equal(summary.timeline[0].timeLabel, "Recorded at T+12h");
  assert.deepEqual(summary.localBattle, summarizeHendersonPressureBoard(snapshot, operations));
  assert.equal(summary.landForces.available, true);
  assert.deepEqual(summary.landForces.metrics, [
    { label: "Visible Formations", value: "2" },
    { label: "HQ Linked", value: "2" },
    { label: "HQ Records", value: "1" },
    { label: "LOC Alerts", value: "1" },
  ]);
  assert.equal(summary.landForces.oob.headline, "1 HQ record across 2 linked formations.");
  assert.equal(summary.landForces.oob.rows[0].label, "Henderson Perimeter HQ");
  assert.equal(summary.landForces.oob.rows[0].value, "2 formations");
  assert.match(summary.landForces.oob.rows[0].note, /1st Marines, 2nd Marines/i);
  assert.equal(summary.landForces.support.headline, "2 formations with support or attachment exposure.");
  assert.equal(summary.landForces.support.rows[0].label, "1st Marines");
  assert.equal(summary.landForces.support.rows[0].value, "11th Marines Battalion");
  assert.equal(summary.landForces.loc.headline, "1 visible LOC alert.");
  assert.equal(summary.landForces.loc.rows[0].label, "2nd Marines");
  assert.equal(summary.landForces.loc.rows[0].value, "LOC Threatened");
  assert.equal(summary.landForces.organization.headline, "1 reserve posture • 1 active order.");
  assert.equal(summary.landForces.organization.rows[0].value, "1 HQ record visible");
  assert.equal(summary.landForces.organization.rows[1].value, "1 reserve posture • 1 active order");
  assert.match(summary.landForces.organization.rows[2].note, /2 formations show attached or detached support exposure/i);
  assert.equal(summary.operations.available, true);
  assert.equal(summary.operations.total, 1);
  assert.equal(summary.operations.lead.name, "Offensive • Henderson Field");
  assert.equal(summary.operations.lead.status, "Moving to Start Line");
  assert.match(summary.operations.lead.supportAssigned[0], /CAS • Not exposed/i);
  assert.match(summary.operations.lead.supportAssigned[1], /Shore Support • Available/i);
  assert.equal(summary.localBattle.perimeterStatus[0].value, "Under Pressure");
  assert.equal(summary.turnBrief.priorityFocus, "Bloody Ridge Under Pressure");
  assert.match(summary.turnBrief.note, /Turn 4 brief built only from exposed pressure, support, reporting, force-change, and readiness concerns/i);
  assert.match(summary.turnBrief.lines[0], /Bloody Ridge Under Pressure/i);
  assert(summary.turnBrief.actionItems.some((item) => /Sustainment strained across local formations/i.test(item)));
  assert(summary.turnBrief.actionItems.some((item) => /bloody ridge remains unresolved on the current shell path/i.test(item)));
  assert(summary.turnBrief.actionItems.some((item) => /Arrival • 2nd Marine Regiment Day 2 • due in 1 day/i.test(item)));
  assert(summary.turnBrief.actionItems.some((item) => /Limited visibility is the current exposed weather limitation/i.test(item)));
  assert.equal(summary.communicationsIntel.latestDispatch.id, communications.latest.id);
  assert.equal(summary.communicationsIntel.latestDispatch.title, communications.latest.title);
  assert.equal(summary.communicationsIntel.latestDispatch.senderLabel, communications.latest.senderLabel);
  assert.equal(summary.communicationsIntel.localContact, summary.localBattle.recentContacts[0].title);
  assert.equal(summary.communicationsIntel.reconLimitation, intelligenceBranch.recon.detail);
  assert.equal(summary.communicationsIntel.reportingLimitation, intelligenceBranch.confidence.detail);
  assert.equal(summary.communicationsIntel.keyConcern, intelligenceBranch.concerns[0]);
  assert.equal(summary.reinforcementsWithdrawals.nextChange.headline, "Arrival • 2nd Marine Regiment");
  assert.equal(summary.reinforcementsWithdrawals.nextChange.detail, reinforcementsBoard.arrivals[0].timing);
  assert.equal(summary.reinforcementsWithdrawals.incoming[0].command, "I_MARINE_AMPHIBIOUS_CORPS");
  assert.equal(summary.reinforcementsWithdrawals.outgoing[0].name, "Tokyo Express Screen");
  assert.match(summary.reinforcementsWithdrawals.planningWarning, /Replacement-impact events are not exposed/i);
  assert.equal(summary.forceQuality.available, true);
  assert.equal(summary.forceQuality.rowCount, 2);
  assert.equal(summary.forceQuality.rows[0].name, "1st Marines");
  assert.equal(summary.forceQuality.rows[0].supplySecondary, "LOC Connected");
  assert.equal(summary.forceQuality.rows[1].posture, "Reserve");
  assert.match(summary.forceQuality.rows[1].note, /LOC threatened/i);
  assert.equal(summary.forceQuality.rows[1].veteranPrimary, "39% veteran core");
  assert.equal(summary.forceQuality.rows[1].veteranSecondary, "42% newcomers");
  assert.equal(summary.supportPicture.available, true);
  assert.equal(summary.supportPicture.rows[0].status, "Humid Overcast • Daylight");
  assert.equal(summary.supportPicture.rows[1].status, "Not exposed");
  assert.equal(summary.supportPicture.rows[2].status, "Available");
  assert.equal(summary.supportPicture.rows[3].status, "Strained");
  assert.equal(summary.supportPicture.rows[4].status, "Mixed");
  assert.match(summary.supportPicture.immediateConstraint, /fall below 3\.0 days current tempo/i);
});

test("theater dashboard comparison mode uses the immediately previous snapshot only", () => {
  const snapshot = buildDashboardSnapshot();
  const previousSnapshot = buildDashboardSnapshot();

  previousSnapshot.time = { turn: 3, time_remaining_hours: 42, current_hours: 6 };
  previousSnapshot.weather = {
    condition: "Clear",
    ground: "dry",
    forecast: [{ id: "wx-0", hour: 6, visibility: "good" }],
  };
  previousSnapshot.pressure = { summary: null, reasons: [], active: false, details: {} };
  previousSnapshot.reports = {
    pending_count: 1,
    recent: [
      {
        id: "r0",
        kind: "status",
        title: "Kukum Watch Quiet",
        summary: "Local contact picture remains quiet around Kukum.",
        severity: "info",
        time: 6,
        sender_label: "Kukum Watch",
        local_area_id: "lunga-point",
      },
    ],
  };
  previousSnapshot.units[0].readiness = 74;
  previousSnapshot.units[0].morale = 76;
  previousSnapshot.units[0].supply = "4.6 days";
  previousSnapshot.units[0].inspector.operational_state.readiness = 74;
  previousSnapshot.units[0].inspector.operational_state.fatigue = 10;
  previousSnapshot.units[0].inspector.operational_state.morale = 76;
  previousSnapshot.units[0].inspector.operational_state.cohesion = 71;
  previousSnapshot.units[0].inspector.supply = { supply_pct: 85, supply_days_current: "4.6 days" };
  previousSnapshot.units[1].readiness = 42;
  previousSnapshot.units[1].morale = 40;
  previousSnapshot.units[1].supply = "1.4 days";
  previousSnapshot.units[1].inspector.operational_state.readiness = 42;
  previousSnapshot.units[1].inspector.operational_state.fatigue = 45;
  previousSnapshot.units[1].inspector.operational_state.morale = 40;
  previousSnapshot.units[1].inspector.operational_state.cohesion = 38;
  previousSnapshot.units[1].inspector.operational_state.loc = {
    state: "broken",
    label: "LOC Broken",
    detail: "Local supply route temporarily cut.",
  };
  previousSnapshot.units[1].inspector.supply = { supply_pct: 38, supply_display: "1.4 days", supply_days_current: 1.4 };
  previousSnapshot.local_pressure_areas[0].pressure_reasons = [];
  previousSnapshot.naval_support_windows = [];

  const summary = summarizeTheaterDashboard(snapshot, previousSnapshot);

  assert.equal(summary.comparison.available, true);
  assert.equal(summary.comparison.sourceLabel, "Previous snapshot • Turn 3 • T+6h");
  assert.match(summary.comparison.note, /immediately previous authoritative snapshot captured in this session/i);
  assert.equal(summary.comparison.localBattle.tone, "changed");
  assert.match(summary.comparison.localBattle.summary, /Active pressure now centered on Bloody Ridge \(Under Pressure\)/i);
  assert.equal(summary.comparison.communicationsIntel.tone, "changed");
  assert.match(summary.comparison.communicationsIntel.summary, /New latest dispatch: AI Command Update/i);
  assert.equal(summary.comparison.forceQuality.rows.u1.tone, "down");
  assert.match(summary.comparison.forceQuality.rows.u1.summary, /Readiness -4/i);
  assert.equal(summary.comparison.forceQuality.rows.u2.tone, "up");
  assert.match(summary.comparison.forceQuality.rows.u2.summary, /Readiness \+7/i);
  assert.equal(summary.comparison.supportPicture.rows.weather.tone, "down");
  assert.match(summary.comparison.supportPicture.rows.weather.summary, /Visibility worsened from Good visibility to Limited visibility/i);
  assert(summary.comparison.highlights.some((item) => /Active pressure now centered on Bloody Ridge/i.test(item)));
  assert(summary.comparison.highlights.some((item) => /1st Marines: Readiness -4/i.test(item)));
});
