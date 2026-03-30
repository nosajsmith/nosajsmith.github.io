import test from "node:test";
import assert from "node:assert/strict";

import { summarizeIntelligenceBranch } from "../src/components/shell/intelligence_branch_summary.js";

test("intelligence branch summary uses communications and pressure reasons only", () => {
  const summary = summarizeIntelligenceBranch({
    pressure: { active: true, reasons: ["enemy_pressure_north"] },
    reports: {
      pending_count: 2,
      recent: [
        { id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info", time: 4 },
      ],
    },
    staff: { summary: "Elevated" },
  });

  assert.equal(summary.overview.pending, 2);
  assert.equal(summary.overview.latestTitle, "Landing Continues");
  assert.equal(summary.dispatches.length, 1);
  assert.equal(summary.recon.sightings[0].title, "enemy pressure north");
  assert.equal(summary.confidence.status, "Live picture partial");
  assert.match(summary.concerns[0], /enemy pressure north/i);
});

test("intelligence branch summary stays explicit when intel detail is absent", () => {
  const summary = summarizeIntelligenceBranch({ reports: { pending_count: null, recent: [] }, pressure: { reasons: [] } });

  assert.equal(summary.dispatches.length, 0);
  assert.match(summary.overview.statusLine, /No current intelligence dispatches/);
  assert.equal(summary.concerns[0], "No explicit intelligence concerns are exposed beyond the current communications feed.");
});
