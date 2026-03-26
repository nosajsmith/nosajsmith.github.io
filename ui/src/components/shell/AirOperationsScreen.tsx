import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeAirOperations } from "./air_operations_summary.js";

type AirOperationsScreenProps = {
  snapshot: ViewSnapshot;
  onReturnHome: () => void;
};

function formatValue(value: number | null, suffix = "") {
  return value != null ? `${value.toFixed(0)}${suffix}` : "Unavailable";
}

function formatDays(value: number | null) {
  return value != null ? `${value.toFixed(1)} days` : "Unavailable";
}

export default function AirOperationsScreen({ snapshot, onReturnHome }: AirOperationsScreenProps) {
  const summary = summarizeAirOperations(snapshot);

  return (
    <section className="shell-airops" aria-label="Air operations screen">
      <header className="shell-airops__hero shell-card">
        <div>
          <div className="shell-eyebrow">Air Branch</div>
          <h2 className="shell-panel__title">Air Operations Staff Board</h2>
          <p className="shell-card__body">
            Air-command view built only from currently exposed air formations, weather context, and authored airfields. Sorties, serviceability, maintenance, and aircraft inventories remain explicit placeholders where the shell path does not expose them.
          </p>
        </div>
        <div className="shell-airops__hero-actions">
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </header>

      <div className="shell-airops__grid">
        <section className="shell-airops__panel shell-card shell-airops__panel--overview">
          <div className="shell-card__title">Air Overview</div>
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Air Formations</span>
              <strong>{summary.overview.formationsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Airfields</span>
              <strong>{summary.overview.airfieldsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Readiness</span>
              <strong>{formatValue(summary.overview.readinessAverage)}</strong>
            </div>
            <div className="shell-stat">
              <span>Sustainment</span>
              <strong>{formatDays(summary.overview.sustainmentAverageDays)}</strong>
            </div>
          </div>
          <div className="shell-airops__panel-note">{summary.overview.statusLine}</div>
        </section>

        <section className="shell-airops__panel shell-card shell-airops__panel--formations">
          <div className="shell-card__title">Formations</div>
          {summary.formations.length ? (
            <div className="shell-airops__list">
              {summary.formations.map((row) => (
                <div className="shell-airops__entry" key={row.id}>
                  <div className="shell-airops__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.sorties}</span>
                  </div>
                  <div className="shell-airops__entry-body">
                    <span>Readiness {row.readiness ?? "Unavailable"}</span>
                    <span>Supply {row.supply != null ? `${row.supply.toFixed(1)} days` : "Unavailable"}</span>
                    <span>{row.role}</span>
                  </div>
                  <div className="shell-airops__entry-body">
                    <span>{row.aircraft}</span>
                    <span>{row.base}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-airops__empty">No air formations are exposed in the active scenario snapshot.</div>
          )}
        </section>

        <section className="shell-airops__panel shell-card">
          <div className="shell-card__title">Aircraft / Strength</div>
          <div className="shell-airops__empty">{summary.aircraft.status}</div>
          <div className="shell-airops__panel-note">{summary.aircraft.detail}</div>
        </section>

        <section className="shell-airops__panel shell-card">
          <div className="shell-card__title">Sorties / Tempo</div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Sorties</span>
              <span className="shell-list__value">{summary.operations.sorties}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Operational Tempo</span>
              <span className="shell-list__value">{summary.operations.tempo}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Aviation Support</span>
              <span className="shell-list__value">{summary.operations.support}</span>
            </div>
          </div>
        </section>

        <section className="shell-airops__panel shell-card">
          <div className="shell-card__title">Basing / Airfields</div>
          {summary.basing.airfields.length ? (
            <div className="shell-list">
              {summary.basing.airfields.map((row) => (
                <div className="shell-list__row" key={row.id}>
                  <span className="shell-list__title">{row.name}</span>
                  <span className="shell-list__value">{row.location}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-airops__empty">No authored airfields are exposed for the active scenario.</div>
          )}
          <div className="shell-airops__panel-note">{summary.basing.detail}</div>
        </section>

        <section className="shell-airops__panel shell-card">
          <div className="shell-card__title">Air Concerns</div>
          <div className="shell-airops__signal-list">
            {summary.concerns.map((item) => (
              <div className="shell-airops__signal" key={item}>
                <strong>Air Staff Note</strong>
                <div>{item}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
