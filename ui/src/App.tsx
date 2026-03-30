import { useEffect, useMemo, useRef, useState } from "react";
import TopStrip from "./components/shell/TopStrip";
import MapPanelShell from "./components/shell/MapPanelShell";
import MainMapDrawer from "./components/shell/MainMapDrawer";
import ReportsFeed from "./components/shell/ReportsFeed";
import HomeCommandBar from "./components/shell/HomeCommandBar";
import MapWeatherBrief from "./components/shell/MapWeatherBrief";
import CommunicationsCenter from "./components/shell/CommunicationsCenter";
import BranchPlaceholder from "./components/shell/BranchPlaceholder";
import LauncherScreen from "./components/shell/LauncherScreen";
import TheaterDashboardScreen from "./components/shell/TheaterDashboardScreen";
import LandOperationsScreen from "./components/shell/LandOperationsScreen";
import LogisticsBranchScreen from "./components/shell/LogisticsBranchScreen";
import ReinforcementsBoardScreen from "./components/shell/ReinforcementsBoardScreen";
import AirOperationsScreen from "./components/shell/AirOperationsScreen";
import NavalOperationsScreen from "./components/shell/NavalOperationsScreen";
import IntelligenceBranchScreen from "./components/shell/IntelligenceBranchScreen";
import StateScreen from "./components/shell/StateScreen";
import type { InspectorSelection } from "./components/shell/inspector_types";
import type { PlannerWorkbenchTab } from "./components/shell/OperationPlannerPanel";
import {
  seedPlannerStateFromMapCommand,
  buildDefaultPlannerAssignments,
  createApprovedOperation,
  createOperationPlannerState,
  defaultOperationName,
  sanitizeOperationPlannerState,
  sanitizeTrackedOperations,
  upsertTrackedOperation,
} from "./components/shell/operations_planner.js";
import type { FastCommandPreview, OperationPlannerState, TrackedDemoOperation } from "./components/shell/operations_planner_types";
import { makeWsRpc } from "./lib/ws_rpc";
import {
  buildObjectiveDisplayName,
  containsLegacySouthPacificText,
  humanizeScenarioLabel,
  humanizeSideLabel,
  humanizeToken,
  inferScenarioPresentation,
  isKoreaScenarioContext,
} from "./lib/view_snapshot.js";
import {
  DEFAULT_LAUNCHER_MUSIC_VOLUME,
  LAUNCHER_MUSIC_SRC,
  LAUNCHER_SESSION_KEY,
  deriveLauncherPrimaryAction,
  describeLauncherMusicState,
  loadLauncherScenarioRoster,
  normalizeLauncherMusicVolume,
  selectLauncherScenario,
  shouldStartInShell,
} from "./lib/launcher.js";
import {
  BridgeRpcError,
  bootstrapDemoScenario,
  fetchViewSnapshot,
  launchScenario,
  listScenarios,
  stepHours,
  wsUrl,
} from "./lib/view_snapshot.ts";
import { DEFAULT_PITCH_SCENARIO, pickPreferredPitchScenario, scenarioKeysMatch } from "./lib/scenario_adapter.js";
import type { ViewSnapshot } from "./types/viewSnapshot";
import { summarizeCommunications } from "./components/shell/communications_summary.js";
import { buildMapScene, buildOperationalOverlayState } from "./components/shell/map_scene.js";
import {
  clearGreaseMarkupItems,
  createGreaseMarkupState,
  deserializeGreaseMarkupState,
  getGreaseMarkupStorageKey,
  removeGreaseMarkupItem,
  sanitizeGreaseMarkupState,
  serializeGreaseMarkupState,
} from "./map/greaseMarkup.js";
import { MAP_LAYER_REGISTRY, buildMapOverlayManager, isMapLayerEnabled, toggleMapLayer } from "./map/overlayManager.js";
import { resolveBasemapPackageTheater } from "./map/runtime/BasemapLoader.js";
import "./shell.css";

type ShellPhase = "loading" | "ready" | "bridge_error" | "not_ready" | "empty";
type ActionKind = "refresh" | "launch" | "step" | "ai" | null;
type BranchName = "Theatre" | "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements";
type GreaseMarkupItem = {
  id: string;
  tool: string;
  style: string;
  points: Array<{ x: number; y: number }>;
  createdAt: number;
};
type GreaseMarkupState = {
  version?: number;
  scenarioId: string | null;
  activeTool: string | null;
  activeStyle: string;
  selectedId: string | null;
  items: GreaseMarkupItem[];
};

const AUTO_SAVE_STORAGE_KEY = "mwe.ui.autosaveEnabled";

function readStoredAutoSaveEnabled(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(AUTO_SAVE_STORAGE_KEY) === "true";
}

function selectionExists(snapshot: ViewSnapshot | null, selection: InspectorSelection | null): boolean {
  if (!snapshot || !selection) {
    return false;
  }

  switch (selection.kind) {
    case "unit":
      return snapshot.units.some((unit) => unit.id === selection.id);
    case "objective":
      return snapshot.objectives.some((objective) => objective.id === selection.id);
    case "airfield":
      return snapshot.airfields.some((airfield) => airfield.id === selection.id);
    case "port":
      return snapshot.ports.some((port) => port.id === selection.id);
    default:
      return false;
  }
}

function formatPreviousSnapshotLabel(snapshot: ViewSnapshot | null): string | null {
  if (!snapshot) {
    return null;
  }

  const parts = [];
  if (snapshot.time?.turn != null) {
    parts.push(`Turn ${snapshot.time.turn}`);
  }
  if (snapshot.time?.current_hours != null) {
    parts.push(`T+${snapshot.time.current_hours}h`);
  }

  return parts.length ? `previous snapshot (${parts.join(" • ")})` : "previous snapshot";
}

function formatMapReference(entry: { x?: number | null; y?: number | null } | null | undefined): string | null {
  if (!entry || typeof entry.x !== "number" || typeof entry.y !== "number") {
    return null;
  }
  return `Hex ${entry.x}, ${entry.y}`;
}

