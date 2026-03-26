import test from "node:test";
import assert from "node:assert/strict";

import { summarizeSelectedUnit } from "../src/components/shell/unit_selection_summary.js";

test("selected unit summary uses only authoritative visible fields", () => {
  const summary = summarizeSelectedUnit({
    id: "u1",
    name: "1st Marines",
    side: "ALLIED",
    kind: "land",
    strength: 8,
    supply: "6.0 days",
    readiness: 7,
    morale: 6,
    status: "holding_line",
  });

  assert.equal(summary.selected, true);
  assert.equal(summary.title, "1st Marines");
  assert.equal(summary.subtitle, "Allied Land");
  assert.deepEqual(summary.metrics, [
    { label: "Strength", value: 8 },
    { label: "Supply", value: "6.0 days" },
    { label: "Readiness", value: 7 },
    { label: "Morale", value: 6 },
    { label: "Status", value: "Holding Line" },
  ]);
});

test("selected unit summary provides a clear empty state", () => {
  const summary = summarizeSelectedUnit(null);

  assert.equal(summary.selected, false);
  assert.equal(summary.title, "No unit selected");
  assert.match(summary.subtitle, /Click a visible unit counter/);
  assert.deepEqual(summary.metrics, []);
});
