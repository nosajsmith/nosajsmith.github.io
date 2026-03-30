import mockGreaseBoard from "../../data/mockGreaseBoard.js";
import {
  containsLegacySouthPacificText,
  humanizeIntent,
  humanizePressureReason,
  humanizeToken,
  isKoreaScenarioContext,
} from "../../lib/view_snapshot.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => normalizeString(entry))
    .filter(Boolean);
}

function uniqueList(items, limit = 4) {
  const seen = new Set();
  const rows = [];

  for (const item of items) {
    const text = normalizeString(item);
    if (!text) {
      continue;
    }
    const key = text.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    rows.push(text);
    if (rows.length >= limit) {
      break;
    }
  }

  return rows;
}

function numericValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function labelFromValue(value) {
  const direct = normalizeString(value);
  if (direct) {
    return direct;
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return "";
  }

  for (const key of ["name", "label", "title", "summary", "main_objective", "target_objective", "objective_id", "id"]) {
    const candidate = normalizeString(value[key]);
    if (candidate) {
      return candidate;
    }
  }

  return "";
}

function normalizeGreaseBoardPayload(raw) {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  return {
    turn: normalizeString(raw.turn) || null,
    objective: normalizeString(raw.objective) || null,
    front_status: normalizeString(raw.front_status) || null,
    supply_status: normalizeString(raw.supply_status) || null,
    main_effort: normalizeString(raw.main_effort) || null,
    orders: normalizeList(raw.orders),
    alerts: normalizeList(raw.alerts),
    staff_notes: normalizeString(raw.staff_notes) || null,
  };
}

function sanitizeGreaseText(snapshot, value) {
  const text = normalizeString(value);
  if (!text) {
    return "";
  }
  return isKoreaScenarioContext(snapshot) && containsLegacySouthPacificText(text) ? "" : text;
}

function sanitizeGreaseList(snapshot, items) {
  if (!Array.isArray(items)) {
    return [];
  }
  return items
    .map((entry) => normalizeString(entry))
    .filter(Boolean)
    .filter((entry) => !(isKoreaScenarioContext(snapshot) && containsLegacySouthPacificText(entry)));
}

function sanitizeGreaseBoardPayload(snapshot, payload) {
  if (!payload) {
    return null;
  }
  return {
    ...payload,
    objective: sanitizeGreaseText(snapshot, payload.objective),
    main_effort: sanitizeGreaseText(snapshot, payload.main_effort),
    orders: sanitizeGreaseList(snapshot, payload.orders),
    alerts: sanitizeGreaseList(snapshot, payload.alerts),
    staff_notes: sanitizeGreaseText(snapshot, payload.staff_notes),
  };
}

function mergeGreaseBoardPayload(base, overrides) {
  if (!base && !overrides) {
    return null;
  }

  const next = {
    turn: overrides?.turn || base?.turn || "",
    objective: overrides?.objective || base?.objective || "",
    front_status: overrides?.front_status || base?.front_status || "",
    supply_status: overrides?.supply_status || base?.supply_status || "",
    main_effort: overrides?.main_effort || base?.main_effort || "",
    orders: uniqueList([...(overrides?.orders || []), ...(base?.orders || [])], 4),
    alerts: uniqueList([...(overrides?.alerts || []), ...(base?.alerts || [])], 4),
    staff_notes: overrides?.staff_notes || base?.staff_notes || undefined,
  };

  if (!next.turn || !next.objective || !next.front_status || !next.supply_status || !next.main_effort) {
    return null;
  }

  return next;
}

function looksLikeInchon(snapshot) {
  const scenarioId = normalizeString(snapshot?.scenario?.id).toLowerCase();
  const scenarioName = normalizeString(snapshot?.scenario?.name).toLowerCase();
  return scenarioId.includes("inchon") || scenarioName.includes("inchon");
}

function pickObjective(snapshot) {
  const suppressLegacy = isKoreaScenarioContext(snapshot);
  const reportObjective = labelFromValue(snapshot?.bai_report?.main_objective);
  if (reportObjective && !(suppressLegacy && containsLegacySouthPacificText(reportObjective))) {
    return reportObjective;
  }

  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const ranked = [...objectives].sort((left, right) => {
    const leftContested = /contested/i.test(String(left?.state ?? "")) || left?.controlled === false ? 1 : 0;
    const rightContested = /contested/i.test(String(right?.state ?? "")) || right?.controlled === false ? 1 : 0;
    if (rightContested !== leftContested) {
      return rightContested - leftContested;
    }
    return (numericValue(right?.value) ?? 0) - (numericValue(left?.value) ?? 0);
  });

  return normalizeString(ranked[0]?.name) || "OBJECTIVE PENDING";
}

