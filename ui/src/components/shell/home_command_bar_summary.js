import { pressureFallback } from "../../lib/view_snapshot.js";
import { summarizeCampaign, summarizeObjectives, summarizeReports } from "./dashboard_summary.js";
import { summarizeLogisticsBranch } from "./logistics_branch_summary.js";
import { summarizeAirOperations } from "./air_operations_summary.js";
import { summarizeNavalOperations } from "./naval_operations_summary.js";
import { summarizeIntelligenceBranch } from "./intelligence_branch_summary.js";
import { summarizeHendersonPressureBoard } from "./henderson_pressure_board_summary.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function formatPendingDispatchLabel(pending) {
  if (pending == null) {
    return "Dispatch queue unavailable";
  }
  if (pending === 0) {
    return "No pending dispatches";
  }
  return pluralize(pending, "pending dispatch", "pending dispatches");
}

function sentenceParts(...parts) {
  return parts
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(". ");
}

export function summarizeHomeCommandBar(snapshot, operations = []) {
  const campaign = summarizeCampaign(snapshot);
  const objectives = summarizeObjectives(snapshot?.objectives);
  const reports = summarizeReports(snapshot?.reports);
  const logistics = summarizeLogisticsBranch(snapshot);
  const air = summarizeAirOperations(snapshot);
  const naval = summarizeNavalOperations(snapshot);
  const intelligence = summarizeIntelligenceBranch(snapshot);
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const localBattle = summarizeHendersonPressureBoard(snapshot, operations);
  const operationsOverview = localBattle.operationsOverview;
  const turnLabel = campaign.turn ?? "Unknown";
  const timeRemainingLabel = campaign.timeRemaining != null ? `${campaign.timeRemaining}h remaining` : "Time remaining unavailable";
  const theatreDetail = trackedOperations.lead
    ? `Turn ${turnLabel} • ${timeRemainingLabel} • ${trackedOperations.lead.status}`
    : `Turn ${turnLabel} • ${timeRemainingLabel}`;

  return {
    theatre: {
      status: campaign.status,
      turn: turnLabel,
      timeRemaining: timeRemainingLabel,
      detail: theatreDetail,
    },
    operations: {
      status: operationsOverview.activeOperation,
      detail: sentenceParts(operationsOverview.objectiveSituation, operationsOverview.immediateConcern),
    },
    objectives: {
      total: objectives.total,
      topState: objectives.byState[0] ? `${objectives.byState[0].state} ${objectives.byState[0].count}` : "No objectives tracked",
    },
    pressureStaff: {
      pressure: pressureFallback(snapshot?.pressure ?? { summary: null, reasons: [] }),
      staff: snapshot?.staff?.summary ?? "Staff summary unavailable",
    },
    air: {
      label: air.overview.formationsTracked
        ? `${pluralize(air.overview.formationsTracked, "air formation")} tracked`
        : "Air picture incomplete",
      detail: air.overview.formationsTracked
        ? "Built from exposed air-capable formations on the current shell path."
        : air.overview.statusLine,
    },
    naval: {
      label: naval.overview.formationsTracked
        ? `${pluralize(naval.overview.formationsTracked, "naval formation")} tracked`
        : "Naval picture incomplete",
      detail: naval.overview.formationsTracked
        ? "Built from exposed fleets and task forces on the current shell path."
        : naval.overview.statusLine,
    },
    logistics: {
      label: logistics.overview.supplyAverageDays != null
        ? `${logistics.overview.supplyAverageDays.toFixed(1)}d sustainment`
        : "Logistics picture incomplete",
      detail: logistics.overview.supplyAverageDays != null
        ? `${logistics.overview.supplyAverageDays.toFixed(1)} days average sustainment at current tempo.`
        : logistics.overview.supportHeadline,
    },
    intelligence: {
      label: formatPendingDispatchLabel(intelligence.overview.pending),
      detail: (intelligence.overview.pending ?? 0) > 0 || intelligence.overview.latestTitle !== "No current dispatch"
        ? "Built from current dispatch traffic and exposed pressure cues."
        : intelligence.overview.statusLine,
    },
    reports: {
      pending: reports.pending ?? "Unknown",
      latest: reports.latest?.title ?? "No recent report headline",
    },
  };
}
