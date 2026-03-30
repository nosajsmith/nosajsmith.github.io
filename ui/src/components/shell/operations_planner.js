import { humanizeToken } from "../../lib/view_snapshot.js";
import { axialRound } from "../../lib/hex.js";
import { summarizeLocalAirSupport } from "./air_operations_summary.js";
import { buildOperationalOverlayState } from "./map_scene.js";
import { summarizeLocalNavalSupport } from "./naval_operations_summary.js";

export const OPERATION_TYPE_OPTIONS = [
  { id: "offensive", label: "Offensive", available: true, note: "Only active operation type in the v0 prototype planner." },
  { id: "defense", label: "Defense", available: false, note: "Visible for workflow structure only; unavailable in v0." },
  { id: "withdrawal", label: "Withdrawal", available: false, note: "Visible for workflow structure only; unavailable in v0." },
  { id: "amphibious", label: "Amphibious", available: false, note: "Visible for workflow structure only; unavailable in v0." },
  { id: "air", label: "Air", available: false, note: "Visible for workflow structure only; unavailable in v0." },
  { id: "naval", label: "Naval", available: false, note: "Visible for workflow structure only; unavailable in v0." },
  { id: "logistics", label: "Logistics", available: false, note: "Visible for workflow structure only; unavailable in v0." },
];

export const GROUND_ROLE_OPTIONS = [
  { id: "none", label: "Unassigned" },
  { id: "main_effort", label: "Main Effort" },
  { id: "support", label: "Support" },
  { id: "flank", label: "Flank" },
  { id: "screen", label: "Screen" },
  { id: "reserve", label: "Reserve" },
];

export const AIR_ROLE_OPTIONS = [
  { id: "none", label: "No air request" },
  { id: "air_superiority", label: "Air Superiority" },
  { id: "cas", label: "CAS" },
  { id: "interdiction", label: "Interdiction" },
  { id: "recon", label: "Recon" },
];

export const NAVAL_ROLE_OPTIONS = [
  { id: "none", label: "No naval request" },
  { id: "shore_support", label: "Shore Support" },
  { id: "task_force_support", label: "Task Force Support" },
];

export const TEMPO_OPTIONS = [
  { id: "immediate", label: "Immediate" },
  { id: "standard", label: "Standard" },
  { id: "night_movement", label: "Night Movement" },
  { id: "slow_concealed", label: "Slow / Concealed" },
];

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function optionIds(options) {
  return new Set(options.map((option) => option.id));
}

const validGroundRoleIds = optionIds(GROUND_ROLE_OPTIONS);
const validAirRoleIds = optionIds(AIR_ROLE_OPTIONS);
const validNavalRoleIds = optionIds(NAVAL_ROLE_OPTIONS);
const validTempoIds = optionIds(TEMPO_OPTIONS);
const validCommandIntentIds = new Set(["operation", "move", "attack"]);

function isCombatGroundFormation(unit) {
  const unitType = String(unit?.unit_type ?? "").trim().toUpperCase();
  if (unitType === "HEADQUARTERS") {
    return false;
  }

  const kind = String(unit?.kind ?? "").trim().toLowerCase();
  return !kind.includes("air")
    && !kind.includes("aviation")
    && !kind.includes("naval")
    && !kind.includes("fleet")
    && !kind.includes("task force")
    && !kind.includes("sea")
    && !kind.includes("logistics")
    && !kind.includes("supply")
    && !kind.includes("transport");
}

function groundFormations(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units.filter(isCombatGroundFormation) : [];
  const alliedUnits = units.filter((unit) => String(unit?.side ?? "").trim().toUpperCase() === "ALLIED");
  return alliedUnits.length ? alliedUnits : units;
}

function objectiveById(snapshot, objectiveId) {
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  return objectives.find((objective) => String(objective?.id ?? "") === String(objectiveId ?? "")) ?? null;
}

function objectiveSceneById(scene, objectiveId) {
  const objectives = Array.isArray(scene?.objectives) ? scene.objectives : [];
  return objectives.find((objective) => String(objective?.id ?? "") === String(objectiveId ?? "")) ?? null;
}

function dominantCommandLabel(candidates) {
  const counts = new Map();
  candidates.forEach((candidate) => {
    const label = String(candidate?.commandLabel ?? "").trim();
    if (!label) {
      return;
    }
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });
  const ordered = Array.from(counts.entries()).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  return ordered[0]?.[0] ?? null;
}

function compactList(items, limit = 2) {
  const values = items.map((item) => String(item ?? "").trim()).filter(Boolean);
  if (!values.length) {
    return null;
  }
  if (values.length <= limit) {
    return values.join(", ");
  }
  return `${values.slice(0, limit).join(", ")} +${values.length - limit} more`;
}

function formatSupply(unit, supply) {
  if (typeof supply?.supply_display === "string" && supply.supply_display.trim()) {
    return supply.supply_display.trim();
  }
  if (toNumber(supply?.supply_days_current) != null) {
    return `${toNumber(supply.supply_days_current).toFixed(1)} days`;
  }
  if (toNumber(supply?.supply_pct) != null) {
    return `${Math.round(supply.supply_pct)}% supply`;
  }
  if (typeof unit?.supply === "string" && unit.supply.trim()) {
    return unit.supply.trim();
  }
  return "Supply not exposed";
}

function formatLoc(operational) {
  if (typeof operational?.loc?.label === "string" && operational.loc.label.trim()) {
    return operational.loc.label.trim();
  }
  if (typeof operational?.loc?.state === "string" && operational.loc.state.trim()) {
    return `LOC ${humanizeToken(operational.loc.state)}`;
  }
  return "LOC unavailable";
}

function distanceBetween(left, right) {
  const lx = toNumber(left?.x);
  const ly = toNumber(left?.y);
  const rx = toNumber(right?.x);
  const ry = toNumber(right?.y);
  if (lx == null || ly == null || rx == null || ry == null) {
    return null;
  }
  return Math.hypot(lx - rx, ly - ry);
}

function roundHexPoint(point) {
  const q = toNumber(point?.x);
  const r = toNumber(point?.y);
  if (q == null || r == null) {
    return null;
  }
  return axialRound(q, r);
}

function formatHexLabel(hex) {
  if (!hex) {
    return "Unknown hex";
  }
  return `Hex ${hex.q}, ${hex.r}`;
}

function commandIntentLabel(intent) {
  if (intent === "move") {
    return "Move";
  }
  if (intent === "attack") {
    return "Attack";
  }
  return "Operation";
}

