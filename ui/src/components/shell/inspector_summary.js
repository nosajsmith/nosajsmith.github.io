import { humanizePressureReason, humanizeToken } from "../../lib/view_snapshot.js";
import { summarizeUnitInspector } from "./unit_inspector_summary.js";

function formatValue(value, fallback = "Unavailable") {
  if (value == null || value === "") {
    return fallback;
  }
  return value;
}

function formatBoolean(value) {
  if (typeof value !== "boolean") {
    return "Not exposed on current shell path";
  }
  return value ? "Yes" : "No";
}

function hasCoord(item) {
  return item && typeof item.x === "number" && typeof item.y === "number";
}

function coordMatch(left, right, threshold = 0.6) {
  if (!hasCoord(left) || !hasCoord(right)) {
    return false;
  }
  return Math.abs(left.x - right.x) <= threshold && Math.abs(left.y - right.y) <= threshold;
}

function normalizeId(value) {
  return String(value ?? "").trim().toUpperCase();
}

function summarizeLocState(unit) {
  const loc = unit?.inspector?.operational_state?.loc;
  if (!loc || typeof loc !== "object") {
    return "LOC unavailable";
  }
  const state = typeof loc.state === "string" && loc.state.trim() ? humanizeToken(loc.state) : "Unavailable";
  return `LOC ${state}`;
}

function summarizeUnitPresence(unit) {
  const operational = unit?.inspector?.operational_state ?? {};
  const parts = [];

  if (operational.posture) {
    parts.push(humanizeToken(operational.posture));
  }
  if (typeof operational.readiness === "number") {
    parts.push(`${operational.readiness} readiness`);
  }
  if (typeof operational.fatigue === "number") {
    parts.push(`${operational.fatigue} fatigue`);
  }
  parts.push(summarizeLocState(unit));

  return parts.join(" • ") || "No current unit detail exposed";
}

function buildEmptyInspector() {
  return {
    selected: false,
    header: {
      eyebrow: "Inspector",
      title: "No selection",
      subtitle: "Select a visible unit, objective, airfield, or port to review current state.",
      loc: null,
    },
    summary: null,
    commanderScreen: null,
    sections: [],
  };
}

function areaMatchesEntity(area, entity, objectiveIds, locationIds) {
  if (!area || typeof area !== "object") {
    return false;
  }
  if (objectiveIds.has(String(area.objective_id ?? ""))) {
    return true;
  }
  if (locationIds.has(normalizeId(area.location_id))) {
    return true;
  }
  return coordMatch(area, entity);
}

function buildContext(snapshot, selection, entity) {
  const localAreas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
  const reports = Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : [];
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const airfields = Array.isArray(snapshot?.airfields) ? snapshot.airfields : [];
  const ports = Array.isArray(snapshot?.ports) ? snapshot.ports : [];
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];

  const locationIds = new Set([normalizeId(entity?.id)]);
  const objectiveIds = new Set(selection?.kind === "objective" ? [String(entity?.id ?? "")] : []);
  const matchingAreas = localAreas.filter((area) => areaMatchesEntity(area, entity, objectiveIds, locationIds));

  for (const area of matchingAreas) {
    if (typeof area?.location_id === "string" && area.location_id.trim()) {
      locationIds.add(normalizeId(area.location_id));
    }
    if (typeof area?.objective_id === "string" && area.objective_id.trim()) {
      objectiveIds.add(area.objective_id.trim());
    }
  }

  const relatedObjectives = objectives.filter((objective) => (
    objectiveIds.has(String(objective?.id ?? ""))
      || coordMatch(objective, entity)
      || (selection?.kind === "objective" && String(objective?.id ?? "") === String(entity?.id ?? ""))
  ));
  const relatedAirfields = airfields.filter((airfield) => (
    String(airfield?.id ?? "") === String(entity?.id ?? "")
      || coordMatch(airfield, entity)
  ));
  const relatedPorts = ports.filter((port) => (
    String(port?.id ?? "") === String(entity?.id ?? "")
      || coordMatch(port, entity)
  ));
  const relatedUnits = units.filter((unit) => (
    locationIds.has(normalizeId(unit?.location_id))
      || coordMatch(unit, entity)
  ));
  const relatedReports = reports.filter((report) => matchingAreas.some((area) => area.id === report?.local_area_id));
  const pressureReasons = matchingAreas.flatMap((area) => (Array.isArray(area?.pressure_reasons) ? area.pressure_reasons : []));

  return {
    matchingAreas,
    relatedObjectives,
    relatedAirfields,
    relatedPorts,
    relatedUnits,
    relatedReports,
    pressureReasons,
    locationIds,
  };
}

