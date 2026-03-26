import React, { useMemo } from "react";

function locationScore(location, objectiveCounts, objectiveValues) {
  return (
    Number(location.isPort) * 3 +
    Number(location.isAirfield) * 3 +
    Number(location.occupantCount > 0) * 2 +
    Number(objectiveCounts[location.id] || 0) * 3 +
    Number(objectiveValues[location.id] || 0)
  );
}

function labelDirection(location, index) {
  if (location.px < 420) return "east";
  if (location.px > 900) return "west";
  return index % 2 === 0 ? "east" : "west";
}

function labelDetail(location, objectiveCount, objectiveValue) {
  const details = [];
  if (objectiveValue) details.push(`${objectiveValue} VP`);
  else if (objectiveCount) details.push(`${objectiveCount} OBJ`);
  details.push(String(location.terrain || "UNKNOWN"));
  if (location.isPort) details.push("PORT");
  if (location.isAirfield) details.push("AIRFIELD");
  return details.join(" • ");
}

export default function LocationLabelLayer({ locations = [], objectives = [], showControl = true }) {
  const labels = useMemo(() => {
    const objectiveCounts = objectives.reduce((out, objective) => {
      out[objective.locationId] = (out[objective.locationId] || 0) + 1;
      return out;
    }, {});
    const objectiveValues = objectives.reduce((out, objective) => {
      out[objective.locationId] = (out[objective.locationId] || 0) + Number(objective.value || 0);
      return out;
    }, {});

    return [...locations]
      .sort((left, right) => locationScore(right, objectiveCounts, objectiveValues) - locationScore(left, objectiveCounts, objectiveValues))
      .slice(0, 10)
      .map((location, index) => {
        const direction = labelDirection(location, index);
        const x1 = direction === "east" ? 16 : -16;
        const x2 = direction === "east" ? 30 : -30;
        const textX = direction === "east" ? 36 : -36;
        const anchor = direction === "east" ? "start" : "end";
        const objectiveCount = objectiveCounts[location.id] || 0;
        const objectiveValue = objectiveValues[location.id] || 0;
        const priority = objectiveCount > 0 || location.isPort || location.isAirfield ? "primary" : "secondary";

        return {
          ...location,
          anchor,
          direction,
          x1,
          x2,
          textX,
          objectiveCount,
          objectiveValue,
          priority,
          detail: labelDetail(location, objectiveCount, objectiveValue),
        };
      });
  }, [locations, objectives]);

  return (
    <g className="mwe-location-label-layer" pointerEvents="none">
      {labels.map((location) => (
        <g key={location.id} transform={`translate(${location.px},${location.py})`}>
          {showControl ? (
            <circle cx={0} cy={-20} r={3.5} className={`location-control-dot ${String(location.control || "").toLowerCase()}`} />
          ) : null}
          <line x1={0} y1={-16} x2={location.x1} y2={-24} className={`location-leader ${location.priority}`} />
          <line x1={location.x1} y1={-24} x2={location.x2} y2={-24} className={`location-leader ${location.priority}`} />
          <text x={location.textX} y={-28} textAnchor={location.anchor} className={`location-label ${location.priority}`}>
            {location.name}
          </text>
          <text x={location.textX} y={-15} textAnchor={location.anchor} className="location-sublabel">
            {location.detail}
          </text>
        </g>
      ))}
    </g>
  );
}
