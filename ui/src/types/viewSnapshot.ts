export interface SnapshotScenario {
  id: string;
  name: string;
}

export interface SnapshotTime {
  current_hours: number | null;
  turn: number | null;
  phase: string | null;
  time_remaining_hours: number | null;
  deadline_hours: number | null;
}

export interface SnapshotWeatherForecastRow {
  id?: string | null;
  time?: string | number | null;
  hour?: number | null;
  label?: string | null;
  condition?: string | null;
  temp_c?: number | null;
  temperature_c?: number | null;
  temp?: number | null;
  wind_kph?: number | null;
  wind?: number | null;
  wind_speed_kph?: number | null;
  precip_mm?: number | null;
  precip?: number | null;
  visibility?: string | null;
  sea_state?: string | null;
}

export interface SnapshotWeather {
  condition: string | null;
  temp_c: number | null;
  wind_kph: number | null;
  ground: string | null;
  summary: string | null;
  forecast: SnapshotWeatherForecastRow[];
}

export interface SnapshotCampaign {
  status: string;
  score_by_side: Record<string, number>;
  win_score: number | null;
  objective_state: Record<string, boolean>;
}

export interface SnapshotPressure {
  active: boolean;
  summary: string | null;
  reasons: string[];
  details: Record<string, unknown>;
}

export interface SnapshotReportRow {
  id: string;
  kind: string;
  title: string;
  summary: string;
  severity: string;
  time: number | null;
  sender_label?: string | null;
  local_area_id?: string | null;
}

export interface SnapshotReports {
  pending_count: number | null;
  recent: SnapshotReportRow[];
}

export interface SnapshotStaff {
  load: number | null;
  summary: string;
}

export interface SnapshotAI {
  enabled: boolean;
  last_intent: string | null;
  side?: string | null;
  requested?: boolean;
  controller_available?: boolean;
  last_orders?: number | null;
  budget_exceeded?: boolean;
}

export interface SnapshotGreaseBoard {
  turn: string | null;
  objective: string | null;
  front_status: string | null;
  supply_status: string | null;
  main_effort: string | null;
  orders: string[];
  alerts: string[];
  staff_notes?: string | null;
}

export interface SnapshotBaiReport {
  posture: string | null;
  main_objective: unknown;
  chosen_operation: unknown;
  reserve_level: unknown;
  timing_breakdown: Record<string, unknown>;
  tactical_intents: Record<string, unknown>[];
  unit_orders: Record<string, unknown>[];
  attack_reason_summaries: string[];
  hold_reason_summaries: string[];
  summary_lines: string[];
}

export interface SnapshotForceChangeRow {
  id: string;
  name: string;
  side: string;
  kind: string;
  day: number | null;
  location_id: string | null;
  hq_unit_id: string | null;
  x: number | null;
  y: number | null;
}

export interface SnapshotForceChanges {
  reinforcements: SnapshotForceChangeRow[];
  withdrawals: SnapshotForceChangeRow[];
  replacement_events: SnapshotForceChangeRow[];
}

export interface SnapshotAirfield {
  id: string;
  name: string;
  location_id?: string | null;
  x: number | null;
  y: number | null;
  map_label?: string | null;
  label_priority?: number | null;
  label_offset_x?: number | null;
  label_offset_y?: number | null;
  label_anchor?: string | null;
  side?: string | null;
  state?: string | null;
  control_state?: string | null;
  tier?: string | null;
  readiness?: number | null;
  readiness_band?: string | null;
  damaged?: boolean | null;
  destroyed?: boolean | null;
  damage_state?: string | null;
  sortie_active?: boolean | null;
  sortie_status?: string | null;
}

export interface SnapshotPort {
  id: string;
  name: string;
  location_id?: string | null;
  x: number | null;
  y: number | null;
  map_label?: string | null;
  label_priority?: number | null;
  label_offset_x?: number | null;
  label_offset_y?: number | null;
  label_anchor?: string | null;
  side?: string | null;
  state?: string | null;
  control_state?: string | null;
  tier?: string | null;
  readiness?: number | null;
  readiness_band?: string | null;
  damaged?: boolean | null;
  destroyed?: boolean | null;
  damage_state?: string | null;
}

export interface SnapshotNavalSupportWindow {
  id: string;
  label: string;
  side: string;
  start_hour: number | null;
  end_hour: number | null;
}

