import test from "node:test";
import assert from "node:assert/strict";

import { pickDefaultScenario, summarizeObjectives } from "../src/lib/demo_briefing.js";

test("pickDefaultScenario prefers inchon demo scenario when present", () => {
  assert.equal(
    pickDefaultScenario(["bridgehead.json", "inchon_mvp.json", "interdiction.json"]),
    "inchon_mvp.json",
  );
  assert.equal(pickDefaultScenario(["bridgehead.json"]), "bridgehead.json");
});

test("summarizeObjectives returns compact briefing-ready objective rows", () => {
  const out = summarizeObjectives([
    { id: "OBJ1", label: "Inchon Harbor", controlled: true, side: "ALLIED" },
    { id: "OBJ2", label: "Kimpo Airfield", controlled: false, side: "ALLIED" },
  ]);

  assert.deepEqual(out, [
    { id: "OBJ1", label: "Inchon Harbor", controlled: true, side: "ALLIED" },
    { id: "OBJ2", label: "Kimpo Airfield", controlled: false, side: "ALLIED" },
  ]);
});