function targetHexKey(targetHex) {
  if (!targetHex) {
    return "unknown";
  }
  return `${targetHex.q}:${targetHex.r}`;
}

function estimateQuickMoveReach(unit) {
  const movement = unit?.inspector && typeof unit.inspector === "object" && unit.inspector.movement && typeof unit.inspector.movement === "object"
    ? unit.inspector.movement
    : {};
  const operational = unit?.inspector && typeof unit.inspector === "object" && unit.inspector.operational_state && typeof unit.inspector.operational_state === "object"
    ? unit.inspector.operational_state
    : {};
  const movementState = normalizeText(movement?.remaining);
  const movementKm = toNumber(movement?.km_remaining);
  const fatigue = toNumber(operational?.fatigue);
  let reach = movementKm != null ? Math.max(1, Math.min(6, movementKm / 2)) : 3.25;

  if (movementState === "restricted") {
    reach = Math.min(reach, 2.25);
  } else if (movementState === "fixed") {
    reach = Math.min(reach, 0.75);
  } else if (movementState === "free") {
    reach = Math.max(reach, 3.25);
  }

  if (fatigue != null && fatigue > 30) {
    reach = Math.max(0.75, reach - 0.75);
  }

  return Number(reach.toFixed(2));
}

function objectiveAtHex(snapshot, targetHex) {
  if (!targetHex) {
    return null;
  }
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  return objectives.find((objective) => {
    const hex = roundHexPoint(objective);
    return hex && hex.q === targetHex.q && hex.r === targetHex.r;
  }) ?? null;
}

function nearestObjective(snapshot, targetHex) {
  if (!targetHex) {
    return null;
  }
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  return [...objectives]
    .filter((objective) => toNumber(objective?.x) != null && toNumber(objective?.y) != null)
    .sort((left, right) => {
      const leftDistance = distanceBetween(left, targetHex) ?? Number.POSITIVE_INFINITY;
      const rightDistance = distanceBetween(right, targetHex) ?? Number.POSITIVE_INFINITY;
      if (leftDistance !== rightDistance) {
        return leftDistance - rightDistance;
      }
      return String(left?.name ?? left?.id ?? "").localeCompare(String(right?.name ?? right?.id ?? ""));
    })[0] ?? null;
}

function enemyTargetAtHex(snapshot, unit, targetHex) {
  if (!targetHex || !unit) {
    return null;
  }
  const side = normalizeText(unit?.side);
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  return units.find((candidate) => {
    if (!candidate || String(candidate?.id ?? "") === String(unit?.id ?? "")) {
      return false;
    }
    if (side && normalizeText(candidate?.side) === side) {
      return false;
    }
    const hex = roundHexPoint(candidate);
    return hex && hex.q === targetHex.q && hex.r === targetHex.r;
  }) ?? null;
}

function proximityLabel(distance) {
  if (distance == null) {
    return "Range unavailable";
  }
  if (distance <= 1.25) {
    return "Near area";
  }
  if (distance <= 3.25) {
    return "Approach march";
  }
  return "Rear position";
}

function estimateAssembly(unit, objective) {
  const distance = distanceBetween(unit, objective);
  const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
  const movement = inspector?.movement && typeof inspector.movement === "object" ? inspector.movement : {};
  const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
  let hours = distance == null ? 12 : distance <= 1.25 ? 0 : distance <= 3.25 ? 6 : 12;
  const locState = normalizeText(operational?.loc?.state);
  const movementState = normalizeText(movement?.remaining);
  const fatigue = toNumber(operational?.fatigue);
  const movementKm = toNumber(movement?.km_remaining);

  if (movementState === "restricted") {
    hours += 6;
  } else if (movementState === "fixed") {
    hours += 12;
  }
  if (locState === "threatened") {
    hours += 6;
  } else if (locState === "broken") {
    hours += 12;
  }
  if (fatigue != null && fatigue > 30) {
    hours += 6;
  }
  if (movementKm != null && distance != null && movementKm >= distance * 4) {
    hours = Math.max(0, hours - 6);
  }

  let label = "~1 day";
  let prepDays = "1 day";
  if (hours <= 0) {
    label = "Current-step";
    prepDays = "0 day";
  } else if (hours <= 6) {
    label = "~6h";
    prepDays = "0.25 day";
  } else if (hours <= 12) {
    label = "~12h";
    prepDays = "0.5 day";
  } else if (hours <= 24) {
    label = "~1 day";
    prepDays = "1 day";
  } else {
    label = ">1 day";
    prepDays = "1 day+";
  }

  return {
    distance,
    proximity: proximityLabel(distance),
    hours,
    label,
    prepDays,
    note: "Demo estimate from current map distance, exposed movement, fatigue, and LOC state only.",
  };
}

function buildGroundCandidates(snapshot, objective, unitRoles = {}) {
  return groundFormations(snapshot)
    .filter((unit) => toNumber(unit?.x) != null && toNumber(unit?.y) != null)
    .map((unit) => {
      const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
      const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
      const supply = inspector?.supply && typeof inspector.supply === "object" ? inspector.supply : {};
      const attachmentsSupport = inspector?.attachments_support && typeof inspector.attachments_support === "object" ? inspector.attachments_support : {};
      const command = inspector?.command && typeof inspector.command === "object" ? inspector.command : {};
      const assembly = estimateAssembly(unit, objective);
      const support = [
        ...(Array.isArray(attachmentsSupport?.support) ? attachmentsSupport.support : []),
        ...(Array.isArray(attachmentsSupport?.attachments) ? attachmentsSupport.attachments : []),
      ].map((item) => String(item ?? "").trim()).filter(Boolean);
      const commandLabel = typeof command?.superior?.name === "string" && command.superior.name.trim()
        ? command.superior.name.trim()
        : (typeof command?.hq_unit_id === "string" && command.hq_unit_id.trim() ? command.hq_unit_id.trim() : null);
      const locLabel = formatLoc(operational);
      const readiness = toNumber(operational?.readiness ?? unit?.readiness);
      const fatigue = toNumber(operational?.fatigue);
      const roleId = validGroundRoleIds.has(unitRoles[unit.id]) ? unitRoles[unit.id] : "none";
      const warnings = [];
      if (normalizeText(operational?.loc?.state) === "broken") {
        warnings.push("LOC broken");
      } else if (normalizeText(operational?.loc?.state) === "threatened") {
        warnings.push("LOC threatened");
      }
      if (toNumber(supply?.supply_pct) != null && supply.supply_pct < 60) {
        warnings.push("Supply strained");
      }
      if (readiness != null && readiness < 55) {
        warnings.push("Readiness low");
      }
      if (fatigue != null && fatigue > 30) {
        warnings.push("Fatigue high");
      }

      return {
        id: String(unit?.id ?? unit?.name ?? ""),
        name: String(unit?.name ?? "Formation"),
        roleId,
        roleLabel: GROUND_ROLE_OPTIONS.find((option) => option.id === roleId)?.label ?? "Unassigned",
        commandLabel,
        locLabel,
        supplyLabel: formatSupply(unit, supply),
        supportLabel: compactList(support) ?? "No support assignment exposed",
        readiness: readiness != null ? Math.round(readiness) : null,
        fatigue: fatigue != null ? Math.round(fatigue) : null,
        assembly,
        warning: warnings.join(" • ") || "No immediate warning from exposed readiness, LOC, or supply fields.",
      };
    })
    .sort((left, right) => {
      const leftDistance = left.assembly.distance ?? Number.POSITIVE_INFINITY;
      const rightDistance = right.assembly.distance ?? Number.POSITIVE_INFINITY;
      if (leftDistance !== rightDistance) {
        return leftDistance - rightDistance;
      }
      return left.name.localeCompare(right.name);
    });
}

