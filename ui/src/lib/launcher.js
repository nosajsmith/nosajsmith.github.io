import { humanizeScenarioLabel, humanizeToken } from "./view_snapshot.js";
import { pickPreferredPitchScenario, scenarioKeysMatch } from "./scenario_adapter.js";

export const LAUNCHER_SESSION_KEY = "too.inchon.launcher.dismissed";
export const LAUNCHER_MUSIC_SRC = "/audio/inchon_launcher_theme.wav";
export const DEFAULT_LAUNCHER_MUSIC_VOLUME = 0.34;

export function normalizeLauncherMusicVolume(value, fallback = DEFAULT_LAUNCHER_MUSIC_VOLUME) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  return Math.min(0.7, Math.max(0, numeric));
}

export function shouldStartInShell(search, persistedDismissed = false) {
  const params = new URLSearchParams(String(search ?? ""));
  if (params.get("launcher") === "1") {
    return false;
  }
  if (params.get("shell") === "1" || params.get("direct") === "1" || params.get("start") === "shell") {
    return true;
  }
  return Boolean(persistedDismissed);
}

export function deriveLauncherPrimaryAction({ hasSnapshot, phase, selectedScenario, activeScenario, actionKind }) {
  if (actionKind === "launch") {
    return { label: "Launching Scenario...", intent: "launch", disabled: true };
  }
  if (actionKind === "refresh") {
    return { label: "Refreshing Bridge...", intent: "refresh", disabled: true };
  }
  if (actionKind === "step") {
    return { label: "Updating Theater...", intent: "enter", disabled: true };
  }
  if (hasSnapshot && selectedScenario && !scenarioKeysMatch(selectedScenario, activeScenario)) {
    return { label: `Load ${humanizeScenarioLabel(selectedScenario)}`, intent: "launch", disabled: false };
  }
  if (hasSnapshot) {
    return { label: "Enter Command Shell", intent: "enter", disabled: false };
  }
  if (phase === "bridge_error") {
    return { label: "Retry Bridge", intent: "refresh", disabled: false };
  }
  if (selectedScenario) {
    return { label: `Launch ${humanizeScenarioLabel(selectedScenario)}`, intent: "launch", disabled: false };
  }
  if (phase === "loading") {
    return { label: "Connecting Bridge...", intent: "refresh", disabled: true };
  }
  return { label: "Open Command Shell", intent: "enter", disabled: false };
}

export function describeLauncherMusicState({ available, enabled, playing }) {
  if (available === false) {
    return "Theme unavailable";
  }
  if (enabled && playing) {
    return "Theme active";
  }
  if (enabled) {
    return "Cueing theme...";
  }
  if (available) {
    return "Theme ready";
  }
  return "Music standby";
}

export function selectLauncherScenario(currentScenario, scenarios) {
  const roster = Array.isArray(scenarios) ? scenarios.map((scenario) => String(scenario)) : [];
  if (currentScenario && roster.includes(currentScenario)) {
    return currentScenario;
  }
  return pickPreferredPitchScenario(roster) ?? "";
}

export function summarizeLauncherBridgeState({ connected, snapshot, phase }) {
  const bridgeConnected = Boolean(connected || snapshot);
  return {
    bridgeConnected,
    bridgeStatus: bridgeConnected ? "Connected" : "Offline",
    scenarioStatus: snapshot
      ? "Live operational picture ready"
      : bridgeConnected
        ? "Bridge connected, awaiting launch state"
        : phase === "bridge_error"
          ? "Bridge offline"
          : "Awaiting launch state",
    currentTurn: snapshot?.time?.turn != null
      ? `Turn ${snapshot.time.turn}`
      : bridgeConnected
        ? "Turn pending"
        : "Turn unavailable",
    currentPhase: snapshot?.time?.phase
      ? humanizeToken(snapshot.time.phase)
      : bridgeConnected
        ? "Phase pending"
        : "Phase unavailable",
  };
}

export async function loadLauncherScenarioRoster({ connect, listScenarios }) {
  await connect();
  const roster = await listScenarios();
  return Array.isArray(roster) ? roster.map((scenario) => String(scenario)) : [];
}