function formatTurn(snapshot) {
  const parts = [];
  const turn = numericValue(snapshot?.time?.turn);
  const hours = numericValue(snapshot?.time?.current_hours);
  const phase = normalizeString(snapshot?.time?.phase);

  if (turn != null) {
    parts.push(`TURN ${Math.round(turn)}`);
  }
  if (hours != null) {
    parts.push(`T+${Math.round(hours)}H`);
  }
  if (phase) {
    parts.push(humanizeToken(phase).toUpperCase());
  }

  return parts.join(" — ") || "TURN STATUS UNAVAILABLE";
}

function deriveFrontStatus(snapshot) {
  const localAreas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
  const contestedObjectives = (Array.isArray(snapshot?.objectives) ? snapshot.objectives : []).filter((objective) => (
    /contested/i.test(String(objective?.state ?? ""))
      || objective?.controlled === false
  ));
  const brokenLocUnits = (Array.isArray(snapshot?.units) ? snapshot.units : []).filter((unit) => (
    normalizeString(unit?.inspector?.operational_state?.loc?.state).toLowerCase() === "broken"
  ));

  if (brokenLocUnits.length >= 2) {
    return "LINE FRAGILE";
  }
  if (snapshot?.pressure?.active || contestedObjectives.length || localAreas.length) {
    return "CONTESTED";
  }
  if ((Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : []).some((report) => String(report?.severity ?? "").toLowerCase() === "warning")) {
    return "PRESSURED";
  }
  if ((Array.isArray(snapshot?.units) ? snapshot.units : []).length) {
    return "HOLDING";
  }
  return "STATUS UNCLEAR";
}

function deriveSupplyStatus(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  if (!units.length) {
    return "SUPPLY PICTURE THIN";
  }

  let critical = 0;
  let strained = 0;

  for (const unit of units) {
    const supplyPct = numericValue(unit?.inspector?.supply?.supply_pct);
    const supplyDays = numericValue(unit?.inspector?.supply?.supply_days_current);
    const locState = normalizeString(unit?.inspector?.operational_state?.loc?.state).toLowerCase();

    if (locState === "broken" || (supplyPct != null && supplyPct < 40) || (supplyDays != null && supplyDays < 2)) {
      critical += 1;
      continue;
    }
    if (locState === "threatened" || (supplyPct != null && supplyPct < 65) || (supplyDays != null && supplyDays < 4)) {
      strained += 1;
    }
  }

  if (critical) {
    return critical === 1 ? "CRITICAL FORWARD SUPPLY" : `${critical} FORMATIONS CRITICAL`;
  }
  if (strained) {
    return strained === 1 ? "STRAINED FORWARD SUPPLY" : `${strained} FORMATIONS STRAINED`;
  }
  return "FORWARD STOCKS STABLE";
}

function formatReserveLevel(value) {
  const numeric = numericValue(value);
  if (numeric == null) {
    return "";
  }
  if (numeric > 0 && numeric <= 1) {
    return `${Math.round(numeric * 100)}% reserve`;
  }
  return `${Math.round(numeric)} reserve`;
}

function presentTargetLabel(value) {
  const label = labelFromValue(value);
  return label ? humanizeToken(label) : "";
}

function formatOrderRow(order, unitsById) {
  const unitName = normalizeString(unitsById.get(normalizeString(order?.unit_id))?.name) || normalizeString(order?.unit_id);
  const action = normalizeString(order?.action || order?.type);
  const target = presentTargetLabel(order?.target_location_id) || presentTargetLabel(order?.objective_id) || presentTargetLabel(order?.target_unit_id);
  const rationale = normalizeString(order?.metadata?.evaluation?.dominant_reason) || normalizeString(order?.rationale);

  const prefix = [unitName, action ? humanizeToken(action).toLowerCase() : "", target ? target : ""]
    .filter(Boolean)
    .join(" ")
    .trim();

  if (prefix && rationale) {
    return `${prefix} — ${rationale}`;
  }
  return prefix || rationale;
}

function formatTrackedOrderRow(operation) {
  if (!operation || typeof operation !== "object") {
    return "";
  }

  const explicitName = normalizeString(operation?.name);
  const status = normalizeString(operation?.status);
  if (explicitName && !Array.isArray(operation?.participants)) {
    return status ? `${explicitName} (${humanizeToken(status)})` : explicitName;
  }

  const unitName = Array.isArray(operation?.participants) && operation.participants[0]?.name
    ? normalizeString(operation.participants[0].name)
    : explicitName;
  const action = normalizeString(operation?.commandIntent);
  const target = normalizeString(operation?.targetLabel) || normalizeString(operation?.objectiveName);

  return [unitName, action ? humanizeToken(action).toLowerCase() : "", target, status ? `(${status})` : ""]
    .filter(Boolean)
    .join(" ")
    .trim();
}