export interface SnapshotUnitCountPair {
  on_hand: number | null;
  authorized: number | null;
}

export interface SnapshotUnitInspectorOperationalState {
  strength_pct: number | null;
  readiness: number | null;
  readiness_band: string | null;
  fatigue: number | null;
  fatigue_trend: string | null;
  morale: number | null;
  morale_band: string | null;
  cohesion: number | null;
  posture: string | null;
  status: string | null;
  location_status: string | null;
  loc: SnapshotUnitInspectorLoc;
}

export interface SnapshotUnitInspectorLoc {
  state: "connected" | "threatened" | "broken" | "unavailable";
  label: string;
  detail: string;
  broken_at: string | null;
}

export interface SnapshotUnitInspectorToe {
  toe_pct: number | null;
  men: SnapshotUnitCountPair | null;
  tanks: SnapshotUnitCountPair | null;
  guns: SnapshotUnitCountPair | null;
  vehicles: SnapshotUnitCountPair | null;
  missing_summary: string | null;
}

export interface SnapshotUnitInspectorSupply {
  supply_pct: number | null;
  supply_display: string | null;
  supply_days_current: number | null;
  supply_days_defensive: number | null;
  supply_days_resting: number | null;
  fuel: string | null;
  ammo: Record<string, number> | null;
  rations: string | null;
}

export interface SnapshotUnitInspectorMovement {
  remaining: string | null;
  km_remaining: number | null;
}

export interface SnapshotUnitInspectorOrders {
  action: string | null;
  status: string | null;
  lifecycle_state: string | null;
  delay_reason: string | null;
  note: string | null;
}

export interface SnapshotUnitInspectorReplacementQuality {
  replacement_quality_band: string | null;
  experience_band: string | null;
  newcomer_pct: number | null;
  veteran_core_pct: number | null;
  reconstitution_state: string | null;
  combat_cohesion_state: string | null;
}

export interface SnapshotUnitInspectorCommand {
  hq_unit_id: string | null;
  superior: SnapshotUnitRelationship | null;
  next_superior: SnapshotUnitRelationship | null;
  subordinates: SnapshotUnitRelationship[];
  commander: string | null;
}

export interface SnapshotUnitInspectorAttachmentsSupport {
  attachments: string[] | null;
  support: string[] | null;
  detached: string[] | null;
  detachment_state?: SnapshotUnitInspectorDetachmentState | null;
}

export interface SnapshotUnitInspectorSupportDetachment {
  id: string;
  name: string;
  company_name: string;
  source_battalion_id: string;
  source_battalion_name: string;
  attachment_target_unit_id: string | null;
  attachment_target_unit_name: string | null;
  detachment_type: string;
  detachment_label: string;
  company_equivalent: number;
  strength_pct: number | null;
  equipment: Record<string, unknown>;
  detached_status: boolean;
  cohesion_marker: string | null;
  command_efficiency_marker: string | null;
}

export interface SnapshotUnitInspectorDetachmentState {
  eligible: boolean;
  detachment_type: string | null;
  detachment_label: string | null;
  max_detachments: number | null;
  companies_total: number | null;
  detached_count: number | null;
  remaining_organic_companies: number | null;
  remaining_organic_strength_pct: number | null;
  parent_cohesion_marker: string | null;
  active_detachments: SnapshotUnitInspectorSupportDetachment[];
  attached_detachments: SnapshotUnitInspectorSupportDetachment[];
}

export interface SnapshotUnitInspectorArtillery {
  ammo_rounds: Record<string, number>;
  fire_policy: string | null;
  endurance_days: number | null;
}

export interface SnapshotUnitInspectorBranchSpecific {
  artillery: SnapshotUnitInspectorArtillery | null;
}

export interface SnapshotUnitRelationship {
  id: string | null;
  name: string | null;
  side: string;
  kind: string;
}

export interface SnapshotUnitInspector {
  operational_state: SnapshotUnitInspectorOperationalState;
  toe: SnapshotUnitInspectorToe;
  supply: SnapshotUnitInspectorSupply;
  movement: SnapshotUnitInspectorMovement;
  orders: SnapshotUnitInspectorOrders;
  replacement_quality: SnapshotUnitInspectorReplacementQuality | null;
  command: SnapshotUnitInspectorCommand;
  attachments_support: SnapshotUnitInspectorAttachmentsSupport;
  branch_specific: SnapshotUnitInspectorBranchSpecific;
}

