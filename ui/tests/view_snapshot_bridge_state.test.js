import test from "node:test";
import assert from "node:assert/strict";

import { bootstrapDemoScenario, fetchViewSnapshot, launchScenario, listScenarios, normalizeSnapshot, stepHours } from "../src/lib/view_snapshot.ts";

test("normalizeSnapshot adapts engine-style live bridge state into shell-friendly snapshot data", () => {
  const snapshot = normalizeSnapshot({
    game: {
      scenario: "Mini Guadalcanal 1942",
      time: { day: 2, phase: "day", weather: "Clear" },
      vp: { ALLIED: 50, AXIS: 10 },
      ai: {
        enabled: true,
        side: "AXIS",
        controller_available: true,
        last_orders: 1,
      },
    },
    units: [
      {
        id: "JP-35BDE",
        name: "35th Infantry Brigade",
        side: "AXIS",
        unit_type: "INFANTRY",
        strength: 90,
        readiness: 55,
        morale: 65,
        fatigue: 10,
        supply: 70,
        posture: "DEFEND",
        location_id: "TULAGI",
      },
    ],
    objectives: [
      { location_id: "LUNGA", side: "ALLIED", value: 50 },
      { location_id: "TULAGI", side: "AXIS", value: 50 },
    ],
    bai_report: {
      posture: "CONTAIN",
      main_objective: "TULAGI",
      chosen_operation: { name: "Hold line at TULAGI" },
      summary_lines: ["Posture: CONTAIN", "Main objective: TULAGI"],
      unit_orders: [
        {
          unit_id: "JP-35BDE",
          action: "hold",
          target_location_id: "TULAGI",
        },
      ],
    },
  });

  assert.equal(snapshot.scenario.name, "Mini Guadalcanal 1942");
  assert.equal(snapshot.scenario.id, "mini_guadalcanal_1942");
  assert.equal(snapshot.time.current_hours, 24);
  assert.equal(snapshot.time.turn, 2);
  assert.equal(snapshot.time.phase, "day");
  assert.equal(snapshot.weather?.condition, "Clear");
  assert.equal(snapshot.campaign.score_by_side.ALLIED, 50);
  assert.equal(snapshot.ai.enabled, true);
  assert.equal(snapshot.ai.side, "AXIS");
  assert.equal(snapshot.ai.last_intent, "Hold line at TULAGI");
  assert.equal(snapshot.ai.last_orders, 1);
  assert.equal(snapshot.bai_report?.posture, "CONTAIN");
  assert.equal(snapshot.bai_report?.summary_lines[0], "Posture: CONTAIN");
  assert.equal(snapshot.reports.recent[0]?.sender_label, "BAI");
  assert.equal(snapshot.units[0]?.fatigue, 10);
  assert.equal(snapshot.units[0]?.posture, "DEFEND");
  assert.equal(snapshot.units[0]?.supply, "70%");
  assert.equal(snapshot.units[0]?.inspector.orders.action, "hold");
  assert.equal(snapshot.units[0]?.inspector.operational_state.location_status, "TULAGI");
  assert.ok(snapshot.units[0]?.x != null);
  assert.ok(snapshot.units[0]?.y != null);
  assert.ok(snapshot.objectives[0]?.x != null);
  assert.ok(snapshot.objectives[0]?.y != null);
});

