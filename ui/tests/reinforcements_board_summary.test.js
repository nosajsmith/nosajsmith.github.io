import test from "node:test";
import assert from "node:assert/strict";

import { summarizeReinforcementsBoard } from "../src/components/shell/reinforcements_board_summary.js";

test("reinforcements board summary uses authoritative scheduled force changes only", () => {
  const summary = summarizeReinforcementsBoard({
    time: { current_hours: 24 },
    force_changes: {
      reinforcements: [
        {
          id: "US-2MAR",
          name: "2nd Marine Regiment",
          side: "ALLIED",
          kind: "INFANTRY",
          day: 3,
          location_id: "LUNGA",
          hq_unit_id: null,
          x: 0,
          y: 0,
        },
      ],
      withdrawals: [],
      replacement_events: [],
    },
  });

  assert.equal(summary.currentDay, 2);
  assert.equal(summary.overview.arrivals, 1);
  assert.equal(summary.arrivals[0].timing, "Day 3 • due in 1 day");
  assert.equal(summary.arrivals[0].destination, "LUNGA");
  assert.equal(summary.arrivals[0].command, "Command destination not exposed");
  assert.match(summary.placeholders.withdrawals, /withdrawal schedule is exposed/i);
});

test("reinforcements board summary stays explicit when no force-change schedule is exposed", () => {
  const summary = summarizeReinforcementsBoard({
    time: { current_hours: null },
    force_changes: {
      reinforcements: [],
      withdrawals: [],
      replacement_events: [],
    },
  });

  assert.equal(summary.overview.arrivals, 0);
  assert.equal(summary.currentDay, null);
  assert.match(summary.overview.staffNote, /No reinforcement schedule is exposed/);
  assert.match(summary.placeholders.replacements, /not exposed/);
});
