import { humanizeToken } from "../../lib/view_snapshot.js";
import { sanitizeTrackedOperations, summarizeTrackedOperations } from "./operations_planner.js";
import { summarizeLandForcesModule } from "./theater_dashboard_summary.js";

const GROUND_ROLE_LABELS = {
  main_effort: "Main Effort",
  support: "Support",
  flank: "Flank",
  screen: "Screen",
  reserve: "Reserve",
  none: "Unassigned",
};

function normalizeText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactList(items, limit = 2) {
  const values = (Array.isArray(items) ? items : [])
    .map((item) => String(item ?? "").trim())
    .filter(Boolean);
  if (!values.length) {
    return null;
  }
  if (values.length <= limit) {
    return values.join(", ");
  }
  return `${values.slice(0, limit).join(", ")} +${values.length - limit} more`;
}

function numericValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const match = String(value ?? "").match(/(\d+(?:\.\d+)?)/);
  return match ? Number.parseFloat(match[1]) : null;
}

function isLandUnit(unit) {
  const rawKind = String(unit?.kind ?? "").trim().toLowerCase();
  return !rawKind.includes("air")
    && !rawKind.includes("naval")
    && !rawKind.includes("sea")
    && !rawKind.includes("logistics")
    && !rawKind.includes("supply")
    && !rawKind.includes("transport");
}

function landUnits(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units.filter(isLandUnit) : [];
  const alliedUnits = units.filter((unit) => String(unit?.side ?? "").toUpperCase() === "ALLIED");
  return alliedUnits.length ? alliedUnits : units;
}

function landHeadquarters(snapshot) {
  return landUnits(snapshot).filter((unit) => String(unit?.unit_type ?? "").toUpperCase() === "HEADQUARTERS");
}

function landFormations(snapshot) {
  return landUnits(snapshot).filter((unit) => String(unit?.unit_type ?? "").toUpperCase() !== "HEADQUARTERS");
}

function extractFormationState(unit) {
  const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
  const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
  const supply = inspector?.supply && typeof inspector.supply === "object" ? inspector.supply : {};
  const command = inspector?.command && typeof inspector.command === "object" ? inspector.command : {};
  const attachmentsSupport = inspector?.attachments_support && typeof inspector.attachments_support === "object" ? inspector.attachments_support : {};
  const orders = inspector?.orders && typeof inspector.orders === "object" ? inspector.orders : {};

  const hqId = typeof command?.hq_unit_id === "string" && command.hq_unit_id.trim() ? command.hq_unit_id.trim() : null;
  const superiorName = typeof command?.superior?.name === "string" && command.superior.name.trim()
    ? command.superior.name.trim()
    : (typeof command?.superior?.id === "string" && command.superior.id.trim() ? command.superior.id.trim() : null);

  return {
    id: String(unit?.id ?? ""),
    name: String(unit?.name ?? "Formation"),
    hqId,
    commandLabel: superiorName || hqId || "No HQ linkage exposed",
    commander: typeof command?.commander === "string" && command.commander.trim() ? command.commander.trim() : null,
    readiness: numericValue(operational?.readiness ?? unit?.readiness),
    fatigue: numericValue(operational?.fatigue),
    posture: typeof operational?.posture === "string" && operational.posture.trim() ? operational.posture.trim() : null,
    orderAction: typeof orders?.action === "string" && orders.action.trim() ? orders.action.trim() : null,
    orderStatus: typeof orders?.lifecycle_state === "string" && orders.lifecycle_state.trim()
      ? orders.lifecycle_state.trim()
      : (typeof orders?.status === "string" && orders.status.trim() ? orders.status.trim() : null),
    locState: normalizeText(operational?.loc?.state),
    locLabel: typeof operational?.loc?.label === "string" && operational.loc.label.trim()
      ? operational.loc.label.trim()
      : (typeof operational?.loc?.state === "string" && operational.loc.state.trim() ? `LOC ${humanizeToken(operational.loc.state)}` : "LOC unavailable"),
    locDetail: typeof operational?.loc?.detail === "string" && operational.loc.detail.trim() ? operational.loc.detail.trim() : "LOC detail unavailable",
    supplyPct: numericValue(supply?.supply_pct),
    supplyDays: numericValue(supply?.supply_days_current ?? supply?.supply_display ?? unit?.supply),
    support: Array.isArray(attachmentsSupport?.support) ? attachmentsSupport.support.map((item) => String(item ?? "").trim()).filter(Boolean) : [],
    attachments: Array.isArray(attachmentsSupport?.attachments) ? attachmentsSupport.attachments.map((item) => String(item ?? "").trim()).filter(Boolean) : [],
    detached: Array.isArray(attachmentsSupport?.detached) ? attachmentsSupport.detached.map((item) => String(item ?? "").trim()).filter(Boolean) : [],
  };
}