function buildSelectionSummary(
  snapshot: ViewSnapshot | null,
  selection: InspectorSelection | null,
  operations: TrackedDemoOperation[] = [],
): { label: string; detail: string } | null {
  if (!snapshot || !selection) {
    return null;
  }

  switch (selection.kind) {
    case "unit": {
      const unit = snapshot.units.find((entry) => entry.id === selection.id);
      if (!unit) {
        return null;
      }
      const inspector = unit.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
      const operational = inspector.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
      const supply = inspector.supply && typeof inspector.supply === "object" ? inspector.supply : {};
      const orders = inspector.orders && typeof inspector.orders === "object" ? inspector.orders : {};
      const liveOrder = Array.isArray(snapshot?.bai_report?.unit_orders)
        ? snapshot.bai_report.unit_orders.find((order) => String(order?.unit_id ?? "").trim() === String(unit.id ?? "").trim()) ?? null
        : null;
      const trackedOperation = operations.find((operation) => (
        operation?.seedUnitId === unit.id
        || (Array.isArray(operation?.participants) && operation.participants.some((participant) => participant?.unitId === unit.id))
      )) ?? null;
      const location = String(operational.location_status ?? unit.location_id ?? "").trim();
      const readiness = typeof operational.readiness === "number"
        ? `${Math.round(operational.readiness)} readiness`
        : typeof unit.readiness === "number"
          ? `${Math.round(unit.readiness)} readiness`
          : "";
      const supplyState = typeof supply.supply_days_current === "number"
        ? `${supply.supply_days_current.toFixed(1)}d supply`
        : typeof supply.supply_pct === "number"
          ? `${Math.round(supply.supply_pct)}% supply`
          : "";
      const locState = String(operational?.loc?.label ?? "").trim();
      const taskAction = String(liveOrder?.action ?? trackedOperation?.commandIntent ?? orders.action ?? "").trim();
      const taskTarget = String(
        liveOrder?.target_location_id
          ?? liveOrder?.objective_id
          ?? trackedOperation?.targetLabel
          ?? trackedOperation?.objectiveName
          ?? "",
      ).trim();
      const taskStatus = String(
        liveOrder?.lifecycle_state
          ?? liveOrder?.status
          ?? (trackedOperation
            ? trackedOperation.source === "map_shortcut"
              ? "queued"
              : "approved"
            : orders.lifecycle_state ?? orders.status ?? "")
      ).trim();
      const taskDetail = [
        taskAction ? humanizeToken(taskAction) : "",
        taskTarget ? humanizeToken(taskTarget) : "",
        taskStatus ? humanizeToken(taskStatus) : "",
      ].filter(Boolean).join(" • ");
      const detail = [
        humanizeSideLabel(unit.side),
        humanizeToken(unit.unit_type ?? unit.kind ?? "formation"),
        location ? humanizeToken(location) : formatMapReference(unit),
        readiness,
        supplyState,
        locState,
        taskDetail ? `Task ${taskDetail}` : "",
      ].filter(Boolean).join(" • ");

      return {
        label: String(unit.name ?? unit.id ?? "Formation").trim() || "Formation",
        detail: detail || "Selected formation",
      };
    }
    case "objective": {
      const objective = snapshot.objectives.find((entry) => entry.id === selection.id);
      if (!objective) {
        return null;
      }
      const detail = [
        objective.state ? humanizeToken(objective.state) : "",
        objective.side ? humanizeSideLabel(objective.side) : "",
        typeof objective.value === "number" ? `Value ${objective.value}` : "",
      ].filter(Boolean).join(" • ");

      return {
        label: buildObjectiveDisplayName(objective),
        detail: detail || "Selected objective",
      };
    }
    case "airfield": {
      const airfield = snapshot.airfields.find((entry) => entry.id === selection.id);
      if (!airfield) {
        return null;
      }
      const detail = [
        airfield.state || airfield.control_state ? humanizeToken(airfield.state ?? airfield.control_state) : "",
        airfield.side ? humanizeSideLabel(airfield.side) : "",
        formatMapReference(airfield),
      ].filter(Boolean).join(" • ");

      return {
        label: String(airfield.name ?? airfield.id ?? "Airfield").trim() || "Airfield",
        detail: detail || "Selected airfield",
      };
    }
    case "port": {
      const port = snapshot.ports.find((entry) => entry.id === selection.id);
      if (!port) {
        return null;
      }

      return {
        label: String(port.name ?? port.id ?? "Port").trim() || "Port",
        detail: [humanizeToken("port anchor"), formatMapReference(port)].filter(Boolean).join(" • ") || "Selected port",
      };
    }
    default:
      return null;
  }
}

function buildToolbarLayerCatalog(
  scene: ReturnType<typeof buildMapScene> | null,
  overlayState: ReturnType<typeof buildOperationalOverlayState> | null,
  greaseEnabled: boolean,
  greaseMarkupCount: number,
  basemapAvailable: boolean,
  snapshot: ViewSnapshot | null,
) {
  const presentation = inferScenarioPresentation(snapshot ?? undefined);
  return {
    basemap: {
      label: "Packaged basemap",
      available: basemapAvailable,
      status: basemapAvailable ? "Packaged" : "Unavailable",
      detail: basemapAvailable
        ? `${presentation.basemapLabel} is available for the active scenario shell path.`
        : "No packaged runtime basemap is registered for the current scenario family.",
    },
    historicalUnderlay: overlayState?.historicalUnderlay ?? {
      label: "Historical underlay",
      available: false,
      status: "Unavailable",
      detail: "No scenario-specific historical underlay is available on the current shell path.",
    },
    terrainEmphasis: overlayState?.terrainEmphasis ?? {
      label: "Terrain emphasis",
      available: true,
      status: "Available",
      detail: "Adds a restrained terrain-emphasis wash above the terrain field.",
    },
    grid: overlayState?.grid ?? {
      label: "Hex grid",
      available: true,
      status: "Available",
      detail: "Zoom-aware major and minor grid strokes remain centralized through the overlay registry.",
    },
    weatherWash: overlayState?.weatherWash ?? {
      label: "Weather wash",
      available: false,
      status: "Unavailable",
      detail: "No authoritative weather cue is available on the current shell path.",
    },
    barriers: overlayState?.barriers ?? {
      label: "Barriers",
      available: false,
      status: "Unavailable",
      detail: "Barrier geometry is not exposed on the current shell path.",
    },
    infrastructure: overlayState?.infrastructure ?? {
      label: "Infrastructure",
      available: false,
      status: "Unavailable",
      detail: "Infrastructure geometry is not exposed on the current shell path.",
    },
    supply: overlayState?.supply ?? {
      label: "Supply",
      available: false,
      status: "Unavailable",
      detail: "Supply overlay data is not exposed on the current shell path.",
    },
    command: overlayState?.command ?? {
      label: "Command",
      available: false,
      status: "Unavailable",
      detail: "Command overlay data is not exposed on the current shell path.",
    },
    movementIntent: overlayState?.movementIntent ?? {
      label: "Movement / Orders",
      available: false,
      status: "Unavailable",
      detail: "No plotted formation currently exposes enough order state to infer an operational axis.",
    },
    frontline: overlayState?.frontline ?? {
      label: "Front / Sectors",
      available: false,
      status: "Unavailable",
      detail: "No local pressure areas are exposed for front-line inference on the current shell path.",
    },
    artillery: overlayState?.artillery ?? {
      label: "Artillery / Fire Support",
      available: false,
      status: "Unavailable",
      detail: "No artillery-support overlay records are exposed for currently plotted formations.",
    },
    fogIntel: overlayState?.fogIntel ?? {
      label: "Fog / Intel",
      available: true,
      status: "Placeholder",
      detail: "Reserved for future fog/intel wiring.",
    },
    greasePlanning: {
      label: "Planning markup",
      available: true,
      status: greaseEnabled ? `${greaseMarkupCount} mark${greaseMarkupCount === 1 ? "" : "s"}` : "Planner off",
      detail: greaseEnabled
        ? `${greaseMarkupCount} local grease mark${greaseMarkupCount === 1 ? "" : "s"} stored for this scenario.`
        : "Enable grease overlay from the planner to draw markup on the map.",
    },
    objectives: overlayState?.objectives ?? {
      label: "Objectives",
      available: Boolean(scene?.objectives?.length),
      status: scene?.objectives?.length ? `${scene.objectives.length} plotted` : "Unavailable",
      detail: scene?.objectives?.length
        ? "Objective localities and their current control state are plotted from the current command snapshot."
        : "No plotted objective localities are available on the current shell path.",
    },
  };
}

