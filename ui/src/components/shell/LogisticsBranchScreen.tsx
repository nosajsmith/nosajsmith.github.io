import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeLogisticsBranch } from "./logistics_branch_summary.js";

type LogisticsBranchScreenProps = {
  snapshot: ViewSnapshot;
  onReturnHome: () => void;
  onOpenReinforcementsBoard: () => void;
};

function formatPercent(value: number | null) {
  return value != null ? `${value.toFixed(0)}%` : "Unavailable";
}

function formatDays(value: number | null) {
  return value != null ? `${value.toFixed(1)} days` : "Unavailable";
}

export default function LogisticsBranchScreen({ snapshot, onReturnHome, onOpenReinforcementsBoard }: LogisticsBranchScreenProps) {
  const summary = summarizeLogisticsBranch(snapshot);

  return (
    <section className="shell-logistics" aria-label="Logistics branch screen">
      <header className="shell-logistics__hero shell-card">
        <div>
          <div className="shell-eyebrow">Logistics Branch</div>
          <h2 className="shell-panel__title">Sustainment Staff Board</h2>
          <p className="shell-card__body">
            Staff-level sustainment overview built from currently exposed unit logistics records. Throughput, replacement, and depot systems remain explicitly marked where the shell path does not expose them.
          </p>
        </div>
        <div className="shell-logistics__hero-actions">
          <button type="button" className="shell-button" onClick={onOpenReinforcementsBoard}>
            Reinforcements Board
          </button>
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </header>

      <div className="shell-logistics__grid">
        <section className="shell-logistics__panel shell-card shell-logistics__panel--overview">
          <div className="shell-card__title">Supply Overview</div>
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Tracked Formations</span>
              <strong>{summary.overview.formationsTracked}</strong>
            </div>
            <div className="shell-stat">
              <span>Logistics Units</span>
              <strong>{summary.overview.logisticsFormations}</strong>
            </div>
            <div className="shell-stat">
              <span>Avg Supply</span>
              <strong>{formatPercent(summary.overview.supplyAveragePct)}</strong>
            </div>
            <div className="shell-stat">
              <span>Current Tempo</span>
              <strong>{formatDays(summary.overview.supplyAverageDays)}</strong>
            </div>
          </div>
          <div className="shell-logistics__panel-note">{summary.overview.supportHeadline}</div>
          <div className="shell-logistics__panel-note">
            Staff load {summary.overview.staffLoad ?? "Unavailable"} • {summary.overview.staffSummary}
          </div>
        </section>

        <section className="shell-logistics__panel shell-card shell-logistics__panel--transport">
          <div className="shell-card__title">Transport / Throughput</div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Vehicle Tables Exposed</span>
              <span className="shell-list__value">{summary.transport.vehicleFormationCount}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Movement Status Exposed</span>
              <span className="shell-list__value">{summary.transport.movementTrackedCount}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Logistics Formations</span>
              <span className="shell-list__value">{summary.transport.logisticsFormationCount}</span>
            </div>
          </div>
          <div className="shell-logistics__panel-note">{summary.transport.detail}</div>
        </section>

        <section className="shell-logistics__panel shell-card shell-logistics__panel--stock">
          <div className="shell-card__title">Reserves / Stock</div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Fuel Records</span>
              <span className="shell-list__value">{summary.reserves.fuelTrackedCount}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Ration Records</span>
              <span className="shell-list__value">{summary.reserves.rationsTrackedCount}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Reserve Stocks</span>
              <span className="shell-list__value">Not exposed</span>
            </div>
          </div>
          <div className="shell-logistics__panel-note">{summary.reserves.reserveStockStatus}</div>
        </section>

        <section className="shell-logistics__panel shell-card shell-logistics__panel--replacements">
          <div className="shell-card__title">Replacement Status</div>
          <div className="shell-logistics__empty">{summary.replacements.status}</div>
          <div className="shell-logistics__panel-note">{summary.replacements.detail}</div>
        </section>

        <section className="shell-logistics__panel shell-card shell-logistics__panel--warnings">
          <div className="shell-card__title">Bottlenecks / Warnings</div>
          <div className="shell-logistics__signal-list">
            {summary.warnings.map((item) => (
              <div className="shell-logistics__signal" key={item}>
                <strong>Staff Note</strong>
                <div>{item}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="shell-logistics__panel shell-card shell-logistics__panel--support">
          <div className="shell-card__title">Support Posture</div>
          <div className="shell-list">
            <div className="shell-list__row">
              <span className="shell-list__title">Support Links Exposed</span>
              <span className="shell-list__value">{summary.support.attachmentTrackedCount}</span>
            </div>
            <div className="shell-list__row">
              <span className="shell-list__title">Distribution Posture</span>
              <span className="shell-list__value">Partial</span>
            </div>
          </div>
          <div className="shell-logistics__panel-note">{summary.support.detail}</div>
        </section>

        <section className="shell-logistics__panel shell-card">
          <div className="shell-card__title">Low Supply Formations</div>
          {summary.tables.lowSupply.length ? (
            <div className="shell-list">
              {summary.tables.lowSupply.map((row) => (
                <div className="shell-list__row" key={row.name}>
                  <span className="shell-list__title">{row.name}</span>
                  <span className="shell-list__value">{row.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-logistics__empty">No low-supply formations are exposed below the current tempo threshold.</div>
          )}
        </section>

        <section className="shell-logistics__panel shell-card">
          <div className="shell-card__title">LOC Warnings</div>
          {summary.tables.locWarnings.length ? (
            <div className="shell-list">
              {summary.tables.locWarnings.map((row) => (
                <div className="shell-list__row" key={row.name}>
                  <span className="shell-list__title">{row.name}</span>
                  <span className="shell-list__value">{row.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-logistics__empty">No threatened or broken LOC reports are exposed in the current view.</div>
          )}
        </section>

        <section className="shell-logistics__panel shell-card">
          <div className="shell-card__title">TO&E Shortfalls</div>
          {summary.tables.shortfalls.length ? (
            <div className="shell-list">
              {summary.tables.shortfalls.map((row) => (
                <div className="shell-list__row" key={row.name}>
                  <span className="shell-list__title">{row.name}</span>
                  <span className="shell-list__value">{row.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-logistics__empty">No TO&E shortfall summaries are exposed in the current view.</div>
          )}
        </section>
      </div>
    </section>
  );
}
