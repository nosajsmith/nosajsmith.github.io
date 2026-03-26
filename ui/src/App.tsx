import { useEffect, useMemo, useRef, useState } from "react";
import TopStrip from "./components/shell/TopStrip";
import MapPanelShell from "./components/shell/MapPanelShell";
import MainMapDrawer from "./components/shell/MainMapDrawer";
import ReportsFeed from "./components/shell/ReportsFeed";
import HomeCommandBar from "./components/shell/HomeCommandBar";
import MapWeatherBrief from "./components/shell/MapWeatherBrief";
import CommunicationsCenter from "./components/shell/CommunicationsCenter";
import BranchPlaceholder from "./components/shell/BranchPlaceholder";
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
  buildDefaultPlannerAssignments,
  createApprovedOperation,
  createOperationPlannerState,
  defaultOperationName,
  sanitizeOperationPlannerState,
  sanitizeTrackedOperations,
  upsertTrackedOperation,
} from "./components/shell/operations_planner.js";
import type { OperationPlannerState, TrackedDemoOperation } from "./components/shell/operations_planner_types";
import { makeWsRpc } from "./lib/ws_rpc";
import { humanizeScenarioLabel } from "./lib/view_snapshot.js";
import {
  BridgeRpcError,
  bootstrapDemoScenario,
  fetchViewSnapshot,
  launchScenario,
  listScenarios,
  stepHours,
  wsUrl,
} from "./lib/view_snapshot.ts";
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

function buildToolbarLayerCatalog(
  scene: ReturnType<typeof buildMapScene> | null,
  overlayState: ReturnType<typeof buildOperationalOverlayState> | null,
  greaseEnabled: boolean,
  greaseMarkupCount: number,
  basemapAvailable: boolean,
) {
  return {
    basemap: {
      label: "Packaged basemap",
      available: basemapAvailable,
      status: basemapAvailable ? "Packaged" : "Unavailable",
      detail: basemapAvailable
        ? "Hex-space runtime basemap package is available for the current theater family."
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
  const snapshotRef = useRef<ViewSnapshot | null>(null);
  const aiControlAvailable = false;
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
      await rpc.connect();
      setConnected(true);
      const nextScenarios = await listScenarios(rpc);
      setScenarios(nextScenarios);
      setSelectedScenario((current) => {
        if (current && nextScenarios.includes(current)) {
          return current;
        }
        return nextScenarios[0] ?? "";
      });
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

  async function launchDemo() {
    setActionKind("launch");
    setControlStatus("Launching demo scenario...");
    try {
      await rpc.connect();
      setConnected(true);
      snapshotRef.current = null;
      setPreviousSnapshot(null);
      setApprovedOperations([]);
      const started = await bootstrapDemoScenario(rpc);
      if (started) {
        const [refreshed] = await Promise.all([loadSnapshot(), refreshScenarioList()]);
        setControlStatus(refreshed ? "Demo scenario launched." : "Scenario launched, but picture refresh failed.");
      } else {
        setPhase("empty");
        setControlStatus("No scenarios are available on the active bridge.");
        setMessage("No scenarios are available on the active bridge.");
      }
    } catch (error) {
      setPhase("bridge_error");
      setConnected(false);
      setControlStatus(error instanceof Error ? error.message : "Unable to reach the bridge.");
    } finally {
      setActionKind(null);
    }
  }

  async function launchSelectedScenario() {
    if (!selectedScenario) {
      setControlStatus("No scenario is selected.");
      return;
    }
    const scenarioLabel = humanizeScenarioLabel(selectedScenario);
    setActionKind("launch");
    setControlStatus(`Launching ${scenarioLabel}...`);
    try {
      await rpc.connect();
      setConnected(true);
      snapshotRef.current = null;
      setPreviousSnapshot(null);
      setApprovedOperations([]);
      await launchScenario(rpc, selectedScenario);
      const refreshed = await loadSnapshot();
      setControlStatus(refreshed ? `${scenarioLabel} launched.` : `${scenarioLabel} launched, but refresh failed.`);
    } catch (error) {
      setControlStatus(error instanceof Error ? error.message : "Scenario launch failed.");
    } finally {
      setActionKind(null);
    }
  }

  async function refreshPicture() {
    setActionKind("refresh");
    setControlStatus("Refreshing situation...");
    try {
      const refreshed = await loadSnapshot();
      setControlStatus(refreshed ? "Situation refreshed." : "Refresh failed.");
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
      await stepHours(rpc, 6);
      const refreshed = await loadSnapshot();
      setControlStatus(refreshed ? "Advanced by +6 hours." : "Time advanced, but refresh failed.");
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
    document.documentElement.classList.toggle("shell-html--print", isPrintPreview);
    document.body.classList.toggle("shell-body--print", isPrintPreview);
    return () => {
      document.documentElement.classList.remove("shell-html--print");
      document.body.classList.remove("shell-body--print");
    };
  }, [isPrintPreview]);

  let body;
  if (phase === "ready" && snapshot) {
    const communications = summarizeCommunications(snapshot.reports);
    const selectedUnitId = selectedSelection?.kind === "unit" ? selectedSelection.id : null;
    const trackedOperations = sanitizeTrackedOperations(snapshot, approvedOperations);
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
              onSelectSelection={(selection) => {
                setSelectedSelection(selection);
                setDetailDrawerOpen(true);
              }}
            />
            <MainMapDrawer
              snapshot={snapshot}
              selection={selectedSelection}
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
        <IntelligenceBranchScreen snapshot={snapshot} onReturnHome={() => setActiveBranch("Theatre")} />
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

  return (
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
        aiActivityState={!snapshot || !aiControlAvailable ? "unavailable" : actionKind === "ai" ? "active" : "idle"}
        autoSaveEnabled={autoSaveEnabled}
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
}
