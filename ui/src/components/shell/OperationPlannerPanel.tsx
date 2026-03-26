import type { ReactNode } from "react";
import {
  AIR_ROLE_OPTIONS,
  GROUND_ROLE_OPTIONS,
  NAVAL_ROLE_OPTIONS,
  TEMPO_OPTIONS,
} from "./operations_planner.js";
import type {
  AirRoleId,
  GroundRoleId,
  NavalRoleId,
  OperationPlannerActions,
  OperationPlannerState,
  OperationTypeId,
  TempoId,
} from "./operations_planner_types";

export type PlannerWorkbenchTab = "plan" | "map" | "qa";

type OperationPlannerPanelProps = {
  summary: any;
  plannerState: OperationPlannerState;
  actions: OperationPlannerActions;
  embedded?: boolean;
  workbenchTab: PlannerWorkbenchTab;
  onSelectWorkbenchTab: (tab: PlannerWorkbenchTab) => void;
  showQaTab?: boolean;
  plannerStatus: {
    activeTool: string;
    selectedColor: string;
    visibility: string;
    layers: string;
  };
  planWorkbench?: ReactNode;
  mapWorkbench?: ReactNode;
  qaWorkbench?: ReactNode;
};

const WORKBENCH_TABS: Array<{ id: PlannerWorkbenchTab; label: string; description: string }> = [
  { id: "plan", label: "Plan", description: "Operation design, grease markup, and approval workflow." },
  { id: "map", label: "Map", description: "Detailed layer, grid, and map-state controls." },
  { id: "qa", label: "QA", description: "Dev-only validation and benchmark tooling." },
];

