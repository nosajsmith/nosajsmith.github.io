import {
  buildObjectiveDisplayName,
  formatReportPresentation,
  humanizeCampaignStatus,
  humanizeIntent,
  humanizePressureReason,
} from "../../lib/view_snapshot.js";
import { orderRecentReports } from "./dashboard_summary.js";
import { humanizeObjectiveState } from "./map_scene.js";

export function summarizeOperationsBoard(snapshot) {
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const duplicateNames = new Set(
    objectives
      .map((objective) => String(objective?.name ?? "").trim())
      .filter(Boolean)
      .filter((name, index, items) => items.indexOf(name) !== index),
  );
  const reports = orderRecentReports(snapshot?.reports?.recent).slice(0, 3);
  const pressureReasons = Array.isArray(snapshot?.pressure?.reasons)
    ? snapshot.pressure.reasons.map((reason) => humanizePressureReason(reason))
    : [];

  return {
    situation: {
      status: humanizeCampaignStatus(snapshot?.campaign?.status),
      turn: snapshot?.time?.turn ?? null,
      timeRemaining: snapshot?.time?.time_remaining_hours ?? null,
      pendingReports: snapshot?.reports?.pending_count ?? null,
    },
    objectives: objectives.slice(0, 3).map((objective) => ({
      id: String(objective?.id || ""),
      name: buildObjectiveDisplayName(objective, duplicateNames),
      state: humanizeObjectiveState(objective?.state),
      side: objective?.side ? String(objective.side) : null,
    })),
    pressure: {
      summary: snapshot?.pressure?.summary ? String(snapshot.pressure.summary) : null,
      reasons: pressureReasons,
    },
    aiIntent: humanizeIntent(snapshot?.ai?.last_intent),
    developments: reports.map((report) => {
      const display = formatReportPresentation(report);
      return {
        id: String(report?.id || ""),
        title: display.title,
        summary: display.summary,
        severity: String(report?.severity || "info").toUpperCase(),
      };
    }),
  };
}
