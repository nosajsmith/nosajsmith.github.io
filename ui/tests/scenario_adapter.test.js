import test from "node:test";
import assert from "node:assert/strict";

import {
  adaptMapState,
  canonicalScenarioKey,
  DEFAULT_PITCH_SCENARIO,
  pickPreferredPitchScenario,
  scenarioKeysMatch,
} from "../src/lib/scenario_adapter.js";

test("adaptMapState preserves map meta and converts q/r units to pixel-ready units", () => {
  const adapted = adaptMapState({
    map: {
      meta: { width: 20, height: 12, hexSize: 24, padX: 40, padY: 50 },
    },
    units: [
      { id: "U1", name: "Unit 1", side: "BLUE", q: 3, r: 4 },
    ],
  });

  assert.equal(adapted.meta.width, 20);
  assert.equal(adapted.meta.height, 12);
  assert.equal(adapted.meta.hexSize, 24);
  assert.equal(adapted.units[0].id, "U1");
  assert.equal(adapted.units[0].q, 3);
  assert.equal(adapted.units[0].r, 4);
  assert.equal(typeof adapted.units[0].px, "number");
  assert.equal(typeof adapted.units[0].py, "number");
});

test("pitch scenario selection prefers the Inchon/Korea slice over legacy defaults", () => {
  assert.equal(DEFAULT_PITCH_SCENARIO, "inchon_mvp");
  assert.equal(canonicalScenarioKey("Inchon MVP.json"), "inchon_mvp");
  assert.equal(scenarioKeysMatch("inchon_mvp.json", "inchon_mvp"), true);
  assert.equal(scenarioKeysMatch("gc_1942_historical.json", "inchon_mvp"), false);
  assert.equal(
    pickPreferredPitchScenario(["gc_1942_historical", "inchon_mvp", "waegwan_crossing"]),
    "inchon_mvp",
  );
  assert.equal(
    pickPreferredPitchScenario(["bridgehead.json", "gc_1942_historical.json", "inchon_mvp.json"]),
    "inchon_mvp.json",
  );
  assert.equal(
    pickPreferredPitchScenario(["gc_1942_historical", "waegwan_crossing"]),
    "waegwan_crossing",
  );
  assert.equal(pickPreferredPitchScenario([]), null);
});