export function createOperationPlannerState(scenarioId = null) {
  return {
    scenarioId,
    greaseEnabled: false,
    plannerOpen: false,
    selectingObjective: false,
    operationType: "offensive",
    objectiveId: null,
    name: "",
    unitRoles: {},
    airRole: "none",
    navalRole: "none",
    tempo: "standard",
    approved: false,
    commandIntent: "operation",
    commandSource: "planner",
    seedUnitId: null,
    targetHex: null,
    targetLabel: null,
    enemyTargetId: null,
  };
}

export function sanitizeTrackedOperations(snapshot, operations) {
  const scenarioId = typeof snapshot?.scenario?.id === "string" ? snapshot.scenario.id : null;
  if (!Array.isArray(operations)) {
    return [];
  }

  return operations
    .filter((operation) => operation && typeof operation === "object" && operation.scenarioId === scenarioId)
    .map((operation) => ({
      id: typeof operation.id === "string" && operation.id.trim() ? operation.id.trim() : `${scenarioId ?? "scenario"}:operation`,
      scenarioId,
      name: typeof operation.name === "string" ? operation.name : "",
      type: operation.type === "offensive" ? "offensive" : "offensive",
      objectiveId: typeof operation.objectiveId === "string" ? operation.objectiveId : "",
      objectiveName: typeof operation.objectiveName === "string" ? operation.objectiveName : "Objective",
      leadHq: typeof operation.leadHq === "string" && operation.leadHq.trim() ? operation.leadHq.trim() : null,
      participants: Array.isArray(operation.participants)
        ? operation.participants
          .map((participant) => ({
            unitId: typeof participant?.unitId === "string" ? participant.unitId : "",
            name: typeof participant?.name === "string" && participant.name.trim() ? participant.name.trim() : "Formation",
            roleId: validGroundRoleIds.has(participant?.roleId) ? participant.roleId : "none",
          }))
          .filter((participant) => participant.unitId)
        : [],
      airRole: validAirRoleIds.has(operation.airRole) ? operation.airRole : "none",
      navalRole: validNavalRoleIds.has(operation.navalRole) ? operation.navalRole : "none",
      tempo: validTempoIds.has(operation.tempo) ? operation.tempo : "standard",
      estimatedPrepHours: toNumber(operation.estimatedPrepHours),
      approvedAtTurn: toNumber(operation.approvedAtTurn),
      approvedAtHours: toNumber(operation.approvedAtHours),
      commandIntent: validCommandIntentIds.has(operation.commandIntent) ? operation.commandIntent : "operation",
      source: operation.source === "map_shortcut" ? "map_shortcut" : "planner",
      seedUnitId: typeof operation.seedUnitId === "string" && operation.seedUnitId.trim() ? operation.seedUnitId.trim() : null,
      targetHex: operation.targetHex && Number.isFinite(Number(operation.targetHex.q)) && Number.isFinite(Number(operation.targetHex.r))
        ? { q: Number(operation.targetHex.q), r: Number(operation.targetHex.r) }
        : null,
      targetLabel: typeof operation.targetLabel === "string" && operation.targetLabel.trim() ? operation.targetLabel.trim() : null,
      enemyTargetId: typeof operation.enemyTargetId === "string" && operation.enemyTargetId.trim() ? operation.enemyTargetId.trim() : null,
    }));
}

export function upsertTrackedOperation(operations, operation) {
  const rows = Array.isArray(operations) ? operations : [];
  const index = rows.findIndex((row) => row?.id === operation?.id);
  if (index === -1) {
    return [...rows, operation];
  }
  return rows.map((row, rowIndex) => (rowIndex === index ? operation : row));
}

function shallowEqualRoles(left, right) {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) {
    return false;
  }
  return leftKeys.every((key) => left[key] === right[key]);
}

