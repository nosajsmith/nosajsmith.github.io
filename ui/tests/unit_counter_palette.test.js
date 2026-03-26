import test from "node:test";
import assert from "node:assert/strict";

import {
  buildUnitCounterPalettePresentation,
  inferUnitCounterService,
  inferUnitCounterState,
  normalizeUnitCounterFaction,
} from "../src/map/unitCounterPalette.js";

test("unit counter palette normalizes faction states without confusing unknown and neutral", () => {
  assert.equal(normalizeUnitCounterFaction("ALLIED"), "friendly");
  assert.equal(normalizeUnitCounterFaction("AXIS"), "enemy");
  assert.equal(normalizeUnitCounterFaction("NEUTRAL"), "neutral");
  assert.equal(normalizeUnitCounterFaction(""), "unknown");
  assert.equal(normalizeUnitCounterFaction("ROK"), "partner");
});

test("unit counter palette infers service branch from currently exposed unit metadata", () => {
  assert.equal(inferUnitCounterService({ name: "1st Marines", kind: "land", unit_type: "INFANTRY" }), "marines");
  assert.equal(inferUnitCounterService({ name: "5th Air Wing", kind: "air", unit_type: "AIR" }), "air_force");
  assert.equal(inferUnitCounterService({ name: "Task Force 77", kind: "naval", unit_type: "NAVAL" }), "navy");
  assert.equal(inferUnitCounterService({ name: "7th Infantry", kind: "land", unit_type: "INFANTRY" }), "army");
});

test("unit counter palette surfaces disabled and out-of-command variants", () => {
  const state = inferUnitCounterState({
    status: "disabled",
    inspector: { operational_state: { loc: { state: "broken" } } },
  });
  assert.equal(state.disabled, true);
  assert.equal(state.outOfCommand, false);

  const outOfCommand = buildUnitCounterPalettePresentation({
    faction: "friendly",
    service: "marines",
    outOfCommand: true,
  });
  const disabled = buildUnitCounterPalettePresentation({
    faction: "friendly",
    service: "army",
    disabled: true,
  });
  const neutral = buildUnitCounterPalettePresentation({
    faction: "neutral",
    service: "army",
  });
  const unknown = buildUnitCounterPalettePresentation({
    faction: "unknown",
    service: "army",
  });

  assert.notEqual(outOfCommand.border, buildUnitCounterPalettePresentation({ faction: "friendly", service: "marines" }).border);
  assert.notEqual(disabled.fill, buildUnitCounterPalettePresentation({ faction: "friendly", service: "army" }).fill);
  assert.notEqual(neutral.fill, unknown.fill);
});
