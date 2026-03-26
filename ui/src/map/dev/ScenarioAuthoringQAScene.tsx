import { useMemo, useState } from "react";
import ObjectiveOverlayBadge from "../../components/shell/ObjectiveOverlayBadge";
import SettlementIcon from "../../components/shell/SettlementIcon";
import { axialToPixel, hexPolygonPoints } from "../../lib/hex.js";
import { normalizeHexTerrain } from "../hexTile.js";

type ScenarioAuthoringQASceneProps = {
  theaterId: string | null;
};

type Coord = [number, number];
type AuthoringMode = "features" | "objectives" | "setup" | "supply";
type FeatureGeometry = "point" | "line" | "zone";
type NamedFeatureKind = "hill" | "ridgeline" | "pass" | "valley" | "sector" | "subsector" | "phase_line";
type ObjectiveType = "primary" | "secondary" | "supply" | "political" | "strategic";
type VisibilityRule = "always" | "far" | "operational" | "close" | "selected_only" | "hidden";
type ZoneKind = "deployment" | "entry" | "withdrawal";
type EntryKind = "map_edge" | "road" | "rail" | "airfield" | "port_entry" | "off_map_road" | "off_map_rail";
type SupplyKind = "depot" | "port" | "harbor" | "off_map" | "railhead" | "airhead";

type BaseHex = {
  hex_id: string;
  q: number;
  r: number;
  terrain_class: string;
  road_class?: string | null;
  rail_class?: string | null;
  coastline?: boolean;
  settlement_name?: string | null;
  airfield_name?: string | null;
};

type NamedFeatureRow = {
  id: string;
  label: string;
  kind: NamedFeatureKind;
  geometry_type: FeatureGeometry;
  position?: Coord;
  points?: Coord[];
  visibility: VisibilityRule;
  label_priority: number;
  objective_id?: string | null;
  note?: string | null;
  aliases?: Array<{ name: string; era: string }>;
  provenance?: Record<string, string>;
  ui_hexes?: Coord[];
};

type ObjectiveRow = {
  id: string;
  title: string;
  name: string;
  objective_type: ObjectiveType;
  category: ObjectiveType;
  importance_tier: number;
  value: number;
  owner: string | null;
  visibility: VisibilityRule;
  position: Coord;
  note?: string | null;
  provenance?: Record<string, string>;
};

type ZoneRow = {
  id: string;
  label: string;
  side: string | null;
  points: Coord[];
  anchor: Coord | null;
  note?: string | null;
  provenance?: Record<string, string>;
  ui_hexes?: Coord[];
  formation_ids?: string[];
  allowed_unit_types?: string[];
  setup_tags?: string[];
  entry_kind?: EntryKind;
  route_class?: string | null;
  linked_location_id?: string | null;
  extraction_kind?: string;
};

type SetupRestrictionRow = {
  id: string;
  formation_id: string;
  zone_id: string | null;
  allowed_unit_types: string[];
  note?: string | null;
  provenance?: Record<string, string>;
};

type ReinforcementRow = {
  id: string;
  name: string;
  side: string | null;
  unit_type: string;
  entry_zone_id: string | null;
  arrival_day: number | null;
  scripted_hook?: string | null;
  note?: string | null;
  provenance?: Record<string, string>;
};

type SupplySourceRow = {
  id: string;
  label: string;
  side: string | null;
  daily_supply: number;
  kind: SupplyKind;
  coord: Coord;
  note?: string | null;
  provenance?: Record<string, string>;
};

type OffMapLinkRow = {
  id: string;
  label: string;
  side: string | null;
  source_node_id: string;
  entry_zone_id: string | null;
  route_class: string;
  capacity: number;
  note?: string | null;
  provenance?: Record<string, string>;
};

type ScenarioAuthoringState = {
  scenario_id: string | null;
  theater_id: string | null;
  named_features: NamedFeatureRow[];
  objectives: ObjectiveRow[];
  deployment_zones: ZoneRow[];
  setup_restrictions: SetupRestrictionRow[];
  reinforcement_entry_zones: ZoneRow[];
  reinforcements: ReinforcementRow[];
  supply_sources: SupplySourceRow[];
  off_map_links: OffMapLinkRow[];
  withdrawal_zones: ZoneRow[];
  scripted_arrivals: Array<Record<string, unknown>>;
  withdrawals: Array<Record<string, unknown>>;
};

type ValidationIssue = {
  severity: "error" | "warning";
  code: string;
  message: string;
};

type FeatureFormState = {
  id: string;
  label: string;
  kind: NamedFeatureKind;
  geometry: FeatureGeometry;
  visibility: VisibilityRule;
  priority: number;
  objectiveId: string;
  note: string;
  source: string;
  confidence: string;
};

type ObjectiveFormState = {
  id: string;
  label: string;
  objectiveType: ObjectiveType;
  visibility: VisibilityRule;
  owner: string;
  value: number;
  priority: number;
  note: string;
  source: string;
  confidence: string;
};

type ZoneFormState = {
  id: string;
  label: string;
  zoneKind: ZoneKind;
  side: string;
  entryKind: EntryKind;
  routeClass: string;
  note: string;
  source: string;
  confidence: string;
};

type RestrictionFormState = {
  id: string;
  formationId: string;
  zoneId: string;
  allowedTypes: string;
};

type ReinforcementFormState = {
  id: string;
  name: string;
  side: string;
  unitType: string;
  entryZoneId: string;
  arrivalDay: string;
};

type SupplyFormState = {
  id: string;
  label: string;
  side: string;
  kind: SupplyKind;
  dailySupply: number;
  note: string;
  source: string;
  confidence: string;
};

type LinkFormState = {
  id: string;
  label: string;
  side: string;
  sourceNodeId: string;
  entryZoneId: string;
  routeClass: string;
  capacity: number;
};

const HEX_SIZE = 24;
const SCENE_WIDTH = 440;
const SCENE_HEIGHT = 286;
const SCENE_OFFSET_X = 88;
const SCENE_OFFSET_Y = 78;
const HEX_DIRS: Coord[] = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];

