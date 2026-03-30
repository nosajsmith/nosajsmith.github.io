import {
  containsLegacySouthPacificText,
  formatReportPresentation,
  humanizeIntent,
  humanizeToken,
  isKoreaScenarioContext,
} from "../../lib/view_snapshot.js";
import { orderRecentReports } from "./dashboard_summary.js";

const DEMO_82ND_AIRBORNE = {
  id: "demo-82nd-airborne",
  title: "82nd Airborne Situation Report",
  kind: "Demo Example",
  showKind: true,
  summary: "82nd Airborne reports scattered but organized drop elements consolidating near the objective corridor.",
  body:
    "Frontend demo example for visual evaluation only. 82nd Airborne elements report consolidation underway, perimeter control improving, and immediate resupply requests pending by drop zone conditions.",
  severity: "info",
  timeLabel: "Demo presentation example",
  senderLabel: "82nd Airborne",
  insigniaCode: "AA",
  isDemo: true,
};

function normalizeSeverity(value) {
  const raw = String(value ?? "").trim().toLowerCase();
  if (raw === "warning" || raw === "warn" || raw === "error" || raw === "critical") {
    return "warning";
  }
  return "info";
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function uniqueStrings(items, limit = 4) {
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
  if (typeof value === "string") {
    const direct = normalizeString(value);
    if (direct) {
      return humanizeToken(direct);
    }
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return "";
  }

  for (const key of ["name", "label", "title", "summary", "objective_id", "target_objective", "target_location_id", "id"]) {
    const candidate = normalizeString(value[key]);
    if (candidate) {
      return humanizeToken(candidate);
    }
  }

  return "";
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

function normalizeInput(input) {
  const snapshot = input && typeof input === "object" && !Array.isArray(input) && (
    Object.prototype.hasOwnProperty.call(input, "reports")
      || Object.prototype.hasOwnProperty.call(input, "bai_report")
      || Object.prototype.hasOwnProperty.call(input, "ai")
      || Object.prototype.hasOwnProperty.call(input, "units")
      || Object.prototype.hasOwnProperty.call(input, "pressure")
  )
    ? input
    : null;

  return {
    snapshot,
    reports: snapshot ? snapshot.reports : input,
  };
}

function deriveInsigniaCode(senderLabel, kind) {
  const sender = String(senderLabel ?? "").trim();
  if (/^bai$/i.test(sender)) {
    return "AI";
  }
  if (/^g[1-9]$/i.test(sender) || /^engine$/i.test(sender)) {
    return sender.toUpperCase();
  }
  if (sender) {
    const initials = sender
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("");
    if (initials) {
      return initials;
    }
  }
  const kindLabel = String(kind ?? "").trim();
  return kindLabel ? kindLabel.slice(0, 2).toUpperCase() : null;
}

function unitsById(snapshot) {
  const rows = Array.isArray(snapshot?.units) ? snapshot.units : [];
  return new Map(rows.map((unit) => [normalizeString(unit?.id), unit]));
}

function formatOrderSummary(order, unitIndex) {
  const unit = unitIndex.get(normalizeString(order?.unit_id));
  const unitName = normalizeString(unit?.name) || normalizeString(order?.unit_id) || "Formation";
  const action = normalizeString(order?.action || order?.type);
  const target = labelFromValue(order?.target_location_id)
    || labelFromValue(order?.objective_id)
    || labelFromValue(order?.target_unit_id);
  const rationale = normalizeString(order?.metadata?.evaluation?.dominant_reason)
    || normalizeString(order?.rationale);
  const parts = [unitName, action ? humanizeToken(action).toLowerCase() : "", target]
    .filter(Boolean)
    .join(" ")
    .trim();

  if (parts && rationale) {
    return `${parts} — ${rationale}`;
  }
  return parts || rationale;
}

function formatTrackedOperationSummary(operation, unitIndex) {
  if (!operation || typeof operation !== "object") {
    return "";
  }
  const seedUnit = unitIndex.get(normalizeString(operation?.seedUnitId));
  const participant = Array.isArray(operation?.participants) ? operation.participants[0] : null;
  const participantName = normalizeString(participant?.name);
  const unitName = normalizeString(seedUnit?.name) || participantName || normalizeString(operation?.name) || "Formation";
  const action = normalizeString(operation?.commandIntent || operation?.type);
  const target = normalizeString(operation?.targetLabel) || normalizeString(operation?.objectiveName);
  const source = operation?.source === "map_shortcut" ? "Player order" : "Planned operation";
  return [source, unitName, action ? humanizeToken(action).toLowerCase() : "", target].filter(Boolean).join(" ").trim();
}

function summarizeForceChanges(snapshot) {
  const forceChanges = snapshot?.force_changes && typeof snapshot.force_changes === "object"
    ? snapshot.force_changes
    : null;
  if (!forceChanges) {
    return [];
  }

  const reinforcements = Array.isArray(forceChanges.reinforcements) ? forceChanges.reinforcements : [];
  const withdrawals = Array.isArray(forceChanges.withdrawals) ? forceChanges.withdrawals : [];
  const rows = [];

  if (reinforcements.length) {
    const lead = reinforcements[0];
    const leadName = labelFromValue(lead) || "Reinforcement";
    rows.push(
      reinforcements.length === 1
        ? `${leadName} enters the theater picture.`
        : `${leadName} and ${reinforcements.length - 1} more reinforcement${reinforcements.length - 1 === 1 ? "" : "s"} enter the theater picture.`,
    );
  }

  if (withdrawals.length) {
    const lead = withdrawals[0];
    const leadName = labelFromValue(lead) || "Withdrawal";
    rows.push(
      withdrawals.length === 1
        ? `${leadName} begins withdrawal or redeployment.`
        : `${leadName} and ${withdrawals.length - 1} more formation${withdrawals.length - 1 === 1 ? "" : "s"} begin withdrawal or redeployment.`,
    );
  }

  return rows;
}

function summarizeLocalPressure(snapshot) {
  const areas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
  const labels = [...new Set(
    areas
      .map((area) => normalizeString(area?.label))
      .filter(Boolean),
  )];
  const reasons = [...new Set(
    areas.flatMap((area) => Array.isArray(area?.pressure_reasons) ? area.pressure_reasons.map((reason) => normalizeString(reason)) : [])
      .filter(Boolean),
  )];

  let summary = normalizeString(snapshot?.pressure?.summary);
  if (!summary) {
    if (labels.length === 1) {
      summary = `${labels[0]} remains the active sector.`;
    } else if (labels.length === 2) {
      summary = `${labels[0]} and ${labels[1]} remain active sectors.`;
    } else if (labels.length > 2) {
      summary = `${labels[0]}, ${labels[1]}, and ${labels.length - 2} more sectors remain active.`;
    }
  }

  return {
    labels,
    reasons,
    summary,
  };
}

function buildSyntheticMessages(snapshot, operations = []) {
  if (!snapshot || typeof snapshot !== "object") {
    return [];
  }

  const messages = [];
  const koreaScenario = isKoreaScenarioContext(snapshot);
  const report = snapshot?.bai_report && typeof snapshot.bai_report === "object" ? snapshot.bai_report : null;
  const timeValue = numericValue(snapshot?.time?.current_hours);
  const turnValue = numericValue(snapshot?.time?.turn);
  const timeLabel = formatCommunicationTime(timeValue);
  const objectiveRaw = labelFromValue(report?.main_objective);
  const objective = koreaScenario && containsLegacySouthPacificText(objectiveRaw) ? "" : objectiveRaw;
  const operationRaw = labelFromValue(report?.chosen_operation);
  const operation = koreaScenario && containsLegacySouthPacificText(operationRaw) ? "" : operationRaw;
  const posture = normalizeString(report?.posture) ? humanizeToken(report.posture) : "";
  const reserveLevel = formatReserveLevel(report?.reserve_level);
  const rawIntent = normalizeString(snapshot?.ai?.last_intent);
  const aiIntent = rawIntent && !(koreaScenario && containsLegacySouthPacificText(rawIntent))
    ? humanizeIntent(rawIntent)
    : "";
  const summaryLineRaw = Array.isArray(report?.summary_lines)
    ? report.summary_lines.map((entry) => normalizeString(entry)).find(Boolean)
    : "";
  const summaryLine = koreaScenario && containsLegacySouthPacificText(summaryLineRaw) ? "" : summaryLineRaw;
  const unitIndex = unitsById(snapshot);
  const unitOrders = Array.isArray(report?.unit_orders)
    ? report.unit_orders.map((order) => formatOrderSummary(order, unitIndex)).filter(Boolean)
    : [];
  const tacticalIntents = Array.isArray(report?.tactical_intents)
    ? report.tactical_intents
        .map((intent) => formatOrderSummary(intent, unitIndex))
        .filter(Boolean)
    : [];
  const aiActionRows = [...new Set([...unitOrders, ...tacticalIntents])];
  const trackedOperationOrders = Array.isArray(operations)
    ? operations
        .map((operation) => formatTrackedOperationSummary(operation, unitIndex))
        .filter(Boolean)
    : [];
  const localPressure = summarizeLocalPressure(snapshot);
  const forceChangeRows = summarizeForceChanges(snapshot);

  if (posture || operation || objective || summaryLine || aiIntent || aiActionRows.length || localPressure.summary || forceChangeRows.length) {
    const summary = uniqueStrings([
      posture ? `${posture} posture` : "",
      operation ? `${operation}${objective ? ` toward ${objective}` : ""}` : objective ? `Objective ${objective}` : "",
      aiActionRows[0],
      localPressure.summary,
      reserveLevel ? `${reserveLevel} retained` : "",
    ], 4).join(". ");
    const bodySections = [
      summaryLine,
      aiIntent,
      aiActionRows.length ? `Orders and activity:\n${aiActionRows.map((row) => `- ${row}`).join("\n")}` : "",
      localPressure.summary ? `Pressure:\n${localPressure.summary}` : "",
      localPressure.labels[0]
        ? `${localPressure.labels[0]} remains the lead named pressure area${localPressure.reasons[0] ? ` with ${humanizeToken(localPressure.reasons[0]).toLowerCase()}` : ""}.`
        : "",
      forceChangeRows.length ? `Force changes:\n${forceChangeRows.map((row) => `- ${row}`).join("\n")}` : "",
      reserveLevel ? `Reserve posture: ${reserveLevel}.` : "",
    ].filter(Boolean);
    messages.push({
      id: `synthetic-ai-${turnValue ?? "now"}-${normalizeString(operation || objective || aiIntent || posture).replace(/\s+/g, "-") || "update"}`,
      title: "AI Command Update",
      kind: "AI Update",
      showKind: true,
      summary: summary || summaryLine || aiIntent || "AI command activity recorded.",
      body: bodySections.join("\n\n") || "AI activity is present, but no richer command narrative is exposed.",
      severity: snapshot?.ai?.budget_exceeded ? "warning" : "info",
      timeLabel,
      senderLabel: "BAI",
      insigniaCode: "AI",
      isDemo: false,
    });
  }

  if (trackedOperationOrders.length) {
    messages.push({
      id: `synthetic-player-orders-${turnValue ?? "now"}-${trackedOperationOrders.length}`,
      title: "Player Order Update",
      kind: "Order Flow",
      showKind: true,
      summary: trackedOperationOrders.slice(0, 2).join(" • "),
      body: trackedOperationOrders.join("\n"),
      severity: "info",
      timeLabel,
      senderLabel: "Operations Staff",
      insigniaCode: "OP",
      isDemo: false,
    });
  }

  if (unitOrders.length || tacticalIntents.length) {
    const orderRows = unitOrders.length ? unitOrders : tacticalIntents;
    messages.push({
      id: `synthetic-orders-${turnValue ?? "now"}-${orderRows.length}`,
      title: "Orders Issued",
      kind: "Order Flow",
      showKind: true,
      summary: orderRows.slice(0, 2).join(" • "),
      body: orderRows.join("\n"),
      severity: "info",
      timeLabel,
      senderLabel: "Operations Staff",
      insigniaCode: "OP",
      isDemo: false,
    });
  }

  const criticalUnits = (Array.isArray(snapshot?.units) ? snapshot.units : []).filter((unit) => {
    const locState = normalizeString(unit?.inspector?.operational_state?.loc?.state).toLowerCase();
    const supplyPct = numericValue(unit?.inspector?.supply?.supply_pct);
    const supplyDays = numericValue(unit?.inspector?.supply?.supply_days_current);
    return locState === "broken" || (supplyPct != null && supplyPct < 40) || (supplyDays != null && supplyDays < 2);
  });
  const pressureSummary = localPressure.summary;
  const leadArea = localPressure.labels[0];
  const leadReason = localPressure.reasons[0] ? humanizeToken(localPressure.reasons[0]).toLowerCase() : "";
  if (pressureSummary || criticalUnits.length || leadArea) {
    const leadCritical = criticalUnits[0];
    const criticalLine = leadCritical
      ? `${normalizeString(leadCritical?.name) || "Formation"} reports strained supply or LOC.`
      : "";
    messages.push({
      id: `synthetic-risk-${turnValue ?? "now"}-${criticalUnits.length}`,
      title: "Operational Pressure",
      kind: "Risk",
      showKind: true,
      summary: [pressureSummary, criticalLine].filter(Boolean).join(" ") || "Operational pressure remains active.",
      body: [
        pressureSummary,
        leadArea ? `${leadArea} is the lead named pressure area${leadReason ? ` with ${leadReason}` : ""}.` : "",
        criticalLine,
        criticalUnits.length > 1 ? `${criticalUnits.length} formations currently show critical sustainment or LOC warnings.` : "",
      ].filter(Boolean).join("\n\n"),
      severity: "warning",
      timeLabel,
      senderLabel: "Theater Staff",
      insigniaCode: "TS",
      isDemo: false,
    });
  }

  return messages;
}

function dedupeMessages(messages) {
  const seen = new Set();
  return messages.filter((message) => {
    const key = `${normalizeString(message?.title).toLowerCase()}|${normalizeString(message?.summary).toLowerCase()}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function formatCommunicationTime(value) {
  return value != null ? `Recorded at T+${value}h` : "Time unavailable";
}

export function summarizeCommunications(input = { pending_count: null, recent: [] }, operations = []) {
  const { snapshot, reports } = normalizeInput(input);
  const koreaScenario = isKoreaScenarioContext(snapshot);
  const ordered = orderRecentReports(reports?.recent).filter((report) => {
    if (!koreaScenario) {
      return true;
    }
    const reportText = [
      report?.title,
      report?.summary,
      report?.body,
      report?.sender_label,
    ].filter(Boolean).join(" ");
    return !containsLegacySouthPacificText(reportText);
  });
  const reportMessages = ordered.map((report) => {
    const display = formatReportPresentation(report);
    const summary = display.summary || "No message body is available on the current shell path.";
    const senderLabel = typeof report?.sender_label === "string" && report.sender_label.trim() ? report.sender_label.trim() : null;
    const body = typeof report?.body === "string" && report.body.trim() ? report.body.trim() : summary;

    return {
      id: String(report?.id ?? ""),
      title: display.title,
      kind: display.kind,
      showKind: display.showKind,
      summary,
      body,
      severity: normalizeSeverity(report?.severity),
      timeLabel: formatCommunicationTime(report?.time ?? null),
      senderLabel,
      insigniaCode: deriveInsigniaCode(senderLabel, display.kind),
      isDemo: false,
    };
  });
  const syntheticMessages = buildSyntheticMessages(snapshot, operations);
  const messages = dedupeMessages([...syntheticMessages, ...reportMessages]);

  return {
    pending: reports?.pending_count ?? null,
    latest: messages[0] ?? null,
    history: messages,
    demoExample: messages.length || snapshot ? null : DEMO_82ND_AIRBORNE,
  };
}
