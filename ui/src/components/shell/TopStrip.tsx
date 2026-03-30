import type { ViewSnapshot } from "../../types/viewSnapshot";
import { humanizeCampaignStatus, humanizeScenarioLabel, humanizeToken, inferScenarioPresentation } from "../../lib/view_snapshot.js";
import { DEFAULT_PITCH_SCENARIO } from "../../lib/scenario_adapter.js";
import type { PlannerWorkbenchTab } from "./OperationPlannerPanel";

type ActionKind = "refresh" | "launch" | "step" | "ai" | null;
type LayerEntry = {
  id: string;
  label: string;
  toggleable: boolean;
  active: boolean;
  status: string;
  detail: string;
};

type TopStripProps = {
  snapshot: ViewSnapshot | null;
  activeBranch: "Theatre" | "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements";
  layerEntries: LayerEntry[];
  activeLayerCount: number;
  connected: boolean;
  refreshing: boolean;
  scenarios: string[];
  scenariosLoading: boolean;
  selectedScenario: string;
  controlStatus: string;
  actionKind: ActionKind;
  aiControlAvailable: boolean;
  aiActivityState: "active" | "idle" | "unavailable";
  autoSaveEnabled: boolean;
  selectionSummary: { label: string; detail: string } | null;
  onSelectBranch: (branch: "Theatre" | "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements") => void;
  onOpenPlannerWorkbench: (tab: PlannerWorkbenchTab) => void;
  onSelectScenario: (value: string) => void;
  onLaunchScenario: () => void;
  onStepSixHours: () => void;
  onRefresh: () => void;
  onToggleAi: () => void;
  onToggleAutoSave: () => void;
  onReplay: () => void;
  onSave: () => void;
  onLoad: () => void;
};

function buildScenarioInstant(currentHours: number | null, epoch: { year: number; monthIndex: number; day: number } | null): Date | null {
  if (currentHours == null || !epoch) {
    return null;
  }
  return new Date(Date.UTC(epoch.year, epoch.monthIndex, epoch.day, 0, 0, 0) + currentHours * 60 * 60 * 1000);
}

function formatScenarioCalendar(instant: Date | null): string {
  if (!instant) {
    return "Calendar unavailable";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(instant).replace(",", "");
}

function formatReferenceClock(instant: Date | null, timeZone: string): string {
  if (!instant) {
    return "----";
  }
  const parts = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone,
  }).formatToParts(instant);
  const hour = parts.find((part) => part.type === "hour")?.value ?? "--";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "--";
  return `${hour}${minute}`;
}

const VIEW_OPTIONS = [
  { value: "Theatre", label: "Theatre" },
  { value: "Dashboard", label: "Dashboard" },
  { value: "Land", label: "Land Operations" },
  { value: "Air", label: "Air Operations" },
  { value: "Naval", label: "Naval Operations" },
  { value: "Logistics", label: "Logistics" },
  { value: "Intelligence", label: "Intelligence" },
  { value: "Reinforcements", label: "Reinforcements" },
] as const;