test("normalizeSnapshot preserves the view.snapshot contract as the shell first-read source", () => {
  const snapshot = normalizeSnapshot({
    contract: {
      id: "view.snapshot",
      version: 1,
      source: "backend_read_model",
    },
    scenario: {
      id: "contract_demo",
      name: "Contract Demo",
    },
    operation: {
      id: "contract_demo",
      name: "Contract Demo",
      theater_id: "demo_theater",
    },
    time: {
      current_hours: 24,
      turn: 2,
      phase: "day",
      time_remaining_hours: 48,
    },
    campaign: {
      status: "active",
      score_by_side: { ALLIED: 1, AXIS: 0 },
      win_score: 999,
      objective_state: { "LEGACY:HILL": false },
    },
    score: {
      score_by_side: { ALLIED: 80, AXIS: 0 },
      win_score: 120,
    },
    objective_truth: {
      "ALLIED:HILL": {
        status: "contested",
        controller_side: null,
        friendly_present: true,
        enemy_present: true,
      },
    },
    objective_state: {
      "ALLIED:HILL": true,
    },
    pressure: {
      active: false,
      objective_pressure: {
        semantics: "supply_aware_objective_pressure_v1",
        radius: 1,
        affects_scoring: false,
        total_pressure_score: 50,
        reasons: ["ALLIED:HILL:degraded_by_supply"],
        by_objective: {
          "ALLIED:HILL": {
            side: "ALLIED",
            location_id: "HILL",
            objective_status: "contested",
            pressure_state: "degraded",
            pressure_score: 50,
            nearby_unit_count: 1,
            contributing_unit_count: 1,
            low_supply_unit_count: 1,
            suppressed_unit_count: 0,
          },
        },
      },
    },
    reports: {
      pending_count: null,
      recent: [
        {
          id: "report-1",
          kind: "objectives",
          title: "Objective Update",
          summary: "Hill 101 remains contested.",
          severity: "info",
          time: 24,
          sender_label: "G8",
        },
      ],
    },
    ai: {
      enabled: true,
      side: "AXIS",
      last_intent: "Delay Hill 101",
      last_orders: 1,
    },
    read_first: {
      scenario: "Contract Demo",
      turn: 2,
      phase: "day",
      campaign_status: "active",
      key_objective: "Hill 101",
      pressure_summary: null,
      latest_report: "Objective Update",
    },
    objectives: [
      {
        id: "obj_hill",
        location_id: "HILL",
        name: "Hill 101",
        side: "ALLIED",
        value: 80,
        truth_state: "contested",
        objective_status: "contested",
        controller_side: null,
        held: false,
        contested: true,
        objective_truth_key: "ALLIED:HILL",
        pressure_state: "degraded",
        pressure_score: 50,
        pressure: {
          state: "degraded",
          score: 50,
          nearby_unit_count: 1,
          contributing_unit_count: 1,
          low_supply_unit_count: 1,
          suppressed_unit_count: 0,
        },
        x: 10,
        y: 10,
      },
    ],
    units: [],
  });

  assert.equal(snapshot.contract?.id, "view.snapshot");
  assert.equal(snapshot.contract?.version, 1);
  assert.equal(snapshot.operation?.id, "contract_demo");
  assert.equal(snapshot.time.turn, 2);
  assert.equal(snapshot.campaign.score_by_side.ALLIED, 80);
  assert.equal(snapshot.score.win_score, 120);
  assert.deepEqual(snapshot.campaign.objective_state, { "ALLIED:HILL": true });
  assert.equal(snapshot.objective_truth["ALLIED:HILL"]?.status, "contested");
  assert.equal(snapshot.objectives[0]?.state, "contested");
  assert.equal(snapshot.objectives[0]?.truth_state, "contested");
  assert.equal(snapshot.objectives[0]?.pressure_state, "degraded");
  assert.equal(snapshot.objectives[0]?.pressure?.low_supply_unit_count, 1);
  assert.equal(snapshot.pressure.active, true);
  assert.equal(snapshot.pressure.summary, "HILL pressure degraded.");
  assert.equal(snapshot.pressure.semantics, "supply_aware_objective_pressure_v1");
  assert.equal(snapshot.pressure.objective_pressure?.affects_scoring, false);
  assert.equal(snapshot.pressure.by_objective["ALLIED:HILL"]?.pressure_score, 50);
  assert.equal(snapshot.pressure.reasons[0], "ALLIED:HILL:degraded_by_supply");
  assert.equal(snapshot.reports.recent[0]?.title, "Objective Update");
  assert.equal(snapshot.ai.last_intent, "Delay Hill 101");
  assert.equal(snapshot.read_first?.key_objective, "Hill 101");
  assert.equal(snapshot.read_first?.latest_report, "Objective Update");
});

