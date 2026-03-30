import { useState } from "react";
import type { ViewSnapshot } from "../../types/viewSnapshot";
import type { TrackedDemoOperation } from "./operations_planner_types";
import { summarizeIntelligenceBranch } from "./intelligence_branch_summary.js";

type IntelligenceBranchScreenProps = {
  snapshot: ViewSnapshot;
  operations?: TrackedDemoOperation[];
  onReturnHome: () => void;
};

function severityLabel(severity: string) {
  return severity === "warning" ? "Warning" : "Info";
}

export default function IntelligenceBranchScreen({ snapshot, operations = [], onReturnHome }: IntelligenceBranchScreenProps) {
  const summary = summarizeIntelligenceBranch(snapshot, operations);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(summary.dispatches[0]?.id ?? null);
  const selectedMessage = summary.dispatches.find((message) => message.id === selectedMessageId) ?? summary.dispatches[0] ?? null;

  return (
    <section className="shell-intel" aria-label="Intelligence branch screen">
      <header className="shell-intel__hero shell-card">
        <div>
          <div className="shell-eyebrow">Intelligence Branch</div>
          <h2 className="shell-panel__title">Recon and Dispatch Board</h2>
          <p className="shell-card__body">
            Intelligence view built from the current communications feed and authoritative pressure-reason path. Confidence values, sender attribution, and enemy strength estimates remain explicit placeholders when the shell path does not expose them.
          </p>
        </div>
        <div className="shell-intel__hero-actions">
          <button type="button" className="shell-button shell-button--secondary" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </header>

      <div className="shell-intel__grid">
        <section className="shell-intel__panel shell-card shell-intel__panel--overview">
          <div className="shell-card__title">Intelligence Overview</div>
          <div className="shell-briefing__grid">
            <div className="shell-stat">
              <span>Pending</span>
              <strong>{summary.overview.pending ?? "Unknown"}</strong>
            </div>
            <div className="shell-stat">
              <span>Pressure</span>
              <strong>{summary.overview.pressureActive ? "Active" : "Quiet"}</strong>
            </div>
            <div className="shell-stat">
              <span>Latest Dispatch</span>
              <strong>{summary.overview.latestTitle}</strong>
            </div>
            <div className="shell-stat">
              <span>Staff Posture</span>
              <strong>{summary.overview.staffSummary}</strong>
            </div>
          </div>
          <div className="shell-intel__panel-note">{summary.overview.statusLine}</div>
          <div className="shell-intel__panel-note">{summary.overview.latestSummary}</div>
        </section>

        <section className="shell-intel__panel shell-card shell-intel__panel--dispatches">
          <div className="shell-card__title">Latest Communications</div>
          {summary.dispatches.length ? (
            <div className="shell-intel__dispatches">
              {summary.dispatches.map((message) => (
                <button
                  type="button"
                  key={message.id}
                  className={"shell-intel__dispatch" + (message.id === selectedMessageId ? " is-selected" : "")}
                  onClick={() => setSelectedMessageId(message.id)}
                >
                  <div className="shell-intel__dispatch-head">
                    <strong>{message.title}</strong>
                    <span className={"shell-report__severity is-" + message.severity}>{severityLabel(message.severity)}</span>
                  </div>
                  {message.showKind ? <div className="shell-intel__dispatch-kind">{message.kind}</div> : null}
                  <div className="shell-intel__dispatch-summary">{message.summary}</div>
                  <div className="shell-intel__dispatch-time">{message.timeLabel}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="shell-intel__empty">No communications are available in the current snapshot.</div>
          )}
        </section>

        <section className="shell-intel__panel shell-card">
          <div className="shell-card__title">Message Detail</div>
          {selectedMessage ? (
            <>
              <div className="shell-intel__detail-head">
                <strong>{selectedMessage.title}</strong>
                <span>{selectedMessage.timeLabel}</span>
              </div>
              <div className="shell-intel__panel-note">{selectedMessage.body}</div>
            </>
          ) : (
            <div className="shell-intel__empty">Select a dispatch to review its full text.</div>
          )}
        </section>

        <section className="shell-intel__panel shell-card">
          <div className="shell-card__title">Recon / Sightings</div>
          {summary.recon.sightings.length ? (
            <div className="shell-intel__signal-list">
              {summary.recon.sightings.map((item) => (
                <div className="shell-intel__signal" key={item.id}>
                  <strong>{item.title}</strong>
                  <div>{item.detail}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="shell-intel__empty">No dedicated recon sightings are exposed on the current shell path.</div>
          )}
          <div className="shell-intel__panel-note">{summary.recon.detail}</div>
        </section>

        <section className="shell-intel__panel shell-card">
          <div className="shell-card__title">Confidence / Limitations</div>
          <div className="shell-intel__empty">{summary.confidence.status}</div>
          <div className="shell-intel__panel-note">{summary.confidence.detail}</div>
        </section>

        <section className="shell-intel__panel shell-card">
          <div className="shell-card__title">Intelligence Concerns</div>
          <div className="shell-intel__signal-list">
            {summary.concerns.map((item) => (
              <div className="shell-intel__signal" key={item}>
                <strong>Command Caution</strong>
                <div>{item}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