export function sanitizeOperationPlannerState(snapshot, plannerState) {
  const scenarioId = typeof snapshot?.scenario?.id === "string" ? snapshot.scenario.id : null;
  if (!plannerState || typeof plannerState !== "object" || plannerState.scenarioId !== scenarioId) {
    return createOperationPlannerState(scenarioId);
  }

  const validObjectiveIds = new Set(
    (Array.isArray(snapshot?.objectives) ? snapshot.objectives : [])
      .map((objective) => String(objective?.id ?? ""))
      .filter(Boolean),
  );
  const validUnitIds = new Set(
    groundFormations(snapshot)
      .map((unit) => String(unit?.id ?? ""))
      .filter(Boolean),
  );

  const cleanedRoles = Object.fromEntries(
    Object.entries(plannerState.unitRoles ?? {}).filter(([unitId, roleId]) => validUnitIds.has(unitId) && validGroundRoleIds.has(roleId)),
  );
  const nextObjectiveId = validObjectiveIds.has(plannerState.objectiveId) ? plannerState.objectiveId : null;
  const nextTargetHex = plannerState?.targetHex && Number.isFinite(Number(plannerState.targetHex.q)) && Number.isFinite(Number(plannerState.targetHex.r))
    ? { q: Number(plannerState.targetHex.q), r: Number(plannerState.targetHex.r) }
    : null;
  const nextCommandIntent = validCommandIntentIds.has(plannerState.commandIntent) ? plannerState.commandIntent : "operation";
  const nextSeedUnitId = validUnitIds.has(String(plannerState.seedUnitId ?? "")) ? String(plannerState.seedUnitId) : null;
  const nextTargetLabel = typeof plannerState.targetLabel === "string" && plannerState.targetLabel.trim()
    ? plannerState.targetLabel.trim()
    : null;
  const nextState = {
    scenarioId,
    greaseEnabled: !!plannerState.greaseEnabled,
    plannerOpen: !!plannerState.plannerOpen,
    selectingObjective: !!plannerState.selectingObjective && !!plannerState.plannerOpen,
    operationType: "offensive",
    objectiveId: nextObjectiveId,
    name: typeof plannerState.name === "string" ? plannerState.name : "",
    unitRoles: cleanedRoles,
    airRole: validAirRoleIds.has(plannerState.airRole) ? plannerState.airRole : "none",
    navalRole: validNavalRoleIds.has(plannerState.navalRole) ? plannerState.navalRole : "none",
    tempo: validTempoIds.has(plannerState.tempo) ? plannerState.tempo : "standard",
    approved: !!plannerState.approved && !!nextObjectiveId,
    commandIntent: nextCommandIntent,
    commandSource: plannerState.commandSource === "map_shortcut" ? "map_shortcut" : "planner",
    seedUnitId: nextSeedUnitId,
    targetHex: nextTargetHex,
    targetLabel: nextTargetLabel,
    enemyTargetId: typeof plannerState.enemyTargetId === "string" && plannerState.enemyTargetId.trim()
      ? plannerState.enemyTargetId.trim()
      : null,
  };

  if (
    nextState.scenarioId === plannerState.scenarioId
    && nextState.greaseEnabled === plannerState.greaseEnabled
    && nextState.plannerOpen === plannerState.plannerOpen
    && nextState.selectingObjective === plannerState.selectingObjective
    && nextState.operationType === plannerState.operationType
    && nextState.objectiveId === plannerState.objectiveId
    && nextState.name === plannerState.name
    && nextState.airRole === plannerState.airRole
    && nextState.navalRole === plannerState.navalRole
    && nextState.tempo === plannerState.tempo
    && nextState.approved === plannerState.approved
    && nextState.commandIntent === plannerState.commandIntent
    && nextState.commandSource === plannerState.commandSource
    && nextState.seedUnitId === plannerState.seedUnitId
    && nextState.targetLabel === plannerState.targetLabel
    && nextState.enemyTargetId === plannerState.enemyTargetId
    && nextState.targetHex?.q === plannerState.targetHex?.q
    && nextState.targetHex?.r === plannerState.targetHex?.r
    && shallowEqualRoles(nextState.unitRoles, plannerState.unitRoles ?? {})
  ) {
    return plannerState;
  }

  return nextState;
}

export function buildMapCommandPreview(snapshot, unitId, targetHex) {
  if (!snapshot || !unitId || !targetHex) {
    return null;
  }

  const unit = (Array.isArray(snapshot?.units) ? snapshot.units : []).find((row) => String(row?.id ?? "") === String(unitId)) ?? null;
  if (!unit) {
    return null;
  }

  const roundedTargetHex = roundHexPoint({ x: targetHex.q, y: targetHex.r });
  const currentHex = roundHexPoint(unit);
  if (!roundedTargetHex || !currentHex) {
    return null;
  }

  const enemyTarget = enemyTargetAtHex(snapshot, unit, roundedTargetHex);
  const matchedObjective = objectiveAtHex(snapshot, roundedTargetHex) ?? nearestObjective(snapshot, roundedTargetHex);
  const distance = Number((distanceBetween(currentHex, roundedTargetHex) ?? 0).toFixed(2));
  const quickMoveReach = estimateQuickMoveReach(unit);
  const attackReach = 1.75;
  const sameHex = currentHex.q === roundedTargetHex.q && currentHex.r === roundedTargetHex.r;
  const commandIntent = sameHex ? "operation" : enemyTarget ? "attack" : "move";
  const immediate = sameHex
    ? false
    : commandIntent === "attack"
      ? distance <= attackReach
      : distance <= quickMoveReach;
  const targetLabel = enemyTarget?.name
    || matchedObjective?.name
    || formatHexLabel(roundedTargetHex);
  const statusLabel = sameHex
    ? "Planner ready"
    : immediate
      ? commandIntent === "attack" ? "Attack available" : "Move available"
      : "Planner review";
  const note = sameHex
    ? `Open the planner with ${unit.name} preloaded for a deliberate operation order.`
    : immediate
      ? commandIntent === "attack"
        ? `${unit.name} can attack toward ${targetLabel} through the planner approval path.`
        : `${unit.name} can move toward ${targetLabel} through the planner approval path.`
      : commandIntent === "attack"
        ? `${unit.name} is not in immediate attack position. Seed the planner for a staged attack toward ${targetLabel}.`
        : `${targetLabel} sits beyond the current quick-order reach estimate. Seed the planner for a deliberate move.`;

  return {
    available: true,
    unitId: String(unit.id),
    unitName: String(unit.name ?? "Formation"),
    commandIntent,
    mode: immediate ? "immediate" : "planner_review",
    legal: immediate || sameHex,
    targetHex: roundedTargetHex,
    targetLabel,
    objectiveId: matchedObjective?.id ? String(matchedObjective.id) : null,
    objectiveName: matchedObjective?.name ? String(matchedObjective.name) : null,
    enemyTargetId: enemyTarget?.id ? String(enemyTarget.id) : null,
    enemyTargetName: enemyTarget?.name ? String(enemyTarget.name) : null,
    route: [
      { x: toNumber(unit?.x) ?? currentHex.q, y: toNumber(unit?.y) ?? currentHex.r },
      { x: roundedTargetHex.q, y: roundedTargetHex.r },
    ],
    distance,
    note,
    title: sameHex
      ? `Open planner for ${unit.name}`
      : `${commandIntentLabel(commandIntent)} • ${unit.name}`,
    statusLabel,
    previewTone: sameHex ? "review" : commandIntent === "attack" ? "attack" : immediate ? "move" : "review",
  };
}

