import type { ViewSnapshot } from "../types/viewSnapshot";
import { canonicalScenarioKey, pickPreferredPitchScenario } from "./scenario_adapter.js";
import { containsLegacySouthPacificText, inferScenarioPresentation, isKoreaScenarioContext } from "./view_snapshot.js";

const DEFAULT_WS_HOST = "127.0.0.1";
const DEFAULT_WS_PORT = "8766";

type RpcLike = {
  rpc: (cmd: string, payload?: Record<string, unknown>) => Promise<any>;
};

type RpcErrorShape = {
  code?: string;
  message?: string;
};

export type AdvanceCommandResult = {
  command: "end_turn" | "process_turn";
  dtHoursApplied: boolean;
};

type ScenarioLaunchAttempt = {
  payload: Record<string, unknown>;
};

export class BridgeRpcError extends Error {
  code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = "BridgeRpcError";
    this.code = code;
  }
}

function toObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function toStringMap(value: unknown): Record<string, number> {
  const obj = toObject(value);
  const out: Record<string, number> = {};
  for (const [key, raw] of Object.entries(obj)) {
    if (typeof raw === "number") {
      out[key] = raw;
    }
  }
  return out;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toNonEmptyString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return null;
}

function toStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => toNonEmptyString(item))
    .filter((item): item is string => Boolean(item));
}

function readBridgeEnv(key: string): string | null {
  try {
    const value = import.meta.env?.[key];
    return typeof value === "string" && value.trim() ? value.trim() : null;
  } catch {
    return null;
  }
}

function readBridgeSearchParam(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = new URLSearchParams(window.location.search).get(key);
  return value && value.trim() ? value.trim() : null;
}