function preferredScenarioChoice(scenarios: string[]): string {
  return pickPreferredPitchScenario(scenarios) ?? "";
}

function snapshotScenarioValue(snapshot: ViewSnapshot | null): string {
  return String(snapshot?.scenario?.id ?? snapshot?.scenario?.name ?? "").trim();
}

function snapshotMatchesScenarioSelection(snapshot: ViewSnapshot | null, selectedScenario: string): boolean {
  if (!selectedScenario) {
    return Boolean(snapshot);
  }
  return scenarioKeysMatch(selectedScenario, snapshotScenarioValue(snapshot));
}

function readLauncherOpenPreference(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const persistedDismissed = window.sessionStorage.getItem(LAUNCHER_SESSION_KEY) === "true";
  return !shouldStartInShell(window.location.search, persistedDismissed);
}

function readUnknownLabel(value: unknown): string | null {
  if (value == null) {
    return null;
  }
  if (typeof value === "string" || typeof value === "number") {
    const raw = String(value).trim();
    return raw ? humanizeToken(raw) : null;
  }
  if (typeof value === "object") {
    for (const key of ["name", "label", "title", "objective_id", "target_objective", "target_location_id", "id"]) {
      const candidate = (value as Record<string, unknown>)[key];
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

function readLauncherObjective(snapshot: ViewSnapshot | null, scenarioContext: unknown = snapshot): string {
  const suppressLegacy = isKoreaScenarioContext(scenarioContext);
  const greaseObjective = snapshot?.grease_board?.objective?.trim();
  if (greaseObjective && !(suppressLegacy && containsLegacySouthPacificText(greaseObjective))) {
    return greaseObjective;
  }
  const aiObjective = readUnknownLabel(snapshot?.bai_report?.main_objective);
  if (aiObjective && !(suppressLegacy && containsLegacySouthPacificText(aiObjective))) {
    return aiObjective;
  }
  const topObjective = [...(snapshot?.objectives ?? [])]
    .filter((objective) => !(suppressLegacy && containsLegacySouthPacificText(objective?.name)))
    .sort((left, right) => (Number(right.value ?? 0) - Number(left.value ?? 0)))
    .find((objective) => Boolean(objective.name || objective.id));
  if (topObjective) {
    return buildObjectiveDisplayName(topObjective);
  }
  return "Seoul Axis";
}

function readLauncherMainEffort(snapshot: ViewSnapshot | null, scenarioContext: unknown = snapshot): string {
  const suppressLegacy = isKoreaScenarioContext(scenarioContext);
  const greaseEffort = snapshot?.grease_board?.main_effort?.trim();
  if (greaseEffort && !(suppressLegacy && containsLegacySouthPacificText(greaseEffort))) {
    return greaseEffort;
  }
  const chosenOperation = readUnknownLabel(snapshot?.bai_report?.chosen_operation);
  if (chosenOperation && !(suppressLegacy && containsLegacySouthPacificText(chosenOperation))) {
    return chosenOperation;
  }
  const aiIntent = snapshot?.ai?.last_intent?.trim();
  if (aiIntent && !(suppressLegacy && containsLegacySouthPacificText(aiIntent))) {
    return humanizeToken(aiIntent);
  }
  return "Inchon / Seoul Push";
}

export default function App() {
  const rpc = useMemo(() => makeWsRpc(wsUrl(), { proto: "1.0" }), []);
  const isPrintPreview = useMemo(() => new URLSearchParams(window.location.search).get("print") === "1", []);
  const [phase, setPhase] = useState<ShellPhase>("loading");
  const [snapshot, setSnapshot] = useState<ViewSnapshot | null>(null);
  const [previousSnapshot, setPreviousSnapshot] = useState<ViewSnapshot | null>(null);
  const [message, setMessage] = useState("Connecting to bridge...");
  const [connected, setConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [actionKind, setActionKind] = useState<ActionKind>(null);
  const [controlStatus, setControlStatus] = useState("");
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [detailDrawerPinned, setDetailDrawerPinned] = useState(false);
  const [selectedSelection, setSelectedSelection] = useState<InspectorSelection | null>(null);
  const [activeBranch, setActiveBranch] = useState<BranchName>("Theatre");
  const [communicationsOpen, setCommunicationsOpen] = useState(false);
  const [selectedCommunicationId, setSelectedCommunicationId] = useState<string | null>(null);
  const [operationPlanner, setOperationPlanner] = useState<OperationPlannerState>(() => createOperationPlannerState(null));
  const [plannerWorkbenchTab, setPlannerWorkbenchTab] = useState<PlannerWorkbenchTab>("plan");
  const [approvedOperations, setApprovedOperations] = useState<TrackedDemoOperation[]>([]);
  const [mapLayerToggles, setMapLayerToggles] = useState<Record<string, boolean>>({});
  const [greaseMarkup, setGreaseMarkup] = useState<GreaseMarkupState>(() => createGreaseMarkupState(null));
  const [autoSaveEnabled, setAutoSaveEnabled] = useState<boolean>(() => readStoredAutoSaveEnabled());
  const [launcherOpen, setLauncherOpen] = useState<boolean>(() => readLauncherOpenPreference());
  const [launcherMusicEnabled, setLauncherMusicEnabled] = useState(false);
  const [launcherMusicAvailable, setLauncherMusicAvailable] = useState<boolean | null>(null);
  const [launcherMusicPlaying, setLauncherMusicPlaying] = useState(false);
  const [launcherMusicVolume, setLauncherMusicVolume] = useState(DEFAULT_LAUNCHER_MUSIC_VOLUME);
  const snapshotRef = useRef<ViewSnapshot | null>(null);
  const launcherAudioRef = useRef<HTMLAudioElement | null>(null);
  const aiControlAvailable = Boolean(snapshot?.ai?.controller_available ?? snapshot?.ai?.enabled);
  const aiActivityState = !snapshot || !aiControlAvailable
    ? "unavailable"
    : actionKind === "ai" || Boolean(snapshot.ai.last_orders && snapshot.ai.last_orders > 0)
      ? "active"
      : "idle";
  const plannerState = useMemo(() => sanitizeOperationPlannerState(snapshot, operationPlanner), [snapshot, operationPlanner]);
  const toolbarScene = useMemo(
    () => (snapshot ? buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 }) : null),
    [snapshot],
  );
  const toolbarOverlayState = useMemo(
    () => (snapshot && toolbarScene ? buildOperationalOverlayState(snapshot, toolbarScene) : null),
    [snapshot, toolbarScene],
  );
  const toolbarLayerCatalog = useMemo(
    () => buildToolbarLayerCatalog(
      toolbarScene,
      toolbarOverlayState,
      plannerState.greaseEnabled,
      greaseMarkup.items.length,
      Boolean(snapshot && resolveBasemapPackageTheater(snapshot)),
      snapshot ?? null,
    ),
    [toolbarScene, toolbarOverlayState, plannerState.greaseEnabled, greaseMarkup.items.length, snapshot],
  );
  const toolbarResolvedLayerToggles = useMemo(() => {
    const next = { ...mapLayerToggles };
    if (plannerState.greaseEnabled) {
      next.greasePlanning = Object.prototype.hasOwnProperty.call(mapLayerToggles, "greasePlanning")
        ? mapLayerToggles.greasePlanning
        : true;
    } else {
      next.greasePlanning = false;
    }
    for (const layer of MAP_LAYER_REGISTRY) {
      if (toolbarLayerCatalog[layer.id]?.available === false) {
        next[layer.id] = false;
      }
    }
    return next;
  }, [mapLayerToggles, toolbarLayerCatalog]);
  const toolbarOverlayManager = useMemo(
    () => buildMapOverlayManager({ toggles: toolbarResolvedLayerToggles }),
    [toolbarResolvedLayerToggles],
  );
  const toolbarLayerEntries = useMemo(
    () => (snapshot ? MAP_LAYER_REGISTRY
      .filter((layer) => layer.toggleable)
      .map((layer) => {
        const summary = toolbarLayerCatalog[layer.id] || {
          label: layer.label,
          available: true,
          status: "Available",
          detail: `${layer.label} is registered in the centralized overlay manager.`,
        };
        return {
          id: layer.id,
          label: summary.label || layer.label,
          toggleable: layer.toggleable && summary.available !== false,
          active: isMapLayerEnabled(toolbarOverlayManager, layer.id),
          status: summary.status,
          detail: summary.detail,
        };
      }) : []),
    [snapshot, toolbarLayerCatalog, toolbarOverlayManager],
  );
  const activeLayerCount = useMemo(
    () => toolbarOverlayManager.registry.filter((layer) => layer.toggleable && isMapLayerEnabled(toolbarOverlayManager, layer.id)).length,
    [toolbarOverlayManager],
  );
  const fallbackPitchScenario = selectedScenario || preferredScenarioChoice(scenarios) || DEFAULT_PITCH_SCENARIO;
  const launcherScenarioMismatch = useMemo(
    () => Boolean(snapshot && selectedScenario && !snapshotMatchesScenarioSelection(snapshot, selectedScenario)),
    [snapshot, selectedScenario],
  );
  const launcherScenarioContext = useMemo(
    () => (
      snapshot && !launcherScenarioMismatch
        ? snapshot
        : { scenario: { id: fallbackPitchScenario, name: fallbackPitchScenario } }
    ),
    [snapshot, launcherScenarioMismatch, fallbackPitchScenario],
  );
  const launcherPresentation = useMemo(
    () => inferScenarioPresentation(launcherScenarioContext),
    [launcherScenarioContext],
  );
  const launcherObjective = useMemo(
    () => readLauncherObjective(snapshot, launcherScenarioContext),
    [snapshot, launcherScenarioContext],
  );
  const launcherMainEffort = useMemo(
    () => readLauncherMainEffort(snapshot, launcherScenarioContext),
    [snapshot, launcherScenarioContext],
  );
  const launcherPrimaryAction = useMemo(
    () => deriveLauncherPrimaryAction({
      hasSnapshot: Boolean(snapshot),
      phase,
      selectedScenario,
      activeScenario: snapshotScenarioValue(snapshot),
      actionKind,
    }),
    [snapshot, phase, selectedScenario, actionKind],
  );
  const launcherMusicLabel = useMemo(
    () => describeLauncherMusicState({
      available: launcherMusicAvailable,
      enabled: launcherMusicEnabled,
      playing: launcherMusicPlaying,
    }),
    [launcherMusicAvailable, launcherMusicEnabled, launcherMusicPlaying],
  );

  const updateOperationPlanner = (updater: (current: OperationPlannerState) => OperationPlannerState) => {
    if (!snapshot) {
      return;
    }
    setOperationPlanner((current) => sanitizeOperationPlannerState(snapshot, updater(sanitizeOperationPlannerState(snapshot, current))));
  };

  const plannerActions = {
    onToggleGreaseOverlay: () => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        greaseEnabled: !current.greaseEnabled,
        selectingObjective: current.greaseEnabled ? false : current.selectingObjective,
      }));
    },
    onOpenPlanner: () => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        greaseEnabled: true,
        plannerOpen: true,
        selectingObjective: !current.objectiveId,
      }));
    },
    onClosePlanner: () => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        plannerOpen: false,
        selectingObjective: false,
      }));
    },
    onBeginObjectiveSelection: () => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        greaseEnabled: true,
        plannerOpen: true,
        selectingObjective: true,
        approved: false,
      }));
    },
    onSetOperationType: (operationType: OperationPlannerState["operationType"]) => {
      if (!snapshot || operationType !== "offensive") {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        operationType,
        approved: false,
      }));
    },
    onSelectObjectiveArea: (objectiveId: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => {
        const previousAutoName = current.objectiveId
          ? defaultOperationName(snapshot, current.objectiveId, current.operationType)
          : "";
        const shouldReplaceName = !current.name.trim() || current.name.trim() === previousAutoName;
        return {
          ...current,
          greaseEnabled: true,
          plannerOpen: true,
          selectingObjective: false,
          objectiveId,
          unitRoles: buildDefaultPlannerAssignments(snapshot, objectiveId),
          name: shouldReplaceName ? defaultOperationName(snapshot, objectiveId, current.operationType) : current.name,
          approved: false,
        };
      });
    },
    onSetOperationName: (name: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        name,
        approved: false,
      }));
    },
    onSetGroundRole: (unitId: string, role: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => {
        const nextRoles = { ...current.unitRoles };
        if (role === "none") {
          delete nextRoles[unitId];
        } else {
          nextRoles[unitId] = role;
        }
        return {
          ...current,
          unitRoles: nextRoles,
          approved: false,
        };
      });
    },
    onSetAirRole: (role: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        airRole: role,
        approved: false,
      }));
    },
    onSetNavalRole: (role: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        navalRole: role,
        approved: false,
      }));
    },
    onSetTempo: (tempo: string) => {
      if (!snapshot) {
        return;
      }
      updateOperationPlanner((current) => ({
        ...current,
        tempo,
        approved: false,
      }));
    },
    onApproveOperation: () => {
      if (!snapshot) {
        return;
      }
      const approvedOperation = createApprovedOperation(snapshot, plannerState);
      if (approvedOperation) {
        setApprovedOperations((current) => upsertTrackedOperation(sanitizeTrackedOperations(snapshot, current), approvedOperation));
      }
      updateOperationPlanner((current) => ({
        ...current,
        greaseEnabled: true,
        plannerOpen: true,
        selectingObjective: false,
        approved: true,
      }));
    },
  };

  function commitFastCommand(preview: FastCommandPreview | null) {
    if (!snapshot || !preview?.available) {
      return;
    }

    const seededPlannerState = seedPlannerStateFromMapCommand(snapshot, plannerState, preview);

    setActiveBranch("Theatre");
    setPlannerWorkbenchTab("plan");
    setSelectedSelection({ kind: "unit", id: preview.unitId });
    setDetailDrawerOpen(true);

    if (preview.commandIntent === "operation" || preview.mode === "planner_review") {
      setOperationPlanner(seededPlannerState);
      setControlStatus(preview.note);
      return;
    }

    const approvedOperation = createApprovedOperation(snapshot, seededPlannerState);
    if (!approvedOperation) {
      setOperationPlanner(seededPlannerState);
      setControlStatus("Fast command seeded the planner, but deliberate objective review is still required.");
      return;
    }

    setOperationPlanner(sanitizeOperationPlannerState(snapshot, {
      ...seededPlannerState,
      approved: true,
    }));
    setApprovedOperations((current) => upsertTrackedOperation(sanitizeTrackedOperations(snapshot, current), approvedOperation));
    setControlStatus(preview.note);
  }

  const openPlannerWorkbench = (tab: PlannerWorkbenchTab) => {
    if (!snapshot) {
      return;
    }
    setActiveBranch("Theatre");
    setPlannerWorkbenchTab(tab);
    updateOperationPlanner((current) => ({
      ...current,
      plannerOpen: true,
      selectingObjective: tab === "plan" ? current.selectingObjective : false,
    }));
  };

  const greaseMarkupActions = {
    onSetActiveTool: (toolId: string | null) => {
      setGreaseMarkup((current) => ({
        ...sanitizeGreaseMarkupState(current, current.scenarioId),
        activeTool: toolId,
      }));
    },
    onSetActiveStyle: (styleId: string) => {
      setGreaseMarkup((current) => ({
        ...sanitizeGreaseMarkupState(current, current.scenarioId),
        activeStyle: styleId,
      }));
    },
    onCommitItem: (item: GreaseMarkupItem) => {
      setGreaseMarkup((current) => {
        const sanitized = sanitizeGreaseMarkupState(current, current.scenarioId);
        return {
          ...sanitized,
          selectedId: item.id,
          items: [...sanitized.items, item],
        };
      });
    },
    onSelectItem: (itemId: string | null) => {
      setGreaseMarkup((current) => ({
        ...sanitizeGreaseMarkupState(current, current.scenarioId),
        selectedId: itemId,
      }));
    },
    onRemoveSelectedItem: () => {
      setGreaseMarkup((current) => removeGreaseMarkupItem(current, current.selectedId));
    },
    onClearAll: () => {
      setGreaseMarkup((current) => clearGreaseMarkupItems(current));
    },
  };

  function toggleMapOverlay(id: string) {
    setMapLayerToggles((current) => toggleMapLayer(current, id, MAP_LAYER_REGISTRY));
  }

  async function refreshScenarioList() {
    setScenariosLoading(true);
    try {
      const nextScenarios = await loadLauncherScenarioRoster({
        connect: () => rpc.connect(),
        listScenarios: () => listScenarios(rpc),
      });
      setConnected(true);
      setScenarios(nextScenarios);
      setSelectedScenario((current) => selectLauncherScenario(current, nextScenarios));
      setControlStatus(
        nextScenarios.length
          ? `${nextScenarios.length} scenario${nextScenarios.length === 1 ? "" : "s"} available on the active bridge.`
          : "No scenarios are available on the active bridge.",
      );
    } catch (error) {
      setControlStatus(error instanceof Error ? error.message : "Unable to load scenarios.");
    } finally {
      setScenariosLoading(false);
    }
  }

  async function loadSnapshot(): Promise<boolean> {
    setRefreshing(true);
    try {
      await rpc.connect();
      setConnected(true);
      const next = await fetchViewSnapshot(rpc);
      const prior = snapshotRef.current;
      if (prior && prior.scenario?.id === next.scenario?.id) {
        setPreviousSnapshot(prior);
      } else {
        setPreviousSnapshot(null);
      }
      setOperationPlanner((current) => sanitizeOperationPlannerState(next, current));
      setApprovedOperations((current) => sanitizeTrackedOperations(next, current));
      snapshotRef.current = next;
      setSnapshot(next);
      setPhase("ready");
      setMessage("");
      return true;
    } catch (error) {
      const rpcError = error instanceof BridgeRpcError ? error : null;
      const code = rpcError?.code ?? null;
      if (code === "not_ready") {
        setPhase("not_ready");
        snapshotRef.current = null;
        setPreviousSnapshot(null);
        setSnapshot(null);
        setOperationPlanner(createOperationPlannerState(null));
        setApprovedOperations([]);
        setMessage(rpcError?.message ?? "Scenario is not active yet.");
      } else {
        setPhase("bridge_error");
        setConnected(false);
        snapshotRef.current = null;
        setPreviousSnapshot(null);
        setSnapshot(null);
        setOperationPlanner(createOperationPlannerState(null));
        setApprovedOperations([]);
        setMessage(error instanceof Error ? error.message : "Unable to reach the bridge.");
      }
      return false;
    } finally {
      setRefreshing(false);
    }
  }

  async function launchDemo(): Promise<boolean> {
    setActionKind("launch");
    setControlStatus("Launching demo scenario...");
    try {
      await rpc.connect();
      setConnected(true);
      snapshotRef.current = null;
      setPreviousSnapshot(null);
      setApprovedOperations([]);
      const startedScenario = await bootstrapDemoScenario(rpc);
      if (startedScenario) {
        const [refreshed] = await Promise.all([loadSnapshot(), refreshScenarioList()]);
        if (refreshed && !snapshotMatchesScenarioSelection(snapshotRef.current, startedScenario)) {
          const runtimeLabel = humanizeScenarioLabel(snapshotScenarioValue(snapshotRef.current) || "unknown scenario");
          setControlStatus(`Selected ${humanizeScenarioLabel(startedScenario)}, but bridge returned ${runtimeLabel}. Refusing silent fallback.`);
          return false;
        }
        setSelectedScenario(startedScenario);
        setControlStatus(refreshed ? "Demo scenario launched." : "Scenario launched, but picture refresh failed.");
        return true;
      } else {
        setPhase("empty");
        setControlStatus("No scenarios are available on the active bridge.");
        setMessage("No scenarios are available on the active bridge.");
        return false;
      }
    } catch (error) {
      setPhase("bridge_error");
      setConnected(false);
      setControlStatus(error instanceof Error ? error.message : "Unable to reach the bridge.");
      return false;
    } finally {
      setActionKind(null);
    }
  }

  async function launchSelectedScenario(): Promise<boolean> {
    if (!selectedScenario) {
      setControlStatus("No scenario is selected.");
      return false;
    }
    const targetScenario = selectedScenario;
    const scenarioLabel = humanizeScenarioLabel(targetScenario);
    setActionKind("launch");
    setControlStatus(`Launching ${scenarioLabel}...`);
    try {
      await rpc.connect();
      setConnected(true);
      snapshotRef.current = null;
      setPreviousSnapshot(null);
      setApprovedOperations([]);
      await launchScenario(rpc, targetScenario);
      const refreshed = await loadSnapshot();
      if (refreshed && !snapshotMatchesScenarioSelection(snapshotRef.current, targetScenario)) {
        const runtimeLabel = humanizeScenarioLabel(snapshotScenarioValue(snapshotRef.current) || "unknown scenario");
        setControlStatus(`Selected ${scenarioLabel}, but bridge returned ${runtimeLabel}. Refusing silent fallback.`);
        return false;
      }
      setControlStatus(refreshed ? `${scenarioLabel} launched.` : `${scenarioLabel} launched, but refresh failed.`);
      return true;
    } catch (error) {
      setControlStatus(error instanceof Error ? error.message : "Scenario launch failed.");
      return false;
    } finally {
      setActionKind(null);
    }
  }

  async function refreshPicture(): Promise<boolean> {
    setActionKind("refresh");
    setControlStatus("Refreshing situation...");
    try {
      const refreshed = await loadSnapshot();
      setControlStatus(refreshed ? "Situation refreshed." : "Refresh failed.");
      return refreshed;
    } finally {
      setActionKind(null);
    }
  }

  async function stepSixHours() {
    setActionKind("step");
    setControlStatus("Advancing by +6 hours...");
    try {
      await rpc.connect();
      setConnected(true);
      const advanceResult = await stepHours(rpc, 6);
      const refreshed = await loadSnapshot();
      if (refreshed) {
        setControlStatus(
          advanceResult.dtHoursApplied
            ? "Advanced by +6 hours."
            : advanceResult.command === "process_turn"
              ? "Processed live turn update."
              : "Advanced using bridge fallback timing.",
        );
      } else {
        setControlStatus("Time advanced, but refresh failed.");
      }
    } catch (error) {
      setControlStatus(error instanceof Error ? error.message : "Unable to advance time.");
    } finally {
      setActionKind(null);
    }
  }

  async function toggleAi() {
    if (!snapshot || !aiControlAvailable) {
      setControlStatus("AI control is unavailable on this bridge.");
      return;
    }
  }

  function toggleAutoSave() {
    setAutoSaveEnabled((current) => {
      const next = !current;
      setControlStatus(next ? "Auto Save enabled for this shell." : "Auto Save disabled for this shell.");
      return next;
    });
  }

  function exportReplay() {
    if (!snapshot || !snapshot.capabilities.can_export_replay) {
      setControlStatus("Replay export is unavailable on this bridge.");
      return;
    }
    setControlStatus("Replay export is not wired into this shell path yet.");
  }

  function saveSnapshotCapture() {
    if (!snapshot || !snapshot.capabilities.can_save_snapshot) {
      setControlStatus("Save is unavailable on this bridge.");
      return;
    }
    setControlStatus("Snapshot save is not wired into this shell path yet.");
  }

  function loadSnapshotCapture() {
    if (!snapshot || !snapshot.capabilities.can_load_snapshot) {
      setControlStatus("Load is unavailable on this bridge.");
      return;
    }
    setControlStatus("Snapshot load is not wired into this shell path yet.");
  }

  function finalizeEnterCommandShell() {
    const audio = launcherAudioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    setLauncherMusicEnabled(false);
    setLauncherMusicPlaying(false);
    setLauncherOpen(false);
  }

  async function enterCommandShell() {
    if (selectedScenario && !snapshotMatchesScenarioSelection(snapshotRef.current, selectedScenario)) {
      setControlStatus(`Syncing ${humanizeScenarioLabel(selectedScenario)} with the live command shell...`);
      const launched = await launchSelectedScenario();
      if (!launched) {
        return;
      }
    }
    finalizeEnterCommandShell();
  }

  async function handleLauncherPrimaryAction() {
    if (launcherPrimaryAction.disabled) {
      return;
    }
    if (launcherPrimaryAction.intent === "enter") {
      await enterCommandShell();
      return;
    }
    if (launcherPrimaryAction.intent === "refresh") {
      const refreshed = await refreshPicture();
      if (refreshed && snapshotRef.current) {
        await enterCommandShell();
      }
      return;
    }
    const launched = selectedScenario ? await launchSelectedScenario() : await launchDemo();
    if (launched) {
      finalizeEnterCommandShell();
    }
  }

  async function toggleLauncherMusic() {
    if (launcherMusicAvailable === false) {
      return;
    }
    const audio = launcherAudioRef.current;
    if (!audio) {
      return;
    }
    if (launcherMusicEnabled) {
      audio.pause();
      audio.currentTime = 0;
      setLauncherMusicEnabled(false);
      setLauncherMusicPlaying(false);
      return;
    }
    audio.volume = normalizeLauncherMusicVolume(launcherMusicVolume);
    audio.currentTime = 0;
    setLauncherMusicEnabled(true);
    try {
      await audio.play();
      setLauncherMusicAvailable(true);
      setLauncherMusicPlaying(true);
    } catch {
      setLauncherMusicPlaying(false);
    }
  }

  function updateLauncherMusicVolume(nextValue: number) {
    const volume = normalizeLauncherMusicVolume(nextValue);
    setLauncherMusicVolume(volume);
    const audio = launcherAudioRef.current;
    if (audio) {
      audio.volume = volume;
    }
  }

  useEffect(() => {
    void refreshScenarioList();
    void loadSnapshot();
    const timer = window.setInterval(() => setConnected(rpc.isConnected()), 1000);
    return () => {
      window.clearInterval(timer);
      rpc.close();
    };
  }, [rpc]);

  useEffect(() => {
    if (scenariosLoading || refreshing || actionKind === "launch") {
      return undefined;
    }
    if (connected && scenarios.length > 0) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void refreshScenarioList();
    }, 4000);
    return () => window.clearTimeout(timer);
  }, [actionKind, connected, refreshing, scenarios.length, scenariosLoading]);

  useEffect(() => {
    if (refreshing || actionKind === "launch") {
      return undefined;
    }
    if (!connected || phase !== "bridge_error") {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void loadSnapshot();
    }, 4500);
    return () => window.clearTimeout(timer);
  }, [actionKind, connected, phase, refreshing]);

  useEffect(() => {
    if (phase !== "ready") {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void loadSnapshot();
    }, 8000);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    if (!snapshot || !selectedSelection) {
      return;
    }
    if (!selectionExists(snapshot, selectedSelection)) {
      setSelectedSelection(null);
    }
  }, [snapshot, selectedSelection]);

  useEffect(() => {
    if (!snapshot) {
      return;
    }
    setOperationPlanner((current) => sanitizeOperationPlannerState(snapshot, current));
    setApprovedOperations((current) => sanitizeTrackedOperations(snapshot, current));
  }, [snapshot]);

  useEffect(() => {
    const scenarioId = snapshot?.scenario?.id ?? null;
    if (!scenarioId) {
      setGreaseMarkup(createGreaseMarkupState(null));
      return;
    }
    const storageKey = getGreaseMarkupStorageKey(scenarioId);
    const storedValue = window.localStorage.getItem(storageKey);
    setGreaseMarkup(deserializeGreaseMarkupState(storedValue, scenarioId));
  }, [snapshot?.scenario?.id]);

  useEffect(() => {
    if (!greaseMarkup.scenarioId) {
      return;
    }
    const storageKey = getGreaseMarkupStorageKey(greaseMarkup.scenarioId);
    window.localStorage.setItem(storageKey, JSON.stringify(serializeGreaseMarkupState(greaseMarkup)));
  }, [greaseMarkup]);

  useEffect(() => {
    window.localStorage.setItem(AUTO_SAVE_STORAGE_KEY, autoSaveEnabled ? "true" : "false");
  }, [autoSaveEnabled]);

  useEffect(() => {
    if (launcherOpen) {
      window.sessionStorage.removeItem(LAUNCHER_SESSION_KEY);
    } else {
      window.sessionStorage.setItem(LAUNCHER_SESSION_KEY, "true");
    }
  }, [launcherOpen]);

  useEffect(() => {
    const audio = launcherAudioRef.current;
    if (!audio) {
      return;
    }
    audio.volume = normalizeLauncherMusicVolume(launcherMusicVolume);
  }, [launcherMusicVolume]);

  useEffect(() => {
    const audio = launcherAudioRef.current;
    if (!audio) {
      return undefined;
    }
    const handleVisibilityChange = () => {
      if (document.hidden) {
        audio.pause();
        setLauncherMusicPlaying(false);
        return;
      }
      if (!launcherOpen || !launcherMusicEnabled || launcherMusicAvailable === false) {
        return;
      }
      void audio.play().then(
        () => {
          setLauncherMusicAvailable(true);
          setLauncherMusicPlaying(true);
        },
        () => {
          setLauncherMusicPlaying(false);
        },
      );
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [launcherMusicAvailable, launcherMusicEnabled, launcherOpen]);

  useEffect(() => {
    const audio = launcherAudioRef.current;
    if (!audio) {
      return;
    }
    if (!launcherOpen || !launcherMusicEnabled || launcherMusicAvailable === false) {
      audio.pause();
      setLauncherMusicPlaying(false);
      return;
    }
    void audio.play().then(
      () => {
        setLauncherMusicAvailable(true);
        setLauncherMusicPlaying(true);
      },
      () => {
        setLauncherMusicPlaying(false);
      },
    );
  }, [launcherOpen, launcherMusicEnabled, launcherMusicAvailable]);

  useEffect(() => {
    document.documentElement.classList.toggle("shell-html--print", isPrintPreview);
    document.body.classList.toggle("shell-body--print", isPrintPreview);
    return () => {
      document.documentElement.classList.remove("shell-html--print");
      document.body.classList.remove("shell-body--print");
    };
  }, [isPrintPreview]);

  const trackedOperations = phase === "ready" && snapshot
    ? sanitizeTrackedOperations(snapshot, approvedOperations)
    : [];

  let body;
  if (phase === "ready" && snapshot) {
    const communications = summarizeCommunications(snapshot, trackedOperations);
    const selectedUnitId = selectedSelection?.kind === "unit" ? selectedSelection.id : null;
    const previousSnapshotLabel = previousSnapshot && previousSnapshot.scenario?.id === snapshot.scenario?.id
      ? formatPreviousSnapshotLabel(previousSnapshot)
      : null;
    const previousSelectedUnit = selectedUnitId && previousSnapshotLabel
      ? previousSnapshot.units.find((unit) => unit.id === selectedUnitId) ?? null
      : null;
    const openBranchFromDashboard = (branch: Exclude<BranchName, "Dashboard" | "Theatre">) => {
      setCommunicationsOpen(false);
      setSelectedCommunicationId(null);
      setActiveBranch(branch);
    };
    const openTheatreMapFromDashboard = () => {
      setCommunicationsOpen(false);
      setSelectedCommunicationId(null);
      setDetailDrawerOpen(false);
      setDetailDrawerPinned(false);
      setSelectedSelection(null);
      setActiveBranch("Theatre");
    };
    const openUnitInspectorFromDashboard = (unitId: string) => {
      setCommunicationsOpen(false);
      setSelectedCommunicationId(null);
      setSelectedSelection({ kind: "unit", id: unitId });
      setDetailDrawerOpen(true);
      setActiveBranch("Theatre");
    };
    const openCommunicationsFromDashboard = (messageId: string | null = null) => {
      setActiveBranch("Theatre");
      setCommunicationsOpen(true);
      setSelectedCommunicationId(messageId ?? communications.latest?.id ?? null);
    };
    body =
      activeBranch === "Theatre" ? (
        <div className="shell-home">
          <div className={"shell-main" + (detailDrawerPinned ? " shell-main--drawer-pinned" : "")}>
            <MapPanelShell
              snapshot={snapshot}
              selectedSelection={selectedSelection}
              operations={trackedOperations}
              activeLayers={mapLayerToggles}
              plannerState={plannerState}
              plannerWorkbenchTab={plannerWorkbenchTab}
              plannerActions={plannerActions}
              greaseMarkup={greaseMarkup}
              greaseMarkupActions={greaseMarkupActions}
              onToggleLayer={toggleMapOverlay}
              onSelectPlannerWorkbenchTab={setPlannerWorkbenchTab}
              onCommitFastCommand={commitFastCommand}
              onSelectSelection={(selection) => {
                setSelectedSelection(selection);
                setDetailDrawerOpen(true);
              }}
            />
            <MainMapDrawer
              snapshot={snapshot}
              selection={selectedSelection}
              operations={trackedOperations}
              previousSelectedUnit={previousSelectedUnit}
              previousSnapshotLabel={previousSnapshotLabel}
              open={detailDrawerOpen}
              pinned={detailDrawerPinned}
              onOpen={() => setDetailDrawerOpen(true)}
              onClose={() => {
                setDetailDrawerOpen(false);
                setDetailDrawerPinned(false);
              }}
              onTogglePin={() => {
                setDetailDrawerOpen(true);
                setDetailDrawerPinned((current) => !current);
              }}
              onClearSelection={() => setSelectedSelection(null)}
            />
          </div>
          <div className="shell-home__lower">
            <section className="shell-weather-dock" aria-label="Weather dock">
              <MapWeatherBrief snapshot={snapshot} />
            </section>
            <div className="shell-home__commandstack">
              <HomeCommandBar snapshot={snapshot} operations={trackedOperations} activeBranch={activeBranch} onSelectBranch={setActiveBranch} />
            </div>
            <ReportsFeed
              snapshot={snapshot}
              operations={trackedOperations}
              onOpenCenter={() => {
                setCommunicationsOpen(true);
                if (!selectedCommunicationId && communications.latest) {
                  setSelectedCommunicationId(communications.latest.id);
                }
              }}
            />
          </div>
          <CommunicationsCenter
            open={communicationsOpen}
            messages={communications.history}
            demoExample={communications.demoExample}
            selectedMessageId={selectedCommunicationId}
            onClose={() => {
              setCommunicationsOpen(false);
              setSelectedCommunicationId(null);
            }}
            onSelectMessage={setSelectedCommunicationId}
            onCloseMessage={() => setSelectedCommunicationId(null)}
          />
        </div>
      ) : activeBranch === "Dashboard" ? (
        <TheaterDashboardScreen
          snapshot={snapshot}
          previousSnapshot={previousSnapshot}
          operations={trackedOperations}
          onInspectUnit={openUnitInspectorFromDashboard}
          onOpenBranch={openBranchFromDashboard}
          onOpenCommunications={openCommunicationsFromDashboard}
          onReturnToTheatre={openTheatreMapFromDashboard}
        />
      ) : activeBranch === "Air" ? (
        <AirOperationsScreen snapshot={snapshot} onReturnHome={() => setActiveBranch("Theatre")} />
      ) : activeBranch === "Land" ? (
        <LandOperationsScreen snapshot={snapshot} operations={trackedOperations} onReturnHome={() => setActiveBranch("Theatre")} />
      ) : activeBranch === "Naval" ? (
        <NavalOperationsScreen snapshot={snapshot} onReturnHome={() => setActiveBranch("Theatre")} />
      ) : activeBranch === "Intelligence" ? (
        <IntelligenceBranchScreen snapshot={snapshot} operations={trackedOperations} onReturnHome={() => setActiveBranch("Theatre")} />
      ) : activeBranch === "Logistics" ? (
        <LogisticsBranchScreen
          snapshot={snapshot}
          onReturnHome={() => setActiveBranch("Theatre")}
          onOpenReinforcementsBoard={() => setActiveBranch("Reinforcements")}
        />
      ) : activeBranch === "Reinforcements" ? (
        <ReinforcementsBoardScreen snapshot={snapshot} onReturnToLogistics={() => setActiveBranch("Logistics")} />
      ) : (
        <BranchPlaceholder branch={activeBranch} onReturnHome={() => setActiveBranch("Theatre")} />
      );
  } else if (phase === "bridge_error") {
    body = (
      <StateScreen
        title="Bridge unavailable"
        message={message || "The shell could not connect to the active ws15 bridge."}
        action={
          <button className="shell-button" onClick={() => void loadSnapshot()} disabled={refreshing || !!actionKind}>
            Retry Connection
          </button>
        }
      />
    );
  } else if (phase === "not_ready") {
    body = (
      <StateScreen
        title="Scenario not ready"
        message={message || "A scenario has not been started on the active bridge yet."}
        action={
          <>
            <button className="shell-button" onClick={() => void loadSnapshot()} disabled={refreshing || !!actionKind}>
              Retry Snapshot
            </button>
            <button className="shell-button" onClick={() => void launchDemo()} disabled={refreshing || !!actionKind}>
              Launch Demo Scenario
            </button>
          </>
        }
      />
    );
  } else if (phase === "empty") {
    body = (
      <StateScreen
        title="No scenarios available"
        message={message || "The bridge responded, but no launchable scenarios were listed."}
      />
    );
  } else {
    body = <StateScreen title="Loading shell" message={message} />;
  }

  const shellChrome = (
    <div className={`shell-root${isPrintPreview ? " shell-root--print" : ""}`}>
      <TopStrip
        snapshot={snapshot}
        activeBranch={activeBranch}
        layerEntries={phase === "ready" && snapshot ? toolbarLayerEntries : []}
        activeLayerCount={phase === "ready" && snapshot ? activeLayerCount : 0}
        connected={connected}
        refreshing={refreshing}
        scenarios={scenarios}
        scenariosLoading={scenariosLoading}
        selectedScenario={selectedScenario}
        controlStatus={controlStatus}
        actionKind={actionKind}
        aiControlAvailable={aiControlAvailable}
        aiActivityState={aiActivityState}
        autoSaveEnabled={autoSaveEnabled}
        selectionSummary={phase === "ready" && snapshot ? buildSelectionSummary(snapshot, selectedSelection, trackedOperations) : null}
        onSelectBranch={setActiveBranch}
        onOpenPlannerWorkbench={openPlannerWorkbench}
        onSelectScenario={setSelectedScenario}
        onLaunchScenario={() => void launchSelectedScenario()}
        onStepSixHours={() => void stepSixHours()}
        onRefresh={() => void refreshPicture()}
        onToggleAi={() => void toggleAi()}
        onToggleAutoSave={toggleAutoSave}
        onReplay={exportReplay}
        onSave={saveSnapshotCapture}
        onLoad={loadSnapshotCapture}
      />
      {body}
    </div>
  );

  return (
    <>
      <audio
        ref={launcherAudioRef}
        src={LAUNCHER_MUSIC_SRC}
        loop
        preload="metadata"
        playsInline
        onLoadedMetadata={() => setLauncherMusicAvailable(true)}
        onCanPlayThrough={() => setLauncherMusicAvailable(true)}
        onError={() => {
          setLauncherMusicAvailable(false);
          setLauncherMusicEnabled(false);
          setLauncherMusicPlaying(false);
        }}
        onPause={() => setLauncherMusicPlaying(false)}
        onPlay={() => setLauncherMusicPlaying(true)}
      />
      {launcherOpen && !isPrintPreview ? (
        <LauncherScreen
          title="Theater of Operations"
          subtitle="Inchon"
          theaterLabel={launcherPresentation.theaterLabel}
          scenarioName={launcherPresentation.scenarioLabel}
          scenarioStatus={launcherScenarioMismatch
            ? `Runtime mismatch: ${humanizeScenarioLabel(snapshotScenarioValue(snapshot))} is active`
            : snapshot ? "Live operational picture ready" : phase === "bridge_error" ? "Bridge offline" : "Awaiting launch state"}
          bridgeStatus={connected ? "Connected" : "Offline"}
          currentTurn={snapshot?.time.turn != null ? `Turn ${snapshot.time.turn}` : "Turn unavailable"}
          currentPhase={snapshot?.time.phase ? humanizeToken(snapshot.time.phase) : "Phase unavailable"}
          objective={launcherObjective}
          mainEffort={launcherMainEffort}
          selectedScenario={selectedScenario}
          scenarios={scenarios}
          scenariosLoading={scenariosLoading}
          controlStatus={controlStatus}
          primaryActionLabel={launcherPrimaryAction.label}
          primaryActionDisabled={launcherPrimaryAction.disabled}
          enterActionDisabled={actionKind !== null}
          refreshDisabled={refreshing || actionKind !== null}
          musicLabel={launcherMusicLabel}
          musicVolume={launcherMusicVolume}
          musicDisabled={launcherMusicAvailable === false}
          musicEnabled={launcherMusicEnabled}
          onSelectScenario={setSelectedScenario}
          onPrimaryAction={() => void handleLauncherPrimaryAction()}
          onEnterShell={() => void enterCommandShell()}
          onRefresh={() => void refreshPicture()}
          onToggleMusic={() => void toggleLauncherMusic()}
          onSetMusicVolume={updateLauncherMusicVolume}
        />
      ) : null}
      {!launcherOpen || isPrintPreview ? shellChrome : null}
    </>
  );
}
