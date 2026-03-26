import test from "node:test";
import assert from "node:assert/strict";

import { displayLogKind, nextActionCue, recentLogsFirst, selectedUnitCue } from "../src/lib/demo_polish.js";

test("nextActionCue points toward the next open allied objective", () => {
  const out = nextActionCue(
    { started: true, time_remaining: 72 },
    [
      { label: "Inchon Harbor", side: "ALLIED", controlled: true },
      { label: "Kimpo Airfield", side: "ALLIED", controlled: false },
    ],
    null,
  );

  assert.equal(out, "Next: push toward Kimpo Airfield.");
});

test("selectedUnitCue warns when a unit is delayed", () => {
  const out = selectedUnitCue({
    id: "US-1MAR",
    name: "1st Marines",
    raw: {
      player_detail: {
        order_lifecycle: {
          state: "Delayed",
          delay_reason: "HQ traffic congestion",
        },
      },
    },
  });

  assert.equal(out, "1st Marines is delayed: HQ traffic congestion");
});

test("recentLogsFirst returns newest entries first and displayLogKind maps demo labels", () => {
  const items = recentLogsFirst([
    { kind: "status", message: "Game started." },
    { kind: "support", message: "Naval gunfire shifted the fight." },
  ]);

  assert.deepEqual(items.map((entry) => entry.message), [
    "Naval gunfire shifted the fight.",
    "Game started.",
  ]);
  assert.equal(displayLogKind("ai"), "AI Pressure");
  assert.equal(displayLogKind("player_order"), "Player Order");
});
