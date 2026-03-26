import test from "node:test";
import assert from "node:assert/strict";

import { summarizeCommunications } from "../src/components/shell/communications_summary.js";

test("communications summary uses available report fields without fabricating metadata", () => {
  const summary = summarizeCommunications({
    pending_count: 2,
    recent: [
      { id: "r1", kind: "status", title: "Landing Continues", summary: "Beachhead expanding.", severity: "info", time: 4, sender_label: "Beachmaster" },
      { id: "r2", kind: "warning", title: "", summary: "", severity: "warning", time: null },
    ],
  });

  assert.equal(summary.pending, 2);
  assert.equal(summary.latest.id, "r2");
  assert.equal(summary.latest.kind, "Warning");
  assert.equal(summary.latest.body, "Operational update.");
  assert.equal(summary.latest.timeLabel, "Time unavailable");
  assert.equal(summary.history[1].title, "Landing Continues");
  assert.equal(summary.history[1].senderLabel, "Beachmaster");
  assert.equal(summary.demoExample.senderLabel, "82nd Airborne");
  assert.equal(summary.demoExample.insigniaCode, "AA");
  assert.equal(summary.demoExample.isDemo, true);
});
