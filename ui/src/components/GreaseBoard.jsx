import React from "react";

export default function GreaseBoard({ data }) {
  const orders = Array.isArray(data?.orders) ? data.orders : [];
  const alerts = Array.isArray(data?.alerts) ? data.alerts : [];

  return (
    <div className="grease-board">
      <div className="card-header">
        <div>
          <div className="card-kicker">Command Awareness</div>
          <div className="card-title">Grease Board</div>
        </div>
        <div className="card-tag">Staff Net</div>
      </div>

      <div className="board-grid">
        <div className="board-field">
          <span className="board-label">Turn</span>
          <strong>{data?.turn || "Awaiting turn data"}</strong>
        </div>
        <div className="board-field">
          <span className="board-label">Objective</span>
          <strong>{data?.objective || "Pending objective"}</strong>
        </div>
        <div className="board-field">
          <span className="board-label">Front Status</span>
          <strong>{data?.front_status || "Unknown"}</strong>
        </div>
        <div className="board-field">
          <span className="board-label">Supply Status</span>
          <strong>{data?.supply_status || "Unknown"}</strong>
        </div>
      </div>

      <div className="main-effort-card">
        <span className="board-label">Main Effort</span>
        <div className="main-effort-value">{data?.main_effort || "Not assigned"}</div>
      </div>

      <div className="board-columns">
        <div className="board-column">
          <div className="board-section-title">Active Orders</div>
          <ul className="board-list">
            {orders.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="board-column">
          <div className="board-section-title">Alerts</div>
          <ul className="board-list board-list-alerts">
            {alerts.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {data?.staff_notes ? (
        <div className="staff-note">
          <div className="board-section-title">Staff Note</div>
          <p>{data.staff_notes}</p>
        </div>
      ) : null}
    </div>
  );
}