const BASE_HEXES: BaseHex[] = [
  { hex_id: "auth:0:0", q: 0, r: 0, terrain_class: "hills", road_class: null, rail_class: null },
  { hex_id: "auth:1:0", q: 1, r: 0, terrain_class: "forest", road_class: null, rail_class: "rail_corridor" },
  { hex_id: "auth:2:0", q: 2, r: 0, terrain_class: "hills", road_class: null, rail_class: "rail_corridor" },
  { hex_id: "auth:3:0", q: 3, r: 0, terrain_class: "water", road_class: null, rail_class: null },
  { hex_id: "auth:4:0", q: 4, r: 0, terrain_class: "hills", road_class: null, rail_class: null },
  { hex_id: "auth:5:0", q: 5, r: 0, terrain_class: "mountain", road_class: null, rail_class: null },
  { hex_id: "auth:0:1", q: 0, r: 1, terrain_class: "grass_open", road_class: "primary_road", rail_class: null },
  { hex_id: "auth:1:1", q: 1, r: 1, terrain_class: "grass_open", road_class: "primary_road", rail_class: "rail_corridor", airfield_name: "Waegwan Strip" },
  { hex_id: "auth:2:1", q: 2, r: 1, terrain_class: "urban_built_up", road_class: "primary_road", rail_class: "rail_corridor", settlement_name: "Waegwan" },
  { hex_id: "auth:3:1", q: 3, r: 1, terrain_class: "water", road_class: null, rail_class: null },
  { hex_id: "auth:4:1", q: 4, r: 1, terrain_class: "grass_open", road_class: "primary_road", rail_class: null },
  { hex_id: "auth:5:1", q: 5, r: 1, terrain_class: "forest", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:0:2", q: 0, r: 2, terrain_class: "grass_open", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:1:2", q: 1, r: 2, terrain_class: "grass_open", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:2:2", q: 2, r: 2, terrain_class: "forest", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:3:2", q: 3, r: 2, terrain_class: "water", road_class: null, rail_class: null },
  { hex_id: "auth:4:2", q: 4, r: 2, terrain_class: "grass_open", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:5:2", q: 5, r: 2, terrain_class: "grass_open", road_class: "primary_road", rail_class: null },
  { hex_id: "auth:0:3", q: 0, r: 3, terrain_class: "coast", road_class: null, rail_class: null, coastline: true, settlement_name: "Pusan Pier" },
  { hex_id: "auth:1:3", q: 1, r: 3, terrain_class: "grass_open", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:2:3", q: 2, r: 3, terrain_class: "rough", road_class: null, rail_class: null },
  { hex_id: "auth:3:3", q: 3, r: 3, terrain_class: "water", road_class: null, rail_class: null },
  { hex_id: "auth:4:3", q: 4, r: 3, terrain_class: "grass_open", road_class: "secondary_road", rail_class: null },
  { hex_id: "auth:5:3", q: 5, r: 3, terrain_class: "forest", road_class: null, rail_class: null },
];

const BULK_SELECTIONS = [
  { id: "railhead", label: "Rail Belt", pick: (hexRecord: BaseHex) => Boolean(hexRecord.rail_class) },
  { id: "river", label: "River Barrier", pick: (hexRecord: BaseHex) => normalizeHexTerrain(hexRecord.terrain_class) === "water" },
  { id: "west", label: "West Sector", pick: (hexRecord: BaseHex) => hexRecord.q <= 2 },
  { id: "east", label: "East Heights", pick: (hexRecord: BaseHex) => hexRecord.q >= 4 },
] as const;

const EMPTY_STATE: ScenarioAuthoringState = {
  scenario_id: "qa_authoring_case",
  theater_id: "korea_preview",
  named_features: [],
  objectives: [],
  deployment_zones: [],
  setup_restrictions: [],
  reinforcement_entry_zones: [],
  reinforcements: [],
  supply_sources: [],
  off_map_links: [],
  withdrawal_zones: [],
  scripted_arrivals: [],
  withdrawals: [],
};

const SAMPLE_STATE: ScenarioAuthoringState = {
  scenario_id: "waegwan_authoring_preview",
  theater_id: "korea_preview",
  named_features: [
    {
      id: "hill-314",
      label: "Hill 314",
      kind: "hill",
      geometry_type: "point",
      position: [4, 0],
      visibility: "operational",
      label_priority: 2,
      note: "Dominant observation point.",
      provenance: { source: "designer_pass", confidence: "high" },
      ui_hexes: [[4, 0]],
    },
    {
      id: "phase-bravo",
      label: "Phase Line Bravo",
      kind: "phase_line",
      geometry_type: "line",
      points: [[1, 1], [2, 1], [4, 1]],
      position: [2.33, 1],
      visibility: "always",
      label_priority: 3,
      provenance: { source: "historical_brief", confidence: "medium" },
      ui_hexes: [[1, 1], [2, 1], [4, 1]],
    },
    {
      id: "east-sector",
      label: "East Sector",
      kind: "sector",
      geometry_type: "zone",
      points: [[3.25, 0.25], [5.75, 0.25], [5.75, 3.75], [3.25, 3.75]],
      position: [4.5, 2],
      visibility: "operational",
      label_priority: 3,
      provenance: { source: "ops_plan", confidence: "medium" },
      ui_hexes: [[4, 0], [5, 0], [4, 1], [5, 1], [4, 2], [5, 2], [4, 3], [5, 3]],
    },
  ],
  objectives: [
    {
      id: "obj-bridgehead",
      title: "Waegwan Bridgehead",
      name: "Waegwan Bridgehead",
      objective_type: "primary",
      category: "primary",
      importance_tier: 2,
      value: 60,
      owner: "RED",
      visibility: "operational",
      position: [2, 1],
      provenance: { source: "historical_brief", confidence: "high" },
    },
    {
      id: "obj-railhead",
      title: "North Railhead",
      name: "North Railhead",
      objective_type: "supply",
      category: "supply",
      importance_tier: 2,
      value: 45,
      owner: "BLUE",
      visibility: "operational",
      position: [1, 1],
      provenance: { source: "designer_pass", confidence: "high" },
    },
  ],
  deployment_zones: [
    {
      id: "blue-start",
      label: "Blue Start",
      side: "BLUE",
      points: [[-0.25, 0.75], [1.75, 0.75], [1.75, 2.75], [-0.25, 2.75]],
      anchor: [0.75, 1.75],
      formation_ids: ["1MAR", "7CAV"],
      provenance: { source: "scenario_author", confidence: "high" },
      ui_hexes: [[0, 1], [1, 1], [0, 2], [1, 2]],
    },
  ],
  setup_restrictions: [
    {
      id: "blue-frontline",
      formation_id: "1MAR",
      zone_id: "blue-start",
      allowed_unit_types: ["INFANTRY", "RECON"],
    },
  ],
  reinforcement_entry_zones: [
    {
      id: "rail-entry",
      label: "Northern Rail Entry",
      side: "BLUE",
      points: [[0.25, 0.25], [2.25, 0.25], [2.25, 1.75], [0.25, 1.75]],
      anchor: [1.25, 1],
      entry_kind: "off_map_rail",
      route_class: "off_map_rail",
      linked_location_id: "NORTH_GATE",
      provenance: { source: "scenario_author", confidence: "high" },
      ui_hexes: [[1, 0], [2, 0], [1, 1], [2, 1]],
    },
    {
      id: "harbor-entry",
      label: "Pusan Harbor Entry",
      side: "BLUE",
      points: [[-0.25, 2.25], [0.75, 2.25], [0.75, 3.75], [-0.25, 3.75]],
      anchor: [0.25, 3],
      entry_kind: "port_entry",
      route_class: "port_entry",
      linked_location_id: "PUSAN_PORT",
      provenance: { source: "scenario_author", confidence: "high" },
      ui_hexes: [[0, 3]],
    },
  ],
  reinforcements: [
    {
      id: "blue-2mar",
      name: "2nd Marines",
      side: "BLUE",
      unit_type: "INFANTRY",
      entry_zone_id: "rail-entry",
      arrival_day: 2,
      provenance: { source: "scenario_author", confidence: "medium" },
    },
  ],
  supply_sources: [
    {
      id: "src-railhead",
      label: "North Railhead",
      side: "BLUE",
      daily_supply: 120,
      kind: "railhead",
      coord: [1, 1],
      provenance: { source: "scenario_author", confidence: "high" },
    },
    {
      id: "src-harbor",
      label: "Pusan Harbor",
      side: "BLUE",
      daily_supply: 90,
      kind: "port",
      coord: [0, 3],
      provenance: { source: "scenario_author", confidence: "high" },
    },
  ],
  off_map_links: [
    {
      id: "link-rail-main",
      label: "Northern Main Line",
      side: "BLUE",
      source_node_id: "src-railhead",
      entry_zone_id: "rail-entry",
      route_class: "off_map_rail",
      capacity: 95,
      provenance: { source: "scenario_author", confidence: "medium" },
    },
  ],
  withdrawal_zones: [
    {
      id: "red-south-exit",
      label: "Red South Exit",
      side: "RED",
      points: [[4.25, 2.25], [5.75, 2.25], [5.75, 3.75], [4.25, 3.75]],
      anchor: [5, 3],
      extraction_kind: "withdrawal",
      provenance: { source: "scenario_author", confidence: "medium" },
      ui_hexes: [[4, 3], [5, 3]],
    },
  ],
  scripted_arrivals: [],
  withdrawals: [],
};

function coordKey(q: number, r: number): string {
  return `${q}:${r}`;
}

function cloneState<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function slugify(value: string, fallback: string) {
  const slug = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || fallback;
}

function pointForCoord(q: number, r: number) {
  const point = axialToPixel(q, r, HEX_SIZE);
  return {
    x: SCENE_OFFSET_X + point.x,
    y: SCENE_OFFSET_Y + point.y,
  };
}

function polygonForFeaturePoints(points: Coord[] | undefined) {
  return (Array.isArray(points) ? points : [])
    .map(([q, r]) => {
      const point = pointForCoord(q, r);
      return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    })
    .join(" ");
}

function selectionRectPoints(coords: Coord[]): Coord[] {
  if (!coords.length) {
    return [];
  }
  const qs = coords.map(([q]) => q);
  const rs = coords.map(([, r]) => r);
  return [
    [Math.min(...qs) - 0.75, Math.min(...rs) - 0.75],
    [Math.max(...qs) + 0.75, Math.min(...rs) - 0.75],
    [Math.max(...qs) + 0.75, Math.max(...rs) + 0.75],
    [Math.min(...qs) - 0.75, Math.max(...rs) + 0.75],
  ];
}

function selectionAnchor(coords: Coord[]): Coord | null {
  if (!coords.length) {
    return null;
  }
  const total = coords.reduce((sum, [q, r]) => [sum[0] + q, sum[1] + r] as Coord, [0, 0]);
  return [Number((total[0] / coords.length).toFixed(2)), Number((total[1] / coords.length).toFixed(2))];
}

function sortCoords(coords: Coord[]) {
  return [...coords].sort((left, right) => (left[1] - right[1]) || (left[0] - right[0]));
}

function upsertById<T extends { id: string }>(rows: T[], row: T): T[] {
  const next = [...rows];
  const index = next.findIndex((entry) => entry.id === row.id);
  if (index === -1) {
    next.push(row);
  } else {
    next[index] = row;
  }
  return next.sort((left, right) => left.id.localeCompare(right.id));
}

function removeById<T extends { id: string }>(rows: T[], rowId: string): T[] {
  return rows.filter((row) => row.id !== rowId);
}

function shouldShowOperationalLabel(visibility: VisibilityRule) {
  return visibility === "always" || visibility === "far" || visibility === "operational";
}

function terrainClassName(hexRecord: BaseHex) {
  return normalizeHexTerrain(hexRecord.terrain_class);
}

function stripUiHexes<T extends { ui_hexes?: Coord[] }>(row: T): Omit<T, "ui_hexes"> {
  const next = { ...row };
  delete next.ui_hexes;
  return next;
}

function serializeObjectivesDocument(state: ScenarioAuthoringState) {
  return {
    schema: "mwe.scenario_objectives.v1",
    version: 1,
    scenario_id: state.scenario_id,
    theater_id: state.theater_id,
    named_features: state.named_features.map(stripUiHexes),
    objectives: state.objectives,
  };
}

function serializeSetupDocument(state: ScenarioAuthoringState) {
  return {
    schema: "mwe.scenario_setup.v1",
    version: 1,
    scenario_id: state.scenario_id,
    theater_id: state.theater_id,
    deployment_zones: state.deployment_zones.map(stripUiHexes),
    setup_restrictions: state.setup_restrictions,
    reinforcement_entry_zones: state.reinforcement_entry_zones.map(stripUiHexes),
    reinforcements: state.reinforcements,
    withdrawals: state.withdrawals,
    supply_sources: state.supply_sources,
    off_map_links: state.off_map_links,
    withdrawal_zones: state.withdrawal_zones.map(stripUiHexes),
    scripted_arrivals: state.scripted_arrivals,
  };
}

function hexLookup() {
  return new Map(BASE_HEXES.map((hexRecord) => [coordKey(hexRecord.q, hexRecord.r), hexRecord]));
}

function zoneCoords(zone: ZoneRow): Coord[] {
  return Array.isArray(zone.ui_hexes) ? zone.ui_hexes : [];
}

function isPassableHex(coord: Coord, byCoord: Map<string, BaseHex>) {
  const hexRecord = byCoord.get(coordKey(coord[0], coord[1]));
  if (!hexRecord) {
    return false;
  }
  const terrain = normalizeHexTerrain(hexRecord.terrain_class);
  return terrain !== "water" && terrain !== "coast";
}

function reachableBetween(starts: Coord[], goals: Coord[], byCoord: Map<string, BaseHex>) {
  const goalKeys = new Set(goals.filter((coord) => isPassableHex(coord, byCoord)).map(([q, r]) => coordKey(q, r)));
  const frontier = starts.filter((coord) => isPassableHex(coord, byCoord));
  const seen = new Set(frontier.map(([q, r]) => coordKey(q, r)));
  while (frontier.length) {
    const current = frontier.shift() as Coord;
    const currentKey = coordKey(current[0], current[1]);
    if (goalKeys.has(currentKey)) {
      return true;
    }
    HEX_DIRS.forEach(([dq, dr]) => {
      const next: Coord = [current[0] + dq, current[1] + dr];
      const nextKey = coordKey(next[0], next[1]);
      if (seen.has(nextKey) || !isPassableHex(next, byCoord)) {
        return;
      }
      seen.add(nextKey);
      frontier.push(next);
    });
  }
  return false;
}

function buildValidationIssues(state: ScenarioAuthoringState): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const objectiveIds = new Set(state.objectives.map((objective) => objective.id));
  const objectiveNames = new Set<string>();
  const hexByCoord = hexLookup();

  state.objectives.forEach((objective) => {
    if (!String(objective.title || objective.name || "").trim()) {
      issues.push({
        severity: "error",
        code: "unnamed_objective",
        message: `Objective ${objective.id || "<missing id>"} is missing a title/name.`,
      });
    }
    const normalizedName = String(objective.title || objective.name || "").trim().toLowerCase();
    if (normalizedName) {
      if (objectiveNames.has(normalizedName)) {
        issues.push({
          severity: "warning",
          code: "ambiguous_objective_name",
          message: `Objective name ${objective.title || objective.name} is duplicated.`,
        });
      }
      objectiveNames.add(normalizedName);
    }
  });

  const featureLabels = new Set<string>();
  state.named_features.forEach((feature) => {
    const normalizedLabel = feature.label.trim().toLowerCase();
    if (normalizedLabel) {
      if (featureLabels.has(normalizedLabel)) {
        issues.push({
          severity: "warning",
          code: "ambiguous_named_feature_label",
          message: `Named feature label ${feature.label} is duplicated.`,
        });
      }
      featureLabels.add(normalizedLabel);
    }
    if (feature.objective_id && !objectiveIds.has(feature.objective_id)) {
      issues.push({
        severity: "error",
        code: "unknown_feature_objective",
        message: `Named feature ${feature.label} references unknown objective ${feature.objective_id}.`,
      });
    }
  });

  for (const [rows, code, label] of [
    [state.deployment_zones, "deployment_zone_overlap", "Deployment"],
    [state.reinforcement_entry_zones, "entry_zone_overlap", "Entry"],
    [state.withdrawal_zones, "withdrawal_zone_overlap", "Withdrawal"],
  ] as const) {
    rows.forEach((left, index) => {
      rows.slice(index + 1).forEach((right) => {
        if (left.side && right.side && left.side !== right.side) {
          return;
        }
        const overlap = zoneCoords(left).filter((coord) => zoneCoords(right).some((other) => coordKey(coord[0], coord[1]) === coordKey(other[0], other[1])));
        if (!overlap.length) {
          return;
        }
        issues.push({
          severity: "warning",
          code,
          message: `${label} zones ${left.label} and ${right.label} overlap across ${overlap.length} hex${overlap.length === 1 ? "" : "es"}.`,
        });
      });
    });
  }

  const deploymentBySide = new Map<string, Coord[]>();
  state.deployment_zones.forEach((zone) => {
    const side = String(zone.side || "").trim().toUpperCase();
    if (!side) {
      return;
    }
    deploymentBySide.set(side, [...(deploymentBySide.get(side) || []), ...zoneCoords(zone)]);
  });

  state.reinforcement_entry_zones.forEach((zone) => {
    const side = String(zone.side || "").trim().toUpperCase();
    const goals = deploymentBySide.get(side) || [];
    if (goals.length && !reachableBetween(zoneCoords(zone), goals, hexByCoord)) {
      issues.push({
        severity: "warning",
        code: "entry_zone_unreachable",
        message: `${zone.label} has no passable path to a same-side deployment zone.`,
      });
    }
  });

  return issues;
}

function entryZoneAnchor(zoneId: string, state: ScenarioAuthoringState) {
  return state.reinforcement_entry_zones.find((zone) => zone.id === zoneId)?.anchor || null;
}

function objectiveControlState(owner: string | null) {
  const normalized = String(owner || "").trim().toUpperCase();
  if (normalized === "BLUE" || normalized === "ALLIED") {
    return "friendly";
  }
  if (normalized === "RED" || normalized === "AXIS" || normalized === "ENEMY") {
    return "enemy";
  }
  if (normalized === "CONTESTED") {
    return "contested";
  }
  return "neutral";
}

function objectiveTier(row: ObjectiveRow) {
  if (row.importance_tier >= 3 || row.objective_type === "strategic" || row.objective_type === "political") {
    return "capital";
  }
  if (row.importance_tier >= 2 || row.objective_type === "primary") {
    return "major_city";
  }
  return "town";
}

function sourceKindIcon(kind: SupplyKind) {
  if (kind === "railhead") {
    return "RAIL";
  }
  if (kind === "port" || kind === "harbor") {
    return "PORT";
  }
  if (kind === "off_map") {
    return "OFF";
  }
  if (kind === "airhead") {
    return "AIR";
  }
  return "DEP";
}

export default function ScenarioAuthoringQAScene({ theaterId }: ScenarioAuthoringQASceneProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<AuthoringMode>("features");
  const [state, setState] = useState<ScenarioAuthoringState>(SAMPLE_STATE);
  const [undoStack, setUndoStack] = useState<ScenarioAuthoringState[]>([]);
  const [redoStack, setRedoStack] = useState<ScenarioAuthoringState[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [featureForm, setFeatureForm] = useState<FeatureFormState>({
    id: "",
    label: "",
    kind: "hill",
    geometry: "point",
    visibility: "operational",
    priority: 2,
    objectiveId: "",
    note: "",
    source: "designer_pass",
    confidence: "medium",
  });
  const [objectiveForm, setObjectiveForm] = useState<ObjectiveFormState>({
    id: "",
    label: "",
    objectiveType: "primary",
    visibility: "operational",
    owner: "BLUE",
    value: 50,
    priority: 2,
    note: "",
    source: "historical_brief",
    confidence: "high",
  });
  const [zoneForm, setZoneForm] = useState<ZoneFormState>({
    id: "",
    label: "",
    zoneKind: "deployment",
    side: "BLUE",
    entryKind: "map_edge",
    routeClass: "primary_road",
    note: "",
    source: "scenario_author",
    confidence: "medium",
  });
  const [restrictionForm, setRestrictionForm] = useState<RestrictionFormState>({
    id: "",
    formationId: "",
    zoneId: "",
    allowedTypes: "INFANTRY",
  });
  const [reinforcementForm, setReinforcementForm] = useState<ReinforcementFormState>({
    id: "",
    name: "",
    side: "BLUE",
    unitType: "INFANTRY",
    entryZoneId: "",
    arrivalDay: "2",
  });
  const [supplyForm, setSupplyForm] = useState<SupplyFormState>({
    id: "",
    label: "",
    side: "BLUE",
    kind: "railhead",
    dailySupply: 80,
    note: "",
    source: "scenario_author",
    confidence: "medium",
  });
  const [linkForm, setLinkForm] = useState<LinkFormState>({
    id: "",
    label: "",
    side: "BLUE",
    sourceNodeId: "",
    entryZoneId: "",
    routeClass: "off_map_rail",
    capacity: 80,
  });

  const selectedCoords = useMemo(
    () => selectedKeys.map((key) => key.split(":").map((value) => Number(value)) as Coord),
    [selectedKeys],
  );
  const selectedHexes = useMemo(
    () => BASE_HEXES.filter((hexRecord) => selectedKeys.includes(coordKey(hexRecord.q, hexRecord.r))),
    [selectedKeys],
  );
  const issues = useMemo(() => buildValidationIssues(state), [state]);
  const serializedObjectives = useMemo(() => serializeObjectivesDocument(state), [state]);
  const serializedSetup = useMemo(() => serializeSetupDocument(state), [state]);

  function commit(nextState: ScenarioAuthoringState) {
    setUndoStack((current) => [...current, cloneState(state)]);
    setRedoStack([]);
    setState(nextState);
  }

  function replaceState(nextState: ScenarioAuthoringState) {
    setState(nextState);
  }

  function toggleHexSelection(q: number, r: number) {
    const key = coordKey(q, r);
    setSelectedKeys((current) => (
      current.includes(key)
        ? current.filter((entry) => entry !== key)
        : [...current, key]
    ));
  }

  function resetSample(nextState: ScenarioAuthoringState) {
    setUndoStack([]);
    setRedoStack([]);
    setSelectedKeys([]);
    replaceState(cloneState(nextState));
  }

  function saveFeature() {
    if (!selectedCoords.length || !featureForm.label.trim()) {
      return;
    }
    const featureId = featureForm.id.trim() || slugify(featureForm.label, "feature");
    const sorted = sortCoords(selectedCoords);
    const anchor = selectionAnchor(sorted);
    const row: NamedFeatureRow = {
      id: featureId,
      label: featureForm.label.trim(),
      kind: featureForm.kind,
      geometry_type: featureForm.geometry,
      visibility: featureForm.visibility,
      label_priority: Math.max(1, Math.min(3, Number(featureForm.priority || 1))),
      objective_id: featureForm.objectiveId.trim() || null,
      note: featureForm.note.trim() || null,
      provenance: { source: featureForm.source, confidence: featureForm.confidence },
      ui_hexes: sorted,
    };
    if (featureForm.geometry === "point") {
      row.position = sorted[0];
    } else if (featureForm.geometry === "line") {
      row.points = sorted;
      row.position = anchor || undefined;
    } else {
      row.points = selectionRectPoints(sorted);
      row.position = anchor || undefined;
    }
    commit({
      ...state,
      named_features: upsertById(state.named_features, row),
    });
    setFeatureForm((current) => ({ ...current, id: featureId }));
  }

  function saveObjective() {
    if (!selectedCoords.length || !objectiveForm.label.trim()) {
      return;
    }
    const objectiveId = objectiveForm.id.trim() || slugify(objectiveForm.label, "objective");
    const row: ObjectiveRow = {
      id: objectiveId,
      title: objectiveForm.label.trim(),
      name: objectiveForm.label.trim(),
      objective_type: objectiveForm.objectiveType,
      category: objectiveForm.objectiveType,
      importance_tier: Math.max(1, Math.min(3, Number(objectiveForm.priority || 1))),
      value: Number(objectiveForm.value || 0),
      owner: objectiveForm.owner.trim() || null,
      visibility: objectiveForm.visibility,
      position: selectedCoords[0],
      note: objectiveForm.note.trim() || null,
      provenance: { source: objectiveForm.source, confidence: objectiveForm.confidence },
    };
    commit({
      ...state,
      objectives: upsertById(state.objectives, row),
    });
    setObjectiveForm((current) => ({ ...current, id: objectiveId }));
  }

  function saveZone() {
    if (!selectedCoords.length || !zoneForm.label.trim()) {
      return;
    }
    const zoneId = zoneForm.id.trim() || slugify(zoneForm.label, "zone");
    const sorted = sortCoords(selectedCoords);
    const row: ZoneRow = {
      id: zoneId,
      label: zoneForm.label.trim(),
      side: zoneForm.side.trim().toUpperCase() || null,
      points: selectionRectPoints(sorted),
      anchor: selectionAnchor(sorted),
      note: zoneForm.note.trim() || null,
      provenance: { source: zoneForm.source, confidence: zoneForm.confidence },
      ui_hexes: sorted,
    };
    let nextState = { ...state };
    if (zoneForm.zoneKind === "deployment") {
      nextState.deployment_zones = upsertById(state.deployment_zones, row);
    } else if (zoneForm.zoneKind === "entry") {
      nextState.reinforcement_entry_zones = upsertById(state.reinforcement_entry_zones, {
        ...row,
        entry_kind: zoneForm.entryKind,
        route_class: zoneForm.routeClass.trim() || null,
      });
    } else {
      nextState.withdrawal_zones = upsertById(state.withdrawal_zones, {
        ...row,
        extraction_kind: "withdrawal",
      });
    }
    commit(nextState);
    setZoneForm((current) => ({ ...current, id: zoneId }));
  }

  function saveRestriction() {
    if (!restrictionForm.id.trim() || !restrictionForm.formationId.trim()) {
      return;
    }
    const row: SetupRestrictionRow = {
      id: restrictionForm.id.trim(),
      formation_id: restrictionForm.formationId.trim(),
      zone_id: restrictionForm.zoneId.trim() || null,
      allowed_unit_types: restrictionForm.allowedTypes.split(",").map((value) => value.trim().toUpperCase()).filter(Boolean),
    };
    commit({
      ...state,
      setup_restrictions: upsertById(state.setup_restrictions, row),
    });
  }

  function saveReinforcement() {
    if (!reinforcementForm.id.trim() || !reinforcementForm.name.trim()) {
      return;
    }
    const row: ReinforcementRow = {
      id: reinforcementForm.id.trim(),
      name: reinforcementForm.name.trim(),
      side: reinforcementForm.side.trim().toUpperCase() || null,
      unit_type: reinforcementForm.unitType.trim().toUpperCase(),
      entry_zone_id: reinforcementForm.entryZoneId.trim() || null,
      arrival_day: reinforcementForm.arrivalDay.trim() ? Number(reinforcementForm.arrivalDay) : null,
      provenance: { source: "scenario_author", confidence: "medium" },
    };
    commit({
      ...state,
      reinforcements: upsertById(state.reinforcements, row),
    });
  }

  function saveSupplySource() {
    if (!selectedCoords.length || !supplyForm.label.trim()) {
      return;
    }
    const sourceId = supplyForm.id.trim() || slugify(supplyForm.label, "source");
    const row: SupplySourceRow = {
      id: sourceId,
      label: supplyForm.label.trim(),
      side: supplyForm.side.trim().toUpperCase() || null,
      daily_supply: Number(supplyForm.dailySupply || 0),
      kind: supplyForm.kind,
      coord: selectedCoords[0],
      note: supplyForm.note.trim() || null,
      provenance: { source: supplyForm.source, confidence: supplyForm.confidence },
    };
    commit({
      ...state,
      supply_sources: upsertById(state.supply_sources, row),
    });
    setSupplyForm((current) => ({ ...current, id: sourceId }));
  }

  function saveOffMapLink() {
    if (!linkForm.id.trim() || !linkForm.label.trim() || !linkForm.sourceNodeId.trim()) {
      return;
    }
    const row: OffMapLinkRow = {
      id: linkForm.id.trim(),
      label: linkForm.label.trim(),
      side: linkForm.side.trim().toUpperCase() || null,
      source_node_id: linkForm.sourceNodeId.trim(),
      entry_zone_id: linkForm.entryZoneId.trim() || null,
      route_class: linkForm.routeClass.trim(),
      capacity: Number(linkForm.capacity || 0),
      provenance: { source: "scenario_author", confidence: "medium" },
    };
    commit({
      ...state,
      off_map_links: upsertById(state.off_map_links, row),
    });
  }

  function removeRow(
    section: "named_features" | "objectives" | "deployment_zones" | "reinforcement_entry_zones" | "withdrawal_zones" | "supply_sources",
    rowId: string,
  ) {
    const nextState = cloneState(state);
    nextState[section] = removeById(nextState[section], rowId);
    commit(nextState);
  }

  function loadFeature(row: NamedFeatureRow) {
    setMode("features");
    setSelectedKeys((row.ui_hexes || []).map(([q, r]) => coordKey(q, r)));
    setFeatureForm({
      id: row.id,
      label: row.label,
      kind: row.kind,
      geometry: row.geometry_type,
      visibility: row.visibility,
      priority: row.label_priority,
      objectiveId: row.objective_id || "",
      note: row.note || "",
      source: row.provenance?.source || "designer_pass",
      confidence: row.provenance?.confidence || "medium",
    });
  }

  function loadObjective(row: ObjectiveRow) {
    setMode("objectives");
    setSelectedKeys([coordKey(row.position[0], row.position[1])]);
    setObjectiveForm({
      id: row.id,
      label: row.title || row.name,
      objectiveType: row.objective_type,
      visibility: row.visibility,
      owner: row.owner || "",
      value: row.value,
      priority: row.importance_tier,
      note: row.note || "",
      source: row.provenance?.source || "historical_brief",
      confidence: row.provenance?.confidence || "high",
    });
  }

  function loadZone(row: ZoneRow, zoneKind: ZoneKind) {
    setMode("setup");
    setSelectedKeys((row.ui_hexes || []).map(([q, r]) => coordKey(q, r)));
    setZoneForm({
      id: row.id,
      label: row.label,
      zoneKind,
      side: row.side || "",
      entryKind: row.entry_kind || "map_edge",
      routeClass: row.route_class || "primary_road",
      note: row.note || "",
      source: row.provenance?.source || "scenario_author",
      confidence: row.provenance?.confidence || "medium",
    });
  }

  function loadSupply(row: SupplySourceRow) {
    setMode("supply");
    setSelectedKeys([coordKey(row.coord[0], row.coord[1])]);
    setSupplyForm({
      id: row.id,
      label: row.label,
      side: row.side || "",
      kind: row.kind,
      dailySupply: row.daily_supply,
      note: row.note || "",
      source: row.provenance?.source || "scenario_author",
      confidence: row.provenance?.confidence || "medium",
    });
  }

  const zoneRows = [
    ...state.deployment_zones.map((row) => ({ section: "deployment" as const, row })),
    ...state.reinforcement_entry_zones.map((row) => ({ section: "entry" as const, row })),
    ...state.withdrawal_zones.map((row) => ({ section: "withdrawal" as const, row })),
  ];

  return (
    <div className={"shell-authorqa" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-authorqa__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-author-qa"
      >
        <span className="shell-authorqa__title">Scenario Authoring QA</span>
        <span className="shell-authorqa__state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-authorqa__body" id="shell-author-qa">
          <div className="shell-authorqa__toolbar">
            {([
              ["features", "Named Terrain"],
              ["objectives", "Objectives"],
              ["setup", "Setup / Entries"],
              ["supply", "Supply / Links"],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={"shell-authorqa__chip" + (mode === value ? " is-active" : "")}
                onClick={() => setMode(value)}
              >
                {label}
              </button>
            ))}
            <button type="button" className="shell-authorqa__action" onClick={() => resetSample(SAMPLE_STATE)}>
              Load Sample
            </button>
            <button type="button" className="shell-authorqa__action" onClick={() => resetSample(EMPTY_STATE)}>
              Clear Scene
            </button>
            <button
              type="button"
              className="shell-authorqa__action"
              disabled={!undoStack.length}
              onClick={() => {
                const previous = undoStack[undoStack.length - 1];
                if (!previous) {
                  return;
                }
                setUndoStack((current) => current.slice(0, -1));
                setRedoStack((current) => [...current, cloneState(state)]);
                replaceState(previous);
              }}
            >
              Undo
            </button>
            <button
              type="button"
              className="shell-authorqa__action"
              disabled={!redoStack.length}
              onClick={() => {
                const next = redoStack[redoStack.length - 1];
                if (!next) {
                  return;
                }
                setRedoStack((current) => current.slice(0, -1));
                setUndoStack((current) => [...current, cloneState(state)]);
                replaceState(next);
              }}
            >
              Redo
            </button>
          </div>

          <div className="shell-authorqa__layout">
            <div className="shell-authorqa__canvaswrap">
              <svg className="shell-authorqa__svg" viewBox={`0 0 ${SCENE_WIDTH} ${SCENE_HEIGHT}`} role="img" aria-label="Scenario authoring preview map">
                <rect className="shell-authorqa__field" x="0" y="0" width={SCENE_WIDTH} height={SCENE_HEIGHT} />

                {zoneRows.map(({ section, row }) => (
                  <polygon
                    key={`${section}:${row.id}`}
                    className={`shell-authorqa__zone shell-authorqa__zone--${section} is-${String(row.side || "neutral").toLowerCase()}`}
                    points={polygonForFeaturePoints(row.points)}
                    onClick={() => loadZone(row, section)}
                  />
                ))}

                {state.named_features.map((feature) => {
                  if (feature.geometry_type === "line") {
                    return (
                      <g key={feature.id} onClick={() => loadFeature(feature)}>
                        <polyline className={`shell-authorqa__feature shell-authorqa__feature--line is-${feature.kind}`} points={polygonForFeaturePoints(feature.points)} />
                        {feature.position && shouldShowOperationalLabel(feature.visibility) ? (
                          <text className="shell-authorqa__feature-label" x={pointForCoord(feature.position[0], feature.position[1]).x} y={pointForCoord(feature.position[0], feature.position[1]).y - 10} textAnchor="middle">
                            {feature.label}
                          </text>
                        ) : null}
                      </g>
                    );
                  }
                  if (feature.geometry_type === "zone") {
                    return (
                      <g key={feature.id} onClick={() => loadFeature(feature)}>
                        <polygon className={`shell-authorqa__feature shell-authorqa__feature--zone is-${feature.kind}`} points={polygonForFeaturePoints(feature.points)} />
                        {feature.position && shouldShowOperationalLabel(feature.visibility) ? (
                          <text className="shell-authorqa__feature-label" x={pointForCoord(feature.position[0], feature.position[1]).x} y={pointForCoord(feature.position[0], feature.position[1]).y} textAnchor="middle">
                            {feature.label}
                          </text>
                        ) : null}
                      </g>
                    );
                  }
                  if (!feature.position) {
                    return null;
                  }
                  const anchor = pointForCoord(feature.position[0], feature.position[1]);
                  return (
                    <g key={feature.id} className={`shell-authorqa__feature-marker is-${feature.kind}`} transform={`translate(${anchor.x}, ${anchor.y})`} onClick={() => loadFeature(feature)}>
                      <circle r={7} />
                      {shouldShowOperationalLabel(feature.visibility) ? (
                        <text className="shell-authorqa__feature-label" x="0" y="-12" textAnchor="middle">
                          {feature.label}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                {state.off_map_links.map((link) => {
                  const source = state.supply_sources.find((row) => row.id === link.source_node_id);
                  const target = entryZoneAnchor(String(link.entry_zone_id || ""), state);
                  if (!source || !target) {
                    return null;
                  }
                  const from = pointForCoord(source.coord[0], source.coord[1]);
                  const to = pointForCoord(target[0], target[1]);
                  return (
                    <g key={link.id}>
                      <line className={`shell-authorqa__link is-${link.route_class.replace(/[^a-z0-9]+/gi, "_")}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
                      <text className="shell-authorqa__link-label" x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 6} textAnchor="middle">
                        {link.label}
                      </text>
                    </g>
                  );
                })}

                {BASE_HEXES.map((hexRecord) => {
                  const point = pointForCoord(hexRecord.q, hexRecord.r);
                  const terrain = terrainClassName(hexRecord);
                  const key = coordKey(hexRecord.q, hexRecord.r);
                  return (
                    <g key={hexRecord.hex_id}>
                      <polygon
                        className={`shell-authorqa__hex is-${terrain}` + (selectedKeys.includes(key) ? " is-selected" : "")}
                        points={hexPolygonPoints(point.x, point.y, HEX_SIZE)}
                        onClick={() => toggleHexSelection(hexRecord.q, hexRecord.r)}
                      />
                      {hexRecord.road_class ? (
                        <line className={`shell-authorqa__road is-${hexRecord.road_class}`} x1={point.x - 16} y1={point.y + 4} x2={point.x + 16} y2={point.y - 4} />
                      ) : null}
                      {hexRecord.rail_class ? (
                        <line className={`shell-authorqa__rail is-${hexRecord.rail_class}`} x1={point.x - 14} y1={point.y - 10} x2={point.x + 14} y2={point.y + 10} />
                      ) : null}
                      {hexRecord.settlement_name ? (
                        <text className="shell-authorqa__contextlabel" x={point.x} y={point.y + 18} textAnchor="middle">{hexRecord.settlement_name}</text>
                      ) : null}
                    </g>
                  );
                })}

                {state.objectives.map((objective) => {
                  const point = pointForCoord(objective.position[0], objective.position[1]);
                  return (
                    <g key={objective.id} className={"shell-authorqa__objective is-" + objectiveControlState(objective.owner)} transform={`translate(${point.x}, ${point.y}) scale(0.88)`} onClick={() => loadObjective(objective)}>
                      <ObjectiveOverlayBadge category={objective.objective_type} importanceTier={objective.importance_tier} contested={objective.owner === "CONTESTED"} zoom={1} />
                      <SettlementIcon
                        tier={objectiveTier(objective)}
                        controlState={objectiveControlState(objective.owner)}
                        damaged={false}
                        supplyHub={objective.objective_type === "supply"}
                        showValueMarks={true}
                        zoom={1}
                      />
                      {shouldShowOperationalLabel(objective.visibility) ? (
                        <text className="shell-authorqa__objective-label" x="0" y="-18" textAnchor="middle">
                          {objective.title || objective.name}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                {state.supply_sources.map((source) => {
                  const point = pointForCoord(source.coord[0], source.coord[1]);
                  return (
                    <g key={source.id} className={`shell-authorqa__source is-${source.kind}`} transform={`translate(${point.x}, ${point.y})`} onClick={() => loadSupply(source)}>
                      <circle r={9} />
                      <text className="shell-authorqa__source-icon" x="0" y="3" textAnchor="middle">{sourceKindIcon(source.kind)}</text>
                      <text className="shell-authorqa__source-label" x="0" y="22" textAnchor="middle">{source.label}</text>
                    </g>
                  );
                })}

                {state.reinforcements.map((row) => {
                  const target = entryZoneAnchor(String(row.entry_zone_id || ""), state);
                  if (!target) {
                    return null;
                  }
                  const point = pointForCoord(target[0], target[1]);
                  return (
                    <g key={row.id}>
                      <path className="shell-authorqa__arrival" d={`M${point.x - 36} ${point.y - 20} L${point.x - 10} ${point.y - 6}`} />
                      <text className="shell-authorqa__arrival-label" x={point.x - 38} y={point.y - 24} textAnchor="end">
                        {row.name}
                      </text>
                    </g>
                  );
                })}

                {selectedHexes.map((hexRecord) => {
                  const point = pointForCoord(hexRecord.q, hexRecord.r);
                  return (
                    <polygon
                      key={`sel:${hexRecord.hex_id}`}
                      className="shell-authorqa__selection"
                      points={hexPolygonPoints(point.x, point.y, HEX_SIZE + 3)}
                    />
                  );
                })}
              </svg>

              <div className="shell-authorqa__actionrow">
                {BULK_SELECTIONS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    className="shell-authorqa__chip"
                    onClick={() => setSelectedKeys(BASE_HEXES.filter(preset.pick).map((hexRecord) => coordKey(hexRecord.q, hexRecord.r)))}
                  >
                    {preset.label}
                  </button>
                ))}
                <button type="button" className="shell-authorqa__action" onClick={() => setSelectedKeys([])}>
                  Clear Selection
                </button>
              </div>
            </div>

            <div className="shell-authorqa__inspect">
              <div className="shell-authorqa__summary">
                <strong>Authoring Surface</strong>
                <span>{state.scenario_id || "scenario"} on {theaterId || state.theater_id || "local sample"}.</span>
                <span>{selectedHexes.length} hex{selectedHexes.length === 1 ? "" : "es"} selected.</span>
              </div>

              {mode === "features" ? (
                <div className="shell-authorqa__section">
                  <div className="shell-authorqa__rowhead"><strong>Named Terrain</strong><span>Place hills, ridgelines, passes, valleys, sectors, and phase lines.</span></div>
                  <div className="shell-authorqa__formgrid">
                    <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={featureForm.id} onChange={(event) => setFeatureForm({ ...featureForm, id: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Label</span><input value={featureForm.label} onChange={(event) => setFeatureForm({ ...featureForm, label: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Kind</span><select value={featureForm.kind} onChange={(event) => setFeatureForm({ ...featureForm, kind: event.target.value as NamedFeatureKind })}>{["hill", "ridgeline", "pass", "valley", "sector", "subsector", "phase_line"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Geometry</span><select value={featureForm.geometry} onChange={(event) => setFeatureForm({ ...featureForm, geometry: event.target.value as FeatureGeometry })}>{["point", "line", "zone"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Visibility</span><select value={featureForm.visibility} onChange={(event) => setFeatureForm({ ...featureForm, visibility: event.target.value as VisibilityRule })}>{["always", "far", "operational", "close", "selected_only", "hidden"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Priority</span><select value={featureForm.priority} onChange={(event) => setFeatureForm({ ...featureForm, priority: Number(event.target.value) })}>{[1, 2, 3].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Objective Ref</span><input value={featureForm.objectiveId} onChange={(event) => setFeatureForm({ ...featureForm, objectiveId: event.target.value })} placeholder="optional objective id" /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Source</span><input value={featureForm.source} onChange={(event) => setFeatureForm({ ...featureForm, source: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Confidence</span><input value={featureForm.confidence} onChange={(event) => setFeatureForm({ ...featureForm, confidence: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol shell-authorqa__fieldcontrol--wide"><span>Note</span><input value={featureForm.note} onChange={(event) => setFeatureForm({ ...featureForm, note: event.target.value })} /></label>
                  </div>
                  <div className="shell-authorqa__actionrow">
                    <button type="button" className="shell-authorqa__action" onClick={saveFeature}>Save Feature</button>
                    {featureForm.id ? <button type="button" className="shell-authorqa__action" onClick={() => removeRow("named_features", featureForm.id)}>Delete</button> : null}
                  </div>
                  <div className="shell-authorqa__rows">
                    {state.named_features.map((row) => (
                      <button key={row.id} type="button" className="shell-authorqa__row" onClick={() => loadFeature(row)}>
                        <div className="shell-authorqa__rowhead"><strong>{row.label}</strong><span>{row.kind} / {row.geometry_type}</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.visibility}</span><span>Priority {row.label_priority}</span></div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {mode === "objectives" ? (
                <div className="shell-authorqa__section">
                  <div className="shell-authorqa__rowhead"><strong>Objectives</strong><span>Primary, secondary, supply, political, and strategic objectives stay distinct from ordinary settlements.</span></div>
                  <div className="shell-authorqa__formgrid">
                    <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={objectiveForm.id} onChange={(event) => setObjectiveForm({ ...objectiveForm, id: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Label</span><input value={objectiveForm.label} onChange={(event) => setObjectiveForm({ ...objectiveForm, label: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Type</span><select value={objectiveForm.objectiveType} onChange={(event) => setObjectiveForm({ ...objectiveForm, objectiveType: event.target.value as ObjectiveType })}>{["primary", "secondary", "supply", "political", "strategic"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Owner</span><input value={objectiveForm.owner} onChange={(event) => setObjectiveForm({ ...objectiveForm, owner: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Value</span><input type="number" value={objectiveForm.value} onChange={(event) => setObjectiveForm({ ...objectiveForm, value: Number(event.target.value) })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Priority</span><select value={objectiveForm.priority} onChange={(event) => setObjectiveForm({ ...objectiveForm, priority: Number(event.target.value) })}>{[1, 2, 3].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Visibility</span><select value={objectiveForm.visibility} onChange={(event) => setObjectiveForm({ ...objectiveForm, visibility: event.target.value as VisibilityRule })}>{["always", "far", "operational", "close", "selected_only", "hidden"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Source</span><input value={objectiveForm.source} onChange={(event) => setObjectiveForm({ ...objectiveForm, source: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Confidence</span><input value={objectiveForm.confidence} onChange={(event) => setObjectiveForm({ ...objectiveForm, confidence: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol shell-authorqa__fieldcontrol--wide"><span>Note</span><input value={objectiveForm.note} onChange={(event) => setObjectiveForm({ ...objectiveForm, note: event.target.value })} /></label>
                  </div>
                  <div className="shell-authorqa__actionrow">
                    <button type="button" className="shell-authorqa__action" onClick={saveObjective}>Save Objective</button>
                    {objectiveForm.id ? <button type="button" className="shell-authorqa__action" onClick={() => removeRow("objectives", objectiveForm.id)}>Delete</button> : null}
                  </div>
                  <div className="shell-authorqa__rows">
                    {state.objectives.map((row) => (
                      <button key={row.id} type="button" className="shell-authorqa__row" onClick={() => loadObjective(row)}>
                        <div className="shell-authorqa__rowhead"><strong>{row.title}</strong><span>{row.objective_type}</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.owner || "neutral"}</span><span>Value {row.value}</span></div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {mode === "setup" ? (
                <div className="shell-authorqa__section">
                  <div className="shell-authorqa__rowhead"><strong>Deployment & Reinforcement</strong><span>Place setup zones on the map, then attach restrictions and reinforcement flows.</span></div>
                  <div className="shell-authorqa__formgrid">
                    <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={zoneForm.id} onChange={(event) => setZoneForm({ ...zoneForm, id: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Label</span><input value={zoneForm.label} onChange={(event) => setZoneForm({ ...zoneForm, label: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Zone Kind</span><select value={zoneForm.zoneKind} onChange={(event) => setZoneForm({ ...zoneForm, zoneKind: event.target.value as ZoneKind })}>{["deployment", "entry", "withdrawal"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Side</span><input value={zoneForm.side} onChange={(event) => setZoneForm({ ...zoneForm, side: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Entry Kind</span><select value={zoneForm.entryKind} onChange={(event) => setZoneForm({ ...zoneForm, entryKind: event.target.value as EntryKind })}>{["map_edge", "road", "rail", "airfield", "port_entry", "off_map_road", "off_map_rail"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Route Class</span><input value={zoneForm.routeClass} onChange={(event) => setZoneForm({ ...zoneForm, routeClass: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Source</span><input value={zoneForm.source} onChange={(event) => setZoneForm({ ...zoneForm, source: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Confidence</span><input value={zoneForm.confidence} onChange={(event) => setZoneForm({ ...zoneForm, confidence: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol shell-authorqa__fieldcontrol--wide"><span>Note</span><input value={zoneForm.note} onChange={(event) => setZoneForm({ ...zoneForm, note: event.target.value })} /></label>
                  </div>
                  <div className="shell-authorqa__actionrow">
                    <button type="button" className="shell-authorqa__action" onClick={saveZone}>Save Zone</button>
                    {zoneForm.id ? (
                      <button
                        type="button"
                        className="shell-authorqa__action"
                        onClick={() => removeRow(
                          zoneForm.zoneKind === "deployment" ? "deployment_zones" : zoneForm.zoneKind === "entry" ? "reinforcement_entry_zones" : "withdrawal_zones",
                          zoneForm.id,
                        )}
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>

                  <div className="shell-authorqa__subgrid">
                    <div className="shell-authorqa__subsection">
                      <div className="shell-authorqa__rowhead"><strong>Setup Restriction</strong><span>Formation / zone gate.</span></div>
                      <div className="shell-authorqa__formgrid">
                        <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={restrictionForm.id} onChange={(event) => setRestrictionForm({ ...restrictionForm, id: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Formation</span><input value={restrictionForm.formationId} onChange={(event) => setRestrictionForm({ ...restrictionForm, formationId: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Zone</span><select value={restrictionForm.zoneId} onChange={(event) => setRestrictionForm({ ...restrictionForm, zoneId: event.target.value })}><option value="">Select</option>{state.deployment_zones.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
                        <label className="shell-authorqa__fieldcontrol shell-authorqa__fieldcontrol--wide"><span>Allowed Types</span><input value={restrictionForm.allowedTypes} onChange={(event) => setRestrictionForm({ ...restrictionForm, allowedTypes: event.target.value })} /></label>
                      </div>
                      <div className="shell-authorqa__actionrow"><button type="button" className="shell-authorqa__action" onClick={saveRestriction}>Save Restriction</button></div>
                    </div>

                    <div className="shell-authorqa__subsection">
                      <div className="shell-authorqa__rowhead"><strong>Reinforcement Row</strong><span>Attach units to authored entry zones.</span></div>
                      <div className="shell-authorqa__formgrid">
                        <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={reinforcementForm.id} onChange={(event) => setReinforcementForm({ ...reinforcementForm, id: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Name</span><input value={reinforcementForm.name} onChange={(event) => setReinforcementForm({ ...reinforcementForm, name: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Side</span><input value={reinforcementForm.side} onChange={(event) => setReinforcementForm({ ...reinforcementForm, side: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Type</span><input value={reinforcementForm.unitType} onChange={(event) => setReinforcementForm({ ...reinforcementForm, unitType: event.target.value })} /></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Entry Zone</span><select value={reinforcementForm.entryZoneId} onChange={(event) => setReinforcementForm({ ...reinforcementForm, entryZoneId: event.target.value })}><option value="">Select</option>{state.reinforcement_entry_zones.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
                        <label className="shell-authorqa__fieldcontrol"><span>Arrival Day</span><input value={reinforcementForm.arrivalDay} onChange={(event) => setReinforcementForm({ ...reinforcementForm, arrivalDay: event.target.value })} /></label>
                      </div>
                      <div className="shell-authorqa__actionrow"><button type="button" className="shell-authorqa__action" onClick={saveReinforcement}>Save Reinforcement</button></div>
                    </div>
                  </div>

                  <div className="shell-authorqa__rows">
                    {zoneRows.map(({ section, row }) => (
                      <button key={`${section}:${row.id}`} type="button" className="shell-authorqa__row" onClick={() => loadZone(row, section)}>
                        <div className="shell-authorqa__rowhead"><strong>{row.label}</strong><span>{section}</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.side || "neutral"}</span><span>{row.ui_hexes?.length || 0} hexes</span></div>
                      </button>
                    ))}
                    {state.reinforcements.map((row) => (
                      <div key={row.id} className="shell-authorqa__row">
                        <div className="shell-authorqa__rowhead"><strong>{row.name}</strong><span>reinforcement</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.entry_zone_id || "unlinked"}</span><span>Day {row.arrival_day ?? "?"}</span></div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {mode === "supply" ? (
                <div className="shell-authorqa__section">
                  <div className="shell-authorqa__rowhead"><strong>Supply / Off-map Links</strong><span>Railheads, ports, and off-map entry links remain scenario-local setup data.</span></div>
                  <div className="shell-authorqa__formgrid">
                    <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={supplyForm.id} onChange={(event) => setSupplyForm({ ...supplyForm, id: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Label</span><input value={supplyForm.label} onChange={(event) => setSupplyForm({ ...supplyForm, label: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Side</span><input value={supplyForm.side} onChange={(event) => setSupplyForm({ ...supplyForm, side: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Kind</span><select value={supplyForm.kind} onChange={(event) => setSupplyForm({ ...supplyForm, kind: event.target.value as SupplyKind })}>{["depot", "port", "harbor", "off_map", "railhead", "airhead"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Daily Supply</span><input type="number" value={supplyForm.dailySupply} onChange={(event) => setSupplyForm({ ...supplyForm, dailySupply: Number(event.target.value) })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Source</span><input value={supplyForm.source} onChange={(event) => setSupplyForm({ ...supplyForm, source: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol"><span>Confidence</span><input value={supplyForm.confidence} onChange={(event) => setSupplyForm({ ...supplyForm, confidence: event.target.value })} /></label>
                    <label className="shell-authorqa__fieldcontrol shell-authorqa__fieldcontrol--wide"><span>Note</span><input value={supplyForm.note} onChange={(event) => setSupplyForm({ ...supplyForm, note: event.target.value })} /></label>
                  </div>
                  <div className="shell-authorqa__actionrow">
                    <button type="button" className="shell-authorqa__action" onClick={saveSupplySource}>Save Supply Source</button>
                    {supplyForm.id ? <button type="button" className="shell-authorqa__action" onClick={() => removeRow("supply_sources", supplyForm.id)}>Delete</button> : null}
                  </div>

                  <div className="shell-authorqa__subsection">
                    <div className="shell-authorqa__rowhead"><strong>Off-map Link</strong><span>Connect authored sources to entry zones without mutating baked transport layers.</span></div>
                    <div className="shell-authorqa__formgrid">
                      <label className="shell-authorqa__fieldcontrol"><span>ID</span><input value={linkForm.id} onChange={(event) => setLinkForm({ ...linkForm, id: event.target.value })} /></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Label</span><input value={linkForm.label} onChange={(event) => setLinkForm({ ...linkForm, label: event.target.value })} /></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Side</span><input value={linkForm.side} onChange={(event) => setLinkForm({ ...linkForm, side: event.target.value })} /></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Source Node</span><select value={linkForm.sourceNodeId} onChange={(event) => setLinkForm({ ...linkForm, sourceNodeId: event.target.value })}><option value="">Select</option>{state.supply_sources.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Entry Zone</span><select value={linkForm.entryZoneId} onChange={(event) => setLinkForm({ ...linkForm, entryZoneId: event.target.value })}><option value="">Select</option>{state.reinforcement_entry_zones.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Route Class</span><input value={linkForm.routeClass} onChange={(event) => setLinkForm({ ...linkForm, routeClass: event.target.value })} /></label>
                      <label className="shell-authorqa__fieldcontrol"><span>Capacity</span><input type="number" value={linkForm.capacity} onChange={(event) => setLinkForm({ ...linkForm, capacity: Number(event.target.value) })} /></label>
                    </div>
                    <div className="shell-authorqa__actionrow"><button type="button" className="shell-authorqa__action" onClick={saveOffMapLink}>Save Off-map Link</button></div>
                  </div>

                  <div className="shell-authorqa__rows">
                    {state.supply_sources.map((row) => (
                      <button key={row.id} type="button" className="shell-authorqa__row" onClick={() => loadSupply(row)}>
                        <div className="shell-authorqa__rowhead"><strong>{row.label}</strong><span>{row.kind}</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.side || "neutral"}</span><span>{row.daily_supply} / day</span></div>
                      </button>
                    ))}
                    {state.off_map_links.map((row) => (
                      <div key={row.id} className="shell-authorqa__row">
                        <div className="shell-authorqa__rowhead"><strong>{row.label}</strong><span>{row.route_class}</span></div>
                        <div className="shell-authorqa__rowmeta"><span>{row.source_node_id}</span><span>{row.entry_zone_id || "unlinked"}</span></div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="shell-authorqa__section">
                <div className="shell-authorqa__rowhead"><strong>Validation</strong><span>Authoritative Python validators now cover the same issue families shown here.</span></div>
                <div className="shell-authorqa__rows">
                  {issues.length ? issues.map((issue, index) => (
                    <div key={`${issue.code}:${index}`} className={"shell-authorqa__row is-" + issue.severity}>
                      <div className="shell-authorqa__rowhead"><strong>{issue.code}</strong><span>{issue.severity}</span></div>
                      <div className="shell-authorqa__rowmeta"><span>{issue.message}</span></div>
                    </div>
                  )) : (
                    <div className="shell-authorqa__status">No obvious authoring issues in the current preview state.</div>
                  )}
                </div>
              </div>

              <div className="shell-authorqa__section">
                <div className="shell-authorqa__rowhead"><strong>Schema Preview</strong><span>Named terrain/objectives and force setup stay distinct from baked geography.</span></div>
                <pre className="shell-authorqa__payload">{JSON.stringify({ objectivesDoc: serializedObjectives, setupDoc: serializedSetup }, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
