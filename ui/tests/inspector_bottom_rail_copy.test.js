import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { summarizeHomeCommandBar } from "../src/components/shell/home_command_bar_summary.js";
import { summarizeInspector } from "../src/components/shell/inspector_summary.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const reportsFeedSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/ReportsFeed.tsx"),
  "utf8",
);
const homeCommandBarSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/HomeCommandBar.tsx"),
  "utf8",
);
const mapWeatherBriefSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MapWeatherBrief.tsx"),
  "utf8",
);

test("bottom rail summaries use clearer operational state labels", () => {
  const emptySummary = summarizeHomeCommandBar({}, []);
  assert.equal(emptySummary.air.label, "Air picture incomplete");
  assert.equal(emptySummary.naval.label, "Naval picture incomplete");
  assert.equal(emptySummary.logistics.label, "Logistics picture incomplete");
  assert.equal(emptySummary.intelligence.label, "Dispatch queue unavailable");

  const pendingSummary = summarizeHomeCommandBar({ reports: { pending_count: 2, recent: [] } }, []);
  assert.equal(pendingSummary.intelligence.label, "2 pending dispatches");
  assert.equal(pendingSummary.intelligence.detail, "Built from current dispatch traffic and exposed pressure cues.");

  const clearQueueSummary = summarizeHomeCommandBar({ reports: { pending_count: 0, recent: [] } }, []);
  assert.equal(clearQueueSummary.intelligence.label, "No pending dispatches");
});

test("location inspector sections use clearer site and status wording", () => {
  const snapshot = {
    objectives: [
      { id: "obj-1", name: "Hill 27", state: "contested", side: "allied", controlled: true, value: 3 },
    ],
    airfields: [],
    ports: [],
    units: [],
    local_pressure_areas: [],
    reports: { recent: [] },
  };

  const inspector = summarizeInspector(snapshot, { kind: "objective", id: "obj-1" });
  assert.equal(inspector.summary.title, "Current Summary");
  assert.equal(inspector.sections[0].title, "Location Summary");
  assert.equal(inspector.sections[1].title, "Objective / Control Status");
  assert.equal(inspector.sections[2].title, "Infrastructure / Condition");
  assert.equal(inspector.sections[3].title, "Operational Significance");
  assert.equal(inspector.sections[4].title, "Units / Assets Present");
  assert.equal(inspector.sections[5].title, "Notes / Warnings");

  assert.deepEqual(
    inspector.sections[0].rows.map((row) => row.label),
    ["Site Type", "Map Reference", "Objectives Here", "Infrastructure Here", "Formations Here"],
  );
});

test("reports and weather cards surface clearer state wording", () => {
  assert.match(homeCommandBarSource, /shell-commandbar__state/);
  assert.match(homeCommandBarSource, /shell-commandbar__support/);
  assert.match(homeCommandBarSource, /Current hotspot/);

  assert.match(reportsFeedSource, /Dispatch queue unavailable/);
  assert.match(reportsFeedSource, /No pending dispatches/);
  assert.match(reportsFeedSource, /Current Dispatch/);
  assert.match(reportsFeedSource, /Review dispatch history, pending traffic, and current reporting gaps/);

  assert.match(mapWeatherBriefSource, /shell-weather__summary-title">Weather/);
  assert.match(mapWeatherBriefSource, /shell-weather__summary-state/);
  assert.match(mapWeatherBriefSource, /shell-weather__summary-support/);
  assert.match(mapWeatherBriefSource, /shell-weather__detail-grid/);
  assert.match(mapWeatherBriefSource, /label: "Sight"/);
  assert.match(mapWeatherBriefSource, /label: "Ground"/);
  assert.match(mapWeatherBriefSource, /label: "Air"/);
});
