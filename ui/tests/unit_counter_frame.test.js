import test from "node:test";
import assert from "node:assert/strict";

import {
  buildUnitCounterFramePresentation,
  inferUnitCounterEchelon,
  isHeadquartersUnit,
  summarizeUnitCounterLabelPolicy,
} from "../src/map/unitCounterFrame.js";

test("unit counter echelon heuristics classify common maneuver and headquarters names", () => {
  assert.equal(inferUnitCounterEchelon({ name: "Alpha Company", unit_type: "INFANTRY" }), "company");
  assert.equal(inferUnitCounterEchelon({ name: "3rd Battalion", unit_type: "INFANTRY" }), "battalion");
  assert.equal(inferUnitCounterEchelon({ name: "1st Marines", unit_type: "INFANTRY" }), "regiment");
  assert.equal(inferUnitCounterEchelon({ name: "2nd Brigade", unit_type: "INFANTRY" }), "brigade");
  assert.equal(inferUnitCounterEchelon({ name: "Americal Division HQ", unit_type: "HEADQUARTERS" }), "division");
  assert.equal(inferUnitCounterEchelon({ name: "XIV Corps", unit_type: "HEADQUARTERS" }), "corps");
  assert.equal(inferUnitCounterEchelon({ name: "11th Engineers", unit_type: "ENGINEER_BATTALION" }), "battalion");
  assert.equal(isHeadquartersUnit({ name: "Americal Division HQ", unit_type: "HEADQUARTERS" }), true);
});

test("unit counter frame presentation differentiates echelon shapes and headquarters treatment", () => {
  const company = buildUnitCounterFramePresentation({ echelon: "company", zoom: 1 });
  const regiment = buildUnitCounterFramePresentation({ echelon: "regiment", zoom: 1 });
  const brigade = buildUnitCounterFramePresentation({ echelon: "brigade", zoom: 1 });
  const corps = buildUnitCounterFramePresentation({ echelon: "corps", isHeadquarters: true, zoom: 1 });

  assert.ok(company.width < regiment.width);
  assert.equal(brigade.innerPath !== null, true);
  assert.equal(brigade.headerRulePath, null);
  assert.equal(corps.innerPath !== null, true);
  assert.equal(corps.headerRulePath !== null, true);
  assert.equal(corps.hqPennant !== null, true);
  assert.notEqual(company.outerPath, corps.outerPath);
});

test("unit counter label policy follows the documented zoom tiers", () => {
  assert.equal(summarizeUnitCounterLabelPolicy(0.78).unitName, "Hidden");
  assert.equal(summarizeUnitCounterLabelPolicy(1).unitName, "Visible");
  assert.equal(summarizeUnitCounterLabelPolicy(1.6).counterCode, "Visible");
});