function slugifyScenarioId(value: unknown): string {
  const raw = toNonEmptyString(value) ?? "scenario";
  return raw
    .toLowerCase()
    .replace(/\.json$/i, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "scenario";
}

function labelFromValue(value: unknown): string | null {
  const direct = toNonEmptyString(value);
  if (direct) {
    return direct;
  }
  const row = toObject(value);
  for (const key of ["name", "label", "title", "summary", "main_objective", "target_objective", "objective_id", "id"]) {
    const candidate = toNonEmptyString(row[key]);
    if (candidate) {
      return candidate;
    }
  }
  return null;
}

function bandFromPercent(
  value: number | null,
  thresholds: Array<[number, string]>,
): string | null {
  if (value == null) {
    return null;
  }
  for (const [threshold, label] of thresholds) {
    if (value >= threshold) {
      return label;
    }
  }
  return thresholds[thresholds.length - 1]?.[1] ?? null;
}

function inferUnitKind(unit: Record<string, unknown>): string {
  const explicitKind = toNonEmptyString(unit.kind);
  if (explicitKind) {
    return explicitKind;
  }
  const unitType = String(unit.unit_type ?? "").trim().toUpperCase();
  if (unitType === "AIR") {
    return "air";
  }
  if (unitType === "NAVAL") {
    return "naval";
  }
  return "land";
}

function formatSupplyDisplay(value: unknown): string | null {
  const numeric = toFiniteNumber(value);
  if (numeric != null) {
    return `${Math.round(numeric)}%`;
  }
  return toNonEmptyString(value);
}

function buildSyntheticBaiReport(report: Record<string, unknown>, currentHours: number | null) {
  const posture = toNonEmptyString(report.posture);
  const operation = labelFromValue(report.chosen_operation);
  const objective = labelFromValue(report.main_objective);
  const summaryLines = Array.isArray(report.summary_lines)
    ? report.summary_lines.map((item) => String(item)).filter(Boolean)
    : [];
  if (!posture && !operation && !objective && !summaryLines.length) {
    return null;
  }

  const title = [posture, operation].filter(Boolean).join(" • ") || "AI turn report";
  const summary = summaryLines.find((line) => /rationale|objective|reserve/i.test(line))
    ?? [objective ? `Objective ${objective}.` : null, operation ? `Operation ${operation}.` : null].filter(Boolean).join(" ")
    ?? "BAI generated a live turn report.";

  return {
    id: "bai-turn-report",
    kind: "ai_report",
    title,
    summary,
    severity: "info",
    time: currentHours,
    sender_label: "BAI",
    local_area_id: null,
  };
}

function normalizeSnapshotGreaseBoard(raw: unknown): ViewSnapshot["grease_board"] {
  const board = toObject(raw);
  if (!Object.keys(board).length) {
    return null;
  }

  return {
    turn: toNonEmptyString(board.turn),
    objective: toNonEmptyString(board.objective),
    front_status: toNonEmptyString(board.front_status),
    supply_status: toNonEmptyString(board.supply_status),
    main_effort: toNonEmptyString(board.main_effort),
    orders: toStringList(board.orders),
    alerts: toStringList(board.alerts),
    staff_notes: toNonEmptyString(board.staff_notes),
  };
}

function normalizeSnapshotBaiReport(raw: unknown): ViewSnapshot["bai_report"] {
  const report = toObject(raw);
  if (!Object.keys(report).length) {
    return null;
  }

  return {
    posture: toNonEmptyString(report.posture),
    main_objective: report.main_objective ?? null,
    chosen_operation: report.chosen_operation ?? null,
    reserve_level: report.reserve_level ?? null,
    timing_breakdown: toObject(report.timing_breakdown),
    tactical_intents: Array.isArray(report.tactical_intents)
      ? report.tactical_intents.map((item) => toObject(item))
      : [],
    unit_orders: Array.isArray(report.unit_orders)
      ? report.unit_orders.map((item) => toObject(item))
      : [],
    attack_reason_summaries: toStringList(report.attack_reason_summaries),
    hold_reason_summaries: toStringList(report.hold_reason_summaries),
    summary_lines: toStringList(report.summary_lines),
  };
}

function normalizeReportSeverity(value: unknown): string {
  const raw = String(value ?? "").trim().toLowerCase();
  if (raw === "warning" || raw === "warn" || raw === "error" || raw === "critical") {
    return "warning";
  }
  return "info";
}

function buildLogReportTitle(log: Record<string, unknown>): string {
  const src = toNonEmptyString(log.src) ?? "ENGINE";
  const phase = toNonEmptyString(log.phase);
  if (src.toUpperCase() === "BAI" && phase?.toLowerCase() === "orders") {
    return "BAI Orders";
  }
  if (src.toUpperCase() === "BAI" && phase?.toLowerCase() === "turn") {
    return "BAI Turn Assessment";
  }
  if (src.toUpperCase() === "ENGINE" && phase?.toLowerCase() === "turn") {
    return "Turn Progression";
  }
  if (src.toUpperCase() === "G4") {
    return "Logistics Update";
  }
  if (src.toUpperCase() === "G8") {
    return "Objective Update";
  }
  if (phase) {
    return `${src} ${phase}`.trim();
  }
  return `${src} Update`;
}

function buildLogReportKind(log: Record<string, unknown>): string {
  const phase = toNonEmptyString(log.phase);
  if (phase) {
    return phase.toLowerCase();
  }
  const src = toNonEmptyString(log.src);
  return src ? src.toLowerCase() : "status";
}

function buildLogReportSeverity(log: Record<string, unknown>): string {
  const message = String(log.message ?? "").toLowerCase();
  if (/(routed|broken|collapse|critical|threat|warning|low supply|shaken|loss)/.test(message)) {
    return "warning";
  }
  return normalizeReportSeverity(log.severity);
}

function buildLogReportTime(
  log: Record<string, unknown>,
  currentHours: number | null,
  currentTurn: number | null,
): number | null {
  const explicitTime = toFiniteNumber(log.time);
  if (explicitTime != null) {
    return explicitTime;
  }
  const logTurn = toFiniteNumber(log.turn);
  if (currentHours != null && currentTurn != null && logTurn != null) {
    return Math.max(0, currentHours - Math.max(0, currentTurn - logTurn) * 24);
  }
  return currentHours;
}

function buildReportsFromLogs(
  logs: unknown[],
  currentHours: number | null,
  currentTurn: number | null,
): ViewSnapshot["reports"]["recent"] {
  return logs.flatMap((item, index) => {
    if (typeof item === "string") {
      const summary = item.trim();
      if (!summary) {
        return [];
      }
      return [{
        id: `log-${index}`,
        kind: "status",
        title: "Situation Log",
        summary,
        severity: "info",
        time: currentHours,
        sender_label: "ENGINE",
        local_area_id: null,
      }];
    }

    const log = toObject(item);
    const summary = String(log.message ?? "").trim();
    if (!summary) {
      return [];
    }

    const src = toNonEmptyString(log.src) ?? "ENGINE";
    const phase = buildLogReportKind(log);
    const turn = toFiniteNumber(log.turn);

    return [{
      id: String(log.id ?? `log-${src}-${turn ?? "na"}-${index}`),
      kind: phase,
      title: buildLogReportTitle(log),
      summary,
      severity: buildLogReportSeverity(log),
      time: buildLogReportTime(log, currentHours, currentTurn),
      sender_label: src,
      local_area_id: toNonEmptyString(log.local_area_id),
    }];
  });
}

function mergeReportRows(
  ...groups: ViewSnapshot["reports"]["recent"][]
): ViewSnapshot["reports"]["recent"] {
  const merged: ViewSnapshot["reports"]["recent"] = [];
  const seenIds = new Set<string>();
  const seenFingerprints = new Set<string>();

  for (const group of groups) {
    for (const row of group) {
      const id = String(row?.id ?? "").trim();
      if (!id) {
        continue;
      }
      const fingerprint = [
        row.kind,
        row.title,
        row.summary,
        row.sender_label ?? "",
        row.time ?? "",
      ].join("::").toLowerCase();

      if (seenIds.has(id) || seenFingerprints.has(fingerprint)) {
        continue;
      }

      seenIds.add(id);
      seenFingerprints.add(fingerprint);
      merged.push(row);
    }
  }

  return merged;
}

function buildLocationKeys(row: Record<string, unknown>): string[] {
  const keys = new Set<string>();
  for (const key of ["location_id", "objective_id", "id", "name"]) {
    const value = toNonEmptyString(row[key]);
    if (value) {
      keys.add(value);
    }
  }
  return [...keys];
}

function buildSyntheticAnchor(index: number, total: number) {
  const columns = Math.max(2, Math.ceil(Math.sqrt(Math.max(total, 1))));
  const spacingX = 3.6;
  const spacingY = 2.8;
  const col = index % columns;
  const row = Math.floor(index / columns);
  return {
    x: Number((3 + col * spacingX).toFixed(2)),
    y: Number((3 + row * spacingY).toFixed(2)),
  };
}

function buildLocationAnchors(
  units: unknown[],
  objectives: unknown[],
  airfields: unknown[],
  ports: unknown[],
  namedFeatures: unknown[],
) {
  const anchors = new Map<string, { x: number; y: number }>();
  const pending = new Set<string>();

  const register = (key: string | null, x: number | null, y: number | null) => {
    if (!key || x == null || y == null || anchors.has(key)) {
      return;
    }
    anchors.set(key, { x, y });
  };

  const registerRow = (item: unknown) => {
    const row = toObject(item);
    const x = toFiniteNumber(row.x);
    const y = toFiniteNumber(row.y);
    const keys = buildLocationKeys(row);
    if (x != null && y != null) {
      for (const key of keys) {
        register(key, x, y);
      }
      return;
    }
    for (const key of keys) {
      if (!anchors.has(key)) {
        pending.add(key);
      }
    }
  };

  [...objectives, ...airfields, ...ports, ...namedFeatures, ...units].forEach(registerRow);

  [...pending]
    .sort((left, right) => left.localeCompare(right))
    .forEach((key, index, ordered) => {
      if (!anchors.has(key)) {
        anchors.set(key, buildSyntheticAnchor(index, ordered.length));
      }
    });

  return anchors;
}

function buildUnitOffset(index: number, total: number) {
  if (total <= 1) {
    return { x: 0, y: 0 };
  }
  const angle = (Math.PI * 2 * index) / total;
  const radius = Math.min(0.42, 0.22 + total * 0.035);
  return {
    x: Number((Math.cos(angle) * radius).toFixed(2)),
    y: Number((Math.sin(angle) * radius).toFixed(2)),
  };
}

function buildFallbackInspector(
  unit: Record<string, unknown>,
  unitOrder: Record<string, unknown> | null,
): ViewSnapshot["units"][number]["inspector"] {
  const readiness = toFiniteNumber(unit.readiness);
  const morale = toFiniteNumber(unit.morale);
  const fatigue = toFiniteNumber(unit.fatigue);
  const supplyPct = toFiniteNumber(unit.supply);
  const posture = toNonEmptyString(unit.posture);
  const status = toNonEmptyString(unit.status) ?? posture ?? "active";
  const locationId = toNonEmptyString(unit.location_id);
  const orderTarget = toNonEmptyString(unitOrder?.target_location_id ?? unitOrder?.target ?? null);

  return {
    operational_state: {
      strength_pct: toFiniteNumber(unit.strength),
      readiness,
      readiness_band: bandFromPercent(readiness, [[75, "ready"], [50, "limited"], [0, "spent"]]),
      fatigue,
      fatigue_trend: null,
      morale,
      morale_band: bandFromPercent(morale, [[70, "steady"], [45, "shaken"], [0, "fragile"]]),
      cohesion: null,
      posture,
      status,
      location_status: locationId,
      loc: {
        state: locationId ? "connected" : "unavailable",
        label: locationId ? "Connected" : "Unavailable",
        detail: locationId ? `Formation reported at ${locationId}.` : "No live location is exposed.",
        broken_at: null,
      },
    },
    toe: {
      toe_pct: toFiniteNumber(unit.strength),
      men: null,
      tanks: null,
      guns: null,
      vehicles: null,
      missing_summary: null,
    },
    supply: {
      supply_pct: supplyPct,
      supply_display: formatSupplyDisplay(unit.supply),
      supply_days_current: null,
      supply_days_defensive: null,
      supply_days_resting: null,
      fuel: null,
      ammo: null,
      rations: null,
    },
    movement: {
      remaining: null,
      km_remaining: null,
    },
    orders: {
      action: toNonEmptyString(unitOrder?.action ?? unitOrder?.type ?? null),
      status: unitOrder ? "issued" : null,
      lifecycle_state: unitOrder ? "active" : null,
      delay_reason: null,
      note: orderTarget ? `Target ${orderTarget}.` : null,
    },
    replacement_quality: null,
    command: {
      hq_unit_id: toNonEmptyString(unit.hq_unit_id),
      superior: null,
      next_superior: null,
      subordinates: [],
      commander: null,
    },
    attachments_support: {
      attachments: null,
      support: null,
      detached: null,
      detachment_state: null,
    },
    branch_specific: {
      artillery: null,
    },
  };
}

function normalizeSnapshotMapPresentationBounds(
  raw: unknown,
): NonNullable<ViewSnapshot["map_presentation"]>["world_bounds"] {
  const bounds = toObject(raw);
  if (!Object.keys(bounds).length) {
    return null;
  }

  const minX = toFiniteNumber(bounds.min_x ?? bounds.minX);
  const maxX = toFiniteNumber(bounds.max_x ?? bounds.maxX);
  const minY = toFiniteNumber(bounds.min_y ?? bounds.minY);
  const maxY = toFiniteNumber(bounds.max_y ?? bounds.maxY);

  if (minX == null || maxX == null || minY == null || maxY == null) {
    return null;
  }
  if (maxX <= minX || maxY <= minY) {
    return null;
  }

  return {
    min_x: minX,
    max_x: maxX,
    min_y: minY,
    max_y: maxY,
  };
}

function normalizeSnapshotMapPresentation(raw: unknown): ViewSnapshot["map_presentation"] {
  const presentation = toObject(raw);
  if (!Object.keys(presentation).length) {
    return null;
  }

  const worldBounds = normalizeSnapshotMapPresentationBounds(
    presentation.world_bounds ?? presentation.worldBounds,
  );
  const basemapRawBounds = normalizeSnapshotMapPresentationBounds(
    presentation.basemap_raw_bounds ?? presentation.basemapRawBounds,
  );
  const rawFocusPoints = presentation.focus_points ?? presentation.focusPoints;
  const focusPoints = Array.isArray(rawFocusPoints)
    ? rawFocusPoints.flatMap((item) => {
        const row = toObject(item);
        const x = toFiniteNumber(row.x);
        const y = toFiniteNumber(row.y);
        if (x == null || y == null) {
          return [];
        }
        return [{
          id: toNonEmptyString(row.id),
          label: toNonEmptyString(row.label),
          x,
          y,
        }];
      })
    : [];

  if (!worldBounds && !basemapRawBounds && !focusPoints.length) {
    return null;
  }

  return {
    world_bounds: worldBounds,
    basemap_raw_bounds: basemapRawBounds,
    focus_points: focusPoints,
    hex_scale_km: toFiniteNumber(presentation.hex_scale_km ?? presentation.hexScaleKm),
    playable_scale_locked: typeof presentation.playable_scale_locked === "boolean"
      ? presentation.playable_scale_locked
      : typeof presentation.playableScaleLocked === "boolean"
        ? presentation.playableScaleLocked
        : null,
  };
}

function normalizeMapLabelAnchor(value: unknown): "start" | "middle" | "end" | null {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
  return normalized === "start" || normalized === "middle" || normalized === "end"
    ? normalized
    : null;
}

function unwrapBridgeEnvelope(value: unknown): unknown {
  let current = value;

  for (let depth = 0; depth < 4; depth += 1) {
    const row = toObject(current);
    if (!Object.keys(row).length) {
      return current;
    }

    if (row.ok && Object.prototype.hasOwnProperty.call(row, "payload")) {
      current = row.payload;
      continue;
    }
    if (row.status === "ok" && Object.prototype.hasOwnProperty.call(row, "data")) {
      current = row.data;
      continue;
    }
    if (typeof row.type === "string" && row.type.toLowerCase() !== "error" && Object.prototype.hasOwnProperty.call(row, "data")) {
      current = row.data;
      continue;
    }

    return current;
  }

  return current;
}

function inferScenarioRoster(payload: unknown): string[] {
  const resolved = unwrapBridgeEnvelope(payload);
  if (Array.isArray(resolved)) {
    return resolved.map((item) => String(item));
  }

  const root = toObject(resolved);
  const explicitRoster = Array.isArray(root.scenarios)
    ? root.scenarios
    : Array.isArray(root.files)
      ? root.files
      : null;
  if (explicitRoster) {
    return explicitRoster.map((item) => String(item));
  }

  const scenario = toObject(root.scenario);
  const game = toObject(root.game);
  const candidates = [
    toNonEmptyString(scenario.id),
    toNonEmptyString(root.scenario_id),
    toNonEmptyString(game.scenario_id),
    toNonEmptyString(scenario.name),
    typeof root.scenario === "string" ? toNonEmptyString(root.scenario) : null,
    toNonEmptyString(game.scenario),
  ].filter((value): value is string => Boolean(value));
  if (candidates.length) {
    return [candidates[0]];
  }

  const inferred = inferScenarioPresentation(root);
  const inferredLabel = toNonEmptyString(inferred?.scenarioLabel);
  return inferredLabel ? [inferredLabel] : [];
}

export function normalizeSnapshot(payload: unknown): ViewSnapshot {
  const root = toObject(unwrapBridgeEnvelope(payload));
  const game = toObject(root.game);
  const scenario = toObject(root.scenario);
  const engine = toObject(root.engine);
  const engineClock = toObject(engine.clock);
  const time = toObject(root.time);
  const gameTime = toObject(game.time);
  const weather = toObject(root.weather);
  const campaign = toObject(root.campaign);
  const pressure = toObject(root.pressure);
  const reports = toObject(root.reports);
  const staff = toObject(root.staff);
  const ai = toObject(root.ai);
  const gameAi = toObject(game.ai);
  const baiReport = toObject(root.bai_report);
  const forceChanges = toObject(root.force_changes);
  const meta = toObject(root.meta);
  const capabilities = toObject(root.capabilities);
  const greaseBoard = normalizeSnapshotGreaseBoard(root.grease_board);
  const localPressureAreas = Array.isArray(root.local_pressure_areas) ? root.local_pressure_areas : [];
  const namedFeatures = Array.isArray(root.named_features) ? root.named_features : [];
  const airfields = Array.isArray(root.airfields) ? root.airfields : [];
  const ports = Array.isArray(root.ports) ? root.ports : [];
  const mapPresentation = normalizeSnapshotMapPresentation(root.map_presentation ?? meta.map_presentation);
  const navalSupportWindows = Array.isArray(root.naval_support_windows) ? root.naval_support_windows : [];
  const logs = Array.isArray(root.logs)
    ? root.logs
    : Array.isArray(game.logs)
      ? game.logs
      : [];

  const units = Array.isArray(root.units) ? root.units : [];
  const objectives = Array.isArray(root.objectives)
    ? root.objectives
    : Array.isArray(meta.objectives)
      ? meta.objectives
      : [];
  const recent = Array.isArray(reports.recent) ? reports.recent : [];
  const dayValue = toFiniteNumber(time.day ?? gameTime.day ?? engineClock.day);
  const currentHours = toFiniteNumber(time.current_hours)
    ?? toFiniteNumber(engineClock.current_hours)
    ?? (dayValue != null ? Math.max(0, (dayValue - 1) * 24) : null);
  const turnValue = toFiniteNumber(
    time.turn
    ?? gameTime.turn
    ?? engineClock.turn
    ?? engineClock.turn_number
    ?? time.day
    ?? gameTime.day
    ?? engineClock.day,
  );
  const syntheticBaiReport = buildSyntheticBaiReport(baiReport, currentHours);
  const normalizedBaiReport = normalizeSnapshotBaiReport(baiReport);
  const scoreBySide = Object.keys(toStringMap(campaign.score_by_side)).length
    ? toStringMap(campaign.score_by_side)
    : toStringMap(game.vp);
  const reportRows = recent.map((item, index) => {
    const row = toObject(item);
    return {
      id: String(row.id ?? `report-${index}`),
      kind: String(row.kind ?? "report"),
      title: String(row.title ?? "Report"),
      summary: String(row.summary ?? "Operational update."),
      severity: normalizeReportSeverity(row.severity),
      time: typeof row.time === "number" ? row.time : null,
      sender_label: typeof row.sender_label === "string" ? row.sender_label : null,
      local_area_id: typeof row.local_area_id === "string" ? row.local_area_id : null,
    };
  });
  const logRows = buildReportsFromLogs(logs, currentHours, turnValue);
  const reportsRecent = mergeReportRows(reportRows, logRows);
  if (!reportsRecent.length && syntheticBaiReport) {
    reportsRecent.push(syntheticBaiReport);
  }
  const pendingCount = typeof reports.pending_count === "number"
    ? reports.pending_count
    : reportsRecent.length
      ? 0
      : null;
  const normalizedScenarioId = String(
    scenario.id
    ?? root.scenario_id
    ?? game.scenario_id
    ?? slugifyScenarioId(scenario.name ?? root.scenario ?? game.scenario ?? "scenario"),
  );
  const normalizedScenarioName = String(
    scenario.name
    ?? root.scenario_name
    ?? game.scenario_name
    ?? root.scenario
    ?? game.scenario
    ?? "Scenario",
  );
  const fallbackStaffSummary = typeof staff.summary === "string"
    ? staff.summary
    : labelFromValue(baiReport.chosen_operation) ?? "unknown";
  const fallbackAiIntent = typeof ai.last_intent === "string"
    ? ai.last_intent
    : labelFromValue(baiReport.chosen_operation) ?? toNonEmptyString(baiReport.posture);
  const koreaContext = isKoreaScenarioContext({
    scenario: { id: normalizedScenarioId, name: normalizedScenarioName },
    objectives,
    airfields,
    ports,
    local_pressure_areas: localPressureAreas,
    grease_board: greaseBoard,
    bai_report: normalizedBaiReport,
  });
  const sanitizedStaffSummary = koreaContext && containsLegacySouthPacificText(fallbackStaffSummary)
    ? "Staff summary unavailable"
    : fallbackStaffSummary;
  const sanitizedAiIntent = koreaContext && containsLegacySouthPacificText(fallbackAiIntent)
    ? null
    : fallbackAiIntent;

  const locationAnchors = buildLocationAnchors(units, objectives, airfields, ports, namedFeatures);
  const unitsByLocation = new Map<string, number>();
  for (const item of units) {
    const unit = toObject(item);
    const locationId = toNonEmptyString(unit.location_id);
    if (!locationId) {
      continue;
    }
    unitsByLocation.set(locationId, (unitsByLocation.get(locationId) ?? 0) + 1);
  }
  const seenUnitsByLocation = new Map<string, number>();
  const unitOrders = Array.isArray(baiReport.unit_orders) ? baiReport.unit_orders : [];
  const unitOrdersById = new Map(
    unitOrders.flatMap((item) => {
      const row = toObject(item);
      const unitId = toNonEmptyString(row.unit_id);
      return unitId ? [[unitId, row] as const] : [];
    }),
  );

  return {
    scenario: {
      id: normalizedScenarioId,
      name: normalizedScenarioName,
    },
    time: {
      current_hours: currentHours,
      turn: turnValue,
      phase: toNonEmptyString(time.phase)
        ?? toNonEmptyString(gameTime.phase)
        ?? toNonEmptyString(engineClock.phase),
      time_remaining_hours: typeof time.time_remaining_hours === "number" ? time.time_remaining_hours : null,
      deadline_hours: typeof time.deadline_hours === "number" ? time.deadline_hours : null,
    },
    weather: typeof weather.condition === "string" || typeof gameTime.weather === "string"
      ? {
          condition: String(weather.condition ?? gameTime.weather),
          temp_c: toFiniteNumber(weather.temp_c),
          wind_kph: toFiniteNumber(weather.wind_kph),
          ground: typeof weather.ground === "string" ? weather.ground : null,
          summary: typeof weather.summary === "string" ? weather.summary : null,
          forecast: Array.isArray(weather.forecast)
            ? weather.forecast.map((item) => {
                const row = toObject(item);
                return {
                  id: typeof row.id === "string" ? row.id : null,
                  time: typeof row.time === "string" || typeof row.time === "number" ? row.time : null,
                  hour: toFiniteNumber(row.hour),
                  label: typeof row.label === "string" ? row.label : null,
                  condition: typeof row.condition === "string" ? row.condition : null,
                  temp_c: toFiniteNumber(row.temp_c),
                  temperature_c: toFiniteNumber(row.temperature_c),
                  temp: toFiniteNumber(row.temp),
                  wind_kph: toFiniteNumber(row.wind_kph),
                  wind: toFiniteNumber(row.wind),
                  wind_speed_kph: toFiniteNumber(row.wind_speed_kph),
                  precip_mm: toFiniteNumber(row.precip_mm),
                  precip: toFiniteNumber(row.precip),
                  visibility: typeof row.visibility === "string" ? row.visibility : null,
                  sea_state: typeof row.sea_state === "string" ? row.sea_state : null,
                };
              })
            : [],
        }
      : null,
    campaign: {
      status: String(campaign.status ?? (game.scenario ? "active" : "unknown")),
      score_by_side: scoreBySide,
      win_score: typeof campaign.win_score === "number" ? campaign.win_score : null,
      objective_state: Object.fromEntries(
        Object.entries(toObject(campaign.objective_state)).filter(([, value]) => typeof value === "boolean"),
      ) as Record<string, boolean>,
    },
    pressure: {
      active: Boolean(pressure.active),
      summary: typeof pressure.summary === "string" ? pressure.summary : null,
      reasons: Array.isArray(pressure.reasons) ? pressure.reasons.map((item) => String(item)) : [],
      details: toObject(pressure.details),
    },
    reports: {
      pending_count: pendingCount,
      recent: reportsRecent,
    },
    staff: {
      load: typeof staff.load === "number" ? staff.load : null,
      summary: sanitizedStaffSummary,
    },
    ai: {
      enabled: typeof ai.enabled === "boolean" ? ai.enabled : Boolean(gameAi.enabled),
      last_intent: sanitizedAiIntent,
      side: toNonEmptyString(ai.side) ?? toNonEmptyString(gameAi.side),
      requested: typeof gameAi.requested === "boolean" ? gameAi.requested : undefined,
      controller_available: typeof gameAi.controller_available === "boolean" ? gameAi.controller_available : undefined,
      last_orders: toFiniteNumber(ai.last_orders ?? gameAi.last_orders),
      budget_exceeded: typeof gameAi.budget_exceeded === "boolean" ? gameAi.budget_exceeded : undefined,
    },
    grease_board: greaseBoard,
    bai_report: normalizedBaiReport,
    map_presentation: mapPresentation,
    local_pressure_areas: localPressureAreas.map((item, index) => {
      const area = toObject(item);
      const defensivePreparation = toObject(area.defensive_preparation);
      const hasDefensivePreparation = Object.keys(defensivePreparation).length > 0;
      const anchorKey = toNonEmptyString(area.location_id) ?? toNonEmptyString(area.objective_id) ?? toNonEmptyString(area.id);
      const anchor = anchorKey ? locationAnchors.get(anchorKey) ?? null : null;
      return {
        id: String(area.id ?? `local-area-${index}`),
        label: String(area.label ?? area.id ?? "Local Area"),
        kind: String(area.kind ?? "location"),
        location_id: typeof area.location_id === "string" ? area.location_id : null,
        objective_id: typeof area.objective_id === "string" ? area.objective_id : null,
        pressure_reasons: Array.isArray(area.pressure_reasons) ? area.pressure_reasons.map((value) => String(value)) : [],
        defensive_preparation: hasDefensivePreparation
          ? {
              state: typeof defensivePreparation.state === "string" ? defensivePreparation.state : null,
              fortification_state: typeof defensivePreparation.fortification_state === "string" ? defensivePreparation.fortification_state : null,
              obstacle_state: typeof defensivePreparation.obstacle_state === "string" ? defensivePreparation.obstacle_state : null,
              engineer_state: typeof defensivePreparation.engineer_state === "string" ? defensivePreparation.engineer_state : null,
            }
          : null,
        x: toFiniteNumber(area.x) ?? anchor?.x ?? null,
        y: toFiniteNumber(area.y) ?? anchor?.y ?? null,
      };
    }),
    named_features: namedFeatures.map((item, index) => {
      const feature = toObject(item);
      const anchorKey = toNonEmptyString(feature.location_id) ?? toNonEmptyString(feature.objective_id) ?? toNonEmptyString(feature.id);
      const anchor = anchorKey ? locationAnchors.get(anchorKey) ?? null : null;
      return {
        id: String(feature.id ?? `named-feature-${index}`),
        label: String(feature.label ?? feature.id ?? "Named Feature"),
        map_label: toNonEmptyString(feature.map_label),
        kind: String(feature.kind ?? "feature"),
        geometry_type: String(feature.geometry_type ?? (Array.isArray(feature.points) ? "line" : "point")),
        location_id: typeof feature.location_id === "string" ? feature.location_id : null,
        objective_id: typeof feature.objective_id === "string" ? feature.objective_id : null,
        visibility: typeof feature.visibility === "string" ? feature.visibility : "operational",
        label_priority: toFiniteNumber(feature.label_priority),
        label_offset_x: toFiniteNumber(feature.label_offset_x),
        label_offset_y: toFiniteNumber(feature.label_offset_y),
        label_anchor: normalizeMapLabelAnchor(feature.label_anchor),
        aliases: Array.isArray(feature.aliases)
          ? feature.aliases.map((alias) => {
              const row = toObject(alias);
              return {
                name: String(row.name ?? ""),
                era: String(row.era ?? "alias"),
              };
            }).filter((alias) => alias.name)
          : [],
        historical_name: typeof feature.historical_name === "string" ? feature.historical_name : null,
        modern_name: typeof feature.modern_name === "string" ? feature.modern_name : null,
        points: Array.isArray(feature.points)
          ? feature.points.flatMap((point) => {
              const row = toObject(point);
              const x = toFiniteNumber(row.x);
              const y = toFiniteNumber(row.y);
              return x == null || y == null ? [] : [{ x, y }];
            })
          : [],
        x: toFiniteNumber(feature.x) ?? anchor?.x ?? null,
        y: toFiniteNumber(feature.y) ?? anchor?.y ?? null,
      };
    }),
    airfields: airfields.map((item, index) => {
      const field = toObject(item);
      const anchorKey = toNonEmptyString(field.location_id) ?? toNonEmptyString(field.id) ?? toNonEmptyString(field.name);
      const anchor = anchorKey ? locationAnchors.get(anchorKey) ?? null : null;
      return {
        id: String(field.id ?? `airfield-${index}`),
        name: String(field.name ?? field.id ?? "Airfield"),
        location_id: typeof field.location_id === "string" ? field.location_id : null,
        x: toFiniteNumber(field.x) ?? anchor?.x ?? null,
        y: toFiniteNumber(field.y) ?? anchor?.y ?? null,
        map_label: toNonEmptyString(field.map_label),
        label_priority: toFiniteNumber(field.label_priority),
        label_offset_x: toFiniteNumber(field.label_offset_x),
        label_offset_y: toFiniteNumber(field.label_offset_y),
        label_anchor: normalizeMapLabelAnchor(field.label_anchor),
        side: typeof field.side === "string" ? field.side : null,
        state: typeof field.state === "string" ? field.state : null,
        control_state: typeof field.control_state === "string" ? field.control_state : null,
        tier: typeof field.tier === "string" ? field.tier : null,
        readiness: toFiniteNumber(field.readiness),
        readiness_band: typeof field.readiness_band === "string" ? field.readiness_band : null,
        damaged: typeof field.damaged === "boolean" ? field.damaged : null,
        destroyed: typeof field.destroyed === "boolean" ? field.destroyed : null,
        damage_state: typeof field.damage_state === "string" ? field.damage_state : null,
        sortie_active: typeof field.sortie_active === "boolean" ? field.sortie_active : null,
        sortie_status: typeof field.sortie_status === "string" ? field.sortie_status : null,
      };
    }),
    ports: ports.map((item, index) => {
      const port = toObject(item);
      const anchorKey = toNonEmptyString(port.location_id) ?? toNonEmptyString(port.id) ?? toNonEmptyString(port.name);
      const anchor = anchorKey ? locationAnchors.get(anchorKey) ?? null : null;
      return {
        id: String(port.id ?? `port-${index}`),
        name: String(port.name ?? port.id ?? "Port"),
        location_id: typeof port.location_id === "string" ? port.location_id : null,
        x: toFiniteNumber(port.x) ?? anchor?.x ?? null,
        y: toFiniteNumber(port.y) ?? anchor?.y ?? null,
        map_label: toNonEmptyString(port.map_label),
        label_priority: toFiniteNumber(port.label_priority),
        label_offset_x: toFiniteNumber(port.label_offset_x),
        label_offset_y: toFiniteNumber(port.label_offset_y),
        label_anchor: normalizeMapLabelAnchor(port.label_anchor),
        side: typeof port.side === "string" ? port.side : null,
        state: typeof port.state === "string" ? port.state : null,
        control_state: typeof port.control_state === "string" ? port.control_state : null,
        tier: typeof port.tier === "string" ? port.tier : null,
        readiness: toFiniteNumber(port.readiness),
        readiness_band: typeof port.readiness_band === "string" ? port.readiness_band : null,
        damaged: typeof port.damaged === "boolean" ? port.damaged : null,
        destroyed: typeof port.destroyed === "boolean" ? port.destroyed : null,
        damage_state: typeof port.damage_state === "string" ? port.damage_state : null,
      };
    }),
    naval_support_windows: navalSupportWindows.map((item, index) => {
      const window = toObject(item);
      return {
        id: String(window.id ?? `naval-window-${index}`),
        label: String(window.label ?? window.id ?? "Naval support"),
        side: String(window.side ?? "NEUTRAL"),
        start_hour: toFiniteNumber(window.start_hour),
        end_hour: toFiniteNumber(window.end_hour),
      };
    }),
    units: units.map((item) => {
      const unit = toObject(item);
      const inspector = toObject(unit.inspector);
      const locationId = typeof unit.location_id === "string" ? unit.location_id : null;
      const anchor = locationId ? locationAnchors.get(locationId) ?? null : null;
      const locationIndex = locationId ? (seenUnitsByLocation.get(locationId) ?? 0) : 0;
      const locationCount = locationId ? (unitsByLocation.get(locationId) ?? 1) : 1;
      if (locationId) {
        seenUnitsByLocation.set(locationId, locationIndex + 1);
      }
      const unitOffset = buildUnitOffset(locationIndex, locationCount);
      const unitId = String(unit.id ?? "");
      const fallbackInspector = buildFallbackInspector(unit, unitOrdersById.get(unitId) ?? null);
      return {
        id: unitId,
        name: String(unit.name ?? unit.id ?? "Unit"),
        side: String(unit.side ?? "UNKNOWN"),
        kind: inferUnitKind(unit),
        unit_type: typeof unit.unit_type === "string" ? unit.unit_type : null,
        location_id: locationId,
        map_label: toNonEmptyString(unit.map_label),
        label_priority: toFiniteNumber(unit.label_priority),
        label_offset_x: toFiniteNumber(unit.label_offset_x),
        label_offset_y: toFiniteNumber(unit.label_offset_y),
        label_anchor: normalizeMapLabelAnchor(unit.label_anchor),
        fatigue: toFiniteNumber(unit.fatigue),
        posture: toNonEmptyString(unit.posture),
        x: toFiniteNumber(unit.x) ?? (anchor ? Number((anchor.x + unitOffset.x).toFixed(2)) : null),
        y: toFiniteNumber(unit.y) ?? (anchor ? Number((anchor.y + unitOffset.y).toFixed(2)) : null),
        strength: toFiniteNumber(unit.strength),
        readiness: toFiniteNumber(unit.readiness),
        readiness_band: typeof unit.readiness_band === "string"
          ? unit.readiness_band
          : bandFromPercent(toFiniteNumber(unit.readiness), [[75, "Ready"], [50, "Limited"], [0, "Spent"]]),
        morale: toFiniteNumber(unit.morale),
        morale_band: typeof unit.morale_band === "string"
          ? unit.morale_band
          : bandFromPercent(toFiniteNumber(unit.morale), [[70, "Steady"], [45, "Shaken"], [0, "Fragile"]]),
        supply: typeof unit.supply === "string" ? unit.supply : formatSupplyDisplay(unit.supply),
        status: typeof unit.status === "string" ? unit.status : toNonEmptyString(unit.posture),
        inspector: Object.keys(inspector).length
          ? (inspector as ViewSnapshot["units"][number]["inspector"])
          : fallbackInspector,
      };
    }),
    objectives: objectives.map((item) => {
      const objective = toObject(item);
      const objectiveId = String(objective.id ?? objective.location_id ?? objective.name ?? "");
      const objectiveName = String(objective.name ?? objective.location_id ?? objective.id ?? "Objective");
      const anchorKey = toNonEmptyString(objective.location_id) ?? toNonEmptyString(objective.id) ?? toNonEmptyString(objective.name);
      const anchor = anchorKey ? locationAnchors.get(anchorKey) ?? null : null;
      const derivedState = typeof objective.state === "string"
        ? objective.state
        : typeof objective.controlled === "boolean"
          ? objective.controlled
            ? `held_${String(objective.side ?? "unknown").toLowerCase()}`
            : "unheld"
          : "unheld";
      return {
        id: objectiveId,
        name: objectiveName,
        location_id: typeof objective.location_id === "string" ? objective.location_id : null,
        x: toFiniteNumber(objective.x) ?? anchor?.x ?? null,
        y: toFiniteNumber(objective.y) ?? anchor?.y ?? null,
        map_label: toNonEmptyString(objective.map_label),
        label_priority: toFiniteNumber(objective.label_priority),
        label_offset_x: toFiniteNumber(objective.label_offset_x),
        label_offset_y: toFiniteNumber(objective.label_offset_y),
        label_anchor: normalizeMapLabelAnchor(objective.label_anchor),
        side: typeof objective.side === "string" ? objective.side : null,
        value: toFiniteNumber(objective.value),
        controlled: typeof objective.controlled === "boolean" ? objective.controlled : null,
        state: String(derivedState),
        objective_type: typeof objective.objective_type === "string" ? objective.objective_type : null,
        importance_tier: toFiniteNumber(objective.importance_tier),
        visibility: typeof objective.visibility === "string" ? objective.visibility : "operational",
        owner: typeof objective.owner === "string" ? objective.owner : null,
        capture_conditions: Object.keys(toObject(objective.capture_conditions)).length ? toObject(objective.capture_conditions) : null,
        aliases: Array.isArray(objective.aliases)
          ? objective.aliases.map((alias) => {
              const row = toObject(alias);
              return {
                name: String(row.name ?? ""),
                era: String(row.era ?? "alias"),
              };
            }).filter((alias) => alias.name)
          : [],
        historical_name: typeof objective.historical_name === "string" ? objective.historical_name : null,
        modern_name: typeof objective.modern_name === "string" ? objective.modern_name : null,
      };
    }),
    force_changes: {
      reinforcements: Array.isArray(forceChanges.reinforcements) ? forceChanges.reinforcements as ViewSnapshot["force_changes"]["reinforcements"] : [],
      withdrawals: Array.isArray(forceChanges.withdrawals) ? forceChanges.withdrawals as ViewSnapshot["force_changes"]["withdrawals"] : [],
      replacement_events: Array.isArray(forceChanges.replacement_events) ? forceChanges.replacement_events as ViewSnapshot["force_changes"]["replacement_events"] : [],
    },
    capabilities: {
      can_save_snapshot: Boolean(capabilities.can_save_snapshot),
      can_load_snapshot: Boolean(capabilities.can_load_snapshot),
      can_export_replay: Boolean(capabilities.can_export_replay),
    },
  };
}

function preferredScenario(scenarios: string[]): string | null {
  return pickPreferredPitchScenario(scenarios);
}

function scenarioLaunchAttempts(name: string): ScenarioLaunchAttempt[] {
  const raw = toNonEmptyString(name) ?? "";
  const canonical = canonicalScenarioKey(raw);
  const attempts: ScenarioLaunchAttempt[] = [];
  const seen = new Set<string>();

  const pushAttempt = (payload: Record<string, unknown>) => {
    const key = JSON.stringify(payload);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    attempts.push({ payload });
  };

  if (raw) {
    pushAttempt({ name: raw });
  }
  if (canonical && canonical !== raw.replace(/\.json$/i, "")) {
    pushAttempt({ name: canonical });
  } else if (canonical && !/\.json$/i.test(raw)) {
    pushAttempt({ name: canonical });
  }
  if (canonical) {
    pushAttempt({ id: canonical });
  }

  return attempts;
}

async function rpcPayload<T>(rpc: RpcLike, cmd: string, payload: Record<string, unknown> = {}): Promise<T> {
  const response: any = await rpc.rpc(cmd, payload);

  if (response?.status === "error" || response?.type === "error") {
    const legacyError = toObject(response?.data);
    const error = toObject(response?.error) as RpcErrorShape;
    throw new BridgeRpcError(
      toNonEmptyString(error.message ?? legacyError.message) || `${cmd} failed`,
      toNonEmptyString(error.code ?? legacyError.code),
    );
  }

  if (response?.ok || response?.status === "ok" || (response?.type && "data" in response)) {
    return unwrapBridgeEnvelope(response) as T;
  }

  const error = toObject(response?.error) as RpcErrorShape;
  throw new BridgeRpcError(toNonEmptyString(error.message) || `${cmd} failed`, toNonEmptyString(error.code));
}

export async function fetchViewSnapshot(rpc: RpcLike): Promise<ViewSnapshot> {
  const payload = await rpcPayload<unknown>(rpc, "view.snapshot", {});
  return normalizeSnapshot(payload);
}

export async function listScenarios(rpc: RpcLike): Promise<string[]> {
  const payload = await rpcPayload<unknown>(rpc, "list_scenarios", {});
  return inferScenarioRoster(payload);
}

export async function launchScenario(rpc: RpcLike, name: string): Promise<void> {
  let lastError: unknown = null;

  for (const attempt of scenarioLaunchAttempts(name)) {
    try {
      await rpcPayload(rpc, "load_scenario", attempt.payload);
      try {
        await rpcPayload(rpc, "start_game", {});
      } catch (error) {
        if (!isFallbackEligible(error)) {
          throw error;
        }
      }
      return;
    } catch (error) {
      if (!isFallbackEligible(error)) {
        throw error;
      }
      lastError = error;
    }
  }

  throw lastError ?? new BridgeRpcError(`Unable to launch scenario ${name}`);
}

function isFallbackEligible(error: unknown): boolean {
  if (!(error instanceof BridgeRpcError)) {
    return false;
  }
  const message = error.message.toLowerCase();
  const code = String(error.code ?? "").toLowerCase();
  return (
    code === "bad_request"
    || code === "not_found"
    || code === "unknown_command"
    || code === "unsupported"
    || code === "unsupported_command"
    || code === "method_not_found"
    || /unknown|unsupported|not found|unavailable|missing|invalid/.test(message)
  );
}

export async function stepHours(rpc: RpcLike, dtHours: number): Promise<AdvanceCommandResult> {
  try {
    await rpcPayload(rpc, "end_turn", { dt_hours: dtHours });
    return { command: "end_turn", dtHoursApplied: true };
  } catch (error) {
    if (!isFallbackEligible(error)) {
      throw error;
    }
  }

  try {
    await rpcPayload(rpc, "end_turn", {});
    return { command: "end_turn", dtHoursApplied: false };
  } catch (error) {
    if (!isFallbackEligible(error)) {
      throw error;
    }
  }

  await rpcPayload(rpc, "process_turn", {});
  return { command: "process_turn", dtHoursApplied: false };
}

export async function setAiEnabled(rpc: RpcLike, enabled: boolean): Promise<void> {
  await rpcPayload(rpc, "ai.enable", { enabled });
}

export async function bootstrapDemoScenario(rpc: RpcLike): Promise<string | null> {
  const scenarios = await listScenarios(rpc);
  const scenario = preferredScenario(scenarios);
  if (!scenario) {
    return null;
  }
  await launchScenario(rpc, scenario);
  return scenario;
}

export function wsUrl(): string {
  const explicitUrl = readBridgeSearchParam("bridge") || readBridgeEnv("VITE_BRIDGE_URL");
  if (explicitUrl) {
    return explicitUrl;
  }

  const host = readBridgeSearchParam("bridge_host") || readBridgeEnv("VITE_BRIDGE_HOST") || DEFAULT_WS_HOST;
  const port = readBridgeSearchParam("bridge_port") || readBridgeEnv("VITE_BRIDGE_PORT") || DEFAULT_WS_PORT;
  return `ws://${host}:${port}`;
}
