const FALLBACK_SITREP_LOG = [
  {
    id: "sitrep-1",
    time: "15 SEP 0500",
    category: "SITREP",
    tone: "info",
    title: "Assault echelons established ashore",
    detail: "Initial landing waves are holding the beachhead while command reviews the approach toward Seoul.",
  },
  {
    id: "sitrep-2",
    time: "15 SEP 0615",
    category: "COMBAT",
    tone: "warn",
    title: "Resistance tightening on the western road net",
    detail: "Opposition remains fragmented but is forcing slower movement on the main axis.",
  },
  {
    id: "sitrep-3",
    time: "15 SEP 0710",
    category: "SUPPLY",
    tone: "warn",
    title: "Forward logistics under strain",
    detail: "Supply routing west of Inchon is adequate for now, but tempo will drop if the corridor remains exposed.",
  },
  {
    id: "sitrep-4",
    time: "15 SEP 0830",
    category: "STAFF",
    tone: "info",
    title: "Naval fires available on request",
    detail: "Support remains on-call for shaping fires if the center axis stalls.",
  },
];

function entry({ id, category, tone = "info", title, detail }) {
  return {
    id,
    time: "LIVE",
    category,
    tone,
    title,
    detail,
  };
}

export function buildSitrepEntries({
  scenarioName,
  scenarioData,
  objectives = [],
  units = [],
  selectedUnit,
  activityLog = [],
  wsConnected,
}) {
  const liveEntries = [];
  const allUnits = Array.isArray(units) ? units : [];
  const lowSupplyUnits = allUnits.filter((unit) => Number(unit?.raw?.supply) <= 40);
  const fatiguedUnits = allUnits.filter((unit) => Number(unit?.raw?.fatigue) >= 50);
  const contestedObjectives = objectives.filter((objective) => String(objective?.control || "").toUpperCase() === "CONTESTED");
  const alliedObjectives = objectives.filter((objective) => String(objective?.side || "").toUpperCase() === "ALLIED");

  if (scenarioName) {
    liveEntries.push(
      entry({
        id: "live-scenario",
        category: "SITREP",
        title: `Scenario loaded: ${scenarioName}`,
        detail: scenarioData?.description || "Operational theater data synchronized from the bridge.",
      }),
    );
  }

  if (alliedObjectives.length) {
    const primary = alliedObjectives.sort((left, right) => Number(right.value) - Number(left.value))[0];
    liveEntries.push(
      entry({
        id: "live-objective",
        category: "OBJECTIVE",
        title: `Primary objective: ${primary.locationId}`,
        detail: `${alliedObjectives.length} Allied objective${alliedObjectives.length === 1 ? "" : "s"} tracked on the current map.`,
      }),
    );
  }

  if (contestedObjectives.length) {
    liveEntries.push(
      entry({
        id: "live-contested",
        category: "COMBAT",
        tone: "warn",
        title: `${contestedObjectives.length} contested objective${contestedObjectives.length === 1 ? "" : "s"}`,
        detail: contestedObjectives.map((objective) => objective.locationId).join(", "),
      }),
    );
  }

  if (lowSupplyUnits.length) {
    liveEntries.push(
      entry({
        id: "live-supply",
        category: "SUPPLY",
        tone: "warn",
        title: "Supply attention required",
        detail: `${lowSupplyUnits.length} unit${lowSupplyUnits.length === 1 ? "" : "s"} below preferred supply threshold.`,
      }),
    );
  }

  if (selectedUnit) {
    liveEntries.push(
      entry({
        id: "live-focus",
        category: "TRACK",
        title: `Tracking ${selectedUnit.name}`,
        detail:
          selectedUnit.raw?.location_id
            ? `Current location ${selectedUnit.raw.location_id}.`
            : `Current hex ${selectedUnit.q},${selectedUnit.r}.`,
      }),
    );
  }

  if (fatiguedUnits.length) {
    liveEntries.push(
      entry({
        id: "live-fatigue",
        category: "STAFF",
        tone: "warn",
        title: "Fatigue rising on active formations",
        detail: `${fatiguedUnits.length} unit${fatiguedUnits.length === 1 ? "" : "s"} show elevated fatigue.`,
      }),
    );
  }

  if (!wsConnected) {
    liveEntries.push(
      entry({
        id: "live-bridge",
        category: "ALERT",
        tone: "critical",
        title: "Bridge disconnected",
        detail: "Operational data frozen. Displaying the last synchronized theater picture.",
      }),
    );
  }

  const activityEntries = activityLog.map((item, index) => ({
    id: item.id || `activity-${index}`,
    time: item.time || "LIVE",
    category: item.category || "STATUS",
    tone: item.tone || "info",
    title: item.title,
    detail: item.detail,
  }));

  return [...activityEntries, ...liveEntries, ...FALLBACK_SITREP_LOG].slice(0, 8);
}

export { FALLBACK_SITREP_LOG };