test("normalizeSnapshot preserves grease board payloads when the bridge exposes them", () => {
  const snapshot = normalizeSnapshot({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    time: { current_hours: 48, turn: 3, phase: "night" },
    grease_board: {
      turn: "TURN 3",
      objective: "SEOUL",
      front_status: "CONTESTED",
      supply_status: "STRAINED WEST AXIS",
      main_effort: "SEOUL AXIS",
      orders: ["1st Marines advancing toward Seoul"],
      alerts: ["Supply strain west of Inchon"],
      staff_notes: "Secure the causeway before dawn.",
    },
    units: [],
    objectives: [],
  });

  assert.equal(snapshot.grease_board?.objective, "SEOUL");
  assert.equal(snapshot.grease_board?.main_effort, "SEOUL AXIS");
  assert.equal(snapshot.grease_board?.orders[0], "1st Marines advancing toward Seoul");
  assert.equal(snapshot.grease_board?.staff_notes, "Secure the causeway before dawn.");
});

test("normalizeSnapshot maps engine clock payloads into the launcher time shape", () => {
  const snapshot = normalizeSnapshot({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    engine: {
      clock: {
        turn_number: 4,
        phase: "night",
      },
    },
    units: [],
    objectives: [],
  });

  assert.equal(snapshot.time.turn, 4);
  assert.equal(snapshot.time.phase, "night");
});

test("normalizeSnapshot preserves authored map presentation metadata for live demo boards", () => {
  const snapshot = normalizeSnapshot({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    map_presentation: {
      hex_scale_km: 5,
      playable_scale_locked: true,
      world_bounds: { min_x: 14.2, max_x: 51.2, min_y: 31, max_y: 60.8 },
      basemap_raw_bounds: { min_x: -2.32, max_x: 0.72, min_y: 21.02, max_y: 22.34 },
      focus_points: [
        { id: "focus_inchon_harbor", label: "Inchon Harbor", x: 18.2, y: 58.1 },
        { id: "focus_yongdungpo_crossings", label: "Yongdungpo Crossings", x: 39.4, y: 40.6 },
      ],
    },
    units: [],
    objectives: [],
  });

  assert.equal(snapshot.map_presentation?.world_bounds?.min_x, 14.2);
  assert.equal(snapshot.map_presentation?.basemap_raw_bounds?.max_y, 22.34);
  assert.equal(snapshot.map_presentation?.hex_scale_km, 5);
  assert.equal(snapshot.map_presentation?.playable_scale_locked, true);
  assert.equal(snapshot.map_presentation?.focus_points[1]?.label, "Yongdungpo Crossings");
});

test("normalizeSnapshot preserves authored demo-map label metadata for live objectives, features, and units", () => {
  const snapshot = normalizeSnapshot({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    units: [
      {
        id: "US-1MAR",
        name: "1st Marine Division",
        side: "ALLIED",
        unit_type: "INFANTRY",
        location_id: "INCHON_PORT",
        map_label: "1ST MAR DIV",
        label_priority: 4,
        label_offset_x: 18,
        label_offset_y: 6,
        label_anchor: "start",
      },
    ],
    objectives: [
      {
        id: "obj_seoul",
        location_id: "SEOUL",
        name: "Seoul",
        value: 120,
        state: "unheld",
        x: 46,
        y: 36,
        map_label: "SEOUL",
        label_offset_x: -14,
        label_offset_y: -18,
        label_anchor: "end",
      },
    ],
    named_features: [
      {
        id: "han_estuary_feature",
        label: "Han Estuary",
        map_label: "HAN ESTUARY",
        kind: "sector",
        geometry_type: "zone",
        label_offset_x: -10,
        label_offset_y: 4,
        label_anchor: "middle",
        points: [{ x: 18, y: 58 }, { x: 24, y: 55 }, { x: 30, y: 51 }],
      },
    ],
    airfields: [
      {
        id: "KIMPO_AIRFIELD",
        location_id: "KIMPO_AIRFIELD",
        name: "Kimpo Airfield",
        x: 31,
        y: 46,
        side: "ALLIED",
        state: "contested",
        readiness: 64,
        sortie_status: "turnaround",
      },
    ],
    ports: [
      {
        id: "INCHON_PORT",
        location_id: "INCHON_PORT",
        name: "Inchon Harbor",
        x: 18,
        y: 58,
        side: "ALLIED",
        state: "secured",
        damage_state: "minor_damage",
      },
    ],
  });

  assert.equal(snapshot.units[0]?.map_label, "1ST MAR DIV");
  assert.equal(snapshot.units[0]?.label_priority, 4);
  assert.equal(snapshot.objectives[0]?.map_label, "SEOUL");
  assert.equal(snapshot.objectives[0]?.label_anchor, "end");
  assert.equal(snapshot.named_features[0]?.map_label, "HAN ESTUARY");
  assert.equal(snapshot.named_features[0]?.label_offset_y, 4);
  assert.equal(snapshot.airfields[0]?.state, "contested");
  assert.equal(snapshot.airfields[0]?.sortie_status, "turnaround");
  assert.equal(snapshot.ports[0]?.damage_state, "minor_damage");
  assert.equal(snapshot.ports[0]?.side, "ALLIED");
});

