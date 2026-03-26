import test from "node:test";
import assert from "node:assert/strict";

import { summarizeInspector } from "../src/components/shell/inspector_summary.js";

function sectionByTitle(summary, title) {
  const section = summary.sections.find((entry) => entry.title === title);
  assert.ok(section, `Expected section titled ${title}`);
  return section;
}

test("inspector summary renders objective selections as stacked multi-entity views", () => {
  const snapshot = {
    objectives: [
      { id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", controlled: true, value: 60, x: 4, y: 4 },
    ],
    airfields: [
      { id: "HENDERSON_FIELD", name: "Henderson Airfield", x: 4, y: 4 },
    ],
    ports: [
      { id: "LUNGA_POINT", name: "Lunga Point", x: 4.2, y: 4.1 },
    ],
    units: [
      {
        id: "u1",
        name: "1st Marines",
        side: "ALLIED",
        kind: "land",
        location_id: "HENDERSON_FIELD",
        x: 4.1,
        y: 4,
        inspector: {
          operational_state: {
            posture: "defend",
            readiness: 68,
            fatigue: 15,
            loc: {
              state: "threatened",
              label: "LOC Threatened",
              detail: "Threatened on supply route",
            },
          },
        },
      },
    ],
    local_pressure_areas: [
      {
        id: "henderson-field",
        label: "Henderson Field",
        kind: "objective",
        location_id: "HENDERSON_FIELD",
        objective_id: "o1",
        pressure_reasons: ["enemy_pressure"],
        x: 4,
        y: 4,
      },
    ],
    reports: {
      recent: [
        {
          id: "r1",
          title: "Perimeter Alarm",
          summary: "Japanese probing fire reported near Henderson Field.",
          local_area_id: "henderson-field",
        },
      ],
    },
  };

  const summary = summarizeInspector(snapshot, { kind: "objective", id: "o1" });

  assert.equal(summary.selected, true);
  assert.equal(summary.header.eyebrow, "Inspector");
  assert.equal(summary.header.title, "Henderson Field");
  assert.match(summary.header.subtitle, /Multi-entity location/);
  assert.equal(summary.summary.title, "Current Summary");
  assert.equal(summary.summary.rows[0].value, "Objective");
  assert.deepEqual(
    summary.sections.map((section) => section.title),
    [
      "Location Summary",
      "Objective / Control Status",
      "Infrastructure / Condition",
      "Operational Significance",
      "Units / Assets Present",
      "Notes / Warnings",
    ],
  );
  assert.equal(sectionByTitle(summary, "Objective / Control Status").rows[1].value, "Held Allied");
  assert.match(sectionByTitle(summary, "Infrastructure / Condition").rows[0].label, /Airbase/i);
  assert.match(sectionByTitle(summary, "Infrastructure / Condition").rows[1].label, /Port/i);
  assert.equal(sectionByTitle(summary, "Units / Assets Present").rows[0].label, "1st Marines");
  assert.match(sectionByTitle(summary, "Units / Assets Present").rows[0].value, /LOC Threatened/);
  assert.match(sectionByTitle(summary, "Operational Significance").rows[1].value, /Enemy Pressure/);
  assert.match(sectionByTitle(summary, "Notes / Warnings").rows[0].value, /probing fire/i);
});

test("inspector summary renders selected airbases with truthful infrastructure placeholders", () => {
  const snapshot = {
    objectives: [],
    airfields: [{ id: "AF-1", name: "Kimpo Airfield", x: 7, y: 5 }],
    ports: [],
    units: [],
    local_pressure_areas: [],
    reports: { recent: [] },
  };

  const summary = summarizeInspector(snapshot, { kind: "airfield", id: "AF-1" });

  assert.equal(summary.header.title, "Kimpo Airfield");
  assert.equal(summary.summary.rows[0].value, "Airbase");
  assert.equal(sectionByTitle(summary, "Location Summary").rows[0].value, "Airbase");
  assert.equal(sectionByTitle(summary, "Infrastructure / Condition").rows[0].value, "Kimpo Airfield");
  assert.equal(sectionByTitle(summary, "Infrastructure / Condition").rows[1].value, "Not exposed on current shell path");
  assert.match(sectionByTitle(summary, "Objective / Control Status").body, /No current objective or control status/i);
});

test("inspector summary stays honest when a selected object is no longer exposed", () => {
  const summary = summarizeInspector({ objectives: [], airfields: [], ports: [], units: [] }, { kind: "objective", id: "missing" });

  assert.equal(summary.selected, true);
  assert.equal(summary.header.title, "Selection unavailable");
  assert.match(summary.header.subtitle, /no longer exposed/i);
  assert.deepEqual(summary.sections, []);
});
