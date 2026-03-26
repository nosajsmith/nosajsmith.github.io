import React from "react";

export default function SitrepLog({ entries = [] }) {
  return (
    <div className="sitrep-log">
      <div className="card-header">
        <div>
          <div className="card-kicker">Operational Record</div>
          <div className="card-title">SITREP / Combat Log</div>
        </div>
        <div className="card-tag">Live Feed</div>
      </div>

      <div className="log-list">
        {entries.length ? (
          entries.map((entry) => (
            <article className={`log-entry ${entry.tone || "info"}`} key={entry.id}>
              <div className="log-meta">
                <span>{entry.time || "NOW"}</span>
                <span>{entry.category || "LOG"}</span>
              </div>
              <div className="log-title">{entry.title}</div>
              <div className="log-detail">{entry.detail}</div>
            </article>
          ))
        ) : (
          <div className="log-empty">No command log entries available.</div>
        )}
      </div>
    </div>
  );
}
