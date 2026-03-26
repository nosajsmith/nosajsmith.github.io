import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeHendersonPressureBoard } from "./henderson_pressure_board_summary.js";
import type { TrackedDemoOperation } from "./operations_planner_types";

type HendersonPressureBoardProps = {
  snapshot: ViewSnapshot;
  operations: TrackedDemoOperation[];
};

export default function HendersonPressureBoard({ snapshot, operations }: HendersonPressureBoardProps) {
  const summary = summarizeHendersonPressureBoard(snapshot, operations);
  const operationsOverview = summary.operationsOverview ?? {
    title: "Operations Picture",
    activeOperation: "No approved operation tracked",
    objectiveSituation: "No objective situation exposed on the current shell path.",
    localBattle: "Local battle unavailable outside the current perimeter slice.",
    immediateConcern: "No immediate local battle concern is exposed on the current shell path.",
    note: "No approved demo operations are currently tracked on the shell path.",
  };
  const engagementSummary = summary.engagementSummary ?? {
    summary: "No current engagement summary is exposed.",
    note: "Engagement summary is unavailable on the current shell path.",
    hotspotsSummary: "No named local engagement focus is exposed.",
    formationSummary: "No formation is directly tied to the exposed local fight.",
    hotspots: [],
    formations: [],
  };
  const responseReadiness = summary.responseReadiness ?? {
    summary: "No current response-readiness data.",
    note: "Response readiness is unavailable on the current shell path.",
    units: [],
  };
  const counterattackPlanning = summary.counterattackPlanning ?? {
    summary: "No current counterattack-planning data.",
    note: "Counterattack planning is unavailable on the current shell path.",
    bestCandidate: "No best-positioned local counterattack formation is exposed.",
    candidates: [],
  };
  const defensePreparation = summary.defensePreparation ?? {
    available: false,
    fortificationState: "Unavailable",
    obstacles: "Not exposed",
    engineer: "Not exposed",
    mostPrepared: "No prepared local objective exposed.",
    leastPrepared: "No lightly prepared local objective exposed.",
    note: "Local fortification, obstacle, and engineer-preparation state is unavailable on the current shell path.",
    areas: [],
  };
  const localSustainment = summary.localSustainment ?? {
    available: false,
    status: "Unavailable",
    note: "Local sustainment is unavailable on the current shell path.",
    resources: [
      { label: "Supply", value: "Not exposed" },
      { label: "Ammo", value: "Not exposed" },
      { label: "Fuel", value: "Not exposed" },
      { label: "Rations", value: "Not exposed" },
      { label: "Support", value: "Not exposed" },
    ],
    atRisk: [],
    concerns: ["No local sustainment warning is exposed on the current shell path."],
  };
  const airSupport = summary.airSupport ?? {
    available: false,
    availability: "Unavailable",
    note: "Local air-support context is unavailable on the current shell path.",
    sortiePosture: "Sortie posture unavailable",
    constraint: "Weather-linked local air-response limits are unavailable on the current shell path.",
    supportingFormation: "No supporting air formation exposed.",
  };
  const navalSupport = summary.navalSupport ?? {
    available: false,
    availability: "Unavailable",
    note: "Local naval-support context is unavailable on the current shell path.",
    supportPosture: "Support posture unavailable",
    constraint: "Offshore-support limits are unavailable on the current shell path.",
    supportingFormation: "No supporting naval formation exposed.",
  };

  return (
    <section className="shell-card shell-perimeter" aria-label="Operations board">
      <div className="shell-eyebrow">Operations</div>
      <h2 className="shell-card__title">{operationsOverview.title}</h2>
      <div className="shell-card__body">{operationsOverview.note}</div>
      <div className="shell-card__body">{summary.note}</div>

      <div className="shell-board__section">
        <div className="shell-board__title">Operations Overview</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Active Operation</span>
            <strong>{operationsOverview.activeOperation}</strong>
          </div>
          <div className="shell-list__row">
            <span>Objective Situation</span>
            <strong>{operationsOverview.objectiveSituation}</strong>
          </div>
          <div className="shell-list__row">
            <span>Local Battle</span>
            <strong>{operationsOverview.localBattle}</strong>
          </div>
          <div className="shell-list__row">
            <span>Immediate Concern</span>
            <strong>{operationsOverview.immediateConcern}</strong>
          </div>
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Local Battle Status</div>
        <div className="shell-board__stack">
          {summary.perimeterStatus.length ? (
            summary.perimeterStatus.map((row) => (
              <div className="shell-list__row" key={row.label}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </div>
            ))
          ) : (
            <div className="shell-empty">No local perimeter picture is exposed in the current snapshot.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Pressure Axes</div>
        <div className="shell-board__stack">
          {summary.pressureAxes.length ? (
            summary.pressureAxes.map((axis) => (
              <article className="shell-board__card" key={axis.label}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{axis.label}</div>
                    {axis.kindLabel ? <div className="shell-board__card-meta">{axis.kindLabel}</div> : null}
                  </div>
                  <div className="shell-board__card-state">{axis.status}</div>
                </div>
                <div className="shell-board__body">{axis.detail}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No named local pressure axis is exposed beyond the current perimeter status.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Engagement Summary</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Current Focus</span>
            <strong>{engagementSummary.hotspotsSummary}</strong>
          </div>
          <div className="shell-list__row">
            <span>Carrying The Fight</span>
            <strong>{engagementSummary.formationSummary}</strong>
          </div>
          <div className="shell-board__body">{engagementSummary.summary}</div>
          <div className="shell-board__body">{engagementSummary.note}</div>
          {engagementSummary.hotspots.length ? (
            engagementSummary.hotspots.map((area) => (
              <article className="shell-board__card" key={area.id}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{area.label}</div>
                    <div className="shell-board__card-meta">{area.kindLabel}</div>
                  </div>
                  <div className="shell-board__card-state">{area.status}</div>
                </div>
                <div className="shell-board__body">{area.detail}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No named local engagement area is exposed beyond the current perimeter status.</div>
          )}
          {engagementSummary.formations.length ? (
            engagementSummary.formations.map((unit) => (
              <article className="shell-board__card" key={unit.id}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{unit.name}</div>
                    <div className="shell-board__card-meta">{unit.location} • {unit.posture}</div>
                  </div>
                  <div className="shell-board__card-state">{unit.status}</div>
                </div>
                <div className="shell-board__body">{unit.detail}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No current formation is directly tied to the exposed local engagement areas.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Reserves / Response</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Readiness Summary</span>
            <strong>{responseReadiness.summary}</strong>
          </div>
          <div className="shell-board__body">{responseReadiness.note}</div>
          <div className="shell-board__body">{summary.reserveStatus}</div>
          {responseReadiness.units.length ? (
            responseReadiness.units.map((unit) => (
              <article className="shell-board__card" key={unit.id}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{unit.name}</div>
                    <div className="shell-board__card-meta">{unit.location} • {unit.posture}</div>
                  </div>
                  <div className="shell-board__card-state">{unit.readiness}</div>
                </div>
                <div className="shell-board__body">{unit.note}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No local response option is exposed on the current shell path.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Counterattack Planning</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Counterattack Summary</span>
            <strong>{counterattackPlanning.summary}</strong>
          </div>
          <div className="shell-board__body">{counterattackPlanning.note}</div>
          <div className="shell-board__body">{counterattackPlanning.bestCandidate}</div>
          {counterattackPlanning.candidates.length ? (
            counterattackPlanning.candidates.map((unit) => (
              <article className="shell-board__card" key={unit.id}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{unit.name}</div>
                    <div className="shell-board__card-meta">{unit.location} • {unit.posture}</div>
                  </div>
                  <div className="shell-board__card-state">{unit.status}</div>
                </div>
                <div className="shell-board__body">{unit.factors}</div>
                <div className="shell-board__body">{unit.note}</div>
                <div className="shell-board__body">{unit.locDetail}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No local counterattack candidate is exposed on the current shell path.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Defense Works</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Fortification State</span>
            <strong>{defensePreparation.fortificationState}</strong>
          </div>
          <div className="shell-list__row">
            <span>Obstacles</span>
            <strong>{defensePreparation.obstacles}</strong>
          </div>
          <div className="shell-list__row">
            <span>Engineer Prep</span>
            <strong>{defensePreparation.engineer}</strong>
          </div>
          <div className="shell-list__row">
            <span>Most Prepared</span>
            <strong>{defensePreparation.mostPrepared}</strong>
          </div>
          <div className="shell-list__row">
            <span>Least Prepared</span>
            <strong>{defensePreparation.leastPrepared}</strong>
          </div>
          <div className="shell-board__body">{defensePreparation.note}</div>
          {defensePreparation.areas.length ? (
            defensePreparation.areas.map((area) => (
              <article className="shell-board__card" key={area.id}>
                <div className="shell-board__card-head">
                  <div>
                    <div className="shell-board__card-title">{area.label}</div>
                    <div className="shell-board__card-meta">Local defense preparation</div>
                  </div>
                  <div className="shell-board__card-state">{area.state}</div>
                </div>
                <div className="shell-board__body">Fortification: {area.fortification}</div>
                <div className="shell-board__body">Obstacles: {area.obstacles}</div>
                <div className="shell-board__body">Engineer: {area.engineer}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No local defensive-preparation record is exposed on the current shell path.</div>
          )}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Local Sustainment</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Sustainment Status</span>
            <strong>{localSustainment.status}</strong>
          </div>
          {localSustainment.resources.map((resource) => (
            <div className="shell-list__row" key={resource.label}>
              <span>{resource.label}</span>
              <strong>{resource.value}</strong>
            </div>
          ))}
          <div className="shell-board__body">{localSustainment.note}</div>
          {localSustainment.atRisk.length ? (
            localSustainment.atRisk.map((unit) => (
              <article className="shell-board__card" key={unit.id}>
                <div className="shell-board__card-head">
                  <div className="shell-board__card-title">{unit.name}</div>
                  <div className="shell-board__card-state">At Risk</div>
                </div>
                <div className="shell-board__body">{unit.detail}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No specific local formation is currently flagged as sustainment-critical on the exposed shell path.</div>
          )}
          {localSustainment.concerns.map((item, index) => (
            <div className="shell-board__body" key={`sustainment-concern-${index}`}>{item}</div>
          ))}
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Local Air Support</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Air Support</span>
            <strong>{airSupport.availability}</strong>
          </div>
          <div className="shell-list__row">
            <span>Sortie Posture</span>
            <strong>{airSupport.sortiePosture}</strong>
          </div>
          <div className="shell-list__row">
            <span>Supporting Formation</span>
            <strong>{airSupport.supportingFormation}</strong>
          </div>
          <div className="shell-board__body">{airSupport.note}</div>
          <div className="shell-board__body">{airSupport.constraint}</div>
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Local Naval Support</div>
        <div className="shell-board__stack">
          <div className="shell-list__row">
            <span>Naval Support</span>
            <strong>{navalSupport.availability}</strong>
          </div>
          <div className="shell-list__row">
            <span>Support Posture</span>
            <strong>{navalSupport.supportPosture}</strong>
          </div>
          <div className="shell-list__row">
            <span>Supporting Formation</span>
            <strong>{navalSupport.supportingFormation}</strong>
          </div>
          <div className="shell-board__body">{navalSupport.note}</div>
          <div className="shell-board__body">{navalSupport.constraint}</div>
        </div>
      </div>

      <div className="shell-board__section">
        <div className="shell-board__title">Recent Contacts</div>
        <div className="shell-board__stack">
          {summary.recentContacts.length ? (
            summary.recentContacts.map((report) => (
              <article className="shell-board__report" key={report.id}>
                <div className="shell-board__card-head">
                  <div className="shell-board__card-title">{report.title}</div>
                  <div className={`shell-board__severity is-${report.severity.toLowerCase()}`}>{report.severity}</div>
                </div>
                <div className="shell-board__body">{report.summary}</div>
              </article>
            ))
          ) : (
            <div className="shell-empty">No local contact report is exposed in the current communications feed.</div>
          )}
        </div>
      </div>
    </section>
  );
}