export default function OperationPlannerPanel({
  summary,
  plannerState,
  actions,
  embedded = false,
  workbenchTab,
  onSelectWorkbenchTab,
  showQaTab = true,
  plannerStatus,
  planWorkbench = null,
  mapWorkbench = null,
  qaWorkbench = null,
}: OperationPlannerPanelProps) {
  const workbenchTabs = showQaTab ? WORKBENCH_TABS : WORKBENCH_TABS.filter((tab) => tab.id !== "qa");
  const effectiveWorkbenchTab = workbenchTabs.some((tab) => tab.id === workbenchTab) ? workbenchTab : "plan";

  return (
    <div
      className={"shell-map__planner" + (embedded ? " shell-map__planner--embedded" : "")}
      aria-label="Operations planner"
    >
      {embedded ? null : (
        <div className="shell-map__planner-head">
          <div>
            <div className="shell-map__planner-kicker">Operations Planner</div>
            <div className="shell-map__planner-title">Demo Workflow</div>
          </div>
          <button type="button" className="shell-map__planner-close" onClick={actions.onClosePlanner}>
            Close
          </button>
        </div>
      )}

      <div className="shell-map__planner-statusstrip" aria-label="Planner status">
        <div className="shell-map__planner-statusmetric">
          <span>Tool</span>
          <strong>{plannerStatus.activeTool}</strong>
        </div>
        <div className="shell-map__planner-statusmetric">
          <span>Color</span>
          <strong>{plannerStatus.selectedColor}</strong>
        </div>
        <div className="shell-map__planner-statusmetric">
          <span>Markup</span>
          <strong>{plannerStatus.visibility}</strong>
        </div>
        <div className="shell-map__planner-statusmetric">
          <span>Layers</span>
          <strong>{plannerStatus.layers}</strong>
        </div>
      </div>

      <div className="shell-map__planner-workbench">
        <div className="shell-map__planner-tabs" role="tablist" aria-label="Planner workbench sections">
          {workbenchTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={effectiveWorkbenchTab === tab.id}
              className={"shell-map__planner-tab" + (effectiveWorkbenchTab === tab.id ? " is-active" : "")}
              onClick={() => onSelectWorkbenchTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="shell-map__planner-workbench-note">
          {workbenchTabs.find((tab) => tab.id === effectiveWorkbenchTab)?.description}
        </div>
      </div>

      {effectiveWorkbenchTab === "plan" ? (
        <>
          <div className="shell-map__planner-note">{summary.note}</div>
          {planWorkbench}

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Operation Type</div>
            <div className="shell-map__planner-chip-row">
              {summary.operationTypes.map((option: any) => (
                <button
                  key={option.id}
                  type="button"
                  className={"shell-map__planner-chip" + (option.selected ? " is-selected" : "") + (!option.available ? " is-unavailable" : "")}
                  onClick={() => option.available && actions.onSetOperationType(option.id as OperationTypeId)}
                  disabled={!option.available}
                  title={option.note}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Operation Identity</div>
            <div className="shell-map__planner-grid">
              <label className="shell-map__planner-field">
                <span>Name</span>
                <input
                  className="shell-map__planner-input"
                  value={plannerState.name}
                  onChange={(event) => actions.onSetOperationName(event.target.value)}
                  placeholder={summary.identity.name}
                />
              </label>
              <div className="shell-map__planner-field">
                <span>Type</span>
                <strong>{summary.identity.type}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Lead HQ</span>
                <strong>{summary.identity.leadHq}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Objective Area</span>
                <strong>{summary.identity.objectiveArea}</strong>
              </div>
            </div>
            <div className="shell-map__planner-actions">
              <button type="button" className="shell-button shell-button--secondary" onClick={actions.onBeginObjectiveSelection}>
                {plannerState.selectingObjective ? "Marking Objective..." : "Mark Objective Area"}
              </button>
              <div className="shell-map__planner-note">{summary.objectiveArea.prompt}</div>
            </div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Ground Forces</div>
            <div className="shell-map__planner-note">{summary.groundForces.note}</div>
            {summary.groundForces.rows.length ? (
              <div className="shell-map__planner-force-list">
                {summary.groundForces.rows.map((row: any) => (
                  <div className="shell-map__planner-force-row" key={row.id}>
                    <div className="shell-map__planner-force-head">
                      <strong>{row.name}</strong>
                      <span>{row.proximity}</span>
                    </div>
                    <div className="shell-map__planner-force-meta">{row.condition}</div>
                    <div className="shell-map__planner-force-meta">{row.supplyLabel} • {row.locLabel}</div>
                    <div className="shell-map__planner-force-meta">{row.supportLabel}</div>
                    <div className="shell-map__planner-force-control">
                      <label className="shell-map__planner-field">
                        <span>Role</span>
                        <select
                          className="shell-map__planner-select"
                          value={row.roleId}
                          onChange={(event) => actions.onSetGroundRole(row.id, event.target.value as GroundRoleId)}
                        >
                          {GROUND_ROLE_OPTIONS.map((option) => (
                            <option key={option.id} value={option.id}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                      <div className="shell-map__planner-estimate">
                        <span>Assembly</span>
                        <strong>{row.assemblyEstimate}</strong>
                        <div>{row.assemblyPrepDays}</div>
                      </div>
                    </div>
                    <div className="shell-map__planner-note">{row.warning}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="shell-empty">No plottable ground formations are available for objective-based planning on the current shell path.</div>
            )}
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Air Support</div>
            <div className="shell-map__planner-grid">
              <label className="shell-map__planner-field">
                <span>Role</span>
                <select
                  className="shell-map__planner-select"
                  value={plannerState.airRole}
                  onChange={(event) => actions.onSetAirRole(event.target.value as AirRoleId)}
                >
                  {AIR_ROLE_OPTIONS.map((option) => (
                    <option key={option.id} value={option.id}>{option.label}</option>
                  ))}
                </select>
              </label>
              <div className="shell-map__planner-field">
                <span>Availability</span>
                <strong>{summary.airSupport.availability}</strong>
              </div>
            </div>
            <div className="shell-map__planner-note">{summary.airSupport.supportingFormation}</div>
            <div className="shell-map__planner-note">{summary.airSupport.constraint}</div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Naval Support</div>
            <div className="shell-map__planner-grid">
              <label className="shell-map__planner-field">
                <span>Role</span>
                <select
                  className="shell-map__planner-select"
                  value={plannerState.navalRole}
                  onChange={(event) => actions.onSetNavalRole(event.target.value as NavalRoleId)}
                >
                  {NAVAL_ROLE_OPTIONS.map((option) => (
                    <option key={option.id} value={option.id}>{option.label}</option>
                  ))}
                </select>
              </label>
              <div className="shell-map__planner-field">
                <span>Availability</span>
                <strong>{summary.navalSupport.availability}</strong>
              </div>
            </div>
            <div className="shell-map__planner-note">{summary.navalSupport.posture}</div>
            <div className="shell-map__planner-note">{summary.navalSupport.constraint}</div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Tempo / OPSEC</div>
            <div className="shell-map__planner-chip-row">
              {TEMPO_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={"shell-map__planner-chip" + (plannerState.tempo === option.id ? " is-selected" : "")}
                  onClick={() => actions.onSetTempo(option.id as TempoId)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div className="shell-map__planner-note">{summary.tempo.note}</div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Staff Estimate / Feasibility</div>
            <div className="shell-map__planner-grid">
              <div className="shell-map__planner-field">
                <span>Days to Assemble</span>
                <strong>{summary.staffEstimate.prepDays}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Readiness / Support</span>
                <strong>{summary.staffEstimate.readinessNote}</strong>
              </div>
            </div>
            {summary.staffEstimate.warnings.length ? (
              <ul className="shell-map__planner-warning-list">
                {summary.staffEstimate.warnings.map((warning: string) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : (
              <div className="shell-map__planner-note">No immediate planning warning from current exposed fields.</div>
            )}
            <div className="shell-map__planner-note">{summary.staffEstimate.note}</div>
          </section>

          <section className="shell-map__planner-section">
            <div className="shell-map__planner-section-title">Approval Summary</div>
            <div className="shell-map__planner-grid">
              <div className="shell-map__planner-field">
                <span>Operation</span>
                <strong>{summary.approval.operationName}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Objective</span>
                <strong>{summary.approval.objective}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Prep Time</span>
                <strong>{summary.approval.estimatedPrepTime}</strong>
              </div>
              <div className="shell-map__planner-field">
                <span>Launch Condition</span>
                <strong>{summary.approval.launchCondition}</strong>
              </div>
            </div>
            <div className="shell-map__planner-note">Forces: {summary.approval.participatingForces.join(" • ")}</div>
            <div className="shell-map__planner-note">Support: {summary.approval.supportAssigned.join(" • ")}</div>
            <div className="shell-map__planner-note">{summary.approval.note}</div>
            <div className="shell-map__planner-approval">
              <div className={"shell-map__planner-status" + (plannerState.approved ? " is-approved" : "")}>
                {summary.approval.status}
              </div>
              <button
                type="button"
                className="shell-button"
                onClick={actions.onApproveOperation}
                disabled={!summary.approval.ready}
              >
                {plannerState.approved ? "Update Approved Operation" : "Approve Operation"}
              </button>
            </div>
          </section>
        </>
      ) : null}

      {effectiveWorkbenchTab === "map" ? mapWorkbench : null}
      {showQaTab && effectiveWorkbenchTab === "qa" ? qaWorkbench : null}
    </div>
  );
}
