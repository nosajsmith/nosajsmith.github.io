import React from "react";

function UnitRow({ unit }) {
  return (
    <div className="oob-unit" key={unit.id}>
      <div className="oob-unit-name">{unit.name}</div>
      <div className="oob-unit-meta">
        <span>TOE {unit.toe_pct}%</span>
        <span>Sup {unit.supply_days.toFixed(1)}d</span>
        <span>{unit.readiness_band}</span>
        <span>{unit.morale_band}</span>
        {unit.fire_policy ? <span>{unit.fire_policy}</span> : null}
      </div>
    </div>
  );
}

export default function OobTree({ oob }) {
  const sides = Array.isArray(oob?.sides) ? oob.sides : [];

  if (!sides.length) {
    return (
      <div className="oob-empty">No OOB data.</div>
    );
  }

  return (
    <div className="oob-tree">
      {sides.map((side) => (
        <details className="oob-side" key={side.id} open>
          <summary className="oob-summary">{side.label}</summary>

          {(side.hqs || []).map((hq) => (
            <details className="oob-hq" key={`${side.id}-${hq.id}`} open>
              <summary className="oob-summary">
                <span>{hq.name}</span>
                <span className="oob-summary-note">Cmd {hq.command_load}</span>
              </summary>
              <div className="oob-group">
                {(hq.units || []).map((unit) => <UnitRow key={unit.id} unit={unit} />)}
              </div>
            </details>
          ))}

          {(side.unassigned_units || []).length ? (
            <details className="oob-hq" key={`${side.id}-unassigned`}>
              <summary className="oob-summary">
                <span>Unassigned</span>
                <span className="oob-summary-note">{side.unassigned_units.length}</span>
              </summary>
              <div className="oob-group">
                {side.unassigned_units.map((unit) => <UnitRow key={unit.id} unit={unit} />)}
              </div>
            </details>
          ) : null}
        </details>
      ))}
    </div>
  );
}
