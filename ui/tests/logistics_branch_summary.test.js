import test from "node:test";
import assert from "node:assert/strict";

import { summarizeLogisticsBranch, summarizeLocalSustainment } from "../src/components/shell/logistics_branch_summary.js";

test("logistics branch summary aggregates only exposed sustainment records", () => {
  const summary = summarizeLogisticsBranch({
    staff: { summary: "Sustainment watch elevated.", load: 4 },
    units: [
      {
        id: "log-1",
        name: "Service Group",
        kind: "logistics",
        inspector: {
          supply: { supply_pct: 79, supply_days_current: 4.6, fuel: null, rations: null },
          movement: { remaining: null, km_remaining: null },
          toe: { vehicles: { on_hand: 120, authorized: 140 }, missing_summary: "vehicles 20" },
          operational_state: { loc: { state: "broken", detail: "Broken at Lunga Point" } },
          attachments_support: { attachments: ["Depot Platoon"], support: null, detached: null },
        },
      },
      {
        id: "u-1",
        name: "1st Marines",
        kind: "land",
        inspector: {
          supply: { supply_pct: 61, supply_days_current: 2.4, fuel: "limited", rations: null },
          movement: { remaining: "restricted", km_remaining: 8 },
          toe: { vehicles: null, missing_summary: null },
          operational_state: { loc: { state: "threatened", detail: "Threatened on supply route" } },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
    ],
  });

  assert.equal(summary.overview.formationsTracked, 2);
  assert.equal(summary.overview.logisticsFormations, 1);
  assert.equal(summary.overview.staffLoad, 4);
  assert.equal(summary.transport.vehicleFormationCount, 1);
  assert.equal(summary.transport.movementTrackedCount, 1);
  assert.equal(summary.reserves.fuelTrackedCount, 1);
  assert.equal(summary.support.attachmentTrackedCount, 1);
  assert.equal(summary.tables.lowSupply.length, 1);
  assert.equal(summary.tables.locWarnings.length, 2);
  assert.equal(summary.tables.shortfalls.length, 1);
  assert.match(summary.warnings[0], /below 3.0 days/);
});

test("logistics branch summary stays explicit when sustainment detail is absent", () => {
  const summary = summarizeLogisticsBranch({ units: [] });

  assert.equal(summary.overview.formationsTracked, 0);
  assert.equal(summary.overview.supplyAveragePct, null);
  assert.equal(summary.replacements.status, "Replacement flow not exposed");
  assert.match(summary.reserves.reserveStockStatus, /not exposed/);
  assert.equal(summary.warnings[0], "No major sustainment warnings are exposed in the current shell path.");
});

test("local sustainment summary uses exposed local unit supply and loc state only", () => {
  const summary = summarizeLocalSustainment({
    local_pressure_areas: [
      { id: "henderson-field", location_id: "HENDERSON_FIELD" },
      { id: "bloody-ridge", location_id: "BLOODY_RIDGE" },
    ],
    units: [
      {
        id: "u-1",
        name: "1st Marines",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "BLOODY_RIDGE",
        inspector: {
          supply: { supply_pct: 48, supply_days_current: 2.4, ammo: null, fuel: null, rations: null },
          operational_state: { loc: { state: "threatened", detail: "Threatened on supply route" } },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
      {
        id: "u-2",
        name: "7th Marines",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "ALLIGATOR_CREEK",
        inspector: {
          supply: { supply_pct: 82, supply_days_current: null, ammo: null, fuel: "limited", rations: null },
          operational_state: { loc: { state: "connected", detail: "Connected to HQ" } },
          attachments_support: { attachments: ["11th Marines"], support: null, detached: null },
        },
      },
      {
        id: "hq-1",
        name: "1st Marine Division HQ",
        side: "ALLIED",
        unit_type: "HEADQUARTERS",
        location_id: "HENDERSON_FIELD",
        inspector: {
          supply: { supply_pct: 90, supply_days_current: null, ammo: null, fuel: null, rations: null },
          operational_state: { loc: { state: "connected", detail: "Connected to HQ" } },
          attachments_support: { attachments: null, support: null, detached: null },
        },
      },
    ],
  });

  assert.equal(summary.available, true);
  assert.equal(summary.status, "Critical");
  assert.match(summary.note, /current-tempo sustainment days/i);
  assert.equal(summary.resources[0].label, "Supply");
  assert.match(summary.resources[0].value, /average/i);
  assert.equal(summary.resources[2].value, "1 formation tracked");
  assert.equal(summary.resources[4].value, "1 formation tracked");
  assert.equal(summary.atRisk[0].name, "1st Marines");
  assert.match(summary.atRisk[0].detail, /48% supply/i);
  assert.match(summary.concerns[0], /below 50% supply/i);
  assert.match(summary.concerns[1], /below 3.0 days/i);
});

test("local sustainment summary stays explicit when the local slice is unavailable", () => {
  const summary = summarizeLocalSustainment({ local_pressure_areas: [], units: [] });

  assert.equal(summary.available, false);
  assert.equal(summary.status, "Unavailable");
  assert.equal(summary.resources[0].value, "Not exposed");
  assert.equal(summary.atRisk.length, 0);
  assert.match(summary.note, /unavailable outside the current operational theater slice/i);
});
