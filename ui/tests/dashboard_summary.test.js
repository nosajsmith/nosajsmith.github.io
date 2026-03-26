import test from "node:test";
import assert from "node:assert/strict";

import {
  orderRecentReports,
  summarizeCampaign,
  summarizeObjectives,
  summarizeReports,
  summarizeScore,
} from "../src/components/shell/dashboard_summary.js";

test("dashboard summary groups objectives by authoritative state label and preserves source order for key rows", () => {
  const summary = summarizeObjectives([
    { id: "o1", name: "Inchon Harbor", state: "held_allied", side: "ALLIED" },
    { id: "o2", name: "Kimpo Airfield", state: "unheld", side: "ALLIED" },
    { id: "o3", name: "Seoul Approach", state: "held_allied", side: "ALLIED" },
  ]);

  assert.equal(summary.total, 3);
  assert.deepEqual(summary.byState, [
    { state: "Held Allied", count: 2 },
    { state: "Unheld", count: 1 },
  ]);
  assert.deepEqual(summary.key[0], {
    id: "o1",
    name: "Inchon Harbor",
    state: "Held Allied",
    side: "Allied",
  });
});

test("dashboard summary humanizes campaign, score, and recent report status conservatively", () => {
  const campaign = summarizeCampaign({
    campaign: { status: "ongoing", win_score: 180 },
    time: { turn: 3, time_remaining_hours: 48 },
  });
  const score = summarizeScore({ ALLIED: 35, AXIS: 12 });
  const reports = summarizeReports({
    pending_count: 2,
    recent: [{ kind: "player_order", title: "", severity: "warning" }],
  });

  assert.deepEqual(campaign, {
    status: "Ongoing",
    turn: 3,
    timeRemaining: 48,
    winTarget: 180,
  });
  assert.deepEqual(score, [
    { side: "ALLIED", label: "Allied", value: 35 },
    { side: "AXIS", label: "Axis", value: 12 },
  ]);
  assert.deepEqual(reports, {
    pending: 2,
    latest: {
      title: "Player Order",
      kind: "Player Order",
      showKind: false,
      summary: "Operational update.",
      severity: "WARNING",
    },
  });
});

test("dashboard summary selects the newest recent report entry deterministically", () => {
  const reports = summarizeReports({
    pending_count: 3,
    recent: [
      { kind: "status", title: "Initial Brief", severity: "info" },
      { kind: "objective", title: "Kimpo Secured", severity: "warning" },
    ],
  });

  assert.deepEqual(reports, {
    pending: 3,
    latest: {
      title: "Kimpo Secured",
      kind: "Objective",
      showKind: true,
      summary: "Operational update.",
      severity: "WARNING",
    },
  });
});

test("dashboard summary cleans internal report phrasing and preserves duplicate-label suppression metadata", () => {
  const reports = summarizeReports({
    pending_count: 1,
    recent: [
      {
        kind: "status",
        title: "Status",
        summary: "Game started. Operational AI enabled for visible shell progression.",
        severity: "info",
      },
    ],
  });

  assert.deepEqual(reports, {
    pending: 1,
    latest: {
      title: "Status",
      kind: "Status",
      showKind: false,
      summary: "Game started. Operational AI enabled.",
      severity: "INFO",
    },
  });
});

test("report ordering helper renders newest entries first for feed consistency", () => {
  const ordered = orderRecentReports([
    { id: "r1", title: "Initial Brief" },
    { id: "r2", title: "Kimpo Secured" },
    { id: "r3", title: "Advance Continues" },
  ]);

  assert.deepEqual(ordered.map((report) => report.id), ["r3", "r2", "r1"]);
});
