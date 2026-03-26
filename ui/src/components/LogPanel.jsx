import React from "react";
import { displayLogKind, recentLogsFirst } from "../lib/demo_polish.js";

export default function LogPanel({ logs = [] }) {
  const items = recentLogsFirst(logs).slice(0, 12);

  return (
    <div className="log-panel">
      <div className="inspector-title">Operations Log</div>
      {!items.length ? (
        <div className="inspector-muted">No reports yet.</div>
      ) : (
        <div className="inspector-log">
          {items.map((entry, idx) => (
            <div className={"inspector-log-entry log-kind-" + String(entry.kind || "log").toLowerCase()} key={`${entry.kind || "log"}-${entry.time || idx}-${idx}`}>
              <div className="inspector-log-head">
                <div className="inspector-log-state">{displayLogKind(entry.kind)}</div>
                {entry.time != null ? <div className="inspector-log-time">T+{entry.time}h</div> : null}
              </div>
              <div className="inspector-log-msg">{entry.message || "No message"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
