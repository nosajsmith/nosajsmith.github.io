import React from "react";

function kv(label, value) {
  return (
    <div className="kv" key={label}>
      <div className="kv-k">{label}</div>
      <div className="kv-v">{String(value ?? "")}</div>
    </div>
  );
}

export default function Inspector({ unit }) {
  if (!unit) {
    return (
      <div className="inspector">
        <div className="inspector-title">Inspector</div>
        <div className="inspector-muted">No unit selected.</div>
      </div>
    );
  }

  const id = unit.id ?? unit.uid ?? unit.name;
  const x = unit.x ?? unit.pos_x ?? unit.pos?.x;
  const y = unit.y ?? unit.pos_y ?? unit.pos?.y;

  return (
    <div className="inspector">
      <div className="inspector-title">Inspector</div>

      <div className="inspector-block">
        {kv("Name", unit.name ?? "")}
        {kv("ID", id)}
        {kv("X", x)}
        {kv("Y", y)}
      </div>

      {/* Show any extra fields */}
      <div className="inspector-block">
        <div className="inspector-subtitle">Raw</div>
        <pre className="inspector-pre">{JSON.stringify(unit, null, 2)}</pre>
      </div>
    </div>
  );
}
