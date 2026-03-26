import test from "node:test";
import assert from "node:assert/strict";

import { buildUnitCounterOverlayPresentation, UNIT_COUNTER_OVERLAY_RULES } from "../src/map/unitCounterOverlay.js";

test("unit counter overlay keeps critical as the dominant edge state while retaining supply and command trouble markers", () => {
  const overlay = buildUnitCounterOverlayPresentation({
    status: "engaged and critical",
    inspector: {
      operational_state: {
        readiness: 31,
        fatigue: 72,
        morale: 34,
        cohesion: 33,
        loc: { state: "broken" },
      },
      supply: {
        supply_pct: 28,
        supply_days_current: 1.4,
      },
      orders: {
        action: "counterattack",
        status: "engaged",
      },
    },
  });

  assert.equal(overlay.edgeState, "critical");
  assert.equal(overlay.critical, true);
  assert.equal(overlay.lowSupply, true);
  assert.equal(overlay.outOfCommand, true);
  assert.equal(overlay.damaged, false);
});

test("unit counter overlay separates motion, damage, and idle without inventing them by default", () => {
  const moving = buildUnitCounterOverlayPresentation({
    status: "moving to start line",
    inspector: {
      operational_state: { readiness: 70, fatigue: 18, morale: 71, cohesion: 70, loc: { state: "connected" } },
      supply: { supply_pct: 77, supply_days_current: 3.8 },
      orders: { action: "move", lifecycle_state: "moving to start line" },
    },
  });
  const damaged = buildUnitCounterOverlayPresentation({
    status: "degraded after action",
    inspector: {
      operational_state: { readiness: 50, fatigue: 47, morale: 51, cohesion: 56, loc: { state: "connected" } },
      supply: { supply_pct: 62, supply_days_current: 3.1 },
      orders: { action: "hold", status: "recovering" },
    },
  });
  const idle = buildUnitCounterOverlayPresentation({
    status: "active",
    inspector: {
      operational_state: { readiness: 72, fatigue: 14, morale: 74, cohesion: 72, loc: { state: "connected" } },
      supply: { supply_pct: 81, supply_days_current: 4.4 },
      orders: { action: "reserve", status: "awaiting orders" },
    },
  });
  const neutral = buildUnitCounterOverlayPresentation({
    status: "active",
    inspector: {
      operational_state: { readiness: 72, fatigue: 14, morale: 74, cohesion: 72, loc: { state: "connected" } },
      supply: { supply_pct: 81, supply_days_current: 4.4 },
      orders: { action: "hold", status: "active" },
    },
  });

  assert.equal(moving.edgeState, "moving");
  assert.equal(damaged.edgeState, null);
  assert.equal(damaged.damaged, true);
  assert.equal(idle.edgeState, "idle");
  assert.equal(neutral.active, false);
});

test("unit counter overlay exposes the documented edge-state priority order", () => {
  assert.deepEqual(UNIT_COUNTER_OVERLAY_RULES.priority, ["critical", "engaged", "moving", "idle"]);
});