function buildOrders(snapshot, operations = []) {
  const suppressLegacy = isKoreaScenarioContext(snapshot);
  const report = snapshot?.bai_report;
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const unitsById = new Map(units.map((unit) => [normalizeString(unit?.id), unit]));
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const trackedRows = trackedOperations.available
    ? trackedOperations.rows
        .map((operation) => formatTrackedOrderRow(operation))
        .filter(Boolean)
        .filter((row) => !(suppressLegacy && containsLegacySouthPacificText(row)))
    : [];

  if (trackedRows.length) {
    return uniqueList(trackedRows, 4);
  }

  const unitOrders = Array.isArray(report?.unit_orders)
    ? report.unit_orders
        .map((order) => formatOrderRow(order, unitsById))
        .filter(Boolean)
        .filter((row) => !(suppressLegacy && containsLegacySouthPacificText(row)))
    : [];
  if (unitOrders.length) {
    return uniqueList(unitOrders, 4);
  }

  const tacticalIntents = Array.isArray(report?.tactical_intents)
    ? report.tactical_intents
        .map((intent) => {
          const unitName = normalizeString(unitsById.get(normalizeString(intent?.unit_id))?.name) || normalizeString(intent?.unit_id);
          const action = normalizeString(intent?.action || intent?.type);
          const target = presentTargetLabel(intent?.objective_id) || presentTargetLabel(intent?.target_location_id);
          return [unitName, action ? humanizeToken(action).toLowerCase() : "", target].filter(Boolean).join(" ").trim();
        })
        .filter(Boolean)
        .filter((row) => !(suppressLegacy && containsLegacySouthPacificText(row)))
    : [];
  if (tacticalIntents.length) {
    return uniqueList(tacticalIntents, 4);
  }

  const liveOrderReports = (Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : [])
    .filter((reportRow) => /order|operation|ai_report/i.test(String(reportRow?.kind ?? "")) || /orders?/i.test(String(reportRow?.title ?? "")))
    .map((reportRow) => normalizeString(reportRow?.summary))
    .filter(Boolean)
    .filter((row) => !(suppressLegacy && containsLegacySouthPacificText(row)));
  if (liveOrderReports.length) {
    return uniqueList(liveOrderReports, 4);
  }

  const lastIntent = normalizeString(snapshot?.ai?.last_intent);
  if (lastIntent && !(suppressLegacy && containsLegacySouthPacificText(lastIntent))) {
    return [humanizeIntent(lastIntent)];
  }

  return [];
}

function buildAlerts(snapshot) {
  const suppressLegacy = isKoreaScenarioContext(snapshot);
  const alertRows = [];
  const reports = Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : [];
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const localAreas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];

  for (const report of reports) {
    if (String(report?.severity ?? "").toLowerCase() === "warning") {
      alertRows.push(normalizeString(report?.summary) || normalizeString(report?.title));
    }
  }

  const criticalSupplyUnits = units.filter((unit) => {
    const supplyPct = numericValue(unit?.inspector?.supply?.supply_pct);
    const supplyDays = numericValue(unit?.inspector?.supply?.supply_days_current);
    const locState = normalizeString(unit?.inspector?.operational_state?.loc?.state).toLowerCase();
    return locState === "broken" || (supplyPct != null && supplyPct < 40) || (supplyDays != null && supplyDays < 2);
  });
  for (const unit of criticalSupplyUnits) {
    alertRows.push(`${normalizeString(unit?.name) || "Formation"} supply or LOC critical.`);
  }

  const fatiguedUnits = units.filter((unit) => numericValue(unit?.inspector?.operational_state?.fatigue) >= 35);
  for (const unit of fatiguedUnits) {
    alertRows.push(`${normalizeString(unit?.name) || "Formation"} fatigue rising.`);
  }

  const pressureReasons = Array.isArray(snapshot?.pressure?.reasons) ? snapshot.pressure.reasons : [];
  for (const reason of pressureReasons) {
    alertRows.push(humanizePressureReason(reason));
  }

  for (const area of localAreas) {
    const label = normalizeString(area?.label);
    const state = normalizeString(area?.defensive_preparation?.state);
    const fortification = normalizeString(area?.defensive_preparation?.fortification_state);
    if (label && state) {
      alertRows.push(`${label} ${humanizeToken(state).toLowerCase()}.`);
    }
    if (label && fortification) {
      alertRows.push(`${label} ${humanizeToken(fortification).toLowerCase()}.`);
    }
  }

  return uniqueList(
    alertRows.filter((entry) => !(suppressLegacy && containsLegacySouthPacificText(entry))),
    4,
  );
}

