import type { ViewSnapshot } from "../../types/viewSnapshot";
import { humanizeIntent, humanizePressureReason, pressureFallback } from "../../lib/view_snapshot.js";
import {
  summarizeCampaign,
  summarizeObjectives,
  summarizeReports,
  summarizeScore,
} from "./dashboard_summary.js";

type DashboardPanelProps = {
  snapshot: ViewSnapshot;
};

export default function DashboardPanel({ snapshot }: DashboardPanelProps) {
  const campaign = summarizeCampaign(snapshot);
  const score = summarizeScore(snapshot.campaign.score_by_side);
  const objectives = summarizeObjectives(snapshot.objectives);
  const reports = summarizeReports(snapshot.reports);

  return (
    <aside className="shell-dashboard">
      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Campaign</div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>Status</span>
            <strong>{campaign.status}</strong>
          </div>
          <div className="shell-stat">
            <span>Turn</span>
            <strong>{campaign.turn ?? "Unknown"}</strong>
          </div>
        </div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>Time Remaining</span>
            <strong>{campaign.timeRemaining != null ? `${campaign.timeRemaining}h` : "Unknown"}</strong>
          </div>
          <div className="shell-stat">
            <span>Win Target</span>
            <strong>{campaign.winTarget ?? "Unknown"}</strong>
          </div>
        </div>
      </section>

      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Score</div>
        <div className="shell-list">
          {score.length ? (
            score.map((row) => (
              <div className="shell-list__row" key={row.side}>
                <span className="shell-list__title">{row.label}</span>
                <span className="shell-list__value">{row.value}</span>
              </div>
            ))
          ) : (
            <div className="shell-empty">Score unavailable.</div>
          )}
        </div>
      </section>

      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Objectives</div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>Total</span>
            <strong>{objectives.total}</strong>
          </div>
          <div className="shell-stat">
            <span>Objective States</span>
            <strong>{objectives.byState.length || "None"}</strong>
          </div>
        </div>
        <div className="shell-dashboard__subhead">Status Summary</div>
        <div className="shell-list">
          {objectives.byState.length ? (
            objectives.byState.map((row) => (
              <div className="shell-list__row" key={row.state}>
                <span className="shell-list__title">{row.state}</span>
                <span className="shell-list__value">{row.count}</span>
              </div>
            ))
          ) : (
            <div className="shell-empty">No objectives in the current picture.</div>
          )}
        </div>
        <div className="shell-dashboard__subhead">Key Objectives</div>
        <div className="shell-dashboard__objectives">
          {objectives.key.length ? (
            objectives.key.map((objective) => (
              <div className="shell-dashboard__objective" key={objective.id}>
                <div className="shell-dashboard__objective-head">
                  <span className="shell-dashboard__objective-name">{objective.name}</span>
                  <span className="shell-dashboard__objective-state">{objective.state}</span>
                </div>
                <div className="shell-dashboard__objective-meta">
                  {objective.side ? `Side: ${objective.side}` : "Side not specified"}
                </div>
              </div>
            ))
          ) : (
            <div className="shell-empty">Objective detail unavailable.</div>
          )}
        </div>
      </section>

      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Pressure</div>
        <div className="shell-card__body">{pressureFallback(snapshot.pressure)}</div>
        {snapshot.pressure.reasons.length ? (
          <div className="shell-taglist">
            {snapshot.pressure.reasons.slice(0, 4).map((reason) => (
              <span className="shell-tag" key={reason}>
                {humanizePressureReason(reason)}
              </span>
            ))}
          </div>
        ) : null}
      </section>

      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Staff & AI</div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>Staff Summary</span>
            <strong>{snapshot.staff.summary}</strong>
          </div>
          <div className="shell-stat">
            <span>Staff Load</span>
            <strong>{snapshot.staff.load ?? "Unknown"}</strong>
          </div>
        </div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>AI Status</span>
            <strong>{snapshot.ai.enabled ? "Enabled" : "Disabled"}</strong>
          </div>
          <div className="shell-stat">
            <span>Units Tracked</span>
            <strong>{snapshot.units.length}</strong>
          </div>
        </div>
        <div className="shell-dashboard__subhead">Last AI Intent</div>
        <div className="shell-card__body">{humanizeIntent(snapshot.ai.last_intent)}</div>
      </section>

      <section className="shell-card shell-briefing">
        <div className="shell-card__title">Reports Status</div>
        <div className="shell-briefing__grid">
          <div className="shell-stat">
            <span>Pending</span>
            <strong>{reports.pending ?? "Unknown"}</strong>
          </div>
          <div className="shell-stat">
            <span>Recent Entries</span>
            <strong>{snapshot.reports.recent.length}</strong>
          </div>
        </div>
        {reports.latest ? (
          <div className="shell-dashboard__report-status">
            <div className="shell-dashboard__report-head">
              <span className="shell-dashboard__report-title">{reports.latest.title}</span>
              <span className={"shell-dashboard__report-severity is-" + reports.latest.severity.toLowerCase()}>
                {reports.latest.severity}
              </span>
            </div>
          </div>
        ) : (
          <div className="shell-empty">No recent report headline available.</div>
        )}
      </section>
    </aside>
  );
}