function buildLocationSummarySection(selection, entity, context) {
  const typeLabel = selection.kind === "objective"
    ? "Objective"
    : selection.kind === "airfield"
      ? "Airbase"
      : "Port / Supply Node";

  return {
    id: "location-summary",
    group: "Site Overview",
    title: "Location Summary",
    variant: "key-list",
    rows: [
      { label: "Site Type", value: typeLabel },
      { label: "Map Reference", value: formatValue(entity?.id, "Reference unavailable") },
      { label: "Objectives Here", value: context.relatedObjectives.length ? String(context.relatedObjectives.length) : "None exposed" },
      { label: "Infrastructure Here", value: String(context.relatedAirfields.length + context.relatedPorts.length) },
      { label: "Formations Here", value: context.relatedUnits.length ? String(context.relatedUnits.length) : "None exposed" },
    ],
  };
}

function buildObjectiveStatusSection(selection, entity, context) {
  const objective = selection.kind === "objective"
    ? entity
    : context.relatedObjectives[0] ?? null;

  if (!objective) {
    return {
      id: "objective-status",
      group: "Site Overview",
      title: "Objective / Control Status",
      variant: "placeholder",
      body: "No current objective or control status is exposed for this site.",
    };
  }

  return {
    id: "objective-status",
    group: "Site Overview",
    title: "Objective / Control Status",
    variant: "key-list",
    rows: [
      { label: "Objective", value: formatValue(objective.name, "Objective unavailable") },
      { label: "Status", value: objective.state ? humanizeToken(objective.state) : "Unavailable" },
      { label: "Assigned Side", value: objective.side ? humanizeToken(objective.side) : "Unavailable" },
      { label: "Controlled", value: formatBoolean(objective.controlled) },
      { label: "Objective Value", value: objective.value != null ? objective.value : "Unavailable" },
    ],
  };
}

function buildInfrastructureSection(selection, entity, context) {
  const rows = [];

  if (selection.kind === "airfield") {
    rows.push({ label: "Selected Airbase", value: formatValue(entity?.name, "Airfield unavailable") });
  }
  if (selection.kind === "port") {
    rows.push({ label: "Selected Port", value: formatValue(entity?.name, "Port unavailable") });
  }
  if (selection.kind === "objective") {
    context.relatedAirfields.forEach((airfield) => {
      rows.push({ label: `Airbase • ${airfield.name}`, value: "Visible on current shell path" });
    });
    context.relatedPorts.forEach((port) => {
      rows.push({ label: `Port • ${port.name}`, value: "Visible on current shell path" });
    });
  } else {
    context.relatedAirfields
      .filter((airfield) => String(airfield?.id ?? "") !== String(entity?.id ?? ""))
      .forEach((airfield) => {
        rows.push({ label: `Airbase • ${airfield.name}`, value: "Visible on current shell path" });
      });
    context.relatedPorts
      .filter((port) => String(port?.id ?? "") !== String(entity?.id ?? ""))
      .forEach((port) => {
        rows.push({ label: `Port • ${port.name}`, value: "Visible on current shell path" });
      });
    if (selection.kind === "airfield") {
      rows.push({ label: "Condition", value: "Not exposed on current shell path" });
    }
    if (selection.kind === "port") {
      rows.push({ label: "Condition", value: "Not exposed on current shell path" });
    }
  }

  if (!rows.length) {
    return {
      id: "infrastructure",
      group: "Site Overview",
      title: "Infrastructure / Condition",
      variant: "placeholder",
      body: "No additional airfield, port, bridge, or logistics detail is exposed for this site.",
    };
  }

  return {
    id: "infrastructure",
    group: "Site Overview",
    title: "Infrastructure / Condition",
    variant: "key-list",
    rows,
  };
}

function buildOperationalSignificanceSection(selection, context) {
  const leadArea = context.matchingAreas[0] ?? null;
  const locSummary = context.relatedUnits.length
    ? context.relatedUnits.map((unit) => summarizeLocState(unit)).join(" • ")
    : "No nearby LOC state is exposed from collocated formations.";
  const supportRelevance = selection.kind === "airfield"
    ? "Airfield anchor is visible on the current shell path."
    : selection.kind === "port"
      ? "Port or supply anchor is visible on the current shell path."
      : context.relatedAirfields.length
        ? `${context.relatedAirfields.length} airfield link${context.relatedAirfields.length === 1 ? "" : "s"} exposed.`
        : context.relatedPorts.length
          ? `${context.relatedPorts.length} port link${context.relatedPorts.length === 1 ? "" : "s"} exposed.`
          : "No support link is exposed for this site.";

  return {
    id: "operational-significance",
    group: "Operational Context",
    title: "Operational Significance",
    variant: "key-list",
    rows: [
      { label: "Pressure Area", value: leadArea ? `${leadArea.label} • ${humanizeToken(leadArea.kind)}` : "No local pressure area exposed" },
      { label: "Current Pressure", value: context.pressureReasons.length ? context.pressureReasons.map((reason) => humanizePressureReason(reason)).join(" • ") : "No pressure signal exposed" },
      { label: "LOC Nearby", value: locSummary },
      { label: "Support Link", value: supportRelevance },
    ],
  };
}

