import {
  containsLegacySouthPacificText,
  humanizeIntent,
  humanizeToken,
  isKoreaScenarioContext,
  pressureFallback,
} from "../../lib/view_snapshot.js";
import { summarizeCampaign, summarizeObjectives, summarizePressure, summarizeReports } from "./dashboard_summary.js";
import { summarizeLocalSustainment, summarizeLogisticsBranch } from "./logistics_branch_summary.js";
import { summarizeAirOperations, summarizeLocalAirSupport } from "./air_operations_summary.js";
import { summarizeLocalNavalSupport, summarizeNavalOperations } from "./naval_operations_summary.js";
import { summarizeIntelligenceBranch } from "./intelligence_branch_summary.js";
import { summarizeHendersonPressureBoard } from "./henderson_pressure_board_summary.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function formatPendingDispatchLabel(pending, historyCount = 0) {
  if (pending == null) {
    return historyCount
      ? `${historyCount} live dispatch${historyCount === 1 ? "" : "es"}`
      : "Dispatch queue unavailable";
  }
  if (pending === 0) {
    return "No pending dispatches";
  }
  return pluralize(pending, "pending dispatch", "pending dispatches");
}

function sentenceParts(...parts) {
  return parts
    .map((value) => String(value ?? "").trim().replace(/[.]+$/, ""))
    .filter(Boolean)
    .join(". ");
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function numericValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const raw = String(value ?? "").trim();
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
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

  for (const key of ["name", "label", "title", "summary", "objective_id", "target_objective", "id"]) {
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

export function summarizeHomeCommandBar(snapshot, operations = []) {
  const koreaScenario = isKoreaScenarioContext(snapshot);
  const campaign = summarizeCampaign(snapshot);
  const objectives = summarizeObjectives(snapshot?.objectives);
  const pressure = summarizePressure(snapshot);
  const reports = summarizeReports(snapshot?.reports);
  const logistics = summarizeLogisticsBranch(snapshot);
  const localSustainment = summarizeLocalSustainment(snapshot);
  const air = summarizeAirOperations(snapshot);
  const localAir = summarizeLocalAirSupport(snapshot);
  const naval = summarizeNavalOperations(snapshot);
  const localNaval = summarizeLocalNavalSupport(snapshot);
  const intelligence = summarizeIntelligenceBranch(snapshot, operations);
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const localBattle = summarizeHendersonPressureBoard(snapshot, operations);
  const operationsOverview = localBattle.operationsOverview;
  const turnLabel = campaign.turn ?? "Unknown";
  const timeRemainingLabel = campaign.timeRemaining != null ? `${campaign.timeRemaining}h remaining` : "Time remaining unavailable";
  const chosenOperationRaw = labelFromValue(snapshot?.bai_report?.chosen_operation);
  const mainObjectiveRaw = labelFromValue(snapshot?.bai_report?.main_objective);
  const readFirstObjectiveRaw = normalizeString(snapshot?.read_first?.key_objective);
  const chosenOperation = koreaScenario && containsLegacySouthPacificText(chosenOperationRaw) ? "" : chosenOperationRaw;
  const readFirstObjective = koreaScenario && containsLegacySouthPacificText(readFirstObjectiveRaw) ? "" : readFirstObjectiveRaw;
  const mainObjective = (
    readFirstObjective
    || (koreaScenario && containsLegacySouthPacificText(mainObjectiveRaw)
      ? ""
      : mainObjectiveRaw)
  ) || objectives.key[0]?.name || "";
  const pressureSummary = pressure.summary ?? pressureFallback(snapshot?.pressure ?? { summary: null, reasons: [] });
  const reserveLevel = formatReserveLevel(snapshot?.bai_report?.reserve_level);
  const aiOrderCount = Array.isArray(snapshot?.bai_report?.unit_orders) ? snapshot.bai_report.unit_orders.length : 0;
  const rawIntent = normalizeString(snapshot?.ai?.last_intent);
  const aiIntent = rawIntent && !(koreaScenario && containsLegacySouthPacificText(rawIntent))
    ? humanizeIntent(rawIntent)
    : "";
  const theatreDetail = trackedOperations.lead
    ? `Turn ${turnLabel} • ${timeRemainingLabel} • ${trackedOperations.lead.status}`
    : `Turn ${turnLabel} • ${timeRemainingLabel}`;
  const airFormationDetail = air.overview.formationsTracked
    ? `${pluralize(air.overview.formationsTracked, "air formation")} tracked`
    : "";
  const navalFormationDetail = naval.overview.formationsTracked
    ? `${pluralize(naval.overview.formationsTracked, "naval formation")} tracked`
    : "";
  const latestDispatchLine = normalizeString(intelligence.overview.latestTitle) !== "No current dispatch"
    ? `Latest dispatch ${intelligence.overview.latestTitle}`
    : "";
  const logisticsConcern = localSustainment.concerns?.[0] || logistics.warnings?.[0] || logistics.overview.supportHeadline;
  const airAnchorLabel = normalizeString(localAir.anchorLabel);
  const navalAnchorLabel = normalizeString(localNaval.anchorLabel);
  const liveDispatchCount = intelligence.dispatches.length;

  return {
    theatre: {
      status: campaign.status,
      turn: turnLabel,
      timeRemaining: timeRemainingLabel,
      detail: theatreDetail,
    },
    operations: {
      status: chosenOperation || operationsOverview.activeOperation || aiIntent || "Operations picture incomplete",
      detail: sentenceParts(
        mainObjective ? `Objective ${mainObjective}` : operationsOverview.objectiveSituation,
        aiOrderCount ? `${aiOrderCount} task${aiOrderCount === 1 ? "" : "s"} issued` : "",
        reserveLevel ? `${reserveLevel} retained` : trackedOperations.lead?.statusDetail,
        operationsOverview.immediateConcern || pressureSummary,
      ),
    },
    objectives: {
      total: objectives.total,
      topState: objectives.byState[0] ? `${objectives.byState[0].state} ${objectives.byState[0].count}` : "No objectives tracked",
    },
    pressureStaff: {
      pressure: pressureSummary,
      staff: snapshot?.staff?.summary ?? "Staff summary unavailable",
    },
    air: {
      label: air.overview.formationsTracked
        ? air.overview.readinessAverage != null
          ? `${Math.round(air.overview.readinessAverage)} readiness avg`
          : airFormationDetail
        : air.overview.airfieldsTracked
          ? (airAnchorLabel || "Air context partial")
          : "Air picture incomplete",
      detail: air.overview.formationsTracked
        ? sentenceParts(airFormationDetail, localAir.supportingFormation, localAir.constraint)
        : localAir.available
          ? sentenceParts(
            localAir.availability && localAir.availability !== "Not exposed" ? `${localAir.availability} local air support` : "",
            localAir.note,
            localAir.constraint,
          )
          : air.overview.statusLine,
    },
    naval: {
      label: naval.overview.formationsTracked
        ? naval.overview.supportWindowsTracked
          ? `${naval.overview.supportWindowsTracked} support window${naval.overview.supportWindowsTracked === 1 ? "" : "s"}`
          : navalFormationDetail
        : naval.overview.portsTracked || localNaval.available
          ? (navalAnchorLabel || "Naval context partial")
          : "Naval picture incomplete",
      detail: naval.overview.formationsTracked
        ? sentenceParts(navalFormationDetail, localNaval.supportPosture, localNaval.constraint)
        : localNaval.available
          ? sentenceParts(
            localNaval.availability && localNaval.availability !== "Not exposed" ? `${localNaval.availability} local naval support` : "",
            localNaval.note,
            localNaval.supportPosture,
            localNaval.constraint,
          )
          : naval.overview.statusLine,
    },
    logistics: {
      label: localSustainment.available && localSustainment.status !== "Stable"
        ? `${localSustainment.status} sustainment`
        : logistics.overview.supplyAverageDays != null
          ? `${logistics.overview.supplyAverageDays.toFixed(1)}d sustainment`
          : "Logistics picture incomplete",
      detail: localSustainment.available
        ? sentenceParts(logisticsConcern, localSustainment.atRisk?.[0] ? `${localSustainment.atRisk[0].name} • ${localSustainment.atRisk[0].detail}` : "")
        : logistics.overview.supplyAverageDays != null
          ? `${logistics.overview.supplyAverageDays.toFixed(1)} days average current tempo.`
          : logistics.overview.supportHeadline,
    },
    intelligence: {
      label: formatPendingDispatchLabel(intelligence.overview.pending, liveDispatchCount),
      detail: latestDispatchLine
        ? sentenceParts(latestDispatchLine, intelligence.overview.latestSummary, intelligence.overview.staffSummary)
        : (intelligence.overview.pending ?? 0) > 0 || liveDispatchCount > 0
          ? "Built from current dispatch traffic and exposed pressure cues."
          : intelligence.overview.statusLine,
    },
    reports: {
      pending: reports.pending ?? "Unknown",
      latest: reports.latest?.title ?? "No recent report headline",
    },
  };
}
