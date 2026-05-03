import {
  buildObjectiveDisplayName,
  formatReportPresentation,
  humanizeCampaignStatus,
  humanizePressureReason,
  humanizeSideLabel,
} from "../../lib/view_snapshot.js";
import { humanizeObjectiveState } from "./map_scene.js";

function toObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function toText(value) {
  return String(value ?? "").trim();
}

function objectiveTruthKey(objective) {
  const explicit = toText(objective?.objective_truth_key).toUpperCase();
  if (explicit) {
    return explicit;
  }
  const side = toText(objective?.side).toUpperCase();
  const location = toText(objective?.location_id ?? objective?.id ?? objective?.name).toUpperCase();
  return side && location ? `${side}:${location}` : "";
}

function objectiveState(objective, snapshot = null) {
  const truthKey = objectiveTruthKey(objective);
  const truth = truthKey ? toObject(snapshot?.objective_truth?.[truthKey]) : {};
  const truthState = toText(truth.status)
    || toText(objective?.truth_state)
    || toText(objective?.objective_status);
  const controllerSide = toText(truth.controller_side) || toText(objective?.controller_side);

  if (truthState.toLowerCase() === "held" && controllerSide) {
    return `held_${controllerSide.toLowerCase()}`;
  }
  return truthState
    || toText(objective?.state)
    || "unknown";
}

function pressureRows(snapshotOrPressure = {}) {
  const pressure = snapshotOrPressure?.pressure && typeof snapshotOrPressure.pressure === "object"
    ? snapshotOrPressure.pressure
    : snapshotOrPressure;
  const objectivePressure = toObject(pressure?.objective_pressure);
  const byObjective = Object.keys(toObject(pressure?.by_objective)).length
    ? toObject(pressure.by_objective)
    : toObject(objectivePressure.by_objective);

  return Object.entries(byObjective).map(([key, row]) => {
    const pressureRow = toObject(row);
    return {
      key,
      state: toText(pressureRow.pressure_state),
      score: toNumber(pressureRow.pressure_score),
      locationId: toText(pressureRow.location_id) || key.split(":")[1] || key,
      objectiveStatus: toText(pressureRow.objective_status),
    };
  });
}

export function summarizeScore(scoreBySide = {}) {
  const source = scoreBySide?.score?.score_by_side
    ?? scoreBySide?.campaign?.score_by_side
    ?? scoreBySide;
  return Object.entries(source ?? {}).map(([side, value]) => ({
    side,
    label: humanizeSideLabel(side),
    value,
  }));
}

export function summarizeObjectives(objectives = [], snapshot = null) {
  const rows = Array.isArray(objectives) ? objectives : [];
  const grouped = new Map();
  const duplicateNames = new Set(
    rows
      .map((objective) => String(objective?.name ?? "").trim())
      .filter(Boolean)
      .filter((name, index, items) => items.indexOf(name) !== index),
  );

  for (const objective of rows) {
    const state = humanizeObjectiveState(objectiveState(objective, snapshot));
    grouped.set(state, (grouped.get(state) || 0) + 1);
  }

  return {
    total: rows.length,
    byState: Array.from(grouped.entries()).map(([state, count]) => ({ state, count })),
    key: rows.slice(0, 4).map((objective) => ({
      id: String(objective?.id || ""),
      name: buildObjectiveDisplayName(objective, duplicateNames),
      state: humanizeObjectiveState(objectiveState(objective, snapshot)),
      side: objective?.side ? humanizeSideLabel(objective.side) : null,
    })),
  };
}

export function summarizePressure(snapshotOrPressure = {}) {
  const snapshot = snapshotOrPressure?.pressure && typeof snapshotOrPressure.pressure === "object"
    ? snapshotOrPressure
    : null;
  const pressure = snapshot?.pressure ?? snapshotOrPressure ?? {};
  const objectivePressure = toObject(pressure.objective_pressure);
  const rows = pressureRows(snapshotOrPressure);
  const activeRows = rows.filter((row) => (row.state && row.state !== "none") || (row.score != null && row.score > 0));
  const reasons = Array.isArray(pressure.reasons)
    ? pressure.reasons
    : Array.isArray(objectivePressure.reasons)
      ? objectivePressure.reasons
      : [];
  const totalPressureScore = toNumber(pressure.total_pressure_score) ?? toNumber(objectivePressure.total_pressure_score);
  let summary = toText(snapshot?.read_first?.pressure_summary)
    || toText(pressure.summary);

  if (!summary && activeRows.length === 1) {
    const row = activeRows[0];
    summary = `${row.locationId} pressure ${row.state || "active"}.`;
  } else if (!summary && activeRows.length > 1) {
    summary = `${activeRows.length} objectives show supply-aware pressure.`;
  } else if (!summary && totalPressureScore != null && totalPressureScore > 0) {
    summary = "Supply-aware objective pressure is active.";
  }

  return {
    active: Boolean(pressure.active) || activeRows.length > 0 || Boolean(totalPressureScore && totalPressureScore > 0),
    summary: summary || null,
    reasons: reasons.map((reason) => humanizePressureReason(reason)),
    objectiveRows: rows,
    totalPressureScore,
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
    status: humanizeCampaignStatus(snapshot?.campaign?.status ?? snapshot?.read_first?.campaign_status),
    turn: snapshot?.time?.turn ?? snapshot?.read_first?.turn ?? null,
    timeRemaining: snapshot?.time?.time_remaining_hours ?? null,
    winTarget: snapshot?.score?.win_score ?? snapshot?.campaign?.win_score ?? null,
  };
}