function formatReadiness(state) {
  return state.readiness != null ? `${Math.round(state.readiness)} readiness` : "Readiness not exposed";
}

function formatFatigue(state) {
  return state.fatigue != null ? `${Math.round(state.fatigue)} fatigue` : "Fatigue not exposed";
}

function formatSupply(state) {
  if (state.supplyDays != null) {
    return `${state.supplyDays.toFixed(1)} days`;
  }
  if (state.supplyPct != null) {
    return `${Math.round(state.supplyPct)}% supply`;
  }
  return "Supply not exposed";
}

function formatPosture(state) {
  return state.posture ? humanizeToken(state.posture) : "Posture unavailable";
}

function formatOrder(state) {
  if (state.orderAction && state.orderStatus) {
    return `${humanizeToken(state.orderAction)} • ${humanizeToken(state.orderStatus)}`;
  }
  if (state.orderAction) {
    return humanizeToken(state.orderAction);
  }
  if (state.orderStatus) {
    return humanizeToken(state.orderStatus);
  }
  return "Orders not exposed";
}

function locAlertRank(state) {
  if (state.locState === "broken") {
    return 0;
  }
  if (state.locState === "threatened") {
    return 1;
  }
  return 2;
}

function readinessRank(state) {
  const readiness = state.readiness != null ? state.readiness : Number.POSITIVE_INFINITY;
  const fatigue = state.fatigue != null ? state.fatigue : Number.NEGATIVE_INFINITY;
  return [locAlertRank(state), readiness, -fatigue];
}

function operationStatusRank(status) {
  const normalized = normalizeText(status);
  if (normalized === "stalled") {
    return 0;
  }
  if (normalized === "engaged") {
    return 1;
  }
  if (normalized === "securing objective") {
    return 2;
  }
  if (normalized === "moving to start line") {
    return 3;
  }
  if (normalized === "assembling") {
    return 4;
  }
  if (normalized === "ready") {
    return 5;
  }
  if (normalized === "complete") {
    return 6;
  }
  if (normalized === "aborted") {
    return 7;
  }
  return 8;
}

function buildOobSection(states, hqUnits) {
  if (!states.length) {
    return {
      headline: "No higher-headquarters linkage is exposed on the current shell path.",
      groups: [],
    };
  }

  const hqById = new Map(
    hqUnits
      .filter((unit) => typeof unit?.id === "string" && unit.id.trim())
      .map((unit) => [unit.id.trim(), String(unit?.name ?? unit.id).trim()]),
  );
  const groups = new Map();

  states.forEach((state) => {
    const key = state.hqId || state.commandLabel;
    const current = groups.get(key) ?? {
      id: key,
      label: hqById.get(state.hqId || "") || state.commandLabel,
      note: state.hqId
        ? (hqById.has(state.hqId)
          ? `${hqById.get(state.hqId)} is visible on the current shell path.`
          : `${state.hqId} is referenced, but the HQ unit is not separately visible.`)
        : "No authoritative HQ link is exposed for this command grouping.",
      formations: [],
    };
    current.formations.push({
      id: state.id,
      name: state.name,
      commander: state.commander ?? "Commander not exposed",
      posture: formatPosture(state),
      order: formatOrder(state),
      readiness: formatReadiness(state),
      loc: state.locLabel,
      support: compactList([...state.support, ...state.attachments], 2) ?? "No support exposure",
    });
    groups.set(key, current);
  });

  return {
    headline: `${groups.size} command grouping${groups.size === 1 ? "" : "s"} visible on the current shell path.`,
    groups: Array.from(groups.values())
      .map((group) => ({
        ...group,
        formations: group.formations.sort((left, right) => left.name.localeCompare(right.name)),
      }))
      .sort((left, right) => right.formations.length - left.formations.length || left.label.localeCompare(right.label)),
  };
}

