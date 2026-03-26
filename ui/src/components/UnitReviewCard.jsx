import React from "react";

function readField(unit, ...keys) {
  for (const key of keys) {
    const value = unit?.[key] ?? unit?.raw?.[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return null;
}

function metric(label, value) {
  return (
    <div className="unit-metric" key={label}>
      <span>{label}</span>
      <strong>{value ?? "Unavailable"}</strong>
    </div>
  );
}

function statusSummary(unit) {
  const supply = Number(readField(unit, "supply"));
  const fatigue = Number(readField(unit, "fatigue"));
  const readiness = Number(readField(unit, "readiness"));

  if (Number.isFinite(supply) && supply <= 40) return "Supply constrained and requiring immediate support.";
  if (Number.isFinite(fatigue) && fatigue >= 50) return "Formation fatigue is rising under current operational tempo.";
  if (Number.isFinite(readiness) && readiness <= 45) return "Readiness below preferred threshold. Refit or slower tempo recommended.";
  return "Formation available for current mission posture.";
}

export default function UnitReviewCard({ unit, hoverUnit }) {
  const focusUnit = unit || hoverUnit;
  const modeLabel = unit ? "Selected Unit" : hoverUnit ? "Hover Track" : "No Active Focus";

  if (!focusUnit) {
    return (
      <div className="unit-review">
        <div className="card-header">
          <div>
            <div className="card-kicker">Unit Review</div>
            <div className="card-title">Inspector</div>
          </div>
          <div className="card-tag">Idle</div>
        </div>
        <div className="inspector-muted">No unit selected. Hover or select a formation to review its current posture.</div>
      </div>
    );
  }

  const unitType = readField(focusUnit, "unit_type", "type") || "Formation";
  const location = readField(focusUnit, "location_id") || `HEX ${focusUnit.q ?? "?"},${focusUnit.r ?? "?"}`;
  const side = readField(focusUnit, "side") || "Unknown";
  const posture = readField(focusUnit, "posture") || "Unreported";
  const x = focusUnit.x ?? focusUnit.pos_x ?? focusUnit.pos?.x ?? focusUnit.q ?? "—";
  const y = focusUnit.y ?? focusUnit.pos_y ?? focusUnit.pos?.y ?? focusUnit.r ?? "—";

  return (
    <div className="unit-review">
      <div className="card-header">
        <div>
          <div className="card-kicker">Unit Review</div>
          <div className="card-title">Inspector</div>
        </div>
        <div className="card-tag">{modeLabel}</div>
      </div>

      <div className="unit-review__hero">
        <div>
          <div className="unit-review__name">{focusUnit.name || "Unnamed Formation"}</div>
          <div className="unit-review__subtitle">{side} • {unitType} • {posture}</div>
        </div>
        <div className={`unit-review__side ${String(side).toLowerCase()}`}>{String(side).toUpperCase()}</div>
      </div>

      <div className="unit-review__metrics">
        {metric("Strength", readField(focusUnit, "strength"))}
        {metric("Readiness", readField(focusUnit, "readiness"))}
        {metric("Fatigue", readField(focusUnit, "fatigue"))}
        {metric("Supply", readField(focusUnit, "supply"))}
      </div>

      <div className="inspector-block">
        <div className="section-subtitle">Position</div>
        <div className="unit-review__position">
          <div><span>Location</span><strong>{location}</strong></div>
          <div><span>Hex</span><strong>{x}, {y}</strong></div>
        </div>
      </div>

      <div className="inspector-block">
        <div className="section-subtitle">Status Summary</div>
        <div className="unit-review__summary">{statusSummary(focusUnit)}</div>
      </div>

      <details className="unit-review__raw">
        <summary>Raw signal</summary>
        <pre className="inspector-pre">{JSON.stringify(focusUnit, null, 2)}</pre>
      </details>
    </div>
  );
}
