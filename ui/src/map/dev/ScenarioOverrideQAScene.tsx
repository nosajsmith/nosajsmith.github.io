import { useMemo, useState } from "react";
import AirfieldIcon from "../../components/shell/AirfieldIcon";
import SettlementIcon from "../../components/shell/SettlementIcon";
import { axialToPixel, hexPolygonPoints } from "../../lib/hex.js";
import { normalizeHexTerrain } from "../hexTile.js";

type ScenarioOverrideQASceneProps = {
  theaterId: string | null;
};

type TerrainOption = "inherit" | "plains" | "forest" | "hills" | "rough" | "mountain" | "urban_built_up" | "water";
type TransportOption = "inherit" | "none" | "trail" | "secondary_road" | "primary_road" | "damaged" | "blocked";
type RailOption = "inherit" | "none" | "rail_corridor" | "damaged" | "blocked";
type CrossingAvailability = "inherit" | "none" | "bridge" | "ford" | "ferry";
type CrossingState = "inherit" | "intact_bridge" | "damaged_bridge" | "destroyed_bridge" | "repaired_bridge" | "ford" | "temporary_crossing" | "ferry" | "impassable_river";
type SettlementTier = "inherit" | "none" | "village" | "town" | "city";
type SettlementState = "inherit" | "friendly" | "enemy" | "contested" | "damaged";
type AirfieldTier = "inherit" | "none" | "minor_airstrip" | "operational_airfield" | "major_airbase";
type AirfieldState = "inherit" | "ready" | "damaged" | "destroyed" | "contested";
type SettlementEffectiveState = "friendly" | "enemy" | "contested" | "damaged";
type AirfieldEffectiveState = "ready" | "damaged" | "destroyed" | "contested";

type BaseHex = {
  hex_id: string;
  q: number;
  r: number;
  terrain_class: string;
  road_status: Exclude<TransportOption, "inherit">;
  rail_status: Exclude<RailOption, "inherit">;
  crossing_availability: Exclude<CrossingAvailability, "inherit">;
  crossing_state: Exclude<CrossingState, "inherit"> | null;
  settlement: null | { tier: Exclude<SettlementTier, "inherit" | "none">; state: SettlementEffectiveState; name: string };
  airfield: null | { tier: Exclude<AirfieldTier, "inherit" | "none">; state: AirfieldEffectiveState; name: string };
};

type OverrideDocument = {
  schema: string;
  version: number;
  scenario_id: string | null;
  theater_id: string | null;
  hex_overrides: Array<{
    coord: [number, number];
    hex_id: string | null;
    note?: string | null;
    provenance?: Record<string, string>;
    patch: {
      terrain_class?: string;
      road_status?: string;
      rail_status?: string;
      crossing_availability?: string;
      settlement?: {
        enabled?: boolean;
        tier?: string;
        state?: string;
        name?: string;
      };
      airfield?: {
        enabled?: boolean;
        tier?: string;
        state?: string;
        name?: string;
      };
    };
  }>;
  crossing_states: Array<{
    coord: [number, number];
    hex_id: string | null;
    state: string;
    source: string;
    notes?: string | null;
    engineer_unit_id?: string | null;
    metadata?: Record<string, string>;
  }>;
};

type EffectiveHex = BaseHex & {
  terrainClass: string;
  roadStatus: string;
  railStatus: string;
  crossingAvailability: string;
  crossingState: string | null;
  settlementEffective: BaseHex["settlement"];
  airfieldEffective: BaseHex["airfield"];
  overriddenFields: string[];
  note: string | null;
  provenance: Record<string, string>;
};

const HEX_SIZE = 24;
const SCENE_WIDTH = 420;
const SCENE_HEIGHT = 260;
const SCENE_OFFSET_X = 96;
const SCENE_OFFSET_Y = 84;

const EMPTY_DOCUMENT: OverrideDocument = {
  schema: "mwe.scenario_overrides.v1",
  version: 1,
  scenario_id: "override_preview",
  theater_id: "qa_preview",
  hex_overrides: [],
  crossing_states: [],
};

