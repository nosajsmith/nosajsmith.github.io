import {
  buildObjectiveDisplayName,
  containsLegacySouthPacificText,
  humanizeScenarioLabel,
  humanizeToken,
  isKoreaScenarioContext,
} from "./view_snapshot.js";
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
    return "Audio unavailable";
  }
  if (enabled && playing) {
    return "Theme playing";
  }
  if (enabled) {
    return "Starting theme...";
  }
  if (available) {
    return "Theme available";
  }
  return "Audio standby";
}

export function selectLauncherScenario(currentScenario, scenarios) {
  const roster = Array.isArray(scenarios) ? scenarios.map((scenario) => String(scenario)) : [];
  if (currentScenario && roster.includes(currentScenario)) {
    return currentScenario;
  }
  return pickPreferredPitchScenario(roster) ?? "";
}

function readUnknownLabel(value) {
  if (value == null) {
    return null;
  }
  if (typeof value === "string" || typeof value === "number") {
    const raw = String(value).trim();
    return raw ? humanizeToken(raw) : null;
  }
  if (typeof value === "object") {
    for (const key of ["name", "label", "title", "objective_id", "target_objective", "target_location_id", "id"]) {
      const candidate = value[key];
      if (candidate != null) {
        const raw = String(candidate).trim();
        if (raw) {
          return humanizeToken(raw);
        }
      }
    }
  }
  return null;
}

function sanitizeLauncherSnapshotText(value, scenarioContext) {
  const text = String(value ?? "").trim();
  if (!text) {
    return "";
  }
  return isKoreaScenarioContext(scenarioContext) && containsLegacySouthPacificText(text) ? "" : text;
}

export function deriveLauncherObjectiveLabel(snapshot, scenarioContext = snapshot) {
  const snapshotObjective = sanitizeLauncherSnapshotText(snapshot?.read_first?.key_objective, scenarioContext);
  if (snapshotObjective) {
    return snapshotObjective;
  }
  const greaseObjective = sanitizeLauncherSnapshotText(snapshot?.grease_board?.objective, scenarioContext);
  if (greaseObjective) {
    return greaseObjective;
  }
  const aiObjective = sanitizeLauncherSnapshotText(readUnknownLabel(snapshot?.bai_report?.main_objective), scenarioContext);
  if (aiObjective) {
    return aiObjective;
  }
  const suppressLegacy = isKoreaScenarioContext(scenarioContext);
  const topObjective = [...(snapshot?.objectives ?? [])]
    .filter((objective) => !(suppressLegacy && containsLegacySouthPacificText(objective?.name)))
    .sort((left, right) => (Number(right.value ?? 0) - Number(left.value ?? 0)))
    .find((objective) => Boolean(objective.name || objective.id));
  if (topObjective) {
    return buildObjectiveDisplayName(topObjective);
  }
  return "Seoul Axis";
}

export function deriveLauncherMainEffortLabel(snapshot, scenarioContext = snapshot) {
  const greaseEffort = sanitizeLauncherSnapshotText(snapshot?.grease_board?.main_effort, scenarioContext);
  if (greaseEffort) {
    return greaseEffort;
  }
  const chosenOperation = sanitizeLauncherSnapshotText(readUnknownLabel(snapshot?.bai_report?.chosen_operation), scenarioContext);
  if (chosenOperation) {
    return chosenOperation;
  }
  const aiIntent = sanitizeLauncherSnapshotText(snapshot?.ai?.last_intent, scenarioContext);
  if (aiIntent) {
    return humanizeToken(aiIntent);
  }
  return "Inchon / Seoul Push";
}

export function summarizeLauncherBridgeState({ connected, snapshot, phase }) {
  const bridgeConnected = Boolean(connected || snapshot);
  return {
    bridgeConnected,
    bridgeStatus: bridgeConnected ? "Connected" : "Offline",
    scenarioStatus: snapshot
      ? "Live operational picture ready"
      : bridgeConnected
        ? "Bridge connected, awaiting scenario state"
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
