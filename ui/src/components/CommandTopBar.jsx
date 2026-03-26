import React from "react";

export default function CommandTopBar({
  wsConnected,
  scenarios,
  scenarioName,
  scenarioTitle,
  turnLabel,
  dateLabel,
  phaseLabel,
  unitCount,
  objectiveCount,
  onScenarioChange,
  onRefresh,
  onReload,
  onPing,
  plannerOpen,
  inspectorOpen,
  onTogglePlanner,
  onToggleInspector,
  statusText,
  lastLoadAt,
  lastPingAt,
}) {
  return (
    <header className="command-bar shell-card">
      <div className="command-bar__brand">
        <div className="command-bar__eyebrow">Theater of Operations</div>
        <div className="command-bar__title-row">
          <h1 className="command-bar__title">Inchon Command Shell</h1>
          <div className={`status-pill ${wsConnected ? "ok" : "bad"}`}>
            {wsConnected ? "Bridge Linked" : "Bridge Offline"}
          </div>
        </div>
        <p className="command-bar__subtitle">{statusText}</p>
      </div>

      <div className="command-bar__overview">
        <div className="command-overview-card">
          <div className="cluster-label">Scenario</div>
          <strong>{scenarioTitle || scenarioName || "No scenario loaded"}</strong>
          <span>{scenarioName || "Awaiting selection"}</span>
        </div>
        <div className="command-overview-card">
          <div className="cluster-label">Turn / Date</div>
          <strong>{turnLabel || "Turn pending"}</strong>
          <span>{dateLabel || "Date pending"}</span>
        </div>
        <div className="command-overview-card">
          <div className="cluster-label">Phase</div>
          <strong>{phaseLabel || "Operational review"}</strong>
          <span>{unitCount} units tracked • {objectiveCount} objectives</span>
        </div>
      </div>

      <div className="command-bar__controls">
        <div className="command-cluster">
          <div className="cluster-label">Scenario</div>
          <select className="select command-select" value={scenarioName} onChange={(event) => onScenarioChange(event.target.value)}>
            {!scenarios.length ? <option value="">No scenarios available</option> : null}
            {scenarios.map((scenario) => (
              <option key={scenario} value={scenario}>
                {scenario}
              </option>
            ))}
          </select>
        </div>

        <div className="command-cluster command-cluster--actions">
          <div className="cluster-label">Command</div>
          <div className="button-row button-row--topbar">
            <button className="btn" onClick={() => { void onRefresh(); }}>
              Refresh
            </button>
            <button className="btn" onClick={() => { void onReload(); }}>
              Load
            </button>
            <button className="btn" onClick={() => { void onPing(); }}>
              Ping
            </button>
          </div>
          <div className="button-row button-row--topbar button-row--compact">
            <button className="btn btn-disabled" disabled type="button">
              Launch
            </button>
            <button className="btn btn-disabled" disabled type="button">
              Step
            </button>
            <button className="btn btn-disabled" disabled type="button">
              End Turn
            </button>
          </div>
        </div>

        <div className="command-cluster command-cluster--toggles">
          <div className="cluster-label">Panels</div>
          <div className="button-row button-row--topbar">
            <button className={`btn ${plannerOpen ? "btn-active" : ""}`} onClick={onTogglePlanner}>
              {plannerOpen ? "Hide Planner" : "Show Planner"}
            </button>
            <button className={`btn ${inspectorOpen ? "btn-active" : ""}`} onClick={onToggleInspector}>
              {inspectorOpen ? "Hide Inspector" : "Show Inspector"}
            </button>
          </div>
        </div>
      </div>

      <div className="command-bar__status-row">
        <div className={`status-chip ${wsConnected ? "online" : "offline"}`}>
          {wsConnected ? "Bridge connected" : "Bridge offline"}
        </div>
        <div className="status-chip">{scenarioTitle || scenarioName || "No scenario loaded"}</div>
        <div className="status-chip">{phaseLabel || "Operational review"}</div>
        <div className="status-chip">{unitCount} units on map</div>
        <div className="status-chip">{objectiveCount} objectives tracked</div>
        <div className="status-chip">{plannerOpen ? "Planner open" : "Planner docked"}</div>
        <div className="status-chip">{inspectorOpen ? "Inspector open" : "Inspector docked"}</div>
        <div className="status-chip">Last load {lastLoadAt}</div>
        <div className="status-chip">Last ping {lastPingAt}</div>
      </div>
    </header>
  );
}
