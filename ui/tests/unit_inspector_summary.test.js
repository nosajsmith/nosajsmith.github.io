import test from "node:test";
import assert from "node:assert/strict";

import { summarizeUnitInspector } from "../src/components/shell/unit_inspector_summary.js";

function sectionByTitle(summary, title) {
  const section = summary.sections.find((entry) => entry.title === title);
  assert.ok(section, `Expected section titled ${title}`);
  return section;
}

test("unit inspector summary organizes authoritative unit state into stable sections", () => {
  const unit = {
    id: "u1",
    name: "1st Marines",
    side: "ALLIED",
    kind: "land",
    location_id: "BLOODY_RIDGE",
    x: 7,
    y: 9,
    strength: 92,
    readiness: 70,
    readiness_band: "steady",
    morale: 76,
    morale_band: "firm",
    status: "holding_line",
    inspector: {
      operational_state: {
        strength_pct: 92,
        readiness: 70,
        readiness_band: "steady",
        fatigue: 14,
        fatigue_trend: "steady",
        morale: 76,
        morale_band: "firm",
        cohesion: null,
        posture: "defend",
        status: "holding_line",
        location_status: null,
        loc: {
          state: "connected",
          label: "LOC Connected",
          detail: "Connected to HQ",
          broken_at: null,
        },
      },
      toe: {
        toe_pct: 92,
        men: { on_hand: 2400, authorized: 2600 },
        tanks: null,
        guns: { on_hand: 12, authorized: 12 },
        vehicles: { on_hand: 84, authorized: 96 },
        missing_summary: "vehicles 12",
      },
      supply: {
        supply_pct: 84,
        supply_display: "4.2 days",
        supply_days_current: 4.2,
        supply_days_defensive: 5.1,
        supply_days_resting: 6.3,
        fuel: null,
        ammo: { HE: 96, SMOKE: 18 },
        rations: null,
      },
      movement: {
        remaining: null,
        km_remaining: null,
      },
      orders: {
        action: "move_to",
        status: "pending",
        lifecycle_state: "Preparing",
        delay_reason: "Held for route clearance",
        note: "Movement route under review.",
      },
      replacement_quality: {
        replacement_quality_band: "Regular",
        experience_band: "Experienced",
        newcomer_pct: 34,
        veteran_core_pct: 66,
        reconstitution_state: "Recovering",
        combat_cohesion_state: "Recovering",
      },
      command: {
        hq_unit_id: "1MAR-DIV",
        superior: { id: "1MAR-DIV", name: "1st Marine Division HQ", side: "ALLIED", kind: "headquarters" },
        next_superior: { id: "IMAC", name: "I Marine Amphibious Corps", side: "ALLIED", kind: "headquarters" },
        subordinates: [
          { id: "11MAR", name: "11th Marines Battery", side: "ALLIED", kind: "artillery" },
        ],
        commander: null,
      },
      attachments_support: {
        attachments: null,
        support: null,
        detached: null,
      },
      branch_specific: {
        artillery: {
          ammo_rounds: { HE: 96, SMOKE: 18 },
          fire_policy: "General Support",
          endurance_days: 7.1,
        },
      },
    },
  };
  const previousUnit = {
    ...unit,
    readiness: 66,
    morale: 76,
    inspector: {
      ...unit.inspector,
      operational_state: {
        ...unit.inspector.operational_state,
        readiness: 66,
        fatigue: 18,
        morale: 76,
        cohesion: null,
      },
      toe: {
        ...unit.inspector.toe,
        men: { on_hand: 2160, authorized: 2600 },
      },
      supply: {
        ...unit.inspector.supply,
        supply_pct: 79,
        supply_display: "3.8 days",
        supply_days_current: 3.8,
      },
      replacement_quality: {
        replacement_quality_band: "Regular",
        experience_band: "Veteran",
        newcomer_pct: 24,
        veteran_core_pct: 72,
        reconstitution_state: "Stable",
        combat_cohesion_state: "Recovering",
      },
    },
  };
  const summary = summarizeUnitInspector(unit, {
    previousUnit,
    previousSnapshotLabel: "previous snapshot (Turn 3 • T+6h)",
  });

  assert.equal(summary.selected, true);
  assert.equal(summary.header.title, "1st Marines");
  assert.equal(summary.header.subtitle, "ALLIED • Land • Defend");
  assert.equal(summary.header.loc.state, "connected");
  assert.equal(summary.header.loc.label, "LOC Connected");
  assert.equal(summary.summary.title, "Current Summary");
  assert.deepEqual(summary.summary.rows, [
    { label: "Side", value: "ALLIED" },
    { label: "Type / Role", value: "Land • Defend" },
    { label: "Location / Hex", value: "BLOODY RIDGE • Hex 7, 9" },
    { label: "Readiness", value: "70" },
    { label: "Fatigue", value: "14" },
    { label: "Supply", value: "4.2 days current tempo" },
  ]);
  assert.match(summary.summary.note, /Tasking Move To\./);
  assert.match(summary.summary.note, /HQ 1st Marine Division HQ\./);
  assert.match(summary.summary.note, /Movement route under review\./);
  assert.deepEqual(
    summary.sections.slice(0, 4).map((section) => section.title),
    ["Formation Summary", "Command Lead", "Access / LOC", "Readiness / Tasking"],
  );
  assert.equal(summary.sections.length, 11);
  const identity = sectionByTitle(summary, "Formation Summary");
  const commander = sectionByTitle(summary, "Command Lead");
  const loc = sectionByTitle(summary, "Access / LOC");
  const toeStatus = sectionByTitle(summary, "Readiness / Tasking");
  const operational = sectionByTitle(summary, "Readiness / Condition");
  const equipment = sectionByTitle(summary, "Strength / Equipment");
  const supplyMovement = sectionByTitle(summary, "Sustainment / Mobility");
  const commandChain = sectionByTitle(summary, "Command / Control");
  const support = sectionByTitle(summary, "Support / Attachments");
  const recentChange = sectionByTitle(summary, "Recent Change");
  const replacement = sectionByTitle(summary, "Experience / Reconstitution");

  assert.equal(identity.rows[0].value, "1st Marines");
  assert.equal(identity.rows[1].value, "ALLIED");
  assert.equal(identity.rows[2].value, "Land • Defend");
  assert.equal(identity.rows[3].value, "BLOODY RIDGE • Hex 7, 9");
  assert.equal(commander.variant, "commander-link");
  assert.equal(commander.commander.rank, "Rank unavailable");
  assert.equal(commander.commander.name, "Commander not exposed");
  assert.equal(commander.commander.insigniaCode, "US");
  assert.match(commander.commander.traits[0], /Commander identity is not yet exposed/i);
  assert.equal(loc.rows[0].value, "LOC Connected");
  assert.equal(loc.rows[1].value, "Connected to HQ");
  assert.equal(toeStatus.rows[0].value, "92%");
  assert.equal(toeStatus.rows[1].value, 2400);
  assert.equal(toeStatus.rows[2].value, 2600);
  assert.equal(toeStatus.rows[3].value, "Holding Line");
  assert.equal(toeStatus.rows[4].value, "Defend");
  assert.equal(toeStatus.rows[5].value, "Move To");
  assert.equal(toeStatus.rows[6].value, "Preparing");
  assert.equal(operational.metrics[0].value, "92%");
  assert.deepEqual(equipment.rows[0], { label: "Men", onHand: 2400, authorized: 2600, status: null });
  assert.deepEqual(equipment.rows[4], { label: "Rifles", onHand: null, authorized: null, status: "Not exposed" });
  assert.equal(supplyMovement.rows[0].value, "4.2 days");
  assert.equal(supplyMovement.rows[2].value, "HE 96, SMOKE 18");
  assert.equal(summary.commanderScreen.formation, "1st Marines");
  assert.equal(summary.commanderScreen.superiorHq, "1st Marine Division HQ");
  assert.equal(summary.commanderScreen.operationalRole, "Defend posture • Move To order • Preparing state");
  assert.match(summary.commanderScreen.profileScope, /approved demo UI presentation/i);
  assert.match(summary.commanderScreen.traits[1], /Holding the line/i);
  assert.match(summary.commanderScreen.cautions[0], /No commander-specific caution record/i);
  assert.equal(commandChain.rows[0].value, "1st Marine Division HQ");
  assert.equal(commandChain.rows[1].value, "I Marine Amphibious Corps");
  assert.equal(commandChain.rows[3].value, "11th Marines Battery");
  assert.equal(support.rows[1].value, "Unavailable");
  assert.equal(support.rows[2].value, "Unavailable");
  assert.equal(replacement.rows[0].value, "Experienced");
  assert.equal(replacement.rows[1].value, "66%");
  assert.equal(replacement.rows[2].value, "34%");
  assert.equal(replacement.rows[3].value, "Regular");
  assert.equal(replacement.rows[4].value, "Recovering");
  assert.equal(replacement.rows[5].value, "Recovering");
  assert.equal(recentChange.rows[0].value, "+240");
  assert.equal(recentChange.rows[1].value, "+0.4 days");
  assert.equal(recentChange.rows[2].value, "+4");
  assert.equal(recentChange.rows[3].value, "-4");
  assert.equal(recentChange.rows[4].value, "-6%");
  assert.equal(recentChange.rows[5].value, "+10%");
  assert.equal(recentChange.rows[6].value, "Veteran -> Experienced");
  assert.equal(recentChange.rows[7].value, "Stable -> Recovering");
  assert.match(recentChange.note, /Compared with previous snapshot \(Turn 3 • T\+6h\)\./);
  assert.match(recentChange.note, /veteran cadre is thinning and newcomer share is rising/i);
});

