import { summarizeCampaign, summarizeObjectives, summarizeReports, summarizeScore } from "./dashboard_summary.js";
import { summarizeOperationsBoard } from "./operations_board.js";

function countVisibleUnits(units = []) {
  return units.filter((unit) => Number.isFinite(unit?.x) && Number.isFinite(unit?.y)).length;
}

export function summarizeDetailDrawer(snapshot) {
  const campaign = summarizeCampaign(snapshot);
  const objectives = summarizeObjectives(snapshot?.objectives);
  const reports = summarizeReports(snapshot?.reports);
  const score = summarizeScore(snapshot?.campaign?.score_by_side);
  const operations = summarizeOperationsBoard(snapshot);
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const visibleUnits = countVisibleUnits(units);
  const heldObjectives = Object.values(snapshot?.campaign?.objective_state ?? {}).filter(Boolean).length;

  return {
    campaign,
    objectives,
    reports,
    score,
    operations,
    mapContext: {
      scenarioId: snapshot?.scenario?.id ?? "unknown",
      visibleUnits,
      hiddenTrackedUnits: Math.max(units.length - visibleUnits, 0),
      heldObjectives,
      totalUnits: units.length,
    },
    staff: {
      summary: snapshot?.staff?.summary ?? "Staff summary unavailable.",
      load: snapshot?.staff?.load ?? null,
    },
  };
}
