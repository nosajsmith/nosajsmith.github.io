import {
  humanizeCampaignStatus,
  humanizeIntent,
  humanizeToken,
} from "../../lib/view_snapshot.js";
import { summarizeCommunications } from "./communications_summary.js";
import { summarizeCampaign, summarizeObjectives, summarizePressure, summarizeScore } from "./dashboard_summary.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

function numericValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatTurnLabel(turn) {
  return turn != null ? `Turn ${turn}` : "Turn unavailable";
}

function formatDayLabel(hours) {
  const value = numericValue(hours);
  return value != null ? `Day ${Math.floor(value / 24) + 1}` : "Day unavailable";
}

function formatHourLabel(hours) {
  const value = numericValue(hours);
  return value != null ? `T+${Math.round(value)}h` : "Time unavailable";
}

function scoreLeader(scoreRows) {
  if (!scoreRows.length) {
    return "Score unavailable";
  }
  const ordered = [...scoreRows].sort((left, right) => Number(right.value ?? 0) - Number(left.value ?? 0));
  const lead = ordered[0];
  const next = ordered[1] ?? null;
  if (!next || Number(lead.value ?? 0) === Number(next.value ?? 0)) {
    return scoreRows.map((row) => `${row.label} ${row.value}`).join(" • ");
  }
  return `${lead.label} leads ${lead.value}-${next.value}`;
}

function summarizeHotspots(pressure) {
  const rows = Array.isArray(pressure.objectiveRows) ? pressure.objectiveRows : [];
  return [...rows]
    .sort((left, right) => {
      const leftActive = (left.state && left.state !== "none") || (left.score != null && left.score > 0) ? 1 : 0;
      const rightActive = (right.state && right.state !== "none") || (right.score != null && right.score > 0) ? 1 : 0;
      if (rightActive !== leftActive) {
        return rightActive - leftActive;
      }
      return Number(right.score ?? 0) - Number(left.score ?? 0);
    })
    .slice(0, 4)
    .map((row) => ({
      id: row.key,
      label: row.locationId,
      state: row.state ? humanizeToken(row.state) : "No pressure state",
      score: row.score,
      detail: [
        row.objectiveStatus ? `Objective ${humanizeToken(row.objectiveStatus)}` : "",
        row.score != null ? `Pressure ${row.score}` : "",
      ].filter(Boolean).join(" • ") || "No pressure detail exposed",
    }));
}

export function summarizeOperationsBoard(snapshot, operations = []) {
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const communications = summarizeCommunications(snapshot, operations);
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const objectiveSummary = summarizeObjectives(objectives, snapshot);
  const pressure = summarizePressure(snapshot);
  const campaign = summarizeCampaign(snapshot);
  const scoreRows = summarizeScore(snapshot);
  const turn = snapshot?.time?.turn ?? snapshot?.read_first?.turn ?? null;
  const currentHours = snapshot?.time?.current_hours ?? null;
  const phase = snapshot?.time?.phase ?? snapshot?.read_first?.phase ?? null;

  return {
    identity: {
      scenarioId: snapshot?.scenario?.id ?? "unknown",
      scenarioName: snapshot?.scenario?.name ?? snapshot?.read_first?.scenario ?? "Scenario unavailable",
      operationId: snapshot?.operation?.id ?? null,
      operationName: snapshot?.operation?.name ?? trackedOperations.lead?.name ?? "No approved operation tracked",
      source: snapshot?.contract?.id === "view.snapshot" ? "view.snapshot" : "snapshot-compatible",
    },
    timing: {
      turn,
      turnLabel: formatTurnLabel(turn),
      dayLabel: formatDayLabel(currentHours),
      hourLabel: formatHourLabel(currentHours),
      phaseLabel: phase ? humanizeToken(phase) : "Phase unavailable",
      timeRemainingLabel: campaign.timeRemaining != null ? `${campaign.timeRemaining}h remaining` : "Time remaining unavailable",
    },
    score: {
      status: campaign.status,
      rows: scoreRows,
      leader: scoreLeader(scoreRows),
      winTarget: campaign.winTarget,
    },
    situation: {
      status: humanizeCampaignStatus(snapshot?.campaign?.status),
      turn: snapshot?.time?.turn ?? null,
      timeRemaining: snapshot?.time?.time_remaining_hours ?? null,
      pendingReports: snapshot?.reports?.pending_count ?? null,
    },
    objectives: objectiveSummary.key.slice(0, 3).map((objective) => ({
      id: objective.id,
      name: objective.name,
      state: objective.state,
      side: objective.side ? String(objective.side).toUpperCase() : null,
    })),
    objectiveTruth: {
      total: objectiveSummary.total,
      byState: objectiveSummary.byState,
      key: objectiveSummary.key.slice(0, 5),
    },
    hotspots: summarizeHotspots(pressure),
    pressure: {
      summary: pressure.summary,
      reasons: pressure.reasons,
    },
    aiIntent: humanizeIntent(snapshot?.ai?.last_intent),
    command: {
      aiEnabled: Boolean(snapshot?.ai?.enabled),
      aiIntent: humanizeIntent(snapshot?.ai?.last_intent),
      headline: trackedOperations.lead ? `${trackedOperations.lead.name} • ${trackedOperations.lead.status}` : trackedOperations.headline,
      detail: trackedOperations.lead?.statusDetail ?? trackedOperations.note,
      activeOrders: trackedOperations.available ? trackedOperations.rows.slice(0, 3).map((operation) => ({
        id: operation.id,
        name: operation.name,
        status: operation.status,
        objective: operation.objective,
        detail: operation.statusDetail,
      })) : [],
    },
    operations: {
      available: trackedOperations.available,
      headline: trackedOperations.lead ? `${trackedOperations.lead.name} • ${trackedOperations.lead.status}` : trackedOperations.headline,
      detail: trackedOperations.lead?.statusDetail ?? trackedOperations.note,
    },
    developments: communications.history.slice(0, 3).map((report) => {
      return {
        id: String(report?.id || ""),
        title: String(report?.title || "Dispatch"),
        summary: String(report?.summary || "Operational update."),
        severity: String(report?.severity || "info").toUpperCase(),
      };
    }),
    recent: communications.history.slice(0, 5).map((report) => ({
      id: String(report?.id || ""),
      title: String(report?.title || "Dispatch"),
      summary: String(report?.summary || "Operational update."),
      severity: String(report?.severity || "info").toUpperCase(),
      senderLabel: report?.senderLabel ?? null,
      timeLabel: report?.timeLabel ?? null,
    })),
  };
}