test("unit inspector summary provides a clear empty state", () => {
  const summary = summarizeUnitInspector(null);

  assert.equal(summary.selected, false);
  assert.equal(summary.header.title, "No selection");
  assert.match(summary.header.subtitle, /Select a visible unit or map object/i);
  assert.deepEqual(summary.sections, []);
});

test("unit inspector summary tolerates units without nested inspector data", () => {
  const summary = summarizeUnitInspector({
    id: "legacy-1",
    name: "Legacy Unit",
    side: "ALLIED",
    kind: "land",
    location_id: "KUKUM",
    x: 4,
    y: 6,
    strength: 51,
    readiness: 42,
    fatigue: 31,
    readiness_band: "fatigued",
    morale: 39,
    morale_band: "shaken",
    supply: "unknown",
    status: null,
  });

  assert.equal(summary.selected, true);
  assert.equal(summary.header.title, "Legacy Unit");
  assert.equal(summary.header.subtitle, "ALLIED • Land");
  assert.equal(summary.header.loc.label, "Location Reported");
  assert.equal(summary.summary.title, "Current Summary");
  assert.deepEqual(summary.summary.rows, [
    { label: "Side", value: "ALLIED" },
    { label: "Type / Role", value: "Land" },
    { label: "Location / Hex", value: "KUKUM • Hex 4, 6" },
    { label: "Readiness", value: "42" },
    { label: "Fatigue", value: "31" },
    { label: "Supply", value: "unknown" },
  ]);
  assert.deepEqual(
    summary.sections.slice(0, 4).map((section) => section.title),
    ["Formation Summary", "Command Lead", "Access / LOC", "Readiness / Tasking"],
  );
  assert.equal(sectionByTitle(summary, "Readiness / Condition").metrics[0].value, "51%");
  assert.equal(sectionByTitle(summary, "Sustainment / Mobility").rows[0].value, "unknown");
  assert.equal(sectionByTitle(summary, "Readiness / Tasking").rows[5].value, "Not exposed");
  assert.equal(sectionByTitle(summary, "Command Lead").commander.name, "Commander not exposed");
  assert.equal(sectionByTitle(summary, "Experience / Reconstitution").rows[0].value, "Unavailable");
  assert.equal(sectionByTitle(summary, "Recent Change").variant, "placeholder");
  assert.match(sectionByTitle(summary, "Recent Change").body, /Previous snapshot unavailable/i);
  assert.equal(sectionByTitle(summary, "Command / Control").rows[0].value, "Unavailable");
});

