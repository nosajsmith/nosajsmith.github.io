import { inferScenarioPresentation } from "../../lib/view_snapshot.js";

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function average(values) {
  const numbers = values.map(toNumber).filter((value) => value != null);
  if (!numbers.length) {
    return null;
  }
  return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

function unitKind(unit) {
  return String(unit?.kind ?? "").trim().toLowerCase();
}

function unitName(unit) {
  return String(unit?.name ?? unit?.id ?? "Formation").trim() || "Formation";
}

function weatherCondition(snapshot) {
  return typeof snapshot?.weather?.condition === "string" ? snapshot.weather.condition.trim() : null;
}

function collectNavalUnits(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  return units.filter((unit) => {
    const kind = unitKind(unit);
    return kind.includes("naval") || kind.includes("fleet") || kind.includes("task force") || kind.includes("navy");
  });
}

function portById(snapshot) {
  const ports = Array.isArray(snapshot?.ports) ? snapshot.ports : [];
  return new Map(ports.map((port) => [String(port?.id ?? "").trim().toUpperCase(), port]));
}

function portStatus(port) {
  if (!port || typeof port !== "object") {
    return "State not exposed";
  }
  if (port.destroyed === true) {
    return "Destroyed";
  }
  if (port.damage_state) {
    return port.damage_state;
  }
  if (port.damaged === true) {
    return "Damaged";
  }
  if (port.state || port.control_state) {
    return String(port.state ?? port.control_state).trim() || "State not exposed";
  }
  if (typeof port.readiness === "number" && Number.isFinite(port.readiness)) {
    return `${Math.round(port.readiness)} readiness`;
  }
  return "State not exposed";
}

function navalMissionLabel(unit) {
  const action = String(unit?.inspector?.orders?.action ?? "").trim();
  const posture = String(unit?.inspector?.operational_state?.posture ?? unit?.posture ?? "").trim();
  if (action) {
    return action.replace(/[_:.-]+/g, " ").trim().replace(/\b\w/g, (match) => match.toUpperCase());
  }
  if (posture) {
    return `${posture.replace(/[_:.-]+/g, " ").trim().replace(/\b\w/g, (match) => match.toUpperCase())} posture`;
  }
  return "Mission posture not exposed";
}

function localAreaCue(snapshot, locationIds) {
  const areas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
  const match = areas.find((area) => locationIds.has(String(area?.location_id ?? "").trim().toUpperCase())) ?? null;
  if (!match) {
    return "";
  }
  const label = String(match?.label ?? "").trim();
  const reason = Array.isArray(match?.pressure_reasons) ? String(match.pressure_reasons[0] ?? "").trim() : "";
  if (label && reason) {
    return `${label} currently reflects ${reason.replace(/[_:.-]+/g, " ").trim().toLowerCase()}.`;
  }
  if (label) {
    return `${label} remains the active shore-support axis.`;
  }
  return "";
}

function localPortIds(snapshot) {
  const localAreaIds = new Set(
    (Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [])
      .map((area) => String(area?.location_id ?? "").trim().toUpperCase())
      .filter(Boolean),
  );

  return (Array.isArray(snapshot?.ports) ? snapshot.ports : [])
    .map((port) => String(port?.id ?? "").trim().toUpperCase())
    .filter((id) => localAreaIds.has(id));
}

function formatWindow(window) {
  if (window.start_hour == null && window.end_hour == null) {
    return "Window not exposed";
  }
  if (window.start_hour == null) {
    return `Until H+${window.end_hour}`;
  }
  if (window.end_hour == null) {
    return `From H+${window.start_hour}`;
  }
  return `H+${window.start_hour} to H+${window.end_hour}`;
}

function windowIsActive(window, currentHours) {
  if (currentHours == null) {
    return false;
  }
  const start = toNumber(window?.start_hour);
  const end = toNumber(window?.end_hour);
  if (start == null && end == null) {
    return true;
  }
  if (start != null && currentHours < start) {
    return false;
  }
  if (end != null && currentHours > end) {
    return false;
  }
  return true;
}

export function summarizeLocalNavalSupport(snapshot) {
  const presentation = inferScenarioPresentation(snapshot);
  const localPorts = localPortIds(snapshot);
  const ports = (Array.isArray(snapshot?.ports) ? snapshot.ports : []).filter((port) => localPorts.includes(String(port?.id ?? "").trim().toUpperCase()));
  const navalUnits = collectNavalUnits(snapshot);
  const localUnits = navalUnits.filter((unit) => localPorts.includes(String(unit?.location_id ?? "").trim().toUpperCase()));
  const windows = (Array.isArray(snapshot?.naval_support_windows) ? snapshot.naval_support_windows : []).filter((window) => String(window?.side ?? "").trim().toUpperCase() === "ALLIED");
  const currentHours = toNumber(snapshot?.time?.current_hours);
  const activeWindows = windows.filter((window) => windowIsActive(window, currentHours));
  const weather = weatherCondition(snapshot);
  const anchorLabel = ports.map((port) => port.name).join(", ");
  const anchorStatus = ports.map((port) => portStatus(port)).find((value) => value && value !== "State not exposed") || "";
  const areaCue = localAreaCue(snapshot, new Set(localPorts));

  let availability = "Not exposed";
  if (!ports.length) {
    availability = "Unavailable";
  } else if (activeWindows.length) {
    availability = "Available";
  } else if (windows.length) {
    availability = "Limited";
  } else if (anchorLabel) {
    availability = "Context exposed";
  }

  let supportingFormation = "No supporting naval formation is exposed for the active scenario.";
  if (localUnits.length) {
    supportingFormation = localUnits.map((unit) => unitName(unit)).join(", ");
  } else if (windows.length) {
    supportingFormation = "Formation identity not exposed; naval support window is scenario-authored.";
  }

  let supportPosture = "Support posture not exposed";
  if (activeWindows.length === 1) {
    supportPosture = `Window active • ${formatWindow(activeWindows[0])}`;
  } else if (activeWindows.length > 1) {
    supportPosture = `${activeWindows.length} active support windows`;
  } else if (windows.length === 1) {
    supportPosture = `Window inactive • ${formatWindow(windows[0])}`;
  } else if (windows.length > 1) {
    supportPosture = `${windows.length} authored support windows`;
  } else if (anchorLabel) {
    supportPosture = anchorStatus && anchorStatus !== "State not exposed"
      ? `Port anchor • ${anchorStatus}`
      : "Port anchor only";
  }

  let constraint = "No local naval support window is exposed on the current shell path.";
  if (!ports.length) {
    constraint = `No local shore-support port anchor is exposed for the current ${presentation.frontLabel.toLowerCase()} picture.`;
  } else if (!windows.length) {
    constraint = anchorLabel
      ? `${anchorLabel} is the only currently exposed shore-support anchor.`
      : "No local naval support window is exposed on the current shell path.";
  } else if (windows.length && !activeWindows.length) {
    constraint = currentHours != null
      ? `No authored naval support window is active at H+${currentHours}.`
      : "Current naval support-window activity is not exposed.";
  } else if (weather) {
    constraint = `Weather ${weather} is the only currently exposed offshore-support cue.`;
  }

  let note = `Local naval support availability is not exposed beyond current ${presentation.theaterLabel.toLowerCase()} port context.`;
  if (!ports.length) {
    note = `No local shore-support context is exposed for the current ${presentation.frontLabel.toLowerCase()} picture.`;
  } else if (ports.length) {
    note = `${anchorLabel} anchors the current shore-support picture.`;
  }

  return {
    available: ports.length > 0,
    availability,
    note,
    supportPosture,
    constraint: [constraint, areaCue].filter(Boolean).join(" "),
    supportingFormation,
    anchorLabel,
  };
}

export function summarizeNavalOperations(snapshot) {
  const navalUnits = collectNavalUnits(snapshot);
  const ports = Array.isArray(snapshot?.ports) ? snapshot.ports : [];
  const windows = Array.isArray(snapshot?.naval_support_windows) ? snapshot.naval_support_windows : [];
  const portIndex = portById(snapshot);
  const avgReadiness = average(navalUnits.map((unit) => unit?.readiness));
  const avgSupplyDays = average(navalUnits.map((unit) => unit?.inspector?.supply?.supply_days_current));
  const locWarnings = navalUnits.filter((unit) => {
    const state = String(unit?.inspector?.operational_state?.loc?.state ?? "").trim().toLowerCase();
    return state === "threatened" || state === "broken";
  });

  const concerns = [];
  if (windows.length) {
    concerns.push(`${windows.length} scenario-authored naval support window${windows.length === 1 ? "" : "s"} are available for planning context.`);
  } else {
    concerns.push("No naval support window is exposed on the current shell path for the active scenario.");
  }
  if (locWarnings.length) {
    concerns.push(`${locWarnings.length} naval formations report threatened or broken LOC status.`);
  }
  if (!navalUnits.length) {
    concerns.push("No fleets or task forces are exposed in the active scenario snapshot.");
  }

  return {
    overview: {
      formationsTracked: navalUnits.length,
      portsTracked: ports.length,
      supportWindowsTracked: windows.length,
      readinessAverage: avgReadiness,
      sustainmentAverageDays: avgSupplyDays,
      statusLine: navalUnits.length
        ? "Naval picture built from currently exposed fleet or task-force unit rows."
        : "The current shell path exposes maritime context, but no dedicated fleets or task forces.",
    },
    formations: navalUnits.map((unit) => {
      const port = portIndex.get(String(unit?.location_id ?? "").trim().toUpperCase()) ?? null;
      const anchorStatus = portStatus(port);
      return {
        id: unit.id,
        name: unitName(unit),
        readiness: unit?.readiness ?? null,
        supply: unit?.inspector?.supply?.supply_days_current ?? null,
        mission: navalMissionLabel(unit),
        endurance: unit?.inspector?.supply?.fuel || (unit?.inspector?.supply?.supply_days_current != null
          ? `${unit.inspector.supply.supply_days_current.toFixed(1)} days sustainment`
          : "Fuel and endurance not exposed"),
        composition: typeof unit?.strength === "number" && Number.isFinite(unit.strength)
          ? `${Math.round(unit.strength)} strength exposed`
          : "Ship counts not exposed",
        area: port?.name
          ? `${port.name}${anchorStatus && anchorStatus !== "State not exposed" ? ` • ${anchorStatus}` : ""}`
          : (unit?.location_id || "Operating area not exposed"),
      };
    }),
    composition: {
      status: "Ship classes not exposed",
      detail: "Ship-class inventories, task-force composition, and escort counts are not exposed on the current shell path.",
    },
    operatingContext: {
      ports: ports.map((port) => ({
        id: port.id,
        name: port.name,
        location: [
          port.x != null && port.y != null ? `${port.x}, ${port.y}` : "",
          portStatus(port) !== "State not exposed" ? portStatus(port) : "",
        ].filter(Boolean).join(" • ") || "Coordinates unavailable",
      })),
      windows: windows.map((window) => ({
        id: window.id,
        label: window.label,
        timing: formatWindow(window),
        side: window.side,
      })),
      detail: ports.length
        ? `${ports.length} authored port locations are available as naval operating context.`
        : "No authored ports are exposed for the active scenario.",
    },
    operations: {
      posture: navalUnits.length
        ? navalMissionLabel(navalUnits[0])
        : ports.length
          ? "Port-anchor support only"
          : "No naval formations exposed",
      endurance: avgSupplyDays != null ? `${avgSupplyDays.toFixed(1)} days sustainment at current tempo.` : "Fuel and endurance not exposed on current shell path.",
      convoy: ports.length
        ? `${ports.length} port anchor${ports.length === 1 ? "" : "s"} exposed; convoy and escort detail not exposed`
        : "Convoy and escort state not exposed",
    },
    concerns,
  };
}
