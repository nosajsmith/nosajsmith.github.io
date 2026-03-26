import {
  buildObjectiveDisplayName,
  formatReportPresentation,
  humanizeCampaignStatus,
  humanizeSideLabel,
} from "../../lib/view_snapshot.js";
import { humanizeObjectiveState } from "./map_scene.js";

export function summarizeScore(scoreBySide = {}) {
  return Object.entries(scoreBySide).map(([side, value]) => ({
    side,
    label: humanizeSideLabel(side),
    value,
  }));
}

export function summarizeObjectives(objectives = []) {
  const rows = Array.isArray(objectives) ? objectives : [];
  const grouped = new Map();
  const duplicateNames = new Set(
    rows
      .map((objective) => String(objective?.name ?? "").trim())
      .filter(Boolean)
      .filter((name, index, items) => items.indexOf(name) !== index),
  );

  for (const objective of rows) {
    const state = humanizeObjectiveState(objective?.state);
    grouped.set(state, (grouped.get(state) || 0) + 1);
  }

  return {
    total: rows.length,
    byState: Array.from(grouped.entries()).map(([state, count]) => ({ state, count })),
    key: rows.slice(0, 4).map((objective) => ({
      id: String(objective?.id || ""),
      name: buildObjectiveDisplayName(objective, duplicateNames),
      state: humanizeObjectiveState(objective?.state),
      side: objective?.side ? humanizeSideLabel(objective.side) : null,
    })),
  };
}

export function summarizeReports(reports = { pending_count: null, recent: [] }) {
  const recent = orderRecentReports(reports?.recent);
  const newest = recent.length ? recent[0] : null;
  const latest = newest
    ? {
        ...formatReportPresentation(newest),
        severity: String(newest.severity || "info").toUpperCase(),
      }
    : null;

  return {
    pending: reports?.pending_count ?? null,
    latest,
  };
}

export function orderRecentReports(recent = []) {
  return Array.isArray(recent) ? [...recent].reverse() : [];
}

export function summarizeCampaign(snapshot) {
  return {
    status: humanizeCampaignStatus(snapshot?.campaign?.status),
    turn: snapshot?.time?.turn ?? null,
    timeRemaining: snapshot?.time?.time_remaining_hours ?? null,
    winTarget: snapshot?.campaign?.win_score ?? null,
  };
}