test("unit inspector summary carries commander-screen detail when commander identity is exposed", () => {
  const summary = summarizeUnitInspector({
    id: "hq-1",
    name: "Americal Division",
    side: "ALLIED",
    kind: "land",
    inspector: {
      operational_state: {
        strength_pct: 87,
        readiness: 73,
        readiness_band: "steady",
        fatigue: 10,
        fatigue_trend: "steady",
        morale: 75,
        morale_band: "firm",
        cohesion: null,
        posture: "prepare",
        status: "assembling",
        location_status: null,
        loc: null,
      },
      toe: {},
      supply: {},
      movement: {},
      command: {
        hq_unit_id: "AMERDIV-HQ",
        superior: { id: "XIV", name: "XIV Corps", side: "ALLIED", kind: "headquarters" },
        next_superior: null,
        subordinates: [],
        commander: "Maj. Gen. Alexander M. Patch",
      },
      attachments_support: {},
      branch_specific: {},
    },
  });

  assert.equal(sectionByTitle(summary, "Command Lead").commander.rank, "Maj. Gen.");
  assert.equal(sectionByTitle(summary, "Command Lead").commander.name, "Alexander M. Patch");
  assert.equal(summary.commanderScreen.assignment, "Formation commander, Americal Division");
  assert.equal(summary.commanderScreen.commandContext, "Headquarters record: AMERDIV-HQ");
  assert.equal(summary.commanderScreen.operationalRole, "Prepare posture • Assembling state");
  assert.match(summary.commanderScreen.profileScope, /Named commander identity is authoritative here/i);
  assert.match(summary.commanderScreen.traits[0], /Named commander record present/i);
  assert.match(summary.commanderScreen.traits[1], /Assembling the formation before commitment/i);
  assert.match(summary.commanderScreen.notes, /Biography, service history, and personal dossier notes are not exposed/);
});

