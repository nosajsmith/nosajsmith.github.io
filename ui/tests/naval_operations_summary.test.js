import test from "node:test";
import assert from "node:assert/strict";

import { summarizeNavalOperations, summarizeLocalNavalSupport } from "../src/components/shell/naval_operations_summary.js";

test("naval operations summary uses exposed naval formations and maritime context only", () => {
  const summary = summarizeNavalOperations({
    units: [
      {
        id: "nav-1",
        name: "Task Force 18",
        kind: "naval",
        readiness: 64,
        inspector: {
          supply: { supply_days_current: 4.2 },
          operational_state: { loc: { state: "unavailable" } },
        },
      },
    ],
    ports: [{ id: "TULAGI", name: "Tulagi", x: 2, y: 0 }],
    naval_support_windows: [{ id: "naval-gunfire", label: "Naval Gunfire", side: "ALLIED", start_hour: 0, end_hour: 24 }],
  });

  assert.equal(summary.overview.formationsTracked, 1);
  assert.equal(summary.overview.portsTracked, 1);
  assert.equal(summary.overview.supportWindowsTracked, 1);
  assert.equal(summary.formations[0].endurance, "4.2 days sustainment");
  assert.equal(summary.operatingContext.windows[0].timing, "H+0 to H+24");
  assert.match(summary.concerns[0], /naval support window/);
});

test("naval operations summary stays explicit when naval detail is absent", () => {
  const summary = summarizeNavalOperations({ units: [], ports: [], naval_support_windows: [] });

  assert.equal(summary.overview.formationsTracked, 0);
  assert.equal(summary.overview.portsTracked, 0);
  assert.equal(summary.composition.status, "Ship classes not exposed");
  assert.match(summary.overview.statusLine, /maritime context, but no dedicated fleets/i);
});

test("local naval support summary stays truthful when only Lunga Point shore context is exposed", () => {
  const summary = summarizeLocalNavalSupport({
    weather: { condition: "Humid Overcast" },
    time: { current_hours: 12 },
    local_pressure_areas: [
      { id: "lunga-point", location_id: "LUNGA_POINT" },
      { id: "henderson-field", location_id: "HENDERSON_FIELD" },
    ],
    ports: [{ id: "LUNGA_POINT", name: "Lunga Point", x: -1, y: 1 }],
    naval_support_windows: [],
    units: [],
  });

  assert.equal(summary.available, true);
  assert.equal(summary.availability, "Context exposed");
  assert.equal(summary.supportPosture, "Port anchor only");
  assert.match(summary.note, /Lunga Point/);
  assert.match(summary.constraint, /only currently exposed shore-support anchor/i);
  assert.match(summary.supportingFormation, /No supporting naval formation/i);
});

test("local naval support summary uses active authored support windows when present", () => {
  const summary = summarizeLocalNavalSupport({
    weather: { condition: "Clear" },
    time: { current_hours: 6 },
    local_pressure_areas: [{ id: "lunga-point", location_id: "LUNGA_POINT" }],
    ports: [{ id: "LUNGA_POINT", name: "Lunga Point", x: -1, y: 1 }],
    naval_support_windows: [{ id: "naval-gunfire", label: "Naval Gunfire", side: "ALLIED", start_hour: 0, end_hour: 24 }],
    units: [],
  });

  assert.equal(summary.availability, "Available");
  assert.equal(summary.supportPosture, "Window active • H+0 to H+24");
  assert.match(summary.constraint, /Weather Clear/i);
  assert.match(summary.supportingFormation, /Formation identity not exposed/i);
});