export function seedPlannerStateFromMapCommand(snapshot, plannerState, preview) {
  const state = sanitizeOperationPlannerState(snapshot, plannerState);
  if (!preview?.available) {
    return state;
  }

  const objectiveId = preview.objectiveId ?? state.objectiveId;
  const fallbackObjectiveLabel = preview.objectiveName || preview.targetLabel || "Objective";
  const commandLabel = commandIntentLabel(preview.commandIntent);
  const operationName = preview.commandIntent === "operation"
    ? `${preview.unitName} ${commandLabel} • ${fallbackObjectiveLabel}`
    : `${preview.unitName} ${commandLabel} • ${preview.targetLabel}`;

  return sanitizeOperationPlannerState(snapshot, {
    ...state,
    greaseEnabled: true,
    plannerOpen: preview.mode === "planner_review" || preview.commandIntent === "operation" || state.plannerOpen,
    selectingObjective: !objectiveId,
    objectiveId,
    name: operationName,
    unitRoles: { [preview.unitId]: "main_effort" },
    tempo: preview.commandIntent === "attack" ? "immediate" : state.tempo,
    approved: preview.mode === "immediate" && Boolean(objectiveId),
    commandIntent: preview.commandIntent,
    commandSource: "map_shortcut",
    seedUnitId: preview.unitId,
    targetHex: preview.targetHex,
    targetLabel: preview.targetLabel,
    enemyTargetId: preview.enemyTargetId,
  });
}

export function defaultOperationName(snapshot, objectiveId, operationType = "offensive") {
  const objective = objectiveById(snapshot, objectiveId);
  const objectiveName = typeof objective?.name === "string" && objective.name.trim() ? objective.name.trim() : "Objective";
  return `${humanizeToken(operationType)} • ${objectiveName}`;
}

export function buildDefaultPlannerAssignments(snapshot, objectiveId) {
  const objective = objectiveById(snapshot, objectiveId);
  if (!objective) {
    return {};
  }
  const candidates = buildGroundCandidates(snapshot, objective, {});
  return Object.fromEntries(
    candidates
      .slice(0, 3)
      .map((candidate, index) => [candidate.id, index === 0 ? "main_effort" : index === 1 ? "support" : "reserve"]),
  );
}

function roleLabel(roleId, options) {
  return options.find((option) => option.id === roleId)?.label ?? "Not assigned";
}

function countAssignedRoles(candidates) {
  return candidates.filter((candidate) => candidate.roleId !== "none");
}

function pickLeadFormation(candidates) {
  const assigned = countAssignedRoles(candidates);
  if (assigned.length) {
    const mainEffort = assigned.find((candidate) => candidate.roleId === "main_effort");
    return mainEffort ?? assigned[0];
  }
  return candidates[0] ?? null;
}

function buildWarnings(candidates, plannerState, airSupport, navalSupport, weatherImpact, objectiveSelected) {
  const warnings = [];
  const assigned = countAssignedRoles(candidates);
  if (!objectiveSelected) {
    warnings.push("Objective area is not marked on the map.");
  }
  if (!assigned.some((candidate) => candidate.roleId === "main_effort")) {
    warnings.push("No main effort formation is assigned.");
  }
  if (assigned.some((candidate) => /LOC broken/i.test(candidate.warning))) {
    warnings.push("A participating formation reports broken LOC status.");
  } else if (assigned.some((candidate) => /LOC threatened/i.test(candidate.warning))) {
    warnings.push("A participating formation reports threatened LOC status.");
  }
  if (assigned.some((candidate) => /Supply strained/i.test(candidate.warning))) {
    warnings.push("Participating formations include supply-strained units.");
  }
  if (plannerState.airRole !== "none" && normalizeText(airSupport.availability) === "unavailable") {
    warnings.push("Requested air support is unavailable on the current shell path.");
  } else if (plannerState.airRole !== "none" && normalizeText(airSupport.availability) === "not exposed") {
    warnings.push("Air role is a demo request only; committed sorties are not exposed.");
  }
  if (plannerState.navalRole !== "none" && normalizeText(navalSupport.availability) === "unavailable") {
    warnings.push("Requested naval support is unavailable on the current shell path.");
  } else if (plannerState.navalRole !== "none" && normalizeText(navalSupport.availability) === "not exposed") {
    warnings.push("Naval role is a demo request only; committed task-force support is not exposed.");
  }
  if (plannerState.tempo === "night_movement" && weatherImpact.timeState === "Daylight") {
    warnings.push("Night movement is selected before current night conditions.");
  }
  if (plannerState.tempo === "immediate" && assigned.some((candidate) => candidate.assembly.hours > 6)) {
    warnings.push("Immediate tempo outruns at least one current demo assembly estimate.");
  }
  return warnings.slice(0, 4);
}

export function createApprovedOperation(snapshot, plannerState) {
  const state = sanitizeOperationPlannerState(snapshot, plannerState);
  const objective = state.objectiveId ? objectiveById(snapshot, state.objectiveId) : null;
  if (!objective) {
    return null;
  }

  const candidates = buildGroundCandidates(snapshot, objective, state.unitRoles);
  const assigned = countAssignedRoles(candidates);
  if (!assigned.length) {
    return null;
  }

  const leadFormation = pickLeadFormation(candidates);
  const leadHq = dominantCommandLabel(assigned.length ? assigned : candidates);
  const prepHours = assigned.length ? Math.max(...assigned.map((candidate) => candidate.assembly.hours)) : (leadFormation?.assembly.hours ?? null);
  const scenarioId = typeof snapshot?.scenario?.id === "string" ? snapshot.scenario.id : null;
  const operationTargetHex = state.targetHex ?? roundHexPoint(objective);
  const operationId = state.commandSource === "map_shortcut"
    ? `${scenarioId ?? "scenario"}:${state.commandIntent}:${state.seedUnitId ?? "unit"}:${targetHexKey(operationTargetHex)}`
    : `${scenarioId ?? "scenario"}:${state.operationType}:${objective.id}`;

  return {
    id: operationId,
    scenarioId,
    name: state.name.trim() || defaultOperationName(snapshot, objective.id, state.operationType),
    type: state.operationType,
    objectiveId: objective.id,
    objectiveName: typeof objective?.name === "string" && objective.name.trim() ? objective.name.trim() : "Objective",
    leadHq: leadHq ?? null,
    participants: assigned.map((candidate) => ({
      unitId: candidate.id,
      name: candidate.name,
      roleId: candidate.roleId,
    })),
    airRole: state.airRole,
    navalRole: state.navalRole,
    tempo: state.tempo,
    estimatedPrepHours: prepHours,
    approvedAtTurn: toNumber(snapshot?.time?.turn),
    approvedAtHours: toNumber(snapshot?.time?.current_hours),
    commandIntent: state.commandIntent,
    source: state.commandSource,
    seedUnitId: state.seedUnitId,
    targetHex: state.targetHex,
    targetLabel: state.targetLabel ?? (state.commandIntent === "move" ? formatHexLabel(state.targetHex) : objective.name),
    enemyTargetId: state.enemyTargetId,
  };
}