test("normalizeSnapshot suppresses stale South Pacific fallback summaries in Korea context", () => {
  const snapshot = normalizeSnapshot({
    scenario: { id: "inchon_mvp", name: "Operation Chromite" },
    time: { current_hours: 48, turn: 3, phase: "night" },
    bai_report: {
      posture: "OFFENSIVE",
      main_objective: { name: "Seoul" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
      summary_lines: ["Hold Henderson Field while reserves reorganize."],
    },
    units: [],
    objectives: [
      { id: "o1", name: "Seoul", value: 100, state: "unheld", x: 46, y: 36 },
    ],
    airfields: [{ id: "af1", name: "Kimpo", x: 31, y: 46 }],
    ports: [{ id: "pt1", name: "Inchon Harbor", x: 18, y: 58 }],
  });

  assert.equal(snapshot.staff.summary, "Staff summary unavailable");
  assert.equal(snapshot.ai.last_intent, null);
  assert.equal(snapshot.bai_report?.chosen_operation?.name, "Hold Henderson Perimeter");
});

test("fetchViewSnapshot accepts the older status/data bridge envelope", async () => {
  const rpc = {
    rpc: async (cmd) => {
      assert.equal(cmd, "view.snapshot");
      return {
        status: "ok",
        data: {
          scenario: { id: "inchon_mvp", name: "Inchon MVP" },
          time: { current_hours: 48, turn: 3, phase: "night" },
          units: [],
          objectives: [],
        },
      };
    },
  };

  const snapshot = await fetchViewSnapshot(rpc);
  assert.equal(snapshot.scenario.name, "Inchon MVP");
  assert.equal(snapshot.time.turn, 3);
  assert.equal(snapshot.time.phase, "night");
});

test("listScenarios falls back to the current snapshot when the bridge returns a snapshot envelope", async () => {
  const rpc = {
    rpc: async (cmd) => {
      assert.equal(cmd, "list_scenarios");
      return {
        type: "snapshot",
        data: {
          scenario: { id: "inchon_mvp", name: "Inchon MVP" },
          engine: { clock: { turn_number: 3, phase: "night" } },
          units: [],
          objectives: [],
        },
      };
    },
  };

  const scenarios = await listScenarios(rpc);
  assert.deepEqual(scenarios, ["inchon_mvp"]);
});

test("stepHours falls back to process_turn when end_turn is unavailable", async () => {
  const calls = [];
  const rpc = {
    rpc: async (cmd, payload) => {
      calls.push({ cmd, payload });
      if (cmd === "end_turn") {
        return {
          status: "error",
          error: {
            code: "bad_request",
            message: "Unknown cmd: end_turn",
            details: {},
          },
        };
      }
      if (cmd === "process_turn") {
        return {
          status: "ok",
          data: {
            game: {
              time: { day: 2, phase: "night" },
            },
          },
        };
      }
      throw new Error(`Unexpected cmd ${cmd}`);
    },
  };

  const result = await stepHours(rpc, 6);

  assert.deepEqual(calls, [
    { cmd: "end_turn", payload: { dt_hours: 6 } },
    { cmd: "end_turn", payload: {} },
    { cmd: "process_turn", payload: {} },
  ]);
  assert.deepEqual(result, {
    command: "process_turn",
    dtHoursApplied: false,
  });
});

test("launchScenario falls back from filename payloads to canonical runtime id", async () => {
  const calls = [];
  const rpc = {
    rpc: async (cmd, payload) => {
      calls.push({ cmd, payload });
      if (cmd === "load_scenario" && payload?.name === "inchon_mvp.json") {
        return {
          status: "error",
          error: {
            code: "not_found",
            message: "Scenario not found: inchon_mvp.json",
            details: {},
          },
        };
      }
      if (cmd === "load_scenario" && payload?.name === "inchon_mvp") {
        return {
          status: "error",
          error: {
            code: "bad_request",
            message: "Scenario loader requires canonical runtime id",
            details: {},
          },
        };
      }
      if (cmd === "load_scenario" && payload?.id === "inchon_mvp") {
        return { status: "ok", data: { scenario: { id: "inchon_mvp" } } };
      }
      if (cmd === "start_game") {
        return { status: "ok", data: { started: true } };
      }
      throw new Error(`Unexpected cmd ${cmd}`);
    },
  };

  await launchScenario(rpc, "inchon_mvp.json");

  assert.deepEqual(calls, [
    { cmd: "load_scenario", payload: { name: "inchon_mvp.json" } },
    { cmd: "load_scenario", payload: { id: "inchon_mvp" } },
    { cmd: "start_game", payload: {} },
  ]);
});

test("bootstrapDemoScenario returns the launched Korea/Inchon scenario key", async () => {
  const calls = [];
  const rpc = {
    rpc: async (cmd, payload) => {
      calls.push({ cmd, payload });
      if (cmd === "list_scenarios") {
        return {
          status: "ok",
          data: {
            scenarios: ["gc_1942_historical.json", "inchon_mvp.json"],
          },
        };
      }
      if (cmd === "load_scenario") {
        return { status: "ok", data: { scenario: { id: "inchon_mvp" } } };
      }
      if (cmd === "start_game") {
        return { status: "ok", data: { started: true } };
      }
      throw new Error(`Unexpected cmd ${cmd}`);
    },
  };

  const scenario = await bootstrapDemoScenario(rpc);

  assert.equal(scenario, "inchon_mvp.json");
  assert.equal(calls[0]?.cmd, "list_scenarios");
  assert.equal(calls[1]?.cmd, "load_scenario");
  assert.equal(calls[2]?.cmd, "start_game");
});

test("normalizeSnapshot translates live engine logs into communications rows when reports are absent", () => {
  const snapshot = normalizeSnapshot({
    game: {
      scenario: "Mini Guadalcanal 1942",
      time: { day: 3, phase: "night" },
    },
    logs: [
      { src: "G4", turn: 2, phase: "logistics", message: "JP-35BDE resupplied +8 at TULAGI." },
      { src: "BAI", turn: 2, phase: "orders", message: "JP-35BDE holds TULAGI and screens the western approach." },
      { src: "ENGINE", turn: 2, phase: "turn", message: "Processed Day 2; now Day 3" },
    ],
    units: [],
    objectives: [],
  });

  assert.equal(snapshot.reports.pending_count, 0);
  assert.equal(snapshot.reports.recent.length, 3);
  assert.equal(snapshot.reports.recent[0]?.title, "Logistics Update");
  assert.equal(snapshot.reports.recent[1]?.title, "BAI Orders");
  assert.equal(snapshot.reports.recent[2]?.title, "Turn Progression");
  assert.equal(snapshot.reports.recent[1]?.sender_label, "BAI");
  assert.equal(snapshot.reports.recent[2]?.time, 24);
});
