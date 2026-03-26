function currentScenarioDay(snapshot) {
  const hours = snapshot?.time?.current_hours;
  return typeof hours === "number" && Number.isFinite(hours) ? Math.floor(hours / 24) + 1 : null;
}

function forceRows(snapshot, key) {
  const rows = snapshot?.force_changes?.[key];
  return Array.isArray(rows) ? [...rows] : [];
}

function sortForceRows(rows) {
  return [...rows].sort((left, right) => {
    const leftDay = typeof left?.day === "number" && Number.isFinite(left.day) ? left.day : Number.POSITIVE_INFINITY;
    const rightDay = typeof right?.day === "number" && Number.isFinite(right.day) ? right.day : Number.POSITIVE_INFINITY;
    if (leftDay !== rightDay) {
      return leftDay - rightDay;
    }
    return String(left?.name ?? left?.id ?? "").localeCompare(String(right?.name ?? right?.id ?? ""));
  });
}

function formatSchedule(day, currentDay) {
  if (day == null) {
    return "Schedule not exposed";
  }
  if (currentDay == null) {
    return `Day ${day}`;
  }
  const delta = day - currentDay;
  if (delta > 0) {
    return `Day ${day} • due in ${delta} day${delta === 1 ? "" : "s"}`;
  }
  if (delta === 0) {
    return `Day ${day} • due this day`;
  }
  return `Day ${day} • scheduled day passed`;
}

function formatDestination(row) {
  if (row.location_id) {
    return row.location_id.replace(/[_:.-]+/g, " ");
  }
  return "Destination not exposed";
}

function formatCommand(row) {
  return row.hq_unit_id || "Command destination not exposed";
}

export function summarizeReinforcementsBoard(snapshot) {
  const currentDay = currentScenarioDay(snapshot);
  const reinforcements = sortForceRows(forceRows(snapshot, "reinforcements"));
  const withdrawals = sortForceRows(forceRows(snapshot, "withdrawals"));
  const replacementEvents = sortForceRows(forceRows(snapshot, "replacement_events"));

  return {
    currentDay,
    overview: {
      arrivals: reinforcements.length,
      withdrawals: withdrawals.length,
      replacementEvents: replacementEvents.length,
      staffNote: reinforcements.length
        ? "Scheduled force changes are drawn directly from scenario-authored reinforcement rows."
        : "No reinforcement schedule is exposed on the current shell path for this scenario.",
    },
    arrivals: reinforcements.map((row) => ({
      id: row.id || row.name,
      name: row.name,
      side: row.side || "NEUTRAL",
      kind: row.kind || "land",
      day: typeof row.day === "number" && Number.isFinite(row.day) ? row.day : null,
      timing: formatSchedule(row.day, currentDay),
      destination: formatDestination(row),
      command: formatCommand(row),
    })),
    withdrawals: withdrawals.map((row) => ({
      id: row.id || row.name,
      name: row.name,
      side: row.side || "NEUTRAL",
      kind: row.kind || "land",
      day: typeof row.day === "number" && Number.isFinite(row.day) ? row.day : null,
      timing: formatSchedule(row.day, currentDay),
      destination: formatDestination(row),
      command: formatCommand(row),
    })),
    replacementEvents: replacementEvents.map((row) => ({
      id: row.id || row.name,
      name: row.name,
      day: typeof row.day === "number" && Number.isFinite(row.day) ? row.day : null,
      timing: formatSchedule(row.day, currentDay),
    })),
    placeholders: {
      withdrawals: "No authoritative withdrawal schedule is exposed on the current shell path for this scenario.",
      replacements: "Replacement-impact events are not exposed on the current shell path.",
    },
  };
}
