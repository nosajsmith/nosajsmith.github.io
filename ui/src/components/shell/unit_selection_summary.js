function humanizeValue(value, fallback) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return fallback;
  }
  return raw
    .replace(/[_:.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function summarizeSelectedUnit(unit) {
  if (!unit) {
    return {
      selected: false,
      title: "No unit selected",
      subtitle: "Click a visible unit counter to inspect its current operational state.",
      metrics: [],
    };
  }

  const metrics = [
    { label: "Strength", value: unit.strength ?? "Unavailable" },
    { label: "Supply", value: unit.supply ?? "Unavailable" },
    { label: "Readiness", value: unit.readiness ?? "Unavailable" },
  ];

  if (unit.morale != null || unit.morale_band) {
    metrics.push({
      label: "Morale",
      value: unit.morale != null ? unit.morale : humanizeValue(unit.morale_band, "Unavailable"),
    });
  }

  if (unit.status) {
    metrics.push({
      label: "Status",
      value: humanizeValue(unit.status, "Unavailable"),
    });
  }

  return {
    selected: true,
    title: unit.name || "Unnamed Unit",
    subtitle: `${humanizeValue(unit.side, "Unknown Side")} ${humanizeValue(unit.kind, "Formation")}`,
    metrics,
  };
}