export interface SnapshotUnit {
  id: string;
  name: string;
  side: string;
  kind: string;
  unit_type?: string | null;
  location_id?: string | null;
  map_label?: string | null;
  label_priority?: number | null;
  label_offset_x?: number | null;
  label_offset_y?: number | null;
  label_anchor?: string | null;
  fatigue?: number | null;
  posture?: string | null;
  x: number | null;
  y: number | null;
  strength: number | null;
  readiness: number | null;
  readiness_band: string | null;
  morale: number | null;
  morale_band: string | null;
  supply: string | null;
  status: string | null;
  inspector: SnapshotUnitInspector;
}

export interface SnapshotObjective {
  id: string;
  name: string;
  location_id?: string | null;
  x: number | null;
  y: number | null;
  map_label?: string | null;
  label_priority?: number | null;
  label_offset_x?: number | null;
  label_offset_y?: number | null;
  label_anchor?: string | null;
  side: string | null;
  value: number | null;
  controlled: boolean | null;
  state: string;
  objective_type?: string | null;
  importance_tier?: number | null;
  visibility?: string | null;
  owner?: string | null;
  capture_conditions?: Record<string, unknown> | null;
  aliases?: SnapshotNamedAlias[];
  historical_name?: string | null;
  modern_name?: string | null;
}

export interface SnapshotLocalPressureArea {
  id: string;
  label: string;
  kind: string;
  location_id: string | null;
  objective_id: string | null;
  pressure_reasons: string[];
  defensive_preparation: SnapshotLocalDefensePreparation | null;
  x: number | null;
  y: number | null;
}

export interface SnapshotLocalDefensePreparation {
  state: string | null;
  fortification_state: string | null;
  obstacle_state: string | null;
  engineer_state: string | null;
}

export interface SnapshotNamedAlias {
  name: string;
  era: string;
}

export interface SnapshotNamedFeaturePoint {
  x: number;
  y: number;
}

export interface SnapshotMapPresentationBounds {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
}

export interface SnapshotMapPresentationFocusPoint {
  id: string | null;
  label: string | null;
  x: number;
  y: number;
}

export interface SnapshotMapPresentation {
  world_bounds: SnapshotMapPresentationBounds | null;
  basemap_raw_bounds: SnapshotMapPresentationBounds | null;
  focus_points: SnapshotMapPresentationFocusPoint[];
  hex_scale_km: number | null;
  playable_scale_locked: boolean | null;
}

export interface SnapshotNamedFeature {
  id: string;
  label: string;
  map_label?: string | null;
  kind: string;
  geometry_type: string;
  location_id: string | null;
  objective_id: string | null;
  visibility: string | null;
  label_priority: number | null;
  label_offset_x?: number | null;
  label_offset_y?: number | null;
  label_anchor?: string | null;
  aliases: SnapshotNamedAlias[];
  historical_name: string | null;
  modern_name: string | null;
  points: SnapshotNamedFeaturePoint[];
  x: number | null;
  y: number | null;
}

export interface SnapshotCapabilities {
  can_save_snapshot: boolean;
  can_load_snapshot: boolean;
  can_export_replay: boolean;
}

export interface ViewSnapshot {
  scenario: SnapshotScenario;
  time: SnapshotTime;
  weather: SnapshotWeather | null;
  campaign: SnapshotCampaign;
  pressure: SnapshotPressure;
  reports: SnapshotReports;
  staff: SnapshotStaff;
  ai: SnapshotAI;
  grease_board: SnapshotGreaseBoard | null;
  bai_report: SnapshotBaiReport | null;
  map_presentation: SnapshotMapPresentation | null;
  local_pressure_areas: SnapshotLocalPressureArea[];
  named_features: SnapshotNamedFeature[];
  force_changes: SnapshotForceChanges;
  airfields: SnapshotAirfield[];
  ports: SnapshotPort[];
  naval_support_windows: SnapshotNavalSupportWindow[];
  units: SnapshotUnit[];
  objectives: SnapshotObjective[];
  capabilities: SnapshotCapabilities;
}
