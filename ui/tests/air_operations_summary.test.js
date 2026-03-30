import test from "node:test";
import assert from "node:assert/strict";

import { summarizeAirOperations, summarizeLocalAirSupport } from "../src/components/shell/air_operations_summary.js";

test("air operations summary uses exposed air formations and airfield context only", () => {
  const summary = summarizeAirOperations({
    weather: { condition: "Overcast" },
    units: [
      {
        id: "air-1",
        name: "Cactus Air Group",
        kind: "air",
        readiness: 61,
        inspector: {
          supply: { supply_days_current: 3.1 },
          operational_state: { loc: { state: "threatened" } },
        },
      },
    ],
    airfields: [{ id: "HENDERSON", name: "Henderson Field", x: 0, y: 0 }],
  });

  assert.equal(summary.overview.formationsTracked, 1);
  assert.equal(summary.overview.airfieldsTracked, 1);
  assert.equal(summary.overview.readinessAverage, 61);
  assert.equal(summary.formations[0].sorties, "Sortie posture not exposed");
  assert.equal(summary.basing.airfields[0].name, "Henderson Field");
  assert.match(summary.concerns[0], /Weather Overcast/);
});

test("air operations summary stays explicit when air detail is absent", () => {
  const summary = summarizeAirOperations({ units: [], airfields: [] });

  assert.equal(summary.overview.formationsTracked, 0);
  assert.equal(summary.overview.airfieldsTracked, 0);
  assert.equal(summary.aircraft.status, "Aircraft type counts not exposed");
  assert.match(summary.overview.statusLine, /no dedicated air formations/i);
});

test("local air support summary stays truthful when only local airfield and weather are exposed", () => {
  const summary = summarizeLocalAirSupport({
    weather: { condition: "Humid Overcast" },
    local_pressure_areas: [{ id: "henderson-field", location_id: "HENDERSON_FIELD" }],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 0, y: 0 }],
    units: [],
  });

  assert.equal(summary.available, true);
  assert.equal(summary.availability, "Not exposed");
  assert.equal(summary.sortiePosture, "Sortie posture not exposed");
  assert.match(summary.note, /present on the current operational axis/i);
  assert.match(summary.constraint, /Weather Humid Overcast/i);
  assert.match(summary.supportingFormation, /No locally based air formation/i);
});

test("local air support summary uses locally based air-formation readiness when exposed", () => {
  const summary = summarizeLocalAirSupport({
    weather: { condition: "Clear" },
    local_pressure_areas: [{ id: "henderson-field", location_id: "HENDERSON_FIELD" }],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 0, y: 0 }],
    units: [
      {
        id: "air-1",
        name: "Cactus Air Group",
        kind: "air",
        readiness: 58,
        location_id: "HENDERSON_FIELD",
        inspector: {
          operational_state: { posture: "standby" },
        },
      },
    ],
  });

  assert.equal(summary.availability, "Limited");
  assert.equal(summary.sortiePosture, "Standby");
  assert.match(summary.constraint, /below 60 readiness/i);
  assert.equal(summary.supportingFormation, "Cactus Air Group");
});