function formatRemainingPrep(hours) {
  const value = toNumber(hours);
  if (value == null) {
    return "Prep estimate unavailable";
  }
  if (value <= 0) {
    return "Ready to launch";
  }
  if (value <= 6) {
    return "~6h to assembly";
  }
  if (value <= 12) {
    return "~12h to assembly";
  }
  if (value <= 24) {
    return "~1 day to assembly";
  }
  return ">1 day to assembly";
}

function approvedAtLabel(operation) {
  const parts = [];
  if (toNumber(operation?.approvedAtTurn) != null) {
    parts.push(`Turn ${Math.round(operation.approvedAtTurn)}`);
  }
  if (toNumber(operation?.approvedAtHours) != null) {
    parts.push(`T+${Math.round(operation.approvedAtHours)}h`);
  }
  return parts.length ? `Approved ${parts.join(" • ")}` : "Approval time not exposed";
}

function elapsedHoursSinceApproval(operation, snapshot) {
  const currentHours = toNumber(snapshot?.time?.current_hours);
  const approvedAtHours = toNumber(operation?.approvedAtHours);
  if (currentHours == null || approvedAtHours == null) {
    return 0;
  }
  return Math.max(0, currentHours - approvedAtHours);
}

function objectivePressureContext(snapshot, operation) {
  const objective = objectiveById(snapshot, operation?.objectiveId);
  const localAreas = (Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : []).filter((area) => (
    String(area?.objective_id ?? "") === String(operation?.objectiveId ?? "")
    || String(area?.location_id ?? "").trim().toUpperCase() === String(objective?.id ?? "").trim().toUpperCase()
  ));
  const localAreaIds = new Set(localAreas.map((area) => String(area?.id ?? "")).filter(Boolean));
  const recentReports = (Array.isArray(snapshot?.reports?.recent) ? snapshot.reports.recent : []).filter((report) => (
    localAreaIds.has(String(report?.local_area_id ?? ""))
  ));
  const hasPressure = localAreas.some((area) => Array.isArray(area?.pressure_reasons) && area.pressure_reasons.length > 0);
  return {
    objective,
    recentReports,
    hasPressure,
    active: hasPressure || recentReports.length > 0,
  };
}

function currentParticipants(snapshot, operation, objective) {
  const unitsById = new Map((Array.isArray(snapshot?.units) ? snapshot.units : []).map((unit) => [String(unit?.id ?? ""), unit]));
  return (Array.isArray(operation?.participants) ? operation.participants : []).map((participant) => {
    const unit = unitsById.get(String(participant?.unitId ?? ""));
    const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
    const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
    const supply = inspector?.supply && typeof inspector.supply === "object" ? inspector.supply : {};
    const assembly = unit && objective ? estimateAssembly(unit, objective) : {
      distance: null,
      proximity: "Range unavailable",
      hours: null,
      label: "Assembly unavailable",
      prepDays: "Prep estimate unavailable",
      note: "Current assembly estimate unavailable on the shell path.",
    };
    const warnings = [];
    if (normalizeText(operational?.loc?.state) === "broken") {
      warnings.push("LOC broken");
    } else if (normalizeText(operational?.loc?.state) === "threatened") {
      warnings.push("LOC threatened");
    }
    if (toNumber(supply?.supply_pct) != null && supply.supply_pct < 60) {
      warnings.push("Supply strained");
    }
    if (toNumber(operational?.readiness ?? unit?.readiness) != null && (operational?.readiness ?? unit?.readiness) < 55) {
      warnings.push("Readiness low");
    }
    if (toNumber(operational?.fatigue) != null && operational.fatigue > 30) {
      warnings.push("Fatigue high");
    }

    return {
      unitId: participant.unitId,
      name: unit?.name ?? participant?.name ?? "Formation",
      roleId: validGroundRoleIds.has(participant?.roleId) ? participant.roleId : "none",
      roleLabel: roleLabel(validGroundRoleIds.has(participant?.roleId) ? participant.roleId : "none", GROUND_ROLE_OPTIONS),
      locLabel: formatLoc(operational),
      supplyLabel: unit ? formatSupply(unit, supply) : "Unit supply unavailable",
      readiness: toNumber(operational?.readiness ?? unit?.readiness),
      fatigue: toNumber(operational?.fatigue),
      assembly,
      warning: warnings.join(" • ") || "No immediate warning from exposed readiness, LOC, or supply fields.",
    };
  });
}

function participantSide(snapshot, operation) {
  const unitsById = new Map((Array.isArray(snapshot?.units) ? snapshot.units : []).map((unit) => [String(unit?.id ?? ""), unit]));
  for (const participant of Array.isArray(operation?.participants) ? operation.participants : []) {
    const side = String(unitsById.get(String(participant?.unitId ?? ""))?.side ?? "").trim().toUpperCase();
    if (side) {
      return side;
    }
  }
  return "ALLIED";
}

function objectiveHeldByParticipantSide(objective, side) {
  const state = normalizeText(objective?.state);
  if (!state || !side) {
    return false;
  }
  return state.includes(`held ${String(side).trim().toLowerCase()}`);
}