export default function TopStrip({
  snapshot,
  activeBranch,
  layerEntries,
  activeLayerCount,
  connected,
  refreshing,
  scenarios,
  scenariosLoading,
  selectedScenario,
  controlStatus,
  actionKind,
  aiControlAvailable,
  aiActivityState,
  autoSaveEnabled,
  selectionSummary,
  onSelectBranch,
  onOpenPlannerWorkbench,
  onSelectScenario,
  onLaunchScenario,
  onStepSixHours,
  onRefresh,
  onToggleAi,
  onToggleAutoSave,
  onReplay,
  onSave,
  onLoad,
}: TopStripProps) {
  const fallbackScenario = selectedScenario || DEFAULT_PITCH_SCENARIO;
  const presentation = inferScenarioPresentation(snapshot ?? { scenario: { id: fallbackScenario, name: fallbackScenario } });
  const scenarioName = presentation.scenarioLabel || humanizeScenarioLabel(snapshot?.scenario.name ?? fallbackScenario);
  const currentHours = snapshot?.time.current_hours ?? null;
  const scenarioInstant = buildScenarioInstant(currentHours, presentation.calendarEpoch);
  const turnLabel = snapshot?.time.turn != null ? String(snapshot.time.turn) : "--";
  const day = currentHours != null ? `Day ${Math.floor(currentHours / 24) + 1}` : "Day ?";
  const phaseLabel = snapshot?.time.phase ? humanizeToken(snapshot.time.phase) : "Phase unavailable";
  const unitCount = snapshot?.units.length ?? null;
  const campaignStatus = snapshot?.campaign?.status ? humanizeCampaignStatus(snapshot.campaign.status) : "Status unavailable";
  const calendar = formatScenarioCalendar(scenarioInstant);
  const referenceClocks = presentation.referenceClocks.map((clock) => ({
    label: clock.label,
    value: formatReferenceClock(scenarioInstant, clock.timeZone),
  }));
  const capabilities = snapshot?.capabilities;
  const hasSnapshot = !!snapshot;
  const controlsBusy = refreshing || actionKind !== null;
  const scenarioControlDisabled = scenariosLoading || controlsBusy;
  const canStep = hasSnapshot && !controlsBusy;
  const canToggleAi = hasSnapshot && !controlsBusy && aiControlAvailable;
  const refreshDisabled = controlsBusy;
  const replayUnavailable = !capabilities?.can_export_replay;
  const saveUnavailable = !capabilities?.can_save_snapshot;
  const loadUnavailable = !capabilities?.can_load_snapshot;
  const baiTone = aiActivityState === "active" ? "is-live" : "is-idle";
  const baiTitle = !hasSnapshot
    ? "BAI status is unavailable until a scenario picture is loaded."
    : aiActivityState === "active"
      ? "BAI is actively evaluating or processing."
      : aiControlAvailable
        ? "BAI is idle and not actively processing."
        : "BAI control is unavailable on this bridge.";
  const bridgeTitle = connected ? "Bridge connection is live and reporting." : "Bridge connection is offline or not reporting.";
  const autoSaveTitle = autoSaveEnabled ? "Auto Save is enabled for this shell." : "Auto Save is disabled for this shell.";
  const actionButtons = [
    {
      id: "replay",
      label: "Replay",
      disabled: !hasSnapshot || replayUnavailable || controlsBusy,
      title: !hasSnapshot || replayUnavailable ? "Replay export unavailable on this bridge." : "Replay export action.",
      onClick: onReplay,
    },
    {
      id: "save",
      label: "Save",
      disabled: !hasSnapshot || saveUnavailable || controlsBusy,
      title: !hasSnapshot || saveUnavailable ? "Snapshot save unavailable on this bridge." : "Save current shell snapshot.",
      onClick: onSave,
    },
    {
      id: "load",
      label: "Load",
      disabled: !hasSnapshot || loadUnavailable || controlsBusy,
      title: !hasSnapshot || loadUnavailable ? "Snapshot load unavailable on this bridge." : "Load a saved shell snapshot.",
      onClick: onLoad,
    },
  ];

  return (
    <header className="shell-topstrip">
      <div className="shell-topstrip__identity">
        <div className="shell-eyebrow">{presentation.theaterLabel}</div>
        <h1 className="shell-title">{presentation.shellTitle}</h1>
        <div className="shell-topstrip__identity-note">
          {[scenarioName, presentation.frontLabel, campaignStatus].filter(Boolean).join(" • ")}
        </div>
      </div>

      <div className="shell-topstrip__center">
        <div className="shell-topstrip__status">
          <div className="shell-chip">
            <span className="shell-chip__label">Turn</span>
            <strong>{turnLabel}</strong>
          </div>
          <div className="shell-chip">
            <span className="shell-chip__label">Day</span>
            <strong>{day}</strong>
          </div>
          <div className="shell-chip">
            <span className="shell-chip__label">Phase</span>
            <strong>{phaseLabel}</strong>
          </div>
          <div className="shell-chip">
            <span className="shell-chip__label">Calendar</span>
            <strong>{calendar}</strong>
          </div>
          <div className="shell-chip">
            <span className="shell-chip__label">Units</span>
            <strong>{unitCount ?? "--"}</strong>
          </div>
          {selectionSummary ? (
            <div className="shell-chip shell-chip--selection" title={selectionSummary.detail}>
              <span className="shell-chip__label">Selection</span>
              <strong>{selectionSummary.label}</strong>
            </div>
          ) : null}
          <div className="shell-topstrip__clocks" aria-label="Reference clocks">
            {referenceClocks.map((clock) => (
              <div className="shell-topstrip__clock" key={clock.label}>
                <span className="shell-topstrip__clock-label">{clock.label}</span>
                <strong>{clock.value}</strong>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="shell-topstrip__actions">
        <div className="shell-topstrip__controlbank">
          <div className="shell-control-group shell-control-group--compact">
            <span className="shell-control-group__label">View</span>
            <select
              className="shell-select shell-select--compact"
              value={activeBranch}
              onChange={(event) => onSelectBranch(event.target.value as TopStripProps["activeBranch"])}
              disabled={!hasSnapshot}
            >
              {VIEW_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="shell-control-group shell-control-group--compact">
            <span className="shell-control-group__label">Layers</span>
            <button
              type="button"
              className="shell-button shell-button--secondary shell-topstrip__planner-entry"
              onClick={() => onOpenPlannerWorkbench("map")}
              disabled={!hasSnapshot}
              title={layerEntries.length
                ? `${activeLayerCount} layer toggle${activeLayerCount === 1 ? "" : "s"} currently enabled. Detailed controls live in Planner > Map.`
                : "Detailed layer controls are available from Planner > Map once a scenario picture is loaded."}
            >
              <span>Layers</span>
              <strong>{activeLayerCount ? `${activeLayerCount} On` : "Off"}</strong>
            </button>
          </div>

          <div className="shell-control-group">
            <span className="shell-control-group__label">Scenario</span>
            <div className="shell-control-row">
              <select
                className="shell-select"
                value={selectedScenario}
                onChange={(event) => onSelectScenario(event.target.value)}
                disabled={scenarioControlDisabled || !scenarios.length}
              >
                {scenarios.length ? (
                  scenarios.map((scenario) => (
                    <option key={scenario} value={scenario}>
                      {humanizeScenarioLabel(scenario)}
                    </option>
                  ))
                ) : (
                  <option value="">{scenariosLoading ? "Loading scenarios..." : "No scenarios available"}</option>
                )}
              </select>
              <button className="shell-button" onClick={onLaunchScenario} disabled={scenarioControlDisabled || !selectedScenario}>
                {actionKind === "launch" ? "Launching..." : "Launch"}
              </button>
            </div>
          </div>

          <div className="shell-control-group">
            <span className="shell-control-group__label">Operations</span>
            <div className="shell-control-row">
              <button className="shell-button" onClick={onStepSixHours} disabled={!canStep}>
                {actionKind === "step" ? "Stepping..." : "Step +6h"}
              </button>
              <button className="shell-button shell-button--secondary" onClick={onRefresh} disabled={refreshDisabled}>
                {refreshing || actionKind === "refresh" ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>
        </div>

        <aside className="shell-statusstrip" aria-label="Command status strip" title={controlStatus || undefined}>
          <button
            type="button"
            className={`shell-statusstrip__item shell-statusstrip__item--status ${baiTone}`}
            onClick={onToggleAi}
            disabled={!canToggleAi}
            aria-pressed={snapshot?.ai.enabled ?? false}
            aria-label={`BAI status: ${aiActivityState}`}
            title={baiTitle}
          >
            <span>BAI</span>
          </button>
          <span
            className={`shell-statusstrip__item shell-statusstrip__item--status shell-statusstrip__item--readonly ${connected ? "is-live" : "is-idle"}`}
            role="status"
            aria-label={`Bridge status: ${connected ? "live" : "inactive"}`}
            title={bridgeTitle}
          >
            <span>Bridge</span>
          </span>
          {actionButtons.slice(0, 2).map((item) => (
            <button
              key={item.id}
              type="button"
              className="shell-statusstrip__item shell-statusstrip__item--action"
              onClick={item.onClick}
              disabled={item.disabled}
              title={item.title}
            >
              <span>{item.label}</span>
            </button>
          ))}
          <button
            type="button"
            className={`shell-statusstrip__item shell-statusstrip__item--status ${autoSaveEnabled ? "is-live" : "is-idle"}`}
            onClick={onToggleAutoSave}
            aria-pressed={autoSaveEnabled}
            aria-label={`Auto Save status: ${autoSaveEnabled ? "enabled" : "disabled"}`}
            title={autoSaveTitle}
          >
            <span>Auto Save</span>
          </button>
          {actionButtons.slice(2).map((item) => (
            <button
              key={item.id}
              type="button"
              className="shell-statusstrip__item shell-statusstrip__item--action"
              onClick={item.onClick}
              disabled={item.disabled}
              title={item.title}
            >
              <span>{item.label}</span>
            </button>
          ))}
        </aside>
      </div>
    </header>
  );
}