function buildUnitsPresentSection(context) {
  if (!context.relatedUnits.length) {
    return {
      id: "units-present",
      group: "Operational Context",
      title: "Units / Assets Present",
      variant: "placeholder",
      body: "No collocated formation is currently exposed at this site.",
    };
  }

  const rows = context.relatedUnits
    .slice()
    .sort((left, right) => String(left?.name ?? "").localeCompare(String(right?.name ?? "")))
    .map((unit) => ({
      label: unit.name || unit.id || "Formation",
      value: summarizeUnitPresence(unit),
    }));

  return {
    id: "units-present",
    group: "Operational Context",
    title: "Units / Assets Present",
    variant: "key-list",
    rows,
  };
}

function buildNotesSection(context) {
  const rows = [];

  context.relatedReports.slice(0, 3).forEach((report) => {
    rows.push({
      label: report.title || "Report",
      value: formatValue(report.summary, "No current report summary"),
    });
  });

  if (!rows.length && context.pressureReasons.length) {
    rows.push({
      label: "Immediate Concern",
      value: context.pressureReasons.map((reason) => humanizePressureReason(reason)).join(" • "),
    });
  }

  if (!rows.length) {
    return {
      id: "notes",
      group: "Operational Context",
      title: "Notes / Warnings",
      variant: "placeholder",
      body: "No current report, warning, or local concern is attached to this site.",
    };
  }

  return {
    id: "notes",
    group: "Operational Context",
    title: "Notes / Warnings",
    variant: "key-list",
    rows,
  };
}

function buildEntitySubtitle(selection, entity, context) {
  const typeLabel = selection.kind === "objective"
    ? "Objective"
    : selection.kind === "airfield"
      ? "Airbase"
      : "Port / Supply Node";
  const multiEntity = context.relatedUnits.length + context.relatedAirfields.length + context.relatedPorts.length + context.relatedObjectives.length > 1;
  return multiEntity ? `${typeLabel} • Multi-entity location` : typeLabel;
}

function buildEntitySummary(selection, entity, context) {
  const objective = selection.kind === "objective"
    ? entity
    : context.relatedObjectives[0] ?? null;
  const typeLabel = selection.kind === "objective"
    ? "Objective"
    : selection.kind === "airfield"
      ? "Airbase"
      : "Port / Supply Node";
  const leadConcern = context.pressureReasons.length
    ? humanizePressureReason(context.pressureReasons[0])
    : "No current pressure cue exposed";

  return {
    title: "Current Summary",
    rows: [
      { label: "Site Type", value: typeLabel },
      { label: "Control", value: objective?.state ? humanizeToken(objective.state) : "No control status exposed" },
      { label: "Forces Here", value: context.relatedUnits.length ? String(context.relatedUnits.length) : "None exposed" },
      { label: "Immediate Concern", value: leadConcern },
    ],
    note: objective?.name
      ? `${objective.name} is the primary authored objective context currently tied to this site.`
      : "Summary is limited to current site linkage, exposed formations, and local pressure records only.",
  };
}

function summarizeEntitySelection(snapshot, selection, entity) {
  const context = buildContext(snapshot, selection, entity);
  return {
    selected: true,
    header: {
      eyebrow: "Inspector",
      title: entity?.name || entity?.id || "Selected location",
      subtitle: buildEntitySubtitle(selection, entity, context),
      loc: null,
    },
    summary: buildEntitySummary(selection, entity, context),
    commanderScreen: null,
    sections: [
      buildLocationSummarySection(selection, entity, context),
      buildObjectiveStatusSection(selection, entity, context),
      buildInfrastructureSection(selection, entity, context),
      buildOperationalSignificanceSection(selection, context),
      buildUnitsPresentSection(context),
      buildNotesSection(context),
    ],
  };
}

export function summarizeInspector(snapshot, selection, options = {}) {
  if (!selection || typeof selection !== "object") {
    return buildEmptyInspector();
  }

  if (selection.kind === "unit") {
    const unit = (Array.isArray(snapshot?.units) ? snapshot.units : []).find((row) => String(row?.id ?? "") === String(selection.id ?? "")) ?? null;
    return summarizeUnitInspector(unit, options);
  }

  const collection = selection.kind === "objective"
    ? snapshot?.objectives
    : selection.kind === "airfield"
      ? snapshot?.airfields
      : snapshot?.ports;
  const entity = (Array.isArray(collection) ? collection : []).find((row) => String(row?.id ?? "") === String(selection.id ?? "")) ?? null;
  if (!entity) {
    return {
      ...buildEmptyInspector(),
      selected: true,
      header: {
        eyebrow: "Inspector",
        title: "Selection unavailable",
        subtitle: "The selected map object is no longer exposed on the current shell path.",
        loc: null,
      },
      summary: null,
      sections: [],
    };
  }

  return summarizeEntitySelection(snapshot, selection, entity);
}