function operationStatus(operation, snapshot, participants, objectiveContext) {
  const objective = objectiveContext.objective;
  if (!objective || !participants.length) {
    return {
      status: "Aborted",
      detail: "Objective area or participating formations are no longer exposed on the current shell path.",
    };
  }

  const elapsedHours = elapsedHoursSinceApproval(operation, snapshot);
  const estimatedPrepHours = toNumber(operation?.estimatedPrepHours);
  const remainingPrepHours = estimatedPrepHours == null ? null : Math.max(0, estimatedPrepHours - elapsedHours);
  const stress = participants.some((participant) => /LOC broken|Supply strained|Readiness low|Fatigue high/i.test(participant.warning));
  const objectiveHeld = objectiveHeldByParticipantSide(objective, participantSide(snapshot, operation));

  if (remainingPrepHours != null && remainingPrepHours > 6) {
    return {
      status: "Assembling",
      detail: `${formatRemainingPrep(remainingPrepHours)} based on the approved demo prep estimate and elapsed theatre time.`,
    };
  }
  if (remainingPrepHours != null && remainingPrepHours > 0) {
    return {
      status: "Moving to Start Line",
      detail: `${formatRemainingPrep(remainingPrepHours)} before launch from the approved demo prep estimate.`,
    };
  }
  if (stress && !objectiveContext.active) {
    return {
      status: "Stalled",
      detail: "Operation is nominally ready, but current LOC, supply, or readiness warnings are constraining launch.",
    };
  }
  if (objectiveContext.active && objectiveHeld) {
    return {
      status: "Securing Objective",
      detail: "Objective is in friendly hands, but current local reports or pressure still indicate active fighting nearby.",
    };
  }
  if (objectiveContext.active && stress) {
    return {
      status: "Stalled",
      detail: "Current contact is active around the objective, and at least one assigned formation shows a readiness, LOC, or supply warning.",
    };
  }
  if (objectiveContext.active) {
    return {
      status: "Engaged",
      detail: "Current local reports or pressure reasons place the objective area in active contact.",
    };
  }
  return {
    status: "Ready",
    detail: "Approved operation is assembled to the current demo standard and waiting on command execution.",
  };
}

function operationTaskLabel(operation) {
  const target = operation?.targetLabel || operation?.objectiveName || "objective";
  if (operation?.commandIntent === "move") {
    return `Move toward ${target}`;
  }
  if (operation?.commandIntent === "attack") {
    return `Attack toward ${target}`;
  }
  return `Operation toward ${target}`;
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
  if (normalized === "ready") {
    return 3;
  }
  if (normalized === "moving to start line") {
    return 4;
  }
  if (normalized === "assembling") {
    return 5;
  }
  if (normalized === "aborted") {
    return 6;
  }
  return 7;
}

export function summarizeTrackedOperations(snapshot, operations, options = {}) {
  const trackedOperations = sanitizeTrackedOperations(snapshot, operations);
  if (!trackedOperations.length) {
    return {
      available: false,
      total: 0,
      note: "No approved demo operations are currently tracked on the shell path.",
      headline: "No approved operations",
      lead: null,
      rows: [],
    };
  }

  const scene = options?.scene ?? null;
  const airSupport = summarizeLocalAirSupport(snapshot);
  const navalSupport = summarizeLocalNavalSupport(snapshot);
  const rows = trackedOperations.map((operation) => {
    const objectiveContext = objectivePressureContext(snapshot, operation);
    const objective = objectiveContext.objective;
    const objectiveScene = scene ? objectiveSceneById(scene, operation.objectiveId) : null;
    const participants = currentParticipants(snapshot, operation, objective);
    const prepRemaining = toNumber(operation?.estimatedPrepHours) == null
      ? null
      : Math.max(0, operation.estimatedPrepHours - elapsedHoursSinceApproval(operation, snapshot));
    const state = operationStatus(operation, snapshot, participants, objectiveContext);
    const participatingForces = participants.length
      ? participants.map((participant) => `${participant.name} (${participant.roleLabel})`)
      : (Array.isArray(operation.participants) ? operation.participants.map((participant) => `${participant.name} (${roleLabel(participant.roleId, GROUND_ROLE_OPTIONS)})`) : []);
    const supportAssigned = [
      operation.airRole !== "none" ? `${roleLabel(operation.airRole, AIR_ROLE_OPTIONS)} • ${airSupport.availability}` : null,
      operation.navalRole !== "none" ? `${roleLabel(operation.navalRole, NAVAL_ROLE_OPTIONS)} • ${navalSupport.availability}` : null,
    ].filter(Boolean);
    const leadParticipant = participants.find((participant) => participant.roleId === "main_effort") ?? participants[0] ?? null;
    const readinessNote = leadParticipant
      ? `${leadParticipant.name} • ${leadParticipant.supplyLabel} • ${leadParticipant.locLabel}`
      : "No participating formation is currently exposed on the shell path.";

    return {
      id: operation.id,
      name: operation.name,
      type: humanizeToken(operation.type),
      objective: operation.targetLabel ?? objective?.name ?? operation.objectiveName,
      leadHq: operation.leadHq ?? "Lead HQ not exposed",
      status: state.status,
      statusDetail: `${operationTaskLabel(operation)}. ${state.detail}`,
      participatingForces: participatingForces.length ? participatingForces : ["Participating forces no longer exposed"],
      supportAssigned: supportAssigned.length ? supportAssigned : ["No support assigned"],
      prepStatus: formatRemainingPrep(prepRemaining),
      readinessNote,
      commandIntent: operation.commandIntent,
      source: operation.source,
      approvedLabel: approvedAtLabel(operation),
      marker: objectiveScene
        ? {
            id: operation.id,
            objectiveId: operation.objectiveId,
            x: objectiveScene.anchor?.x ?? objectiveScene.displayAnchor?.x ?? 0,
            y: objectiveScene.anchor?.y ?? objectiveScene.displayAnchor?.y ?? 0,
            radius: 38,
          }
        : null,
      objectiveState: objective?.state ? humanizeToken(objective.state) : "Objective state unavailable",
      note: operation.source === "map_shortcut"
        ? "Fast map command routed through the same approved demo plan path. Lifecycle state still uses approved prep time, elapsed theatre time, and current shell-visible conditions only."
        : "Prototype operation state tracks approved demo plans plus current objective pressure, readiness, LOC, and elapsed theatre time only. No combat progress meter is implied.",
    };
  }).sort((left, right) => {
    const rankDiff = operationStatusRank(left.status) - operationStatusRank(right.status);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    return left.name.localeCompare(right.name);
  });

  const lead = rows[0] ?? null;
  return {
    available: true,
    total: rows.length,
    note: "Approved operations are frontend demo command objects only. Lifecycle state is derived from approved prep time, elapsed theatre time, and current shell-visible objective and unit conditions.",
    headline: lead ? `${lead.status} • ${lead.name}` : "Approved operations tracked",
    lead,
    rows,
  };
}