test("unit inspector summary surfaces controlled support detachment state without adding a new module", () => {
  const summary = summarizeUnitInspector({
    id: "tank-420",
    name: "420th Tank Battalion",
    side: "ALLIED",
    kind: "land",
    inspector: {
      operational_state: {
        strength_pct: 84,
        readiness: 70,
        fatigue: 14,
        morale: 76,
        posture: "support",
        status: "attached_support",
        loc: {
          state: "connected",
          label: "LOC Connected",
          detail: "Connected to HQ",
          broken_at: null,
        },
      },
      toe: {},
      supply: {},
      movement: {},
      command: {
        hq_unit_id: null,
        superior: null,
        next_superior: null,
        subordinates: [],
        commander: null,
      },
      attachments_support: {
        attachments: null,
        support: null,
        detached: ["A Company -> 1st Marines"],
        detachment_state: {
          eligible: true,
          detachment_type: "tank_company",
          detachment_label: "Tank Company",
          max_detachments: 3,
          companies_total: 4,
          detached_count: 1,
          remaining_organic_companies: 3,
          remaining_organic_strength_pct: 63,
          parent_cohesion_marker: "Reduced cohesion while detachments are active",
          active_detachments: [],
          attached_detachments: [],
        },
      },
      branch_specific: {
        artillery: null,
      },
    },
  });

  const support = sectionByTitle(summary, "Support / Attachments");
  assert.equal(support.rows[0].label, "Detached Companies");
  assert.equal(support.rows[0].value, "1 / 3");
  assert.equal(support.rows[1].value, "3 companies");
  assert.equal(support.rows[2].value, "63%");
  assert.equal(support.rows[3].value, "Reduced cohesion while detachments are active");
  assert.equal(support.rows[support.rows.length - 1].value, "A Company -> 1st Marines");
});

