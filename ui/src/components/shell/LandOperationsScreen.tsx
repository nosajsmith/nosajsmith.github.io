import type { ViewSnapshot } from "../../types/viewSnapshot";
import type { TrackedDemoOperation } from "./operations_planner_types";
import { summarizeLandOperations } from "./land_operations_summary.js";

type LandOperationsScreenProps = {
  snapshot: ViewSnapshot;
  operations: TrackedDemoOperation[];
  onReturnHome: () => void;
};

export default function LandOperationsScreen({ snapshot, operations, onReturnHome }: LandOperationsScreenProps) {
  const summary = summarizeLandOperations(snapshot, operations);

  return (
    <section className="shell-landops" aria-label="Land operations screen">
      <header className="shell-landops__hero shell-card">
        <div>
          <div className="shell-eyebrow">Land Branch</div>
          <h2 className="shell-panel__title">Land Operations Command Board</h2>
          <p className="shell-card__body">
            Ground-force command view built only from exposed command links, attached support, LOC state, orders, and tracked operation participation already on the shell path. No deeper OOB hierarchy or reserve logic is inferred where the data is limited.
          </p>
        </div>
        <div className="shell-landops__hero-actions">
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </header>

      <div className="shell-landops__grid">
        <section className="shell-landops__panel shell-card shell-landops__panel--overview">
          <div className="shell-card__title">Land Forces Overview</div>
          <div className="shell-briefing__grid">
            {summary.overview.metrics.map((metric) => (
              <div className="shell-stat" key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <div className="shell-landops__panel-note">{summary.note}</div>
          <div className="shell-landops__panel-note">OOB: {summary.overview.oob.headline}</div>
          <div className="shell-landops__panel-note">Support: {summary.overview.support.headline}</div>
          <div className="shell-landops__panel-note">LOC: {summary.overview.loc.headline}</div>
          <div className="shell-landops__panel-note">Organization: {summary.overview.organization.headline}</div>
        </section>

        <section className="shell-landops__panel shell-card shell-landops__panel--oob">
          <div className="shell-card__title">OOB / Chain Of Command</div>
          <div className="shell-landops__panel-note">{summary.oob.headline}</div>
          {summary.oob.groups.length ? (
            <div className="shell-landops__list">
              {summary.oob.groups.map((group) => (
                <div className="shell-landops__entry" key={group.id}>
                  <div className="shell-landops__entry-head">
                    <strong>{group.label}</strong>
                    <span>{group.formations.length} formations</span>
                  </div>
                  <div className="shell-landops__entry-meta">{group.note}</div>
                  {group.formations.map((formation) => (
                    <div className="shell-landops__entry-body" key={formation.id}>
                      <span>{formation.name}</span>
                      <span>{formation.posture}</span>
                      <span>{formation.readiness}</span>
                      <span>{formation.loc}</span>
                      <span>{formation.support}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-landops__empty">No visible command-organization picture is exposed on the current shell path.</div>
          )}
        </section>

        <section className="shell-landops__panel shell-card shell-landops__panel--support">
          <div className="shell-card__title">Support Assignments</div>
          <div className="shell-landops__panel-note">{summary.supportAssignments.headline}</div>
          {summary.supportAssignments.rows.length ? (
            <div className="shell-landops__list">
              {summary.supportAssignments.rows.map((row) => (
                <div className="shell-landops__entry" key={row.id}>
                  <div className="shell-landops__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.assignment}</span>
                  </div>
                  <div className="shell-landops__entry-meta">{row.note}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-landops__empty">No attached or detached support record is exposed on the current shell path.</div>
          )}
        </section>

        <section className="shell-landops__panel shell-card shell-landops__panel--loc">
          <div className="shell-card__title">LOC Alerts</div>
          <div className="shell-landops__panel-note">{summary.locAlerts.headline}</div>
          {summary.locAlerts.rows.length ? (
            <div className="shell-landops__signal-list">
              {summary.locAlerts.rows.map((row) => (
                <div className="shell-landops__signal" key={row.id}>
                  <strong>{row.name}</strong>
                  <div>{row.status}</div>
                  <div>{row.detail}</div>
                  <div>{row.note}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-landops__empty">No threatened or broken LOC alert is exposed in the current view.</div>
          )}
        </section>

        <section className="shell-landops__panel shell-card shell-landops__panel--readiness">
          <div className="shell-card__title">Readiness / Posture Rollup</div>
          <div className="shell-landops__panel-note">{summary.readinessPosture.headline}</div>
          {summary.readinessPosture.rows.length ? (
            <div className="shell-landops__list">
              {summary.readinessPosture.rows.map((row) => (
                <div className="shell-landops__entry" key={row.id}>
                  <div className="shell-landops__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.posture}</span>
                  </div>
                  <div className="shell-landops__entry-body">
                    <span>{row.condition}</span>
                    <span>{row.sustainment}</span>
                  </div>
                  <div className="shell-landops__entry-meta">{row.order}</div>
                  <div className="shell-landops__entry-meta">{row.note}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-landops__empty">No readiness or posture rollup is exposed on the current shell path.</div>
          )}
        </section>

        <section className="shell-landops__panel shell-card shell-landops__panel--operations">
          <div className="shell-card__title">Current Operation Participation</div>
          <div className="shell-landops__panel-note">{summary.operations.headline}</div>
          {summary.operations.rows.length ? (
            <div className="shell-landops__list">
              {summary.operations.rows.map((row) => (
                <div className="shell-landops__entry" key={row.id}>
                  <div className="shell-landops__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.role}</span>
                  </div>
                  <div className="shell-landops__entry-body">
                    <span>{row.operation}</span>
                    <span>{row.status}</span>
                    <span>{row.objective}</span>
                  </div>
                  <div className="shell-landops__entry-meta">{row.support}</div>
                  <div className="shell-landops__entry-meta">{row.note}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-landops__empty">No visible formation is currently tied to a tracked operation on the shell path.</div>
          )}
        </section>
      </div>
    </section>
  );
}