function buildStaffNote(snapshot, objective, mainEffort, operations = []) {
  const suppressLegacy = isKoreaScenarioContext(snapshot);
  const report = snapshot?.bai_report;
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const staffSummary = normalizeString(snapshot?.staff?.summary);
  if (staffSummary && !(suppressLegacy && containsLegacySouthPacificText(staffSummary))) {
    return staffSummary;
  }
  const summaryLine = Array.isArray(report?.summary_lines)
    ? report.summary_lines.map((entry) => normalizeString(entry)).find(Boolean)
    : "";
  if (summaryLine && !(suppressLegacy && containsLegacySouthPacificText(summaryLine))) {
    return summaryLine;
  }

  const reasonLine = uniqueList([
    ...(Array.isArray(report?.hold_reason_summaries) ? report.hold_reason_summaries : []),
    ...(Array.isArray(report?.attack_reason_summaries) ? report.attack_reason_summaries : []),
  ].filter((entry) => !(suppressLegacy && containsLegacySouthPacificText(entry))), 1)[0];
  if (reasonLine) {
    return reasonLine;
  }

  if (trackedOperations.available && trackedOperations.lead?.statusDetail) {
    return trackedOperations.lead.statusDetail;
  }

  const reserveLevel = formatReserveLevel(report?.reserve_level);
  const posture = normalizeString(report?.posture) ? humanizeToken(report.posture).toUpperCase() : "";
  if (objective && mainEffort && reserveLevel && posture) {
    return `${posture} posture around ${objective}. ${mainEffort} remains the main effort. ${reserveLevel} retained for contingency commitment.`;
  }
  if (objective && mainEffort && reserveLevel) {
    return `${mainEffort} remains the main effort toward ${objective}. ${reserveLevel} retained for contingency commitment.`;
  }
  if (objective && mainEffort && posture) {
    return `${posture} posture around ${objective}. ${mainEffort} remains the main effort.`;
  }
  if (objective && mainEffort) {
    return `${mainEffort} remains the main effort toward ${objective}.`;
  }

  const latestReport = (Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : [])
    .map((reportRow) => normalizeString(reportRow?.summary))
    .find((entry) => entry && !(suppressLegacy && containsLegacySouthPacificText(entry)));
  return latestReport || undefined;
}

function deriveGreaseBoardPayload(snapshot, operations = []) {
  const suppressLegacy = isKoreaScenarioContext(snapshot);
  const hasLiveState = Boolean(
    snapshot?.bai_report
      || numericValue(snapshot?.time?.turn) != null
      || (Array.isArray(snapshot?.reports?.recent) && snapshot.reports.recent.length)
      || (Array.isArray(snapshot?.units) && snapshot.units.length)
      || (Array.isArray(snapshot?.objectives) && snapshot.objectives.length)
      || normalizeString(snapshot?.ai?.last_intent),
  );

  if (!hasLiveState) {
    return null;
  }

  const objective = pickObjective(snapshot);
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const trackedLead = trackedOperations.available ? trackedOperations.lead : null;
  const operationLabel = sanitizeGreaseText(snapshot, labelFromValue(snapshot?.bai_report?.chosen_operation));
  const aiLastIntent = normalizeString(snapshot?.ai?.last_intent);
  const mainEffort = trackedLead?.name
    || operationLabel
    || (aiLastIntent && !(suppressLegacy && containsLegacySouthPacificText(aiLastIntent)) ? humanizeIntent(snapshot.ai.last_intent) : "")
    || objective;

  return {
    turn: formatTurn(snapshot),
    objective,
    front_status: deriveFrontStatus(snapshot),
    supply_status: deriveSupplyStatus(snapshot),
    main_effort: mainEffort || "MAIN EFFORT PENDING",
    orders: buildOrders(snapshot, operations),
    alerts: buildAlerts(snapshot),
    staff_notes: buildStaffNote(snapshot, objective, mainEffort, operations),
  };
}

export function summarizeGreaseBoard(snapshot, operations = []) {
  const authoritativePayload = sanitizeGreaseBoardPayload(snapshot, normalizeGreaseBoardPayload(snapshot?.grease_board));
  const derivedPayload = sanitizeGreaseBoardPayload(snapshot, deriveGreaseBoardPayload(snapshot, operations));
  const livePayload = mergeGreaseBoardPayload(derivedPayload, authoritativePayload);

  if (livePayload) {
    return {
      available: true,
      data: livePayload,
      source: authoritativePayload ? "snapshot" : "derived",
      note: authoritativePayload
        ? null
        : "Derived from live scenario, AI, and command-feed state on the current shell path.",
    };
  }

  if (looksLikeInchon(snapshot)) {
    return {
      available: true,
      data: mockGreaseBoard,
      source: "mock",
      note: "Demo grease-board brief until bridge payloads are exposed on the shell path.",
    };
  }

  return {
    available: false,
    data: null,
    source: "unavailable",
    note: "Grease Board is waiting on either live command-state signals or a scenario-authored brief payload.",
  };
}
