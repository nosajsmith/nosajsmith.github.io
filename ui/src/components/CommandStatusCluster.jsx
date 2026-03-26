import React from "react";

function statusCell(label, value, detail) {
  return (
    <div className="command-status-cell" key={label}>
      <span className="command-status-cell__label">{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default function CommandStatusCluster({
  wsConnected,
  scenarioLoaded,
  turnLabel,
  dateLabel,
  phaseLabel,
  selectedFocusName,
  objectiveLabel,
  aiReady,
}) {
  const flags = [
    wsConnected ? "CONNECTED" : "OFFLINE",
    scenarioLoaded ? "SCENARIO LOADED" : "SCENARIO PENDING",
    turnLabel ? turnLabel.toUpperCase() : "TURN PENDING",
    aiReady ? "AI READY" : "AI PENDING",
  ];

  return (
    <aside className="command-status-cluster">
      <div className="command-status-grid">
        {statusCell("Bridge", wsConnected ? "Linked" : "Offline", scenarioLoaded ? "Scenario synchronized" : "Awaiting load")}
        {statusCell("Turn", turnLabel || "Turn pending", dateLabel || "Date pending")}
        {statusCell("Phase", phaseLabel || "Operational review", objectiveLabel || "Objective pending")}
        {statusCell("Track", selectedFocusName || "No tracked unit", aiReady ? "Command logic online" : "Planning snapshot only")}
      </div>

      <div className="command-status-flags">
        {flags.map((flag) => (
          <span className="command-status-flag" key={flag}>
            {flag}
          </span>
        ))}
      </div>
    </aside>
  );
}
