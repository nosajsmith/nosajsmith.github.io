import type { ViewSnapshot } from "../../types/viewSnapshot";
import { summarizeCommunications } from "./communications_summary.js";

type ReportsFeedProps = {
  snapshot: ViewSnapshot;
  onOpenCenter: () => void;
};

function severityLabel(severity: string): string {
  if (severity === "warning") {
    return "Warning";
  }
  return "Info";
}

export default function ReportsFeed({ snapshot, onOpenCenter }: ReportsFeedProps) {
  const communications = summarizeCommunications(snapshot.reports);
  const latest = communications.latest ?? communications.demoExample;
  const previewSummary = latest?.summary ?? "No communications are available in the current snapshot.";
  const previewContext = [latest?.senderLabel, latest?.timeLabel, latest?.showKind ? latest.kind : null]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(" • ");
  const pendingLabel = communications.pending == null
    ? "Dispatch queue unavailable"
    : communications.pending === 0
      ? "No pending dispatches"
      : `${communications.pending} pending dispatch${communications.pending === 1 ? "" : "es"}`;

  return (
    <section
      className="shell-reports"
      role="button"
      tabIndex={0}
      aria-label="Open Communications Center"
      onClick={onOpenCenter}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpenCenter();
        }
      }}
    >
      <div className="shell-reports__intro">
        <div className="shell-eyebrow">Communications</div>
        <div className="shell-reports__pending">{pendingLabel}</div>
      </div>

      {latest ? (
        <article className="shell-report shell-report--latest">
          <div className="shell-report__identity">
            {latest.insigniaCode ? (
              <span className="shell-report__insignia" aria-hidden="true">
                {latest.insigniaCode}
              </span>
            ) : null}
            <div className="shell-report__identity-copy">
              <div className="shell-report__head">
                <div className="shell-report__kicker">Current Dispatch</div>
                <div className={"shell-report__severity is-" + latest.severity}>{severityLabel(latest.severity)}</div>
              </div>
              <div className="shell-report__title">{latest.title}</div>
              {previewContext ? <div className="shell-report__context">{previewContext}</div> : null}
            </div>
          </div>
          <div className="shell-report__summary shell-report__summary--latest">{previewSummary}</div>
        </article>
      ) : (
        <div className="shell-empty">No communications are available in the current snapshot.</div>
      )}

      <div className="shell-reports__rail">
        <div className="shell-reports__hint">Review dispatch history, pending traffic, and current reporting gaps.</div>
      </div>
    </section>
  );
}
