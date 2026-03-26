import test from "node:test";
import assert from "node:assert/strict";

import { buildUnitCounterSymbolPresentation, inferUnitCounterSymbol } from "../src/map/unitCounterSymbol.js";

test("unit counter symbols infer core land roles from currently exposed unit metadata", () => {
  assert.equal(inferUnitCounterSymbol({ name: "1st Marines", kind: "land", unit_type: "INFANTRY" })?.id, "infantry");
  assert.equal(inferUnitCounterSymbol({ name: "1st Tank Battalion", kind: "land", unit_type: "TANK_BATTALION" })?.id, "armor");
  assert.equal(inferUnitCounterSymbol({ name: "7th Mechanized Brigade", kind: "mechanized", unit_type: "MECHANIZED_INFANTRY" })?.id, "mechanized");
  assert.equal(inferUnitCounterSymbol({ name: "11th Marines Battery", kind: "artillery", unit_type: "ARTILLERY_BATTALION" })?.id, "artillery");
  assert.equal(inferUnitCounterSymbol({ name: "Americal Division HQ", kind: "land", unit_type: "HEADQUARTERS" })?.id, "headquarters");
  assert.equal(inferUnitCounterSymbol({ name: "Recon Troop", kind: "recon", unit_type: "RECON" })?.id, "recon");
  assert.equal(inferUnitCounterSymbol({ name: "11th Engineers", kind: "engineer", unit_type: "ENGINEER_BATTALION" })?.id, "engineer");
});

test("unit counter symbol presentation stays bold at far zoom and calmer at close zoom", () => {
  const far = buildUnitCounterSymbolPresentation({ symbol: "infantry", zoom: 0.78 });
  const operational = buildUnitCounterSymbolPresentation({ symbol: "infantry", zoom: 1 });
  const close = buildUnitCounterSymbolPresentation({ symbol: "infantry", zoom: 1.6 });
  const legend = buildUnitCounterSymbolPresentation({ symbol: "infantry", zoom: 1, placement: "legend" });

  assert.equal(far.tier, "far");
  assert.equal(close.tier, "close");
  assert.ok(far.scale > operational.scale);
  assert.ok(close.scale < operational.scale);
  assert.equal(legend.offsetY, 0);
});