const SAVED_DOCUMENT: OverrideDocument = {
  schema: "mwe.scenario_overrides.v1",
  version: 1,
  scenario_id: "override_preview",
  theater_id: "qa_preview",
  hex_overrides: [
    {
      coord: [1, 1],
      hex_id: "ovrqa:1:1",
      note: "Historic town footprint correction",
      provenance: { source: "ams_sheet", confidence: "high" },
      patch: {
        terrain_class: "urban_built_up",
        road_status: "secondary_road",
        settlement: { enabled: true, tier: "town", state: "damaged", name: "Toktong Hamlet" },
      },
    },
    {
      coord: [2, 1],
      hex_id: "ovrqa:2:1",
      note: "Forward strip cratered by raids",
      provenance: { source: "designer_pass", confidence: "medium" },
      patch: {
        airfield: { enabled: true, tier: "operational_airfield", state: "damaged", name: "Forward Strip" },
      },
    },
    {
      coord: [0, 2],
      hex_id: "ovrqa:0:2",
      note: "Washed-out track no longer passable to wheeled units",
      provenance: { source: "field_report", confidence: "medium" },
      patch: {
        road_status: "blocked",
      },
    },
  ],
  crossing_states: [
    {
      coord: [3, 1],
      hex_id: "ovrqa:3:1",
      state: "destroyed_bridge",
      source: "scenario_override",
      notes: "Opening-turn demolition",
      metadata: { source: "engineer_order", confidence: "high" },
    },
  ],
};