function buildSupportAssignments(states) {
  const rows = states
    .filter((state) => state.support.length || state.attachments.length || state.detached.length)
    .map((state) => ({
      id: state.id,
      name: state.name,
      assignment: compactList(state.support.length ? state.support : state.attachments, 2) ?? "Detached elements only",
      note: state.detached.length
        ? `Detached ${compactList(state.detached, 2) ?? "elements"} • ${state.commandLabel}`
        : `${formatPosture(state)} • ${state.commandLabel}`,
    }))
    .sort((left, right) => left.name.localeCompare(right.name));

  return {
    headline: rows.length
      ? `${rows.length} formation${rows.length === 1 ? "" : "s"} with attached or detached support exposure.`
      : "No support battalion assignments are exposed on the current shell path.",
    rows,
  };
}

function buildLocAlerts(states) {
  const rows = states
    .filter((state) => state.locState === "broken" || state.locState === "threatened")
    .sort((left, right) => {
      const leftRank = locAlertRank(left);
      const rightRank = locAlertRank(right);
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.name.localeCompare(right.name);
    })
    .map((state) => ({
      id: state.id,
      name: state.name,
      status: state.locLabel,
      detail: `${state.locDetail} • ${formatSupply(state)}`,
      note: `${formatPosture(state)} • ${state.commandLabel}`,
    }));

  return {
    headline: rows.length
      ? `${rows.length} threatened or broken LOC alert${rows.length === 1 ? "" : "s"} visible.`
      : "No threatened or broken LOC state is exposed on current formations.",
    rows,
  };
}

function buildReadinessPosture(states) {
  const rows = [...states]
    .sort((left, right) => {
      const leftScore = readinessRank(left);
      const rightScore = readinessRank(right);
      for (let index = 0; index < leftScore.length; index += 1) {
        if (leftScore[index] !== rightScore[index]) {
          return leftScore[index] - rightScore[index];
        }
      }
      return left.name.localeCompare(right.name);
    })
    .map((state) => ({
      id: state.id,
      name: state.name,
      posture: formatPosture(state),
      order: formatOrder(state),
      condition: `${formatReadiness(state)} • ${formatFatigue(state)}`,
      sustainment: `${formatSupply(state)} • ${state.locLabel}`,
      note: state.commander ? `${state.commander} • ${state.commandLabel}` : state.commandLabel,
    }));

  return {
    headline: rows.length
      ? `${rows.length} visible formation${rows.length === 1 ? "" : "s"} with posture and condition exposure.`
      : "No readiness or posture rollup is exposed on the current shell path.",
    rows,
  };
}

function buildOperationParticipation(snapshot, operations, states) {
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const trackedRowsById = new Map(trackedOperations.rows.map((row) => [row.id, row]));
  const sanitizedOperations = sanitizeTrackedOperations(snapshot, operations);
  const rows = [];

  states.forEach((state) => {
    sanitizedOperations.forEach((operation) => {
      const participant = operation.participants.find((item) => item.unitId === state.id);
      if (!participant) {
        return;
      }
      const tracked = trackedRowsById.get(operation.id) ?? null;
      rows.push({
        id: `${operation.id}:${state.id}`,
        name: state.name,
        operation: operation.name,
        role: GROUND_ROLE_LABELS[participant.roleId] ?? humanizeToken(participant.roleId),
        status: tracked?.status ?? "Status unavailable",
        objective: tracked?.objective ?? operation.objectiveName,
        support: tracked?.supportAssigned?.join(" • ") ?? "No support assigned",
        note: tracked?.statusDetail ?? "Operation lifecycle state is unavailable on the current shell path.",
      });
    });
  });

  rows.sort((left, right) => {
    const rankDiff = operationStatusRank(left.status) - operationStatusRank(right.status);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    return left.name.localeCompare(right.name);
  });

  return {
    headline: rows.length
      ? `${rows.length} visible formation assignment${rows.length === 1 ? "" : "s"} across ${trackedOperations.total} tracked operation${trackedOperations.total === 1 ? "" : "s"}.`
      : trackedOperations.note,
    rows,
    note: trackedOperations.note,
  };
}

export function summarizeLandOperations(snapshot, operations = []) {
  const overview = summarizeLandForcesModule(Array.isArray(snapshot?.units) ? snapshot.units : []);
  const formations = landFormations(snapshot).map(extractFormationState);
  const headquarters = landHeadquarters(snapshot);

  return {
    available: formations.length > 0,
    note: overview.note,
    overview,
    oob: buildOobSection(formations, headquarters),
    supportAssignments: buildSupportAssignments(formations),
    locAlerts: buildLocAlerts(formations),
    readinessPosture: buildReadinessPosture(formations),
    operations: buildOperationParticipation(snapshot, operations, formations),
  };
}