test("unit inspector summary adapts to air units with honest unavailable airframe detail", () => {
  const summary = summarizeUnitInspector({
    id: "air-1",
    name: "Cactus Air Group",
    side: "ALLIED",
    kind: "air",
    inspector: {
      operational_state: {
        strength_pct: null,
        readiness: 61,
        readiness_band: "steady",
        fatigue: 28,
        fatigue_trend: "rising",
        morale: 69,
        morale_band: "firm",
        cohesion: null,
        posture: "standby",
        status: null,
        location_status: null,
        loc: {
          state: "threatened",
          label: "LOC Threatened",
          detail: "Threatened on supply route",
          broken_at: null,
        },
      },
      toe: {
        toe_pct: null,
        men: null,
        tanks: null,
        guns: null,
        vehicles: null,
        missing_summary: null,
      },
      supply: {
        supply_pct: 73,
        supply_display: "3.1 days",
        supply_days_current: 3.1,
        supply_days_defensive: null,
        supply_days_resting: null,
        fuel: null,
        ammo: null,
        rations: null,
      },
      movement: {
        remaining: null,
        km_remaining: null,
      },
      command: {
        hq_unit_id: null,
        superior: null,
        next_superior: null,
        subordinates: [],
        commander: null,
      },
      attachments_support: {
        attachments: null,
        support: null,
        detached: null,
      },
      branch_specific: {
        artillery: null,
      },
    },
  });

  assert.deepEqual(
    summary.sections.slice(0, 4).map((section) => section.title),
    ["Formation Summary", "Command Lead", "Access / LOC", "Readiness / Tasking"],
  );
  assert.equal(summary.header.loc.state, "threatened");
  assert.equal(sectionByTitle(summary, "Air Readiness / Condition").metrics[4].label, "Serviceability");
  assert.equal(sectionByTitle(summary, "Aircraft / Lift Picture").rows[0].value, "Unavailable");
  assert.match(sectionByTitle(summary, "Aircraft / Lift Picture").note, /not exposed/);
});

test("unit inspector summary adapts to naval and logistics formations", () => {
  const naval = summarizeUnitInspector({
    id: "nav-1",
    name: "Task Force 18",
    side: "ALLIED",
    kind: "naval",
    inspector: {
      operational_state: {
        strength_pct: null,
        readiness: 64,
        readiness_band: null,
        fatigue: 18,
        fatigue_trend: null,
        morale: 71,
        morale_band: null,
        cohesion: null,
        posture: "patrol",
        status: null,
        location_status: null,
        loc: {
          state: "unavailable",
          label: "LOC Unavailable",
          detail: "LOC state unavailable",
          broken_at: null,
        },
      },
      toe: {
        toe_pct: null,
        men: null,
        tanks: null,
        guns: null,
        vehicles: null,
        missing_summary: null,
      },
      supply: {
        supply_pct: null,
        supply_display: "Unavailable",
        supply_days_current: null,
        supply_days_defensive: null,
        supply_days_resting: null,
        fuel: null,
        ammo: null,
        rations: null,
      },
      movement: {
        remaining: null,
        km_remaining: null,
      },
      command: {
        hq_unit_id: null,
        superior: null,
        next_superior: null,
        subordinates: [],
        commander: null,
      },
      attachments_support: {
        attachments: null,
        support: null,
        detached: null,
      },
      branch_specific: {
        artillery: null,
      },
    },
  });

  const logistics = summarizeUnitInspector({
    id: "log-1",
    name: "Service Group",
    side: "ALLIED",
    kind: "logistics",
    inspector: {
      operational_state: {
        strength_pct: 88,
        readiness: 66,
        readiness_band: null,
        fatigue: 12,
        fatigue_trend: null,
        morale: 70,
        morale_band: null,
        cohesion: null,
        posture: "support",
        status: null,
        location_status: null,
        loc: {
          state: "broken",
          label: "LOC Broken",
          detail: "Broken at Lunga Point",
          broken_at: "Lunga Point",
        },
      },
      toe: {
        toe_pct: 88,
        men: { on_hand: 900, authorized: 1000 },
        tanks: null,
        guns: null,
        vehicles: { on_hand: 120, authorized: 140 },
        missing_summary: "vehicles 20",
      },
      supply: {
        supply_pct: 79,
        supply_display: "4.6 days",
        supply_days_current: 4.6,
        supply_days_defensive: null,
        supply_days_resting: null,
        fuel: null,
        ammo: null,
        rations: null,
      },
      movement: {
        remaining: null,
        km_remaining: null,
      },
      command: {
        hq_unit_id: null,
        superior: null,
        next_superior: null,
        subordinates: [],
        commander: null,
      },
      attachments_support: {
        attachments: null,
        support: null,
        detached: null,
      },
      branch_specific: {
        artillery: null,
      },
    },
  });

  assert.deepEqual(
    naval.sections.slice(0, 4).map((section) => section.title),
    ["Formation Summary", "Command Lead", "Access / LOC", "Readiness / Tasking"],
  );
  assert.equal(sectionByTitle(naval, "Task Force Readiness").title, "Task Force Readiness");
  assert.equal(logistics.header.loc.state, "broken");
  assert.equal(logistics.header.loc.detail, "Broken at Lunga Point");
  assert.equal(sectionByTitle(naval, "Task Force Composition").title, "Task Force Composition");
  assert.equal(sectionByTitle(logistics, "Logistics Readiness").title, "Logistics Readiness");
  assert.equal(sectionByTitle(logistics, "Transport Capacity").rows[1].label, "Vehicles");
  assert.deepEqual(sectionByTitle(logistics, "Transport Capacity").rows[1], { label: "Vehicles", onHand: 120, authorized: 140, status: null });
});