const BASE_HEXES: BaseHex[] = [
  { hex_id: "ovrqa:0:0", q: 0, r: 0, terrain_class: "hills", road_status: "none", rail_status: "rail_corridor", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:1:0", q: 1, r: 0, terrain_class: "grass_open", road_status: "trail", rail_status: "rail_corridor", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:2:0", q: 2, r: 0, terrain_class: "forest", road_status: "none", rail_status: "rail_corridor", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:3:0", q: 3, r: 0, terrain_class: "water", road_status: "none", rail_status: "none", crossing_availability: "bridge", crossing_state: "intact_bridge", settlement: null, airfield: null },
  { hex_id: "ovrqa:4:0", q: 4, r: 0, terrain_class: "grass_open", road_status: "primary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:0:1", q: 0, r: 1, terrain_class: "forest", road_status: "none", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:1:1", q: 1, r: 1, terrain_class: "grass_open", road_status: "primary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: { tier: "village", state: "friendly", name: "Toktong" }, airfield: null },
  { hex_id: "ovrqa:2:1", q: 2, r: 1, terrain_class: "grass_open", road_status: "primary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: { tier: "operational_airfield", state: "ready", name: "Forward Strip" } },
  { hex_id: "ovrqa:3:1", q: 3, r: 1, terrain_class: "water", road_status: "none", rail_status: "none", crossing_availability: "bridge", crossing_state: "intact_bridge", settlement: null, airfield: null },
  { hex_id: "ovrqa:4:1", q: 4, r: 1, terrain_class: "urban_built_up", road_status: "primary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: { tier: "town", state: "enemy", name: "Depot Town" }, airfield: null },
  { hex_id: "ovrqa:0:2", q: 0, r: 2, terrain_class: "rough", road_status: "secondary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:1:2", q: 1, r: 2, terrain_class: "forest", road_status: "secondary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:2:2", q: 2, r: 2, terrain_class: "grass_open", road_status: "secondary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
  { hex_id: "ovrqa:3:2", q: 3, r: 2, terrain_class: "water", road_status: "none", rail_status: "none", crossing_availability: "ford", crossing_state: "ford", settlement: null, airfield: null },
  { hex_id: "ovrqa:4:2", q: 4, r: 2, terrain_class: "grass_open", road_status: "secondary_road", rail_status: "none", crossing_availability: "none", crossing_state: null, settlement: null, airfield: null },
];

const BULK_SELECTIONS = [
  { id: "roads", label: "Road Belt", pick: (hexRecord: BaseHex) => hexRecord.road_status !== "none" },
  { id: "river", label: "River Line", pick: (hexRecord: BaseHex) => hexRecord.crossing_availability !== "none" || normalizeHexTerrain(hexRecord.terrain_class) === "water" },
  { id: "north", label: "North Box", pick: (hexRecord: BaseHex) => hexRecord.q <= 2 && hexRecord.r <= 1 },
  { id: "forest", label: "Forest Band", pick: (hexRecord: BaseHex) => normalizeHexTerrain(hexRecord.terrain_class) === "forest" },
] as const;

function coordKey(q: number, r: number) {
  return `${q}:${r}`;
}

function cloneDocument(document: OverrideDocument): OverrideDocument {
  return JSON.parse(JSON.stringify(document));
}

function normalizeDocument(document: Partial<OverrideDocument> | null | undefined): OverrideDocument {
  return {
    schema: "mwe.scenario_overrides.v1",
    version: 1,
    scenario_id: document?.scenario_id ?? EMPTY_DOCUMENT.scenario_id,
    theater_id: document?.theater_id ?? EMPTY_DOCUMENT.theater_id,
    hex_overrides: Array.isArray(document?.hex_overrides) ? cloneDocument({ ...EMPTY_DOCUMENT, ...document }).hex_overrides : [],
    crossing_states: Array.isArray(document?.crossing_states) ? cloneDocument({ ...EMPTY_DOCUMENT, ...document }).crossing_states : [],
  };
}

function pointForHex(hexRecord: BaseHex) {
  const point = axialToPixel(hexRecord.q, hexRecord.r, HEX_SIZE);
  return {
    x: SCENE_OFFSET_X + point.x,
    y: SCENE_OFFSET_Y + point.y,
  };
}

function upsertHexOverride(document: OverrideDocument, coords: Array<[number, number]>, patch: OverrideDocument["hex_overrides"][number]["patch"], note: string, provenance: Record<string, string>) {
  const next = cloneDocument(document);
  coords.forEach(([q, r]) => {
    const hexRecord = BASE_HEXES.find((candidate) => candidate.q === q && candidate.r === r);
    if (!hexRecord) {
      return;
    }
    const existingIndex = next.hex_overrides.findIndex((row) => row.coord[0] === q && row.coord[1] === r);
    const entry = {
      coord: [q, r] as [number, number],
      hex_id: hexRecord.hex_id,
      note: note || null,
      provenance,
      patch,
    };
    if (existingIndex === -1) {
      next.hex_overrides.push(entry);
      return;
    }
    const current = next.hex_overrides[existingIndex];
    next.hex_overrides[existingIndex] = {
      ...current,
      note: note || current.note || null,
      provenance: { ...(current.provenance || {}), ...provenance },
      patch: { ...(current.patch || {}), ...patch },
    };
  });
  next.hex_overrides.sort((left, right) => (left.coord[1] - right.coord[1]) || (left.coord[0] - right.coord[0]));
  return next;
}

function upsertCrossingState(document: OverrideDocument, coords: Array<[number, number]>, state: Exclude<CrossingState, "inherit">, note: string, provenance: Record<string, string>) {
  const next = cloneDocument(document);
  coords.forEach(([q, r]) => {
    const hexRecord = BASE_HEXES.find((candidate) => candidate.q === q && candidate.r === r);
    if (!hexRecord) {
      return;
    }
    const existingIndex = next.crossing_states.findIndex((row) => row.coord[0] === q && row.coord[1] === r);
    const entry = {
      coord: [q, r] as [number, number],
      hex_id: hexRecord.hex_id,
      state,
      source: provenance.source || "scenario_override",
      notes: note || null,
      metadata: provenance,
    };
    if (existingIndex === -1) {
      next.crossing_states.push(entry);
    } else {
      next.crossing_states[existingIndex] = entry;
    }
  });
  next.crossing_states.sort((left, right) => (left.coord[1] - right.coord[1]) || (left.coord[0] - right.coord[0]));
  return next;
}

function clearOverrideCoords(document: OverrideDocument, coords: Array<[number, number]>) {
  const keys = new Set(coords.map(([q, r]) => coordKey(q, r)));
  return {
    ...cloneDocument(document),
    hex_overrides: document.hex_overrides.filter((row) => !keys.has(coordKey(row.coord[0], row.coord[1]))),
    crossing_states: document.crossing_states.filter((row) => !keys.has(coordKey(row.coord[0], row.coord[1]))),
  };
}

function applyDocumentToHexes(document: OverrideDocument): EffectiveHex[] {
  const overrideByCoord = new Map(document.hex_overrides.map((row) => [coordKey(row.coord[0], row.coord[1]), row]));
  const crossingByCoord = new Map(document.crossing_states.map((row) => [coordKey(row.coord[0], row.coord[1]), row]));

  return BASE_HEXES.map((baseHex) => {
    const key = coordKey(baseHex.q, baseHex.r);
    const overrideRow = overrideByCoord.get(key);
    const crossingRow = crossingByCoord.get(key);
    const patch = overrideRow?.patch || {};
    const settlementPatch = patch.settlement;
    const airfieldPatch = patch.airfield;

    let settlementEffective = baseHex.settlement;
    if (settlementPatch) {
      if (settlementPatch.enabled === false || settlementPatch.tier === "none") {
        settlementEffective = null;
      } else {
        settlementEffective = {
          tier: (settlementPatch.tier as Exclude<SettlementTier, "inherit" | "none">) || baseHex.settlement?.tier || "village",
          state: (settlementPatch.state as SettlementEffectiveState) || baseHex.settlement?.state || "friendly",
          name: settlementPatch.name || baseHex.settlement?.name || "Authored Settlement",
        };
      }
    }

    let airfieldEffective = baseHex.airfield;
    if (airfieldPatch) {
      if (airfieldPatch.enabled === false || airfieldPatch.tier === "none") {
        airfieldEffective = null;
      } else {
        airfieldEffective = {
          tier: (airfieldPatch.tier as Exclude<AirfieldTier, "inherit" | "none">) || baseHex.airfield?.tier || "minor_airstrip",
          state: (airfieldPatch.state as AirfieldEffectiveState) || baseHex.airfield?.state || "ready",
          name: airfieldPatch.name || baseHex.airfield?.name || "Authored Strip",
        };
      }
    }

    return {
      ...baseHex,
      terrainClass: normalizeHexTerrain(patch.terrain_class || baseHex.terrain_class),
      roadStatus: patch.road_status || baseHex.road_status,
      railStatus: patch.rail_status || baseHex.rail_status,
      crossingAvailability: patch.crossing_availability || baseHex.crossing_availability,
      crossingState: crossingRow?.state || baseHex.crossing_state,
      settlementEffective,
      airfieldEffective,
      overriddenFields: Object.keys(patch),
      note: overrideRow?.note || crossingRow?.notes || null,
      provenance: { ...(overrideRow?.provenance || {}), ...(crossingRow?.metadata || {}) },
    };
  });
}

function documentRows(document: OverrideDocument) {
  return applyDocumentToHexes(document)
    .filter((hexRecord) => hexRecord.overriddenFields.length > 0 || hexRecord.crossingState !== hexRecord.crossing_state)
    .map((hexRecord) => ({
      coord: [hexRecord.q, hexRecord.r] as [number, number],
      hex_id: hexRecord.hex_id,
      note: hexRecord.note,
      provenance: hexRecord.provenance,
      overriddenFields: hexRecord.overriddenFields,
      crossingState: hexRecord.crossingState,
      terrainClass: hexRecord.terrainClass,
    }));
}

export default function ScenarioOverrideQAScene({ theaterId }: ScenarioOverrideQASceneProps) {
  const [open, setOpen] = useState(false);
  const [document, setDocument] = useState<OverrideDocument>(EMPTY_DOCUMENT);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [undoStack, setUndoStack] = useState<OverrideDocument[]>([]);
  const [redoStack, setRedoStack] = useState<OverrideDocument[]>([]);
  const [terrainValue, setTerrainValue] = useState<TerrainOption>("inherit");
  const [roadValue, setRoadValue] = useState<TransportOption>("inherit");
  const [railValue, setRailValue] = useState<RailOption>("inherit");
  const [crossingAvailabilityValue, setCrossingAvailabilityValue] = useState<CrossingAvailability>("inherit");
  const [crossingStateValue, setCrossingStateValue] = useState<CrossingState>("inherit");
  const [settlementTierValue, setSettlementTierValue] = useState<SettlementTier>("inherit");
  const [settlementStateValue, setSettlementStateValue] = useState<SettlementState>("inherit");
  const [airfieldTierValue, setAirfieldTierValue] = useState<AirfieldTier>("inherit");
  const [airfieldStateValue, setAirfieldStateValue] = useState<AirfieldState>("inherit");
  const [noteValue, setNoteValue] = useState("");
  const [provenanceSource, setProvenanceSource] = useState("designer_pass");
  const [provenanceConfidence, setProvenanceConfidence] = useState("medium");

  const effectiveHexes = useMemo(() => applyDocumentToHexes(document), [document]);
  const rows = useMemo(() => documentRows(document), [document]);
  const selectedCoords = useMemo(() => selectedKeys.map((key) => key.split(":").map((value) => Number(value)) as [number, number]), [selectedKeys]);
  const selectedHex = useMemo(() => effectiveHexes.find((hexRecord) => selectedKeys.includes(coordKey(hexRecord.q, hexRecord.r))) || null, [effectiveHexes, selectedKeys]);

  function commitDocument(nextDocument: OverrideDocument) {
    setUndoStack((current) => [...current, cloneDocument(document)]);
    setRedoStack([]);
    setDocument(normalizeDocument(nextDocument));
  }

  function toggleSelection(q: number, r: number) {
    const key = coordKey(q, r);
    setSelectedKeys((current) => (
      current.includes(key)
        ? current.filter((entry) => entry !== key)
        : [...current, key]
    ));
  }

  function applyBulkSelection(id: string) {
    const preset = BULK_SELECTIONS.find((entry) => entry.id === id);
    if (!preset) {
      return;
    }
    setSelectedKeys(BASE_HEXES.filter(preset.pick).map((hexRecord) => coordKey(hexRecord.q, hexRecord.r)));
  }

  function handleApplyPatch() {
    if (!selectedCoords.length) {
      return;
    }
    const patch: OverrideDocument["hex_overrides"][number]["patch"] = {};
    if (terrainValue !== "inherit") {
      patch.terrain_class = terrainValue;
    }
    if (roadValue !== "inherit") {
      patch.road_status = roadValue;
    }
    if (railValue !== "inherit") {
      patch.rail_status = railValue;
    }
    if (crossingAvailabilityValue !== "inherit") {
      patch.crossing_availability = crossingAvailabilityValue;
    }
    if (settlementTierValue !== "inherit" || settlementStateValue !== "inherit") {
      if (settlementTierValue === "none") {
        patch.settlement = { enabled: false };
      } else {
        patch.settlement = {
          enabled: true,
          ...(settlementTierValue !== "inherit" ? { tier: settlementTierValue } : {}),
          ...(settlementStateValue !== "inherit" ? { state: settlementStateValue } : {}),
        };
      }
    }
    if (airfieldTierValue !== "inherit" || airfieldStateValue !== "inherit") {
      if (airfieldTierValue === "none") {
        patch.airfield = { enabled: false };
      } else {
        patch.airfield = {
          enabled: true,
          ...(airfieldTierValue !== "inherit" ? { tier: airfieldTierValue } : {}),
          ...(airfieldStateValue !== "inherit" ? { state: airfieldStateValue } : {}),
        };
      }
    }
    if (!Object.keys(patch).length) {
      return;
    }
    commitDocument(upsertHexOverride(document, selectedCoords, patch, noteValue, { source: provenanceSource, confidence: provenanceConfidence }));
  }

  function handleSetCrossingState() {
    if (!selectedCoords.length || crossingStateValue === "inherit") {
      return;
    }
    commitDocument(upsertCrossingState(document, selectedCoords, crossingStateValue, noteValue, { source: provenanceSource, confidence: provenanceConfidence }));
  }

  function handleClearSelected() {
    if (!selectedCoords.length) {
      return;
    }
    commitDocument(clearOverrideCoords(document, selectedCoords));
  }

  function handleClearAll() {
    if (!document.hex_overrides.length && !document.crossing_states.length) {
      return;
    }
    commitDocument(EMPTY_DOCUMENT);
  }

  function handleUndo() {
    setUndoStack((current) => {
      if (!current.length) {
        return current;
      }
      const nextUndo = [...current];
      const previous = nextUndo.pop()!;
      setRedoStack((redoCurrent) => [...redoCurrent, cloneDocument(document)]);
      setDocument(previous);
      return nextUndo;
    });
  }

  function handleRedo() {
    setRedoStack((current) => {
      if (!current.length) {
        return current;
      }
      const nextRedo = [...current];
      const nextDocument = nextRedo.pop()!;
      setUndoStack((undoCurrent) => [...undoCurrent, cloneDocument(document)]);
      setDocument(nextDocument);
      return nextRedo;
    });
  }

  function handleLoadSaved() {
    commitDocument(SAVED_DOCUMENT);
    setSelectedKeys([
      ...SAVED_DOCUMENT.hex_overrides.map((row) => coordKey(row.coord[0], row.coord[1])),
      ...SAVED_DOCUMENT.crossing_states.map((row) => coordKey(row.coord[0], row.coord[1])),
    ]);
  }

  return (
    <div className={"shell-overrideqa" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-overrideqa__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-scenario-override-qa"
      >
        <span className="shell-map__legend-title">Scenario Override QA</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-overrideqa__body" id="shell-scenario-override-qa">
          <div className="shell-overrideqa__toolbar" role="group" aria-label="Scenario override bulk selection">
            {BULK_SELECTIONS.map((selection) => (
              <button key={selection.id} type="button" className="shell-overrideqa__chip" onClick={() => applyBulkSelection(selection.id)}>
                {selection.label}
              </button>
            ))}
            <button type="button" className="shell-overrideqa__chip" onClick={() => setSelectedKeys([])}>Clear Sel</button>
          </div>

          <div className="shell-overrideqa__toolbar" role="group" aria-label="Scenario override document actions">
            <button type="button" className="shell-overrideqa__chip" onClick={handleLoadSaved}>Load Saved</button>
            <button type="button" className="shell-overrideqa__chip" onClick={handleUndo} disabled={!undoStack.length}>Undo</button>
            <button type="button" className="shell-overrideqa__chip" onClick={handleRedo} disabled={!redoStack.length}>Redo</button>
            <button type="button" className="shell-overrideqa__chip" onClick={handleClearSelected} disabled={!selectedCoords.length}>Clear Override</button>
            <button type="button" className="shell-overrideqa__chip" onClick={handleClearAll} disabled={!document.hex_overrides.length && !document.crossing_states.length}>Clear All</button>
          </div>

          <div className="shell-overrideqa__note">
            This preview keeps scenario-local overrides separate from the baked theater. Click hexes to build a multi-hex selection, apply an override patch, inspect provenance, and reload a saved document without mutating base terrain data.
            {theaterId ? ` Current packaged theater: ${theaterId}.` : ""}
          </div>

          <div className="shell-overrideqa__layout">
            <div className="shell-overrideqa__canvaswrap">
              <svg className="shell-overrideqa__svg" viewBox={`0 0 ${SCENE_WIDTH} ${SCENE_HEIGHT}`} role="img" aria-label="Scenario override editor preview">
                <rect className="shell-overrideqa__field" x="0" y="0" width={SCENE_WIDTH} height={SCENE_HEIGHT} />
                {effectiveHexes.map((hexRecord) => {
                  const point = pointForHex(hexRecord);
                  const key = coordKey(hexRecord.q, hexRecord.r);
                  const selected = selectedKeys.includes(key);
                  return (
                    <g key={hexRecord.hex_id} transform={`translate(${point.x}, ${point.y})`}>
                      <polygon
                        className={`shell-overrideqa__hex is-${hexRecord.terrainClass}`}
                        points={hexPolygonPoints(0, 0, HEX_SIZE - 2)}
                        onClick={() => toggleSelection(hexRecord.q, hexRecord.r)}
                      />
                      {hexRecord.roadStatus !== "none" ? (
                        <path className={`shell-overrideqa__road is-${hexRecord.roadStatus}`} d="M-12 4 H12" />
                      ) : null}
                      {hexRecord.railStatus !== "none" ? (
                        <path className={`shell-overrideqa__rail is-${hexRecord.railStatus}`} d="M0 -12 V12" />
                      ) : null}
                      {hexRecord.crossingAvailability !== "none" ? (
                        <circle className="shell-overrideqa__crossing-availability" cx="-9" cy="-9" r="3.4" />
                      ) : null}
                      {hexRecord.crossingState ? (
                        <text className={`shell-overrideqa__crossing-state is-${hexRecord.crossingState}`} x="8" y="-9">
                          {hexRecord.crossingState === "destroyed_bridge" ? "X" : hexRecord.crossingState === "temporary_crossing" ? "P" : hexRecord.crossingState === "damaged_bridge" ? "!" : "B"}
                        </text>
                      ) : null}
                      {hexRecord.settlementEffective ? (
                        <g transform="translate(-3 1)">
                          <SettlementIcon
                            tier={hexRecord.settlementEffective.tier}
                            controlState={hexRecord.settlementEffective.state === "damaged" ? "contested" : hexRecord.settlementEffective.state}
                            damaged={hexRecord.settlementEffective.state === "damaged"}
                            zoom={0.7}
                            placement="harness"
                            showValueMarks={false}
                          />
                        </g>
                      ) : null}
                      {hexRecord.airfieldEffective ? (
                        <g transform="translate(8 6)">
                          <AirfieldIcon
                            tier={hexRecord.airfieldEffective.tier}
                            controlState={hexRecord.airfieldEffective.state === "contested" ? "contested" : "friendly"}
                            damageState={hexRecord.airfieldEffective.state === "destroyed" ? "destroyed" : hexRecord.airfieldEffective.state === "damaged" ? "damaged" : "ready"}
                            readinessBand={hexRecord.airfieldEffective.state === "damaged" ? "limited" : "ready"}
                            zoom={0.56}
                            placement="harness"
                          />
                        </g>
                      ) : null}
                      {hexRecord.overriddenFields.length || hexRecord.crossingState !== hexRecord.crossing_state ? (
                        <>
                          <polygon className="shell-overrideqa__override-ring" points={hexPolygonPoints(0, 0, HEX_SIZE - 0.2)} />
                          <text className="shell-overrideqa__override-tag" x="-11" y="16">OVR</text>
                        </>
                      ) : null}
                      {selected ? <polygon className="shell-overrideqa__selection" points={hexPolygonPoints(0, 0, HEX_SIZE + 1.2)} /> : null}
                      <text className="shell-overrideqa__label" x="-9" y="0">{hexRecord.q},{hexRecord.r}</text>
                    </g>
                  );
                })}
              </svg>
            </div>

            <aside className="shell-overrideqa__inspect">
              <div className="shell-overrideqa__section">
                <div className="shell-overrideqa__summary">
                  <strong>Selection</strong>
                  <span>{selectedCoords.length} hex</span>
                </div>
                <div className="shell-overrideqa__metagrid">
                  <div className="shell-overrideqa__meta"><strong>Overrides</strong><span>{rows.length}</span></div>
                  <div className="shell-overrideqa__meta"><strong>Undo</strong><span>{undoStack.length}</span></div>
                  <div className="shell-overrideqa__meta"><strong>Redo</strong><span>{redoStack.length}</span></div>
                </div>
              </div>

              <div className="shell-overrideqa__section">
                <div className="shell-overrideqa__summary">
                  <strong>Patch Editor</strong>
                </div>
                <div className="shell-overrideqa__formgrid">
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Terrain</span>
                    <select value={terrainValue} onChange={(event) => setTerrainValue(event.target.value as TerrainOption)}>
                      <option value="inherit">Inherit</option>
                      <option value="plains">Plains</option>
                      <option value="forest">Forest</option>
                      <option value="hills">Hills</option>
                      <option value="rough">Rough</option>
                      <option value="mountain">Mountain</option>
                      <option value="urban_built_up">Urban</option>
                      <option value="water">Water</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Road</span>
                    <select value={roadValue} onChange={(event) => setRoadValue(event.target.value as TransportOption)}>
                      <option value="inherit">Inherit</option>
                      <option value="none">None</option>
                      <option value="trail">Trail</option>
                      <option value="secondary_road">Secondary</option>
                      <option value="primary_road">Primary</option>
                      <option value="damaged">Damaged</option>
                      <option value="blocked">Blocked</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Rail</span>
                    <select value={railValue} onChange={(event) => setRailValue(event.target.value as RailOption)}>
                      <option value="inherit">Inherit</option>
                      <option value="none">None</option>
                      <option value="rail_corridor">Rail</option>
                      <option value="damaged">Damaged</option>
                      <option value="blocked">Blocked</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Crossing</span>
                    <select value={crossingAvailabilityValue} onChange={(event) => setCrossingAvailabilityValue(event.target.value as CrossingAvailability)}>
                      <option value="inherit">Inherit</option>
                      <option value="none">None</option>
                      <option value="bridge">Bridge</option>
                      <option value="ford">Ford</option>
                      <option value="ferry">Ferry</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Settlement</span>
                    <select value={settlementTierValue} onChange={(event) => setSettlementTierValue(event.target.value as SettlementTier)}>
                      <option value="inherit">Inherit</option>
                      <option value="none">Disable</option>
                      <option value="village">Village</option>
                      <option value="town">Town</option>
                      <option value="city">City</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Settlement State</span>
                    <select value={settlementStateValue} onChange={(event) => setSettlementStateValue(event.target.value as SettlementState)}>
                      <option value="inherit">Inherit</option>
                      <option value="friendly">Friendly</option>
                      <option value="enemy">Enemy</option>
                      <option value="contested">Contested</option>
                      <option value="damaged">Damaged</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Airfield</span>
                    <select value={airfieldTierValue} onChange={(event) => setAirfieldTierValue(event.target.value as AirfieldTier)}>
                      <option value="inherit">Inherit</option>
                      <option value="none">Disable</option>
                      <option value="minor_airstrip">Strip</option>
                      <option value="operational_airfield">Airfield</option>
                      <option value="major_airbase">Airbase</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Airfield State</span>
                    <select value={airfieldStateValue} onChange={(event) => setAirfieldStateValue(event.target.value as AirfieldState)}>
                      <option value="inherit">Inherit</option>
                      <option value="ready">Ready</option>
                      <option value="damaged">Damaged</option>
                      <option value="destroyed">Destroyed</option>
                      <option value="contested">Contested</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Crossing State</span>
                    <select value={crossingStateValue} onChange={(event) => setCrossingStateValue(event.target.value as CrossingState)}>
                      <option value="inherit">Inherit</option>
                      <option value="intact_bridge">Intact</option>
                      <option value="damaged_bridge">Damaged</option>
                      <option value="destroyed_bridge">Destroyed</option>
                      <option value="repaired_bridge">Repaired</option>
                      <option value="ford">Ford</option>
                      <option value="temporary_crossing">Temporary</option>
                      <option value="ferry">Ferry</option>
                      <option value="impassable_river">Impassable</option>
                    </select>
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Note</span>
                    <input value={noteValue} onChange={(event) => setNoteValue(event.target.value)} placeholder="Designer note" />
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Source</span>
                    <input value={provenanceSource} onChange={(event) => setProvenanceSource(event.target.value)} placeholder="designer_pass" />
                  </label>
                  <label className="shell-overrideqa__fieldcontrol">
                    <span>Confidence</span>
                    <input value={provenanceConfidence} onChange={(event) => setProvenanceConfidence(event.target.value)} placeholder="medium" />
                  </label>
                </div>
                <div className="shell-overrideqa__actionrow">
                  <button type="button" className="shell-overrideqa__action" onClick={handleApplyPatch} disabled={!selectedCoords.length}>Apply Patch</button>
                  <button type="button" className="shell-overrideqa__action" onClick={handleSetCrossingState} disabled={!selectedCoords.length || crossingStateValue === "inherit"}>Set Crossing</button>
                </div>
              </div>

              <div className="shell-overrideqa__section">
                <div className="shell-overrideqa__summary">
                  <strong>Selected Hex</strong>
                </div>
                {selectedHex ? (
                  <div className="shell-overrideqa__metagrid">
                    <div className="shell-overrideqa__meta"><strong>ID</strong><span>{selectedHex.hex_id}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Base Terrain</strong><span>{selectedHex.terrain_class}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Effective Terrain</strong><span>{selectedHex.terrainClass}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Road</strong><span>{selectedHex.roadStatus}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Rail</strong><span>{selectedHex.railStatus}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Crossing</strong><span>{selectedHex.crossingState || selectedHex.crossingAvailability || "none"}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Note</strong><span>{selectedHex.note || "None"}</span></div>
                    <div className="shell-overrideqa__meta"><strong>Provenance</strong><span>{Object.entries(selectedHex.provenance).map(([key, value]) => `${key}:${value}`).join(", ") || "None"}</span></div>
                  </div>
                ) : (
                  <div className="shell-overrideqa__status">Select one or more hexes to inspect the effective override state.</div>
                )}
              </div>

              <div className="shell-overrideqa__section">
                <div className="shell-overrideqa__summary">
                  <strong>Override Rows</strong>
                  <span>{rows.length}</span>
                </div>
                <div className="shell-overrideqa__rows">
                  {rows.length ? rows.map((row) => (
                    <div key={row.hex_id} className="shell-overrideqa__row">
                      <div className="shell-overrideqa__rowhead">
                        <strong>{row.hex_id}</strong>
                        <span>{row.coord[0]},{row.coord[1]}</span>
                      </div>
                      <div className="shell-overrideqa__rowmeta">
                        <span>{row.overriddenFields.join(", ") || "crossing_state_only"}</span>
                        <span>{row.crossingState || row.terrainClass}</span>
                      </div>
                      <div className="shell-overrideqa__rowcopy">{row.note || "No note"} | {Object.entries(row.provenance).map(([key, value]) => `${key}:${value}`).join(", ") || "no provenance"}</div>
                    </div>
                  )) : <div className="shell-overrideqa__status">No scenario-local overrides yet.</div>}
                </div>
              </div>

              <div className="shell-overrideqa__section">
                <div className="shell-overrideqa__summary">
                  <strong>Saved Payload</strong>
                </div>
                <pre className="shell-overrideqa__payload">{JSON.stringify(document, null, 2)}</pre>
              </div>
            </aside>
          </div>
        </div>
      ) : null}
    </div>
  );
}
