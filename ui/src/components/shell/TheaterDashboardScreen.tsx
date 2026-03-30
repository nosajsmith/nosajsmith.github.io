import { useState } from "react";
import type { ViewSnapshot } from "../../types/viewSnapshot";
import { inferScenarioPresentation } from "../../lib/view_snapshot.js";
import { buildMapScene } from "./map_scene.js";
import type { TrackedDemoOperation } from "./operations_planner_types";
import { summarizeTheaterDashboard } from "./theater_dashboard_summary.js";

type DashboardBranchTarget = "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Reinforcements";

type TheaterDashboardScreenProps = {
  snapshot: ViewSnapshot;
  previousSnapshot: ViewSnapshot | null;
  operations: TrackedDemoOperation[];
  onInspectUnit: (unitId: string) => void;
  onOpenBranch: (branch: DashboardBranchTarget) => void;
  onOpenCommunications: (messageId?: string | null) => void;
  onReturnToTheatre: () => void;
};

type PanelHeadingProps = {
  title: string;
  actionLabel?: string;
  onAction?: (() => void) | null;
};

function PanelHeading({ title, actionLabel, onAction = null }: PanelHeadingProps) {
  return (
    <div className="shell-theaterdash__panel-head">
      <div className="shell-card__title">{title}</div>
      {actionLabel && onAction ? (
        <button type="button" className="shell-theaterdash__panel-action" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

export default function TheaterDashboardScreen({
  snapshot,
  previousSnapshot,
  operations,
  onInspectUnit,
  onOpenBranch,
  onOpenCommunications,
  onReturnToTheatre,
}: TheaterDashboardScreenProps) {
  const [comparisonMode, setComparisonMode] = useState(false);
  const presentation = inferScenarioPresentation(snapshot);
  const summary = summarizeTheaterDashboard(snapshot, previousSnapshot, operations);
  const scene = buildMapScene(snapshot, { width: 520, height: 300, inset: 32 });
  const turnBrief = summary.turnBrief;
  const comparison = summary.comparison;
  const showComparison = comparisonMode && comparison.available;
  const communicationsIntel = summary.communicationsIntel;
  const reinforcements = summary.reinforcementsWithdrawals;
  const forceQuality = summary.forceQuality;
  const localBattle = summary.localBattle;
  const supportPicture = summary.supportPicture;
  const campaignPicture = summary.campaignPicture;
  const landForces = summary.landForces;
  const operationsSummary = summary.operations;
  const perimeterStatus = localBattle.perimeterStatus.find((item) => item.label === "Overall Status")?.value ?? "Unavailable";
  const immediateConcern = localBattle.perimeterStatus.find((item) => item.label === "Immediate Concern")?.value ?? "No immediate concern exposed.";
  const staffConcern = localBattle.perimeterStatus.find((item) => item.label === "Staff Concern")?.value ?? localBattle.note;
  const leadAxis = localBattle.pressureAxes[0] ?? null;
  const latestContact = localBattle.recentContacts[0] ?? null;
  const leadResponse = localBattle.counterattackPlanning.candidates[0] ?? null;
  const supportSummary = `${localBattle.localSustainment.status} sustainment • ${localBattle.airSupport.availability} air support • ${localBattle.navalSupport.availability} naval support`;

  return (
    <section className="shell-theaterdash" aria-label="Theater Command Dashboard">
      <header className="shell-theaterdash__hero shell-card">
        <div>
          <div className="shell-eyebrow">{presentation.theaterLabel}</div>
          <h2 className="shell-panel__title">{presentation.scenarioLabel} Briefing Board</h2>
          <p className="shell-card__body">
            Compact {presentation.frontLabel.toLowerCase()} overview for command staff on the current {presentation.scenarioLabel.toLowerCase()} shell path. Unavailable branches remain explicitly marked until deeper scenario detail is exposed.
          </p>
        </div>
        <div className="shell-theaterdash__hero-side">
          <div className="shell-theaterdash__hero-grid">
            <div className="shell-stat">
              <span>Campaign</span>
              <strong>{summary.campaign.status}</strong>
            </div>
            <div className="shell-stat">
              <span>Turn</span>
              <strong>{summary.campaign.turn ?? "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Time Remaining</span>
              <strong>{summary.campaign.timeRemaining != null ? `${summary.campaign.timeRemaining}h` : "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Staff Load</span>
              <strong>{summary.staff.load ?? "Unknown"}</strong>
            </div>
          </div>
          <div className="shell-theaterdash__hero-actions">
            <button
              type="button"
              className={"shell-button shell-button--secondary" + (comparison.available ? "" : " is-unavailable")}
              onClick={() => setComparisonMode((current) => !current)}
              disabled={!comparison.available}
            >
              {showComparison ? "Hide Comparison" : "Compare To Previous"}
            </button>
            <div className="shell-theaterdash__panel-note">
              {comparison.available ? `${comparison.sourceLabel}. ${comparison.note}` : comparison.note}
            </div>
          </div>
          {showComparison ? (
            <div className="shell-theaterdash__signal">
              <strong>Previous Snapshot Comparison</strong>
              <div>{comparison.sourceLabel}</div>
              <div className="shell-theaterdash__compare-list">
                {comparison.highlights.map((item) => (
                  <div className="shell-theaterdash__panel-note" key={item}>{item}</div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </header>

      <div className="shell-theaterdash__tier shell-theaterdash__tier--primary">
        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--campaign">
          <PanelHeading title="Campaign" />
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Status</span>
              <strong>{summary.campaign.status}</strong>
            </div>
            <div className="shell-stat">
              <span>Turn</span>
              <strong>{summary.campaign.turn ?? "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Time Remaining</span>
              <strong>{summary.campaign.timeRemaining != null ? `${summary.campaign.timeRemaining}h` : "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Win Target</span>
              <strong>{summary.campaign.winTarget ?? "Unknown"}</strong>
            </div>
          </div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Objective Progress</span>
              <span className="shell-list__value">{campaignPicture.objectiveProgress}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Key Objective</span>
              <span className="shell-list__value">{campaignPicture.keyObjective}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Score</span>
              <span className="shell-list__value">{campaignPicture.scoreSummary}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Pressure</span>
              <span className="shell-list__value">{campaignPicture.pressureSummary}</span>
            </div>
          </div>
          <div className="shell-theaterdash__panel-note">{campaignPicture.note}</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--theatre">
          <PanelHeading title={presentation.localBattleTitle} actionLabel="Open Theatre" onAction={onReturnToTheatre} />
          {showComparison ? (
            <div className={"shell-theaterdash__delta shell-theaterdash__delta--" + comparison.localBattle.tone}>
              {comparison.localBattle.summary}
            </div>
          ) : null}
          <div className="shell-theaterdash__theatre-grid">
            <div className="shell-theaterdash__map">
              <svg viewBox={`0 0 ${scene.width} ${scene.height}`} role="img" aria-label={`${presentation.frontLabel} context map`}>
                <rect x="0" y="0" width={scene.width} height={scene.height} className="shell-theaterdash__map-field" />
                {scene.objectives.map((objective) => (
                  <g key={objective.id} transform={`translate(${objective.displayAnchor.x}, ${objective.displayAnchor.y})`}>
                    <path d="M0 -7 L7 0 L0 7 L-7 0 Z" className={`shell-theaterdash__objective is-${objective.visualState}`} />
                  </g>
                ))}
                {scene.units.map((unit) => (
                  <rect
                    key={unit.id}
                    x={unit.displayAnchor.x - 9}
                    y={unit.displayAnchor.y - 6}
                    width="18"
                    height="12"
                    rx="2"
                    className={`shell-theaterdash__unit is-${unit.visualSlot}`}
                  />
                ))}
              </svg>
            </div>
            <div className="shell-theaterdash__theatre-copy">
              {localBattle.available ? (
                <>
                  <div className="shell-theaterdash__signal">
                    <strong>{immediateConcern}</strong>
                    <div>{staffConcern}</div>
                  </div>
                  <div className="shell-list">
                    <div className="shell-list__row">
                      <span className="shell-list__title">Perimeter Status</span>
                      <span className="shell-list__value">{perimeterStatus}</span>
                    </div>
                    <div className="shell-list__row">
                      <span className="shell-list__title">Active Pressure</span>
                      <span className="shell-list__value">{leadAxis ? `${leadAxis.label} (${leadAxis.status})` : "No active local pressure axis exposed."}</span>
                    </div>
                    <div className="shell-list__row">
                      <span className="shell-list__title">Latest Contact</span>
                      <span className="shell-list__value">{latestContact ? latestContact.title : "No recent local contact report."}</span>
                    </div>
                    <div className="shell-list__row">
                      <span className="shell-list__title">Reserve / Response</span>
                      <span className="shell-list__value">
                        {leadResponse ? `${leadResponse.name} (${leadResponse.status})` : localBattle.responseReadiness.summary}
                      </span>
                    </div>
                    <div className="shell-list__row">
                      <span className="shell-list__title">Defense Works</span>
                      <span className="shell-list__value">
                        {localBattle.defensePreparation.available ? localBattle.defensePreparation.mostPrepared : localBattle.defensePreparation.fortificationState}
                      </span>
                    </div>
                  </div>
                  <div className="shell-theaterdash__panel-note">{supportSummary}</div>
                </>
              ) : (
                <>
                  <div className="shell-empty">{localBattle.note}</div>
                  <div className="shell-theaterdash__panel-note">{supportSummary}</div>
                </>
              )}
            </div>
          </div>
          <div className="shell-theaterdash__panel-note">{summary.context.unitsTracked} units and {summary.context.objectivesTracked} objectives in the current picture.</div>
        </section>
      </div>

      <div className="shell-theaterdash__tier shell-theaterdash__tier--secondary">
        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--operations">
          <PanelHeading title={presentation.operationsTitle} actionLabel="Open Theatre" onAction={onReturnToTheatre} />
          {operationsSummary.available ? (
            <>
              <div className="shell-theaterdash__signal">
                <strong>{operationsSummary.lead?.name ?? "Lead operation unavailable"}</strong>
                <div>{operationsSummary.lead?.status ?? "Status unavailable"} • {operationsSummary.lead?.objective ?? "Objective unavailable"}</div>
                <div className="shell-theaterdash__panel-note">{operationsSummary.lead?.statusDetail ?? operationsSummary.note}</div>
              </div>
              <div className="shell-theaterdash__support-list">
                {operationsSummary.rows.map((operation) => (
                  <button
                    type="button"
                    className="shell-theaterdash__timeline-entry shell-theaterdash__timeline-entry--link"
                    key={operation.id}
                    onClick={onReturnToTheatre}
                  >
                    <div className="shell-theaterdash__timeline-head">
                      <strong>{operation.name}</strong>
                      <span>{operation.status}</span>
                    </div>
                    <div className="shell-theaterdash__panel-note">{operation.objective} • {operation.leadHq}</div>
                    <div className="shell-theaterdash__panel-note">{operation.prepStatus} • {operation.objectiveState}</div>
                    <div className="shell-theaterdash__panel-note">{operation.participatingForces.join(" • ")}</div>
                    <div className="shell-theaterdash__panel-note">{operation.supportAssigned.join(" • ")}</div>
                  </button>
                ))}
              </div>
              <div className="shell-theaterdash__panel-note">{operationsSummary.note}</div>
            </>
          ) : (
            <div className="shell-empty">{operationsSummary.note}</div>
          )}
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--landforces">
          <PanelHeading title="Land Forces" actionLabel="Open Land Ops" onAction={() => onOpenBranch("Land")} />
          <div className="shell-briefing__grid">
            {landForces.metrics.map((metric) => (
              <div className="shell-stat" key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <div className="shell-theaterdash__support-list">
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>OOB</span>
                <strong>{landForces.oob.headline}</strong>
              </div>
              {landForces.oob.rows.map((row) => (
                <div className="shell-theaterdash__panel-note" key={`oob-${row.label}`}>
                  {row.label}: {row.value}{row.note ? ` • ${row.note}` : ""}
                </div>
              ))}
            </div>
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>Support Assignments</span>
                <strong>{landForces.support.headline}</strong>
              </div>
              {landForces.support.rows.map((row) => (
                <div className="shell-theaterdash__panel-note" key={`support-${row.label}`}>
                  {row.label}: {row.value}{row.note ? ` • ${row.note}` : ""}
                </div>
              ))}
            </div>
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>LOC Alerts</span>
                <strong>{landForces.loc.headline}</strong>
              </div>
              {landForces.loc.rows.map((row) => (
                <div className="shell-theaterdash__panel-note" key={`loc-${row.label}`}>
                  {row.label}: {row.value}{row.note ? ` • ${row.note}` : ""}
                </div>
              ))}
            </div>
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>Force Organization</span>
                <strong>{landForces.organization.headline}</strong>
              </div>
              {landForces.organization.rows.map((row) => (
                <div className="shell-theaterdash__panel-note" key={`org-${row.label}`}>
                  {row.label}: {row.value}{row.note ? ` • ${row.note}` : ""}
                </div>
              ))}
            </div>
          </div>
          <div className="shell-theaterdash__panel-note">{landForces.note}</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--brief">
          <PanelHeading title="Turn Brief & Action Items" />
          <div className="shell-theaterdash__signal">
            <strong>{turnBrief.priorityFocus}</strong>
            <div>{turnBrief.note}</div>
          </div>
          <div className="shell-theaterdash__brief-lines">
            {turnBrief.lines.map((line) => (
              <div className="shell-theaterdash__panel-note" key={line}>{line}</div>
            ))}
          </div>
          {turnBrief.actionItems.length ? (
            <ul className="shell-theaterdash__brief-list">
              {turnBrief.actionItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <div className="shell-empty">No current watch items are exposed on the shell path.</div>
          )}
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--forcematrix">
          <PanelHeading title="Force Quality Matrix" />
          {forceQuality.available ? (
            <>
              <div className="shell-theaterdash__panel-note">
                {forceQuality.rowCount} visible formations compared. {forceQuality.note} Select a row to open the Inspector.
                {showComparison ? ` ${comparison.forceQuality.note}` : ""}
              </div>
              <div className="shell-theaterdash__matrix-wrap">
                <table className="shell-theaterdash__matrix">
                  <thead>
                    <tr>
                      <th scope="col">Formation</th>
                      <th scope="col">Posture / Order</th>
                      <th scope="col">Condition</th>
                      <th scope="col">Supply / LOC</th>
                      <th scope="col">Reconstitution</th>
                      <th scope="col">Veteran Core</th>
                      <th scope="col">Notes</th>
                      {showComparison ? <th scope="col">Change</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {forceQuality.rows.map((row) => (
                      <tr
                        key={row.id}
                        className="shell-theaterdash__matrix-row"
                        role="button"
                        tabIndex={0}
                        aria-label={`Open ${row.name} in Inspector`}
                        onClick={() => onInspectUnit(row.id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onInspectUnit(row.id);
                          }
                        }}
                      >
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.name}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.posture}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.order}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.orderStatus}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.conditionPrimary}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.conditionSecondary}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.supplyPrimary}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.supplySecondary}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.reconstitutionPrimary}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.reconstitutionSecondary}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-main">{row.veteranPrimary}</span>
                          <span className="shell-theaterdash__matrix-sub">{row.veteranSecondary}</span>
                        </td>
                        <td>
                          <span className="shell-theaterdash__matrix-note">{row.note}</span>
                        </td>
                        {showComparison ? (
                          <td>
                            <span className={"shell-theaterdash__delta shell-theaterdash__delta--" + (comparison.forceQuality.rows[row.id]?.tone ?? "flat")}>
                              {comparison.forceQuality.rows[row.id]?.summary ?? "No previous snapshot row captured in this session."}
                            </span>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="shell-empty">{forceQuality.note}</div>
          )}
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--supportpicture">
          <PanelHeading title="Support Picture" actionLabel="Open Logistics" onAction={() => onOpenBranch("Logistics")} />
          {showComparison ? (
            <div className="shell-theaterdash__panel-note">{comparison.supportPicture.note}</div>
          ) : null}
          <div className="shell-theaterdash__signal">
            <strong>Immediate Support Constraint</strong>
            <div>{supportPicture.immediateConstraint}</div>
          </div>
          <div className="shell-theaterdash__support-list">
            {supportPicture.rows.map((row) => (
              <div className="shell-theaterdash__support-row" key={row.id}>
                <div className="shell-theaterdash__support-head">
                  <span>{row.label}</span>
                  <strong>{row.status}</strong>
                </div>
                <div className="shell-theaterdash__panel-note">{row.detail}</div>
                <div className="shell-theaterdash__panel-note">{row.note}</div>
                {showComparison ? (
                  <div className={"shell-theaterdash__delta shell-theaterdash__delta--" + (comparison.supportPicture.rows[row.id]?.tone ?? "flat")}>
                    {comparison.supportPicture.rows[row.id]?.summary ?? "No previous support row captured in this session."}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
          <div className="shell-theaterdash__panel-note">{supportPicture.note}</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--air">
          <PanelHeading title="Air Operations" actionLabel="Open Air" onAction={() => onOpenBranch("Air")} />
          <div className="shell-empty">Air branch data is not exposed on the current shell path yet.</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--naval">
          <PanelHeading title="Naval Disposition" actionLabel="Open Naval" onAction={() => onOpenBranch("Naval")} />
          <div className="shell-empty">Naval disposition detail is not exposed on the current shell path yet.</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--logistics">
          <PanelHeading title="Logistics" actionLabel="Open Logistics" onAction={() => onOpenBranch("Logistics")} />
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Supply Outlook</span>
              <strong>{summary.logistics.supplyAverage != null ? `${summary.logistics.supplyAverage.toFixed(1)}d` : "Limited"}</strong>
            </div>
            <div className="shell-stat">
              <span>Staff Load</span>
              <strong>{summary.logistics.load ?? "Unknown"}</strong>
            </div>
          </div>
          <div className="shell-theaterdash__panel-note">{summary.logistics.supportText}</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--intel">
          <PanelHeading title="Communications & Intelligence" actionLabel="Open Intelligence" onAction={() => onOpenBranch("Intelligence")} />
          <div className="shell-theaterdash__signal">
            <strong>{communicationsIntel.latestDispatch.title}</strong>
            <div>{communicationsIntel.latestDispatch.summary}</div>
            <div className="shell-theaterdash__panel-note">
              {communicationsIntel.latestDispatch.senderLabel
                ? `${communicationsIntel.latestDispatch.senderLabel} • ${communicationsIntel.latestDispatch.timeLabel}`
                : communicationsIntel.latestDispatch.timeLabel}
            </div>
            <button
              type="button"
              className="shell-theaterdash__signal-action"
              onClick={() => onOpenCommunications(communicationsIntel.latestDispatch.id)}
            >
              Open Communications Center
            </button>
          </div>
          {showComparison ? (
            <div className={"shell-theaterdash__delta shell-theaterdash__delta--" + comparison.communicationsIntel.tone}>
              {comparison.communicationsIntel.summary}
            </div>
          ) : null}
          {communicationsIntel.recentItems.length ? (
            <div className="shell-theaterdash__timeline">
              {communicationsIntel.recentItems.map((entry) => (
                <button
                  type="button"
                  className="shell-theaterdash__timeline-entry shell-theaterdash__timeline-entry--link"
                  key={entry.id}
                  onClick={() => onOpenCommunications(entry.id)}
                >
                  <div className="shell-theaterdash__timeline-head">
                    <strong>{entry.title}</strong>
                    <span>{entry.timeLabel}</span>
                  </div>
                  {entry.senderLabel ? <div className="shell-theaterdash__panel-note">{entry.senderLabel}</div> : null}
                  <div className="shell-theaterdash__panel-note">{entry.summary}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="shell-empty">No recent reporting items are exposed on the current shell path.</div>
          )}
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Local Contact</span>
              <span className="shell-list__value">{communicationsIntel.localContact}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Reporting Picture</span>
              <span className="shell-list__value">{communicationsIntel.reportingPicture}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Recon / Reporting</span>
              <span className="shell-list__value">{communicationsIntel.reconLimitation}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Key Concern</span>
              <span className="shell-list__value">{communicationsIntel.keyConcern}</span>
            </div>
          </div>
          <div className="shell-theaterdash__panel-note">{communicationsIntel.reportingLimitation}</div>
          <div className="shell-theaterdash__panel-note">{communicationsIntel.note}</div>
        </section>

        <section className="shell-theaterdash__panel shell-card shell-theaterdash__panel--reinforcements">
          <PanelHeading
            title="Reinforcements & Withdrawals"
            actionLabel="Open Reinforcements"
            onAction={() => onOpenBranch("Reinforcements")}
          />
          {showComparison ? (
            <div className={"shell-theaterdash__delta shell-theaterdash__delta--" + comparison.reinforcementsWithdrawals.tone}>
              {comparison.reinforcementsWithdrawals.summary}
            </div>
          ) : null}
          <div className="shell-theaterdash__signal">
            <strong>{reinforcements.nextChange.headline}</strong>
            <div>{reinforcements.nextChange.detail}</div>
            <div className="shell-theaterdash__panel-note">{reinforcements.nextChange.context}</div>
          </div>
          <div className="shell-theaterdash__support-list">
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>Arriving Soon</span>
                <strong>{reinforcements.incoming[0]?.name ?? "No arrival row exposed"}</strong>
              </div>
              <div className="shell-theaterdash__panel-note">
                {reinforcements.incoming[0]?.timing ?? reinforcements.placeholders.incoming}
              </div>
              <div className="shell-theaterdash__panel-note">
                {reinforcements.incoming[0]
                  ? `${reinforcements.incoming[0].destination} • ${reinforcements.incoming[0].command}`
                  : "Destination and command context unavailable."}
              </div>
            </div>
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>Withdrawing Soon</span>
                <strong>{reinforcements.outgoing[0]?.name ?? "No withdrawal row exposed"}</strong>
              </div>
              <div className="shell-theaterdash__panel-note">
                {reinforcements.outgoing[0]?.timing ?? reinforcements.placeholders.outgoing}
              </div>
              <div className="shell-theaterdash__panel-note">
                {reinforcements.outgoing[0]
                  ? `${reinforcements.outgoing[0].destination} • ${reinforcements.outgoing[0].command}`
                  : "Destination and command context unavailable."}
              </div>
            </div>
            <div className="shell-theaterdash__support-row">
              <div className="shell-theaterdash__support-head">
                <span>Force Change Warning</span>
                <strong>{reinforcements.currentDay != null ? `Current day ${reinforcements.currentDay}` : "Current day unavailable"}</strong>
              </div>
              <div className="shell-theaterdash__panel-note">{reinforcements.planningWarning}</div>
              <div className="shell-theaterdash__panel-note">{reinforcements.note}</div>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
