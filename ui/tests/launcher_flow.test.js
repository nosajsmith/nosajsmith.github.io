import test from "node:test";
import assert from "node:assert/strict";

import { renderLauncherSmoke } from "../src/components/shell/smoke_render.js";
import {
  deriveLauncherMainEffortLabel,
  deriveLauncherObjectiveLabel,
  deriveLauncherPrimaryAction,
  describeLauncherMusicState,
  loadLauncherScenarioRoster,
  selectLauncherScenario,
  summarizeLauncherBridgeState,
  shouldStartInShell,
} from "../src/lib/launcher.js";

test("launcher helpers preserve direct-shell fast path and live launch defaults", () => {
  assert.equal(shouldStartInShell("?shell=1", false), true);
  assert.equal(shouldStartInShell("?launcher=1", true), false);
  assert.deepEqual(
    deriveLauncherPrimaryAction({
      hasSnapshot: true,
      phase: "ready",
      selectedScenario: "inchon_mvp",
      activeScenario: "inchon_mvp",
      actionKind: null,
    }),
    { label: "Enter Command Shell", intent: "enter", disabled: false },
  );
  assert.deepEqual(
    deriveLauncherPrimaryAction({
      hasSnapshot: true,
      phase: "ready",
      selectedScenario: "inchon_mvp.json",
      activeScenario: "gc_1942_historical.json",
      actionKind: null,
    }),
    { label: "Load Inchon", intent: "launch", disabled: false },
  );
  assert.deepEqual(
    deriveLauncherPrimaryAction({
      hasSnapshot: false,
      phase: "not_ready",
      selectedScenario: "inchon_mvp",
      activeScenario: null,
      actionKind: null,
    }),
    { label: "Launch Inchon", intent: "launch", disabled: false },
  );
  assert.equal(
    describeLauncherMusicState({ available: true, enabled: true, playing: true }),
    "Theme playing",
  );
  assert.equal(
    describeLauncherMusicState({ available: true, enabled: false, playing: false }),
    "Theme available",
  );
});

test("launcher smoke render uses operator-facing title treatment", () => {
  const html = renderLauncherSmoke({
    scenarioName: "Inchon MVP",
    bridgeStatus: "Connected",
    objective: "Seoul",
    musicLabel: "Theme playing",
  });

  assert.match(html, /Publisher Preview Build/);
  assert.match(html, /Theater of Operations: Korea Operational Publisher Preview/);
  assert.match(html, /Korea Theater .* Operation Chromite/);
  assert.match(html, /Playable Publisher Preview/);
  assert.match(html, /Operational Command Shell/);
  assert.match(html, /One-Turn Playable Loop/);
  assert.match(html, /Command Shell Command shell ready/);
  assert.match(html, /Publisher Preview Key Art/);
  assert.match(html, /Bridge Connected/);
  assert.match(html, /Objective Seoul/);
  assert.match(html, /Preview Audio Theme playing/);
  assert.match(html, /Opening Theme 34%/);
});

test("launcher roster loader preserves reachable-bridge populated-roster behavior", async () => {
  const calls = [];
  const roster = await loadLauncherScenarioRoster({
    connect: async () => {
      calls.push("connect");
    },
    listScenarios: async () => {
      calls.push("list");
      return ["gc_1942_historical.json", "inchon_mvp.json"];
    },
  });

  assert.deepEqual(calls, ["connect", "list"]);
  assert.deepEqual(roster, ["gc_1942_historical.json", "inchon_mvp.json"]);
  assert.equal(selectLauncherScenario("", roster), "inchon_mvp.json");
  assert.equal(selectLauncherScenario("gc_1942_historical.json", roster), "gc_1942_historical.json");
});

test("launcher bridge summary stays truthful when snapshot data is present", () => {
  assert.deepEqual(
    summarizeLauncherBridgeState({
      connected: false,
      phase: "bridge_error",
      snapshot: {
        time: { turn: 4, phase: "night" },
      },
    }),
    {
      bridgeConnected: true,
      bridgeStatus: "Connected",
      scenarioStatus: "Live operational picture ready",
      currentTurn: "Turn 4",
      currentPhase: "Night",
    },
  );

  assert.deepEqual(
    summarizeLauncherBridgeState({
      connected: true,
      phase: "not_ready",
      snapshot: null,
    }),
    {
      bridgeConnected: true,
      bridgeStatus: "Connected",
      scenarioStatus: "Bridge connected, awaiting scenario state",
      currentTurn: "Turn pending",
      currentPhase: "Phase pending",
    },
  );
});

test("launcher labels prefer read-first objective before legacy command fallbacks", () => {
  const snapshot = {
    scenario: { id: "inchon_mvp", name: "Operation Chromite" },
    read_first: { key_objective: "Seoul Corridor" },
    grease_board: {
      objective: "Henderson Field",
      main_effort: "Secure Kimpo Road",
    },
    bai_report: {
      main_objective: { name: "Bloody Ridge" },
      chosen_operation: { name: "Hold Henderson Perimeter" },
    },
    ai: { last_intent: "hold_henderson_perimeter" },
    objectives: [{ id: "o1", name: "Kimpo Airfield", value: 100 }],
  };

  assert.equal(deriveLauncherObjectiveLabel(snapshot, snapshot), "Seoul Corridor");
  assert.equal(deriveLauncherMainEffortLabel(snapshot, snapshot), "Secure Kimpo Road");
});