export function summarizeOperationPlanner(snapshot, scene, plannerState) {
  const state = sanitizeOperationPlannerState(snapshot, plannerState);
  const objective = state.objectiveId ? objectiveById(snapshot, state.objectiveId) : null;
  const objectiveScene = state.objectiveId ? objectiveSceneById(scene, state.objectiveId) : null;
  const weatherImpact = buildOperationalOverlayState(snapshot, scene).weatherImpact;
  const airSupport = summarizeLocalAirSupport(snapshot);
  const navalSupport = summarizeLocalNavalSupport(snapshot);
  const candidates = objective ? buildGroundCandidates(snapshot, objective, state.unitRoles) : [];
  const assigned = countAssignedRoles(candidates);
  const leadFormation = pickLeadFormation(candidates);
  const leadHq = dominantCommandLabel(assigned.length ? assigned : candidates);
  const prepHours = assigned.length
    ? Math.max(...assigned.map((candidate) => candidate.assembly.hours))
    : (leadFormation?.assembly.hours ?? null);
  const prepDays = prepHours == null
    ? "Prep estimate unavailable"
    : prepHours <= 0 ? "0 day" : prepHours <= 6 ? "0.25 day" : prepHours <= 12 ? "0.5 day" : prepHours <= 24 ? "1 day" : "1 day+";
  const warnings = buildWarnings(candidates, state, airSupport, navalSupport, weatherImpact, !!objective);
  const participatingForces = assigned.map((candidate) => `${candidate.name} (${candidate.roleLabel})`);
  const supportAssigned = [
    state.airRole !== "none" ? `${roleLabel(state.airRole, AIR_ROLE_OPTIONS)} • ${airSupport.availability}` : null,
    state.navalRole !== "none" ? `${roleLabel(state.navalRole, NAVAL_ROLE_OPTIONS)} • ${navalSupport.availability}` : null,
  ].filter(Boolean);
  const approvalReady = !!objective && participatingForces.length > 0 && state.operationType === "offensive";
  const operationName = state.name.trim() || (objective ? defaultOperationName(snapshot, objective.id, state.operationType) : "Offensive draft");
  const currentPlan = state.approved && objective
    ? {
        headline: operationName,
        detail: `${commandIntentLabel(state.commandIntent)} toward ${state.targetLabel ?? objective.name}. ${prepDays} demo prep estimate.`,
        note: supportAssigned.length
          ? `${supportAssigned.join(" • ")}. ${weatherImpact.timeState} conditions currently exposed.`
          : `${weatherImpact.timeState} conditions currently exposed. Support remains unassigned.`,
      }
    : null;

  return {
    note: "Prototype planning object stored in frontend shell state only. Approval creates a visible demo plan, not a backend execution order.",
    currentPlan,
    operationTypes: OPERATION_TYPE_OPTIONS.map((option) => ({
      ...option,
      selected: option.id === state.operationType,
    })),
    objectiveArea: {
      selected: !!objective,
      prompt: objective
        ? `Objective area marked around ${objective.name}.`
        : "Select a visible objective marker to circle the operation area.",
      visibleObjectives: Array.isArray(scene?.objectives) ? scene.objectives.length : 0,
      name: objective?.name ?? "No objective area marked",
      marker: objectiveScene
        ? {
            id: objectiveScene.id,
            x: objectiveScene.anchor?.x ?? objectiveScene.displayAnchor?.x ?? 0,
            y: objectiveScene.anchor?.y ?? objectiveScene.displayAnchor?.y ?? 0,
            radius: state.approved ? 38 : 34,
            status: state.approved ? "approved" : "draft",
          }
        : null,
    },
    identity: {
      name: operationName,
      type: roleLabel(state.operationType, OPERATION_TYPE_OPTIONS),
      leadHq: leadHq ?? "Lead HQ not exposed",
      objectiveArea: state.targetLabel ?? objective?.name ?? "No objective area marked",
      status: state.approved ? "Approved demo plan" : "Draft planning object",
    },
    groundForces: {
      note: objective
        ? "Ground forces are ordered nearest to furthest from the marked objective area."
        : "Mark an objective area to order nearby formations for planning.",
      rows: candidates.map((candidate) => ({
        ...candidate,
        assemblyEstimate: candidate.assembly.label,
        assemblyPrepDays: candidate.assembly.prepDays,
        proximity: candidate.assembly.proximity,
        condition: [
          candidate.readiness != null ? `${candidate.readiness} readiness` : "Readiness unavailable",
          candidate.fatigue != null ? `${candidate.fatigue} fatigue` : "Fatigue unavailable",
        ].join(" • "),
      })),
    },
    airSupport: {
      availability: airSupport.availability,
      selectedRole: state.airRole,
      selectedLabel: roleLabel(state.airRole, AIR_ROLE_OPTIONS),
      note: airSupport.note,
      constraint: airSupport.constraint,
      supportingFormation: airSupport.supportingFormation,
      demoOnly: normalizeText(airSupport.availability) === "not exposed",
    },
    navalSupport: {
      availability: navalSupport.availability,
      selectedRole: state.navalRole,
      selectedLabel: roleLabel(state.navalRole, NAVAL_ROLE_OPTIONS),
      note: navalSupport.note,
      constraint: navalSupport.constraint,
      supportingFormation: navalSupport.supportingFormation,
      posture: navalSupport.supportPosture,
      demoOnly: normalizeText(navalSupport.availability) === "not exposed",
    },
    tempo: {
      selected: state.tempo,
      selectedLabel: roleLabel(state.tempo, TEMPO_OPTIONS),
      note: state.tempo === "night_movement"
        ? `${weatherImpact.timeState} is the current exposed time state for movement timing.`
        : "Tempo choice remains a demo planning instruction until backend execution wiring exists.",
    },
    staffEstimate: {
      prepDays,
      readinessNote: leadFormation
        ? `${leadFormation.name} is the lead visible formation from current distance, readiness, and LOC context.`
        : "No lead formation can be estimated until a visible objective area is marked.",
      warnings,
      note: "Assembly estimate uses only current distance, movement, fatigue, and LOC exposure. No combat-odds or transport model is implied.",
    },
    approval: {
      ready: approvalReady,
      operationName,
      objective: state.targetLabel ?? objective?.name ?? "No objective area marked",
      participatingForces: participatingForces.length ? participatingForces : ["No forces assigned"],
      supportAssigned: supportAssigned.length ? supportAssigned : ["No support assigned"],
      estimatedPrepTime: prepDays,
      launchCondition: `${roleLabel(state.tempo, TEMPO_OPTIONS)} • ${weatherImpact.timeState}`,
      status: state.approved ? "Approved demo plan" : "Awaiting approval",
      note: approvalReady
        ? "Approval records the current demo plan and keeps it visible on the theatre shell."
        : "Mark an objective area and assign at least one ground role before approval.",
    },
  };
}