test("unit inspector summary surfaces tracked shortcut orders through the same tasking presentation", () => {
  const summary = summarizeUnitInspector({
    id: "u1",
    name: "1st Marines",
    side: "ALLIED",
    kind: "land",
    location_id: "SEOUL_AXIS",
    x: 3,
    y: 4,
    inspector: {
      operational_state: {
        posture: "advance",
        readiness: 71,
        fatigue: 11,
        loc: {
          state: "connected",
          label: "LOC Connected",
          detail: "Linked to the west-axis route",
        },
      },
      toe: { toe_pct: 91, men: { on_hand: 2200, authorized: 2400 } },
      supply: {
        supply_pct: 82,
        supply_display: "4.0 days",
        supply_days_current: 4,
      },
      movement: {},
      command: {
        superior: { name: "X Corps" },
      },
      attachments_support: {},
      branch_specific: {},
    },
  }, {
    operations: [
      {
        id: "shortcut-u1-3-4",
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
        approvedAtTurn: 1,
        approvedAtHours: 6,
        commandIntent: "move",
        source: "map_shortcut",
        seedUnitId: "u1",
        targetHex: { q: 4, r: 4 },
        targetLabel: "Seoul Axis",
        enemyTargetId: null,
      },
    ],
  });

  assert.match(summary.summary.note, /Pending move order through the planner approval path/i);
  assert.equal(sectionByTitle(summary, "Readiness / Tasking").rows[5].value, "Move");
  assert.equal(sectionByTitle(summary, "Readiness / Tasking").rows[6].value, "Queued");
});

test("unit inspector summary prefers live runtime order state when it is exposed", () => {
  const unit = {
    id: "u1",
    name: "1st Marines",
    side: "ALLIED",
    kind: "land",
    location_id: "SEOUL_AXIS",
    x: 3,
    y: 4,
    inspector: {
      operational_state: {
        posture: null,
        readiness: 71,
        fatigue: 11,
        loc: {
          state: "connected",
          label: "LOC Connected",
          detail: "Linked to the west-axis route",
        },
      },
      toe: { toe_pct: 91, men: { on_hand: 2200, authorized: 2400 } },
      supply: {
        supply_pct: 82,
        supply_display: "4.0 days",
        supply_days_current: 4,
      },
      movement: {},
      orders: {
        action: "hold",
        lifecycle_state: "planned",
      },
      command: {
        superior: { name: "X Corps" },
      },
      attachments_support: {},
      branch_specific: {},
    },
  };

  const summary = summarizeUnitInspector(unit, {
    snapshot: {
      bai_report: {
        unit_orders: [
          {
            unit_id: "u1",
            action: "attack",
            lifecycle_state: "executing",
            target_location_id: "SEOUL",
          },
        ],
      },
    },
  });

  assert.equal(summary.header.subtitle, "ALLIED • Land • Attack");
  assert.equal(sectionByTitle(summary, "Readiness / Tasking").rows[5].value, "Attack");
  assert.equal(sectionByTitle(summary, "Readiness / Tasking").rows[6].value, "Executing");
});
