import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeReinforcementsBoard } from "./reinforcements_board_summary.js";

type ReinforcementsBoardScreenProps = {
  snapshot: ViewSnapshot;
  onReturnToLogistics: () => void;
};

export default function ReinforcementsBoardScreen({ snapshot, onReturnToLogistics }: ReinforcementsBoardScreenProps) {
  const summary = summarizeReinforcementsBoard(snapshot);

  return (
    <section className="shell-reinforce" aria-label="Reinforcements and withdrawals board">
      <header className="shell-reinforce__hero shell-card">
        <div>
          <div className="shell-eyebrow">Force Change Board</div>
          <h2 className="shell-panel__title">Reinforcements & Withdrawals</h2>
          <p className="shell-card__body">
            Planning board for scheduled force-structure changes. Timing and destinations are shown only when the current scenario path already authors them.
          </p>
        </div>
        <div className="shell-reinforce__hero-actions">
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnToLogistics}>
            Return To Logistics
          </button>
        </div>
      </header>

      <div className="shell-reinforce__grid">
        <section className="shell-reinforce__panel shell-card shell-reinforce__panel--overview">
          <div className="shell-card__title">Planning Overview</div>
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Current Day</span>
              <strong>{summary.currentDay ?? "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Arrivals</span>
              <strong>{summary.overview.arrivals}</strong>
            </div>
            <div className="shell-stat">
              <span>Withdrawals</span>
              <strong>{summary.overview.withdrawals}</strong>
            </div>
            <div className="shell-stat">
              <span>Replacement Events</span>
              <strong>{summary.overview.replacementEvents}</strong>
            </div>
          </div>
          <div className="shell-reinforce__panel-note">{summary.overview.staffNote}</div>
        </section>

        <section className="shell-reinforce__panel shell-card shell-reinforce__panel--arrivals">
          <div className="shell-card__title">Upcoming Arrivals</div>
          {summary.arrivals.length ? (
            <div className="shell-reinforce__list">
              {summary.arrivals.map((row) => (
                <div className="shell-reinforce__entry" key={row.id}>
                  <div className="shell-reinforce__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.timing}</span>
                  </div>
                  <div className="shell-reinforce__entry-meta">
                    <span>{row.side}</span>
                    <span>{row.kind}</span>
                  </div>
                  <div className="shell-reinforce__entry-body">
                    <span>Destination {row.destination}</span>
                    <span>{row.command}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-reinforce__empty">No authoritative reinforcement rows are exposed for the active scenario.</div>
          )}
        </section>

        <section className="shell-reinforce__panel shell-card">
          <div className="shell-card__title">Scheduled Withdrawals</div>
          {summary.withdrawals.length ? (
            <div className="shell-reinforce__list">
              {summary.withdrawals.map((row) => (
                <div className="shell-reinforce__entry" key={row.id}>
                  <div className="shell-reinforce__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.timing}</span>
                  </div>
                  <div className="shell-reinforce__entry-body">
                    <span>Destination {row.destination}</span>
                    <span>{row.command}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-reinforce__empty">{summary.placeholders.withdrawals}</div>
          )}
        </section>

        <section className="shell-reinforce__panel shell-card">
          <div className="shell-card__title">Replacement-Impact Events</div>
          {summary.replacementEvents.length ? (
            <div className="shell-reinforce__list">
              {summary.replacementEvents.map((row) => (
                <div className="shell-reinforce__entry" key={row.id}>
                  <div className="shell-reinforce__entry-head">
                    <strong>{row.name}</strong>
                    <span>{row.timing}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-reinforce__empty">{summary.placeholders.replacements}</div>
          )}
        </section>
      </div>
    </section>
  );
}
