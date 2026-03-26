import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeNavalOperations } from "./naval_operations_summary.js";

type NavalOperationsScreenProps = {
  snapshot: ViewSnapshot;
  onReturnHome: () => void;
};

function formatValue(value: number | null) {
  return value != null ? `${value.toFixed(0)}` : "Unavailable";
}

function formatDays(value: number | null) {
  return value != null ? `${value.toFixed(1)} days` : "Unavailable";
}

export default function NavalOperationsScreen({ snapshot, onReturnHome }: NavalOperationsScreenProps) {
  const summary = summarizeNavalOperations(snapshot);

  return (
    <section className="shell-navalops" aria-label="Naval operations screen">
      <header className="shell-navalops__hero shell-card">
        <div>
          <div className="shell-eyebrow">Naval Branch</div>
          <h2 className="shell-panel__title">Naval Operations Board</h2>
          <p className="shell-card__body">
            Fleet-command view built only from currently exposed naval formations, authored ports, and scenario naval-support windows. Ship classes, endurance, convoy state, and escort detail remain explicit placeholders where the shell path does not expose them.
          </p>
        </div>
        <div className="shell-navalops__hero-actions">
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </header>

      <div className="shell-navalops__grid">
        <section className="shell-navalops__panel shell-card shell-navalops__panel--overview">
          <div className="shell-card__title">Naval Overview</div>
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Fleets / Task Forces</span>
              <strong>{summary.overview.formationsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Ports</span>
              <strong>{summary.overview.portsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Support Windows</span>
              <strong>{summary.overview.supportWindowsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Readiness</span>
              <strong>{formatValue(summary.overview.readinessAverage)}</strong>
            </div>
          </div>
          <div className="shell-navalops__panel-note">{summary.overview.statusLine}</div>
        </section>

        <section className="shell-navalops__panel shell-card shell-navalops__panel--formations">
          <div className="shell-card__title">Fleets / Task Forces</div>
          {summary.formations.length ? (
            <div className="shell-navalops__list">
              {summary.formations.map((row) => (
                <div className="shell-navalops__entry" key={row.id}>
                  <div className="shell-navalops__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.endurance}</span>
                  </div>
                  <div className="shell-navalops__entry-body">
                    <span>Readiness {row.readiness ?? "Unavailable"}</span>
                    <span>Supply {row.supply != null ? `${row.supply.toFixed(1)} days` : "Unavailable"}</span>
                    <span>{row.mission}</span>
                  </div>
                  <div className="shell-navalops__entry-body">
                    <span>{row.composition}</span>
                    <span>{row.area}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-navalops__empty">No fleets or task forces are exposed in the active scenario snapshot.</div>
          )}
        </section>

        <section className="shell-navalops__panel shell-card">
          <div className="shell-card__title">Composition</div>
          <div className="shell-navalops__empty">{summary.composition.status}</div>
          <div className="shell-navalops__panel-note">{summary.composition.detail}</div>
        </section>

        <section className="shell-navalops__panel shell-card">
          <div className="shell-card__title">Fuel / Endurance</div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Endurance</span>
              <span className="shell-list__value">{summary.operations.endurance}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Mission Posture</span>
              <span className="shell-list__value">{summary.operations.posture}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Convoy / Escort</span>
              <span className="shell-list__value">{summary.operations.convoy}</span>
            </div>
          </div>
        </section>

        <section className="shell-navalops__panel shell-card">
          <div className="shell-card__title">Operating Context</div>
          <div className="shell-navalops__subhead">Ports</div>
          {summary.operatingContext.ports.length ? (
            <div className="shell-list">
              {summary.operatingContext.ports.map((row) => (
                <div className="shell-list__row" key={row.id}>
                  <span className="shell-list__title">{row.name}</span>
                  <span className="shell-list__value">{row.location}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-navalops__empty">No authored ports are exposed for the active scenario.</div>
          )}
          <div className="shell-navalops__subhead">Support Windows</div>
          {summary.operatingContext.windows.length ? (
            <div className="shell-list">
              {summary.operatingContext.windows.map((row) => (
                <div className="shell-list__row" key={row.id}>
                  <span className="shell-list__title">{row.label}</span>
                  <span className="shell-list__value">{row.side} • {row.timing}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-navalops__empty">No naval support windows are exposed for the active scenario.</div>
          )}
          <div className="shell-navalops__panel-note">{summary.operatingContext.detail}</div>
        </section>

        <section className="shell-navalops__panel shell-card">
          <div className="shell-card__title">Naval Concerns</div>
          <div className="shell-navalops__signal-list">
            {summary.concerns.map((item) => (
              <div className="shell-navalops__signal" key={item}>
                <strong>Fleet Staff Note</strong>
                <div>{item}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
