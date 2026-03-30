import {
  buildObjectiveDisplayName,
  humanizeCampaignStatus,
  humanizeIntent,
  humanizePressureReason,
} from "../../lib/view_snapshot.js";
import { summarizeCommunications } from "./communications_summary.js";
import { humanizeObjectiveState } from "./map_scene.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

export function summarizeOperationsBoard(snapshot, operations = []) {
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const duplicateNames = new Set(
    objectives
      .map((objective) => String(objective?.name ?? "").trim())
      .filter(Boolean)
      .filter((name, index, items) => items.indexOf(name) !== index),
  );
  const communications = summarizeCommunications(snapshot, operations);
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
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
  };
}
