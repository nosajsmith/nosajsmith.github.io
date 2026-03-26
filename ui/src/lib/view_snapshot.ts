import type { ViewSnapshot } from "../types/viewSnapshot";

const DEFAULT_WS_URL = "ws://127.0.0.1:8766";

type RpcLike = {
  rpc: (cmd: string, payload?: Record<string, unknown>) => Promise<any>;
};

type RpcErrorShape = {
  code?: string;
  message?: string;
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

export function normalizeSnapshot(payload: unknown): ViewSnapshot {
  const root = toObject(payload);
  const scenario = toObject(root.scenario);
  const time = toObject(root.time);
  const weather = toObject(root.weather);
  const campaign = toObject(root.campaign);
  const pressure = toObject(root.pressure);
  const reports = toObject(root.reports);
  const staff = toObject(root.staff);
  const ai = toObject(root.ai);
  const capabilities = toObject(root.capabilities);
  const localPressureAreas = Array.isArray(root.local_pressure_areas) ? root.local_pressure_areas : [];
  const namedFeatures = Array.isArray(root.named_features) ? root.named_features : [];
  const airfields = Array.isArray(root.airfields) ? root.airfields : [];
  const ports = Array.isArray(root.ports) ? root.ports : [];
  const navalSupportWindows = Array.isArray(root.naval_support_windows) ? root.naval_support_windows : [];

  const units = Array.isArray(root.units) ? root.units : [];
  const objectives = Array.isArray(root.objectives) ? root.objectives : [];
  const recent = Array.isArray(reports.recent) ? reports.recent : [];

  return {
    scenario: {
      id: String(scenario.id ?? ""),
      name: String(scenario.name ?? "Scenario"),
    },
    time: {
      current_hours: typeof time.current_hours === "number" ? time.current_hours : null,
      turn: typeof time.turn === "number" ? time.turn : null,
      phase: typeof time.phase === "string" ? time.phase : null,
      time_remaining_hours: typeof time.time_remaining_hours === "number" ? time.time_remaining_hours : null,
      deadline_hours: typeof time.deadline_hours === "number" ? time.deadline_hours : null,
    },
    weather: typeof weather.condition === "string"
      ? {
          condition: weather.condition,
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
      status: String(campaign.status ?? "unknown"),
      score_by_side: toStringMap(campaign.score_by_side),
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
      pending_count: typeof reports.pending_count === "number" ? reports.pending_count : null,
      recent: recent.map((item, index) => {
        const row = toObject(item);
        return {
          id: String(row.id ?? `report-${index}`),
          kind: String(row.kind ?? "report"),
          title: String(row.title ?? "Report"),
          summary: String(row.summary ?? "Operational update."),
          severity: String(row.severity ?? "info"),
          time: typeof row.time === "number" ? row.time : null,
          sender_label: typeof row.sender_label === "string" ? row.sender_label : null,
          local_area_id: typeof row.local_area_id === "string" ? row.local_area_id : null,
        };
      }),
    },
    staff: {
      load: typeof staff.load === "number" ? staff.load : null,
      summary: typeof staff.summary === "string" ? staff.summary : "unknown",
    },
    ai: {
      enabled: Boolean(ai.enabled),
      last_intent: typeof ai.last_intent === "string" ? ai.last_intent : null,
    },
    local_pressure_areas: localPressureAreas.map((item, index) => {
      const area = toObject(item);
      const defensivePreparation = toObject(area.defensive_preparation);
      const hasDefensivePreparation = Object.keys(defensivePreparation).length > 0;
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
        x: toFiniteNumber(area.x),
        y: toFiniteNumber(area.y),
      };
    }),
    named_features: namedFeatures.map((item, index) => {
      const feature = toObject(item);
      return {
        id: String(feature.id ?? `named-feature-${index}`),
        label: String(feature.label ?? feature.id ?? "Named Feature"),
        kind: String(feature.kind ?? "feature"),
        geometry_type: String(feature.geometry_type ?? (Array.isArray(feature.points) ? "line" : "point")),
        location_id: typeof feature.location_id === "string" ? feature.location_id : null,
        objective_id: typeof feature.objective_id === "string" ? feature.objective_id : null,
        visibility: typeof feature.visibility === "string" ? feature.visibility : "operational",
        label_priority: toFiniteNumber(feature.label_priority),
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
        x: toFiniteNumber(feature.x),
        y: toFiniteNumber(feature.y),
      };
    }),
    airfields: airfields.map((item, index) => {
      const field = toObject(item);
      return {
        id: String(field.id ?? `airfield-${index}`),
        name: String(field.name ?? field.id ?? "Airfield"),
        x: toFiniteNumber(field.x),
        y: toFiniteNumber(field.y),
      };
    }),
    ports: ports.map((item, index) => {
      const port = toObject(item);
      return {
        id: String(port.id ?? `port-${index}`),
        name: String(port.name ?? port.id ?? "Port"),
        x: toFiniteNumber(port.x),
        y: toFiniteNumber(port.y),
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
      return {
        id: String(unit.id ?? ""),
        name: String(unit.name ?? unit.id ?? "Unit"),
        side: String(unit.side ?? "UNKNOWN"),
        kind: String(unit.kind ?? "land"),
        unit_type: typeof unit.unit_type === "string" ? unit.unit_type : null,
        location_id: typeof unit.location_id === "string" ? unit.location_id : null,
        x: toFiniteNumber(unit.x),
        y: toFiniteNumber(unit.y),
        strength: typeof unit.strength === "number" ? unit.strength : null,
        readiness: typeof unit.readiness === "number" ? unit.readiness : null,
        readiness_band: typeof unit.readiness_band === "string" ? unit.readiness_band : null,
        morale: typeof unit.morale === "number" ? unit.morale : null,
        morale_band: typeof unit.morale_band === "string" ? unit.morale_band : null,
        supply: typeof unit.supply === "string" ? unit.supply : null,
        status: typeof unit.status === "string" ? unit.status : null,
        inspector: inspector as ViewSnapshot["units"][number]["inspector"],
      };
    }),
    objectives: objectives.map((item) => {
      const objective = toObject(item);
      return {
        id: String(objective.id ?? ""),
        name: String(objective.name ?? "Objective"),
        x: toFiniteNumber(objective.x),
        y: toFiniteNumber(objective.y),
        side: typeof objective.side === "string" ? objective.side : null,
        value: typeof objective.value === "number" ? objective.value : null,
        controlled: typeof objective.controlled === "boolean" ? objective.controlled : null,
        state: String(objective.state ?? "unknown"),
        objective_type: typeof objective.objective_type === "string" ? objective.objective_type : null,
        importance_tier: toFiniteNumber(objective.importance_tier),
        visibility: typeof objective.visibility === "string" ? objective.visibility : null,
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
    capabilities: {
      can_save_snapshot: Boolean(capabilities.can_save_snapshot),
      can_load_snapshot: Boolean(capabilities.can_load_snapshot),
      can_export_replay: Boolean(capabilities.can_export_replay),
    },
  };
}

function preferredScenario(scenarios: string[]): string | null {
  const preferred = scenarios.find((item) => item === "inchon_mvp.json");
  return preferred ?? scenarios[0] ?? null;
}

async function rpcPayload<T>(rpc: RpcLike, cmd: string, payload: Record<string, unknown> = {}): Promise<T> {
  const response = await rpc.rpc(cmd, payload);
  if (response?.ok) {
    return response.payload as T;
  }
  const error = toObject(response?.error) as RpcErrorShape;
  throw new BridgeRpcError(error.message || `${cmd} failed`, error.code || null);
}

export async function fetchViewSnapshot(rpc: RpcLike): Promise<ViewSnapshot> {
  const payload = await rpcPayload<unknown>(rpc, "view.snapshot", {});
  return normalizeSnapshot(payload);
}

export async function listScenarios(rpc: RpcLike): Promise<string[]> {
  const payload = await rpcPayload<{ scenarios?: string[] }>(rpc, "list_scenarios", {});
  return Array.isArray(payload?.scenarios) ? payload.scenarios.map((item) => String(item)) : [];
}

export async function launchScenario(rpc: RpcLike, name: string): Promise<void> {
  await rpcPayload(rpc, "load_scenario", { name });
  await rpcPayload(rpc, "start_game", {});
}

export async function stepHours(rpc: RpcLike, dtHours: number): Promise<void> {
  await rpcPayload(rpc, "end_turn", { dt_hours: dtHours });
}

export async function setAiEnabled(rpc: RpcLike, enabled: boolean): Promise<void> {
  await rpcPayload(rpc, "ai.enable", { enabled });
}

export async function bootstrapDemoScenario(rpc: RpcLike): Promise<boolean> {
  const scenarios = await listScenarios(rpc);
  const scenario = preferredScenario(scenarios);
  if (!scenario) {
    return false;
  }
  await launchScenario(rpc, scenario);
  return true;
}

export function wsUrl(): string {
  return DEFAULT_WS_URL;
}
