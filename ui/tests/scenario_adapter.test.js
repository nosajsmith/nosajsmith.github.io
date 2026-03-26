import test from "node:test";
import assert from "node:assert/strict";

import { adaptMapState } from "../src/lib/scenario_adapter.js";

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
