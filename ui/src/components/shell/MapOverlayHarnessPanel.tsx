import { useMemo, useState, type CSSProperties } from "react";
import { buildMapOverlayManager, toggleMapLayer } from "../../map/overlayManager.js";
import { MAP_OPERATIONAL_OVERLAY_TOKENS } from "../../map/designTokens.js";
import { buildUnitCounterPaletteStyle } from "../../map/unitCounterPalette.js";
import AirfieldIcon from "./AirfieldIcon";
import GreaseMarkupOverlay from "./GreaseMarkupOverlay";
import ObjectiveOverlayBadge from "./ObjectiveOverlayBadge";
import SettlementIcon from "./SettlementIcon";
import UnitCounterFrame from "./UnitCounterFrame";
import UnitCounterStatusOverlay from "./UnitCounterStatusOverlay";

type WeatherHarnessId = "dry" | "rain" | "mud" | "snow" | "frozen_ground" | "fog";
type WeatherVisualVariant = "normal" | "damp" | "churned" | "snow_cover" | "frozen" | "fogged";
type MovementDebugCallout = {
  id: string;
  x: number;
  y: number;
  tone: "cheap" | "costly" | "blocked";
  label: string;
  detail: string;
};
type MovementDebugCase = {
  id: string;
  title: string;
  cost: string;
  tone: "cheap" | "costly" | "blocked";
  outcomeLabel: string;
  outcome: string;
  summary: string;
  drivers: string[];
};

const OVERLAY_HARNESS_LAYERS = [
  "grid",
  "terrainEmphasis",
  "barriers",
  "infrastructure",
  "supply",
  "command",
  "movementIntent",
  "frontline",
  "fogIntel",
  "greasePlanning",
  "objectives",
] as const;

const INITIAL_TOGGLES: Record<string, boolean> = {
  grid: true,
  terrainEmphasis: true,
  barriers: true,
  infrastructure: true,
  supply: true,
  command: true,
  movementIntent: true,
  frontline: true,
  fogIntel: false,
  greasePlanning: true,
  objectives: true,
};

const WEATHER_PREVIEWS: Record<WeatherHarnessId, {
  label: string;
  weatherState: string;
  groundState: string;
  visibilityState: string;
  visualVariant: WeatherVisualVariant;
  note: string;
}> = {
  dry: {
    label: "Dry",
    weatherState: "clear",
    groundState: "dry",
    visibilityState: "clear",
    visualVariant: "normal",
    note: "Baseline route bill with firm ground and no weather surcharge.",
  },
  rain: {
    label: "Rain",
    weatherState: "rain",
    groundState: "wet",
    visibilityState: "reduced",
    visualVariant: "damp",
    note: "Roads still help, but wet hexes add a shallow cost tax and reduce route confidence.",
  },
  mud: {
    label: "Mud",
    weatherState: "mud",
    groundState: "mud",
    visibilityState: "reduced",
    visualVariant: "churned",
    note: "Mud punishes off-road movement sharply, so roads dominate route choice even when longer.",
  },
  snow: {
    label: "Snow",
    weatherState: "snow",
    groundState: "snow",
    visibilityState: "reduced",
    visualVariant: "snow_cover",
    note: "Snow adds a broad movement drag without changing the underlying network geometry.",
  },
  frozen_ground: {
    label: "Frozen Ground",
    weatherState: "frozen_ground",
    groundState: "frozen_ground",
    visibilityState: "clear",
    visualVariant: "frozen",
    note: "Hard freeze recovers some mobility and exposes the provisional frozen-river hook for crossing logic.",
  },
  fog: {
    label: "Fog",
    weatherState: "fog",
    groundState: "wet",
    visibilityState: "fog",
    visualVariant: "fogged",
    note: "Movement cost stays close to wet-ground values, but the same path carries lower observation confidence.",
  },
};

const INFRASTRUCTURE_LINES = {
  primaryRoads: [
    { id: "pr-1", d: "M30 170 C78 156 116 138 166 112 S266 76 330 48" },
    { id: "pr-2", d: "M84 28 C116 56 156 84 212 120 S284 176 332 206" },
  ],
  secondaryRoads: [
    { id: "sr-1", d: "M54 92 C84 104 114 108 150 106" },
    { id: "sr-2", d: "M208 136 C244 146 278 156 314 182" },
  ],
  railLines: [
    { id: "rail-1", d: "M26 54 C76 66 136 78 208 94 S292 116 336 142" },
  ],
};

const BARRIER_LINES = [
  { id: "river-major-1", type: "majorRiver", d: "M18 126 C74 110 124 100 174 96 S270 102 344 118" },
  { id: "river-major-2", type: "majorRiver", d: "M24 138 C82 122 132 114 184 110 S278 114 340 132" },
  { id: "river-minor-1", type: "minorRiver", d: "M194 26 C220 54 238 82 246 118" },
];

const BARRIER_FEATURES = [
  { id: "crossing-1", type: "crossing", x: 164, y: 103 },
  { id: "crossing-2", type: "crossing", x: 258, y: 110 },
  { id: "escarpment-1", type: "escarpment", x: 90, y: 186 },
  { id: "impassable-1", type: "impassable", x: 302, y: 70 },
];

const INFRASTRUCTURE_NODES = [
  { id: "port-1", kind: "port", x: 52, y: 176 },
  { id: "airfield-1", kind: "airfield", x: 250, y: 78 },
  { id: "bridge-1", kind: "crossing", x: 164, y: 103 },
  { id: "bridge-2", kind: "crossing", x: 258, y: 110 },
];

const SUPPLY_SOURCES = [
  { id: "source-port", kind: "port", side: "friendly", x: 52, y: 176 },
  { id: "source-airfield", kind: "airfield", side: "friendly", x: 250, y: 78 },
];

const SUPPLY_CORRIDORS = [
  { id: "corridor-1", state: "primary", from: { x: 52, y: 176 }, to: { x: 134, y: 142 } },
  { id: "corridor-2", state: "strained", from: { x: 250, y: 78 }, to: { x: 212, y: 138 } },
  { id: "corridor-3", state: "degraded", from: { x: 250, y: 78 }, to: { x: 292, y: 168 } },
];

const COMMAND_HQS = [
  { id: "hq-1", x: 118, y: 118, radius: 64, focused: true },
  { id: "hq-2", x: 242, y: 118, radius: 52, focused: false },
];

const COMMAND_LINKS = [
  { id: "link-1", from: { x: 118, y: 118 }, to: { x: 134, y: 142 }, focused: true, degraded: false },
  { id: "link-2", from: { x: 118, y: 118 }, to: { x: 96, y: 164 }, focused: true, degraded: false },
  { id: "link-3", from: { x: 242, y: 118 }, to: { x: 212, y: 138 }, focused: false, degraded: false },
  { id: "link-4", from: { x: 242, y: 118 }, to: { x: 292, y: 168 }, focused: false, degraded: true },
];

const COMMAND_SUBORDINATES = [
  { id: "sub-1", x: 134, y: 142, degraded: false },
  { id: "sub-2", x: 96, y: 164, degraded: false },
];

const MOVEMENT_PATHS = [
  {
    id: "move-1",
    intent: "move",
    commitment: "planned",
    route: [{ x: 96, y: 164 }, { x: 122, y: 152 }, { x: 150, y: 124 }],
    waypoints: [{ x: 122, y: 152 }],
  },
  {
    id: "move-2",
    intent: "attack",
    commitment: "committed",
    route: [{ x: 134, y: 142 }, { x: 206, y: 120 }, { x: 274, y: 90 }],
    waypoints: [],
  },
  {
    id: "move-3",
    intent: "advance",
    commitment: "planned",
    route: [{ x: 212, y: 138 }, { x: 232, y: 126 }, { x: 252, y: 118 }, { x: 300, y: 98 }],
    waypoints: [{ x: 232, y: 126 }, { x: 252, y: 118 }],
  },
  {
    id: "move-4",
    intent: "fallback",
    commitment: "committed",
    route: [{ x: 292, y: 168 }, { x: 262, y: 180 }, { x: 224, y: 190 }],
    waypoints: [{ x: 262, y: 180 }],
  },
];

const MOVEMENT_DEBUG_CALLS_BY_WEATHER: Record<WeatherHarnessId, MovementDebugCallout[]> = {
  dry: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "ROAD", detail: "Road discount" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "BROKEN", detail: "Broken ground" },
    { id: "debug-fallback", x: 274, y: 188, tone: "blocked", label: "BLOCKED", detail: "No crossing" },
  ],
  rain: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "WET", detail: "Road still wins" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "SOFT", detail: "Wet climb" },
    { id: "debug-fallback", x: 274, y: 188, tone: "blocked", label: "HIGH", detail: "River up" },
  ],
  mud: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "MUD", detail: "Road preserves route" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "BOGGED", detail: "Mud surcharge" },
    { id: "debug-fallback", x: 274, y: 188, tone: "blocked", label: "BLOCKED", detail: "Swollen river" },
  ],
  snow: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "SNOW", detail: "Packed route" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "DRIFT", detail: "Snow drag" },
    { id: "debug-fallback", x: 274, y: 188, tone: "blocked", label: "BLOCKED", detail: "Ice not set" },
  ],
  frozen_ground: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "FIRM", detail: "Frozen ground" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "CRUST", detail: "Cold ridge" },
    { id: "debug-fallback", x: 274, y: 188, tone: "costly", label: "ICE", detail: "Frozen span" },
  ],
  fog: [
    { id: "debug-road", x: 118, y: 146, tone: "cheap", label: "ROAD", detail: "Cost steady" },
    { id: "debug-attack", x: 218, y: 116, tone: "costly", label: "COVER", detail: "Low vis" },
    { id: "debug-fallback", x: 274, y: 188, tone: "blocked", label: "BLOCKED", detail: "No crossing" },
  ],
};

const MOVEMENT_DEBUG_CASES_BY_WEATHER: Record<WeatherHarnessId, MovementDebugCase[]> = {
  dry: [
    {
      id: "route-case-road",
      title: "Road corridor wins",
      cost: "2.9 MP",
      tone: "cheap",
      outcomeLabel: "Primary factor",
      outcome: "Secondary road discount",
      summary: "Wheeled route prefers the secondary-road arc over the shorter wetland cut.",
      drivers: ["Grass/open road corridor", "Secondary road discount", "Dry season", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Broken hills slow approach",
      cost: "5.6 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Hills + broken ruggedness",
      summary: "The direct attack lane stays open, but broken and hilly hexes dominate the bill.",
      drivers: ["Hills terrain class", "Broken ruggedness", "Operational attack posture", "Enemy ZOC tax at contact edge"],
    },
    {
      id: "route-case-water",
      title: "Water barrier blocks",
      cost: "BLOCKED",
      tone: "blocked",
      outcomeLabel: "Blocked reason",
      outcome: "water_barrier",
      summary: "Open water without a bridge, ferry, ford, or amphibious state is rejected immediately.",
      drivers: ["Water terrain class", "No crossing state", "Vehicle restriction escalates to blocked"],
    },
  ],
  rain: [
    {
      id: "route-case-road",
      title: "Road corridor still wins",
      cost: "3.8 MP",
      tone: "cheap",
      outcomeLabel: "Primary factor",
      outcome: "Wet-road mitigation",
      summary: "The same road arc stays cheapest, but the wet-ground surcharge trims the discount.",
      drivers: ["Wet ground", "Secondary road discount", "Rain visibility tax", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Wet hills slow approach",
      cost: "6.2 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Hills + wet surcharge",
      summary: "The direct lane remains open, but broken hills now add wet-ground tax on top of terrain cost.",
      drivers: ["Hills terrain class", "Wet ground", "Broken ruggedness", "Attack posture"],
    },
    {
      id: "route-case-water",
      title: "High water still blocks",
      cost: "BLOCKED",
      tone: "blocked",
      outcomeLabel: "Blocked reason",
      outcome: "bridge_or_ford_required",
      summary: "Rain raises the cost of approach hexes, but the decisive issue is still a missing crossing state.",
      drivers: ["Water terrain class", "High-water channel", "No crossing state"],
    },
  ],
  mud: [
    {
      id: "route-case-road",
      title: "Road becomes decisive",
      cost: "5.1 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Road offsets mud",
      summary: "Mud makes the direct cut non-competitive, so even a longer road corridor wins clearly.",
      drivers: ["Mud ground state", "Secondary road discount", "Wheeled penalty", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Mud bogs broken hills",
      cost: "7.4 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Mud + broken hills",
      summary: "Broken hills turn into the expensive route under mud because both slope and ground penalties stack.",
      drivers: ["Mud ground state", "Hills terrain class", "Broken ruggedness", "Attack posture"],
    },
    {
      id: "route-case-water",
      title: "Swollen river blocks",
      cost: "BLOCKED",
      tone: "blocked",
      outcomeLabel: "Blocked reason",
      outcome: "water_barrier",
      summary: "Mud does not create a crossing; it only makes the blocked river approach even less attractive.",
      drivers: ["Water terrain class", "No crossing state", "Mud approach penalty"],
    },
  ],
  snow: [
    {
      id: "route-case-road",
      title: "Snow slows the corridor",
      cost: "4.4 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Snow drag",
      summary: "The road arc still wins, but snow cover adds a broad movement drag across every entry step.",
      drivers: ["Snow ground state", "Secondary road discount", "Wheeled snow penalty", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Snow drifts on high ground",
      cost: "6.8 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Snow + hills",
      summary: "Snow preserves the route but makes the broken hill lane expensive enough to delay the attack window.",
      drivers: ["Snow ground state", "Hills terrain class", "Broken ruggedness", "Attack posture"],
    },
    {
      id: "route-case-water",
      title: "River still closed",
      cost: "BLOCKED",
      tone: "blocked",
      outcomeLabel: "Blocked reason",
      outcome: "ice_not_set",
      summary: "Snow cover alone does not create an operational river crossing; an intact span or hard freeze is still required.",
      drivers: ["Water terrain class", "No crossing state", "Snow is not frozen ground"],
    },
  ],
  frozen_ground: [
    {
      id: "route-case-road",
      title: "Frozen corridor recovers tempo",
      cost: "3.1 MP",
      tone: "cheap",
      outcomeLabel: "Primary factor",
      outcome: "Firm frozen surface",
      summary: "Frozen ground restores most of the baseline route speed while keeping the road advantage in place.",
      drivers: ["Frozen ground state", "Secondary road discount", "Firm winter surface", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Frozen hills stay costly",
      cost: "5.2 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Hills + cold weather",
      summary: "The hard freeze helps, but broken hills still dominate the approach bill for heavy formations.",
      drivers: ["Frozen ground state", "Hills terrain class", "Broken ruggedness", "Attack posture"],
    },
    {
      id: "route-case-water",
      title: "Frozen river opens a provisional lane",
      cost: "4.7 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "frozen_river hook",
      summary: "Hard freeze does not make the lane cheap, but it converts a hard block into a costly provisional crossing.",
      drivers: ["Frozen river hook", "Temporary ice crossing", "Vehicle caution remains"],
    },
  ],
  fog: [
    {
      id: "route-case-road",
      title: "Road corridor holds",
      cost: "3.4 MP",
      tone: "cheap",
      outcomeLabel: "Primary factor",
      outcome: "Wet-road mitigation",
      summary: "Fog leaves route geometry intact, so the cost picture stays close to wet-ground movement with lower observation confidence.",
      drivers: ["Wet ground", "Secondary road discount", "Fog visibility penalty", "No command penalty"],
    },
    {
      id: "route-case-hills",
      title: "Hills unchanged, confidence lower",
      cost: "5.8 MP",
      tone: "costly",
      outcomeLabel: "Primary factor",
      outcome: "Broken hills",
      summary: "Terrain cost stays close to baseline, but low visibility makes the same lane feel more fragile operationally.",
      drivers: ["Hills terrain class", "Broken ruggedness", "Fog visibility penalty", "Attack posture"],
    },
    {
      id: "route-case-water",
      title: "River remains blocked",
      cost: "BLOCKED",
      tone: "blocked",
      outcomeLabel: "Blocked reason",
      outcome: "water_barrier",
      summary: "Fog changes observation, not the crossing state, so the river remains a hard stop without a span or ford.",
      drivers: ["Water terrain class", "No crossing state", "Fog does not alter mobility state"],
    },
  ],
};

const FRONT_SECTORS = [
  { id: "front-1", x: 84, y: 110, radius: 30, state: "quiet", stress: null },
  { id: "front-2", x: 162, y: 102, radius: 38, state: "contested", stress: "thin" },
  { id: "front-3", x: 236, y: 108, radius: 46, state: "hot", stress: "breakthrough" },
  { id: "front-4", x: 308, y: 126, radius: 34, state: "contested", stress: null },
];

const FRONT_SEGMENTS = [
  { id: "seg-1", from: { x: 84, y: 110 }, to: { x: 162, y: 102 }, state: "contested" },
  { id: "seg-2", from: { x: 162, y: 102 }, to: { x: 236, y: 108 }, state: "hot" },
  { id: "seg-3", from: { x: 236, y: 108 }, to: { x: 308, y: 126 }, state: "contested" },
];

const COUNTERS = [
  {
    id: "hq-1",
    x: 118,
    y: 118,
    className: "is-faction-friendly is-service-army is-division is-headquarters is-selected",
    palette: { faction: "friendly", service: "army" },
    frame: { echelon: "division" as const, isHeadquarters: true, symbol: "headquarters" as const, code: "DIV" },
    overlay: null,
  },
  {
    id: "u-1",
    x: 134,
    y: 142,
    className: "is-faction-friendly is-service-marines is-regiment",
    palette: { faction: "friendly", service: "marines" },
    frame: { echelon: "regiment" as const, isHeadquarters: false, symbol: "infantry" as const, code: "1 MAR" },
    overlay: { active: true, edgeState: "engaged" as const, damaged: false, lowSupply: false, outOfCommand: false },
  },
  {
    id: "u-2",
    x: 96,
    y: 164,
    className: "is-faction-friendly is-service-army is-battalion",
    palette: { faction: "friendly", service: "army" },
    frame: { echelon: "battalion" as const, isHeadquarters: false, symbol: "engineer" as const, code: "ENG" },
    overlay: { active: true, edgeState: "moving" as const, damaged: false, lowSupply: false, outOfCommand: false },
  },
  {
    id: "hq-2",
    x: 242,
    y: 118,
    className: "is-faction-friendly is-service-army is-brigade is-headquarters",
    palette: { faction: "friendly", service: "army" },
    frame: { echelon: "brigade" as const, isHeadquarters: true, symbol: "headquarters" as const, code: "BDE" },
    overlay: null,
  },
  {
    id: "u-3",
    x: 212,
    y: 138,
    className: "is-faction-friendly is-service-army is-battalion",
    palette: { faction: "friendly", service: "army" },
    frame: { echelon: "battalion" as const, isHeadquarters: false, symbol: "armor" as const, code: "TK" },
    overlay: { active: true, edgeState: "idle" as const, damaged: false, lowSupply: true, outOfCommand: false },
  },
  {
    id: "u-4",
    x: 292,
    y: 168,
    className: "is-faction-friendly is-service-army is-battalion is-out-of-command",
    palette: { faction: "friendly", service: "army", outOfCommand: true },
    frame: { echelon: "battalion" as const, isHeadquarters: false, symbol: "artillery" as const, code: "105" },
    overlay: { active: true, edgeState: "critical" as const, damaged: true, lowSupply: true, outOfCommand: true },
  },
];

const OBJECTIVES = [
  { id: "obj-1", x: 70, y: 54, tier: "village" as const, controlState: "friendly" as const, category: "secondary" as const, label: "Village" },
  { id: "obj-2", x: 148, y: 48, tier: "town" as const, controlState: "enemy" as const, category: "supply" as const, label: "Supply Node" },
  { id: "obj-3", x: 252, y: 58, tier: "city" as const, controlState: "contested" as const, category: "primary" as const, label: "Forward City" },
  { id: "obj-4", x: 318, y: 48, tier: "major_city" as const, controlState: "contested" as const, category: "strategic" as const, label: "Key City" },
];

const INTEL_CONTACTS = [
  { id: "intel-1", x: 84, y: 82, state: "stale", uncertainStrength: false },
  { id: "intel-2", x: 164, y: 76, state: "spotted", uncertainStrength: true },
  { id: "intel-3", x: 240, y: 84, state: "confirmed", uncertainStrength: false },
  { id: "intel-4", x: 306, y: 94, state: "uncertain", uncertainStrength: true },
];

const GREASE_ITEMS = [
  { id: "grease-1", tool: "freehand", style: "amber", points: [{ x: 26, y: 202 }, { x: 52, y: 190 }, { x: 88, y: 194 }, { x: 116, y: 184 }] },
  { id: "grease-2", tool: "straight_line", style: "offwhite", points: [{ x: 38, y: 148 }, { x: 116, y: 134 }] },
  { id: "grease-3", tool: "arrow", style: "amber", points: [{ x: 114, y: 212 }, { x: 176, y: 184 }] },
  { id: "grease-4", tool: "front_line", style: "blue", points: [{ x: 126, y: 84 }, { x: 176, y: 92 }, { x: 228, y: 86 }, { x: 286, y: 102 }] },
  { id: "grease-5", tool: "objective_circle", style: "amber", points: [{ x: 222, y: 36 }, { x: 282, y: 84 }] },
  { id: "grease-6", tool: "zone_box", style: "offwhite", points: [{ x: 252, y: 144 }, { x: 332, y: 212 }] },
  { id: "grease-7", tool: "defensive_line", style: "blue", points: [{ x: 176, y: 158 }, { x: 228, y: 148 }, { x: 274, y: 154 }] },
  { id: "grease-8", tool: "fallback_line", style: "amber", points: [{ x: 234, y: 198 }, { x: 276, y: 210 }, { x: 318, y: 200 }] },
];

export default function MapOverlayHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [layerToggles, setLayerToggles] = useState<Record<string, boolean>>(INITIAL_TOGGLES);
  const [weatherId, setWeatherId] = useState<WeatherHarnessId>("dry");
  const overlayManager = useMemo(() => buildMapOverlayManager({ toggles: layerToggles }), [layerToggles]);
  const layerEntries = useMemo(
    () => overlayManager.registry.filter((layer) => OVERLAY_HARNESS_LAYERS.includes(layer.id as typeof OVERLAY_HARNESS_LAYERS[number])),
    [overlayManager],
  );
  const weatherPreview = WEATHER_PREVIEWS[weatherId];
  const movementDebugCases = MOVEMENT_DEBUG_CASES_BY_WEATHER[weatherId];
  const movementDebugCallouts = MOVEMENT_DEBUG_CALLS_BY_WEATHER[weatherId];

  return (
    <div className={"shell-overlayharness" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-overlayharness__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-overlay-harness"
      >
        <span className="shell-map__legend-title">Overlay Harness</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-overlayharness__body" id="shell-overlay-harness">
          <div className="shell-overlayharness__toolbar" role="group" aria-label="Overlay harness layer controls">
            {layerEntries.map((layer) => {
              const active = Boolean(overlayManager.toggles[layer.id]);
              return (
                <button
                  key={layer.id}
                  type="button"
                  className={"shell-overlayharness__chip" + (active ? " is-active" : "")}
                  onClick={() => setLayerToggles((current) => toggleMapLayer(current, layer.id, overlayManager.registry))}
                >
                  {layer.label}
                </button>
              );
            })}
          </div>

          <div className="shell-overlayharness__toolbar" role="group" aria-label="Overlay harness weather selection">
            {(["dry", "rain", "mud", "snow", "frozen_ground", "fog"] as WeatherHarnessId[]).map((id) => (
              <button
                key={id}
                type="button"
                className={"shell-overlayharness__chip" + (weatherId === id ? " is-active" : "")}
                onClick={() => setWeatherId(id)}
              >
                {WEATHER_PREVIEWS[id].label}
              </button>
            ))}
          </div>

          <div className="shell-overlayharness__note">
            Mixed supply sectors, HQ influence, roads, rails, front sectors, movement axes, grease markup, objective tiers, and intel confidence states all render through the centralized layer registry without obscuring counters. The movement preview is currently showing {weatherPreview.label.toLowerCase()} conditions so route cost deltas track the same weather-state hooks used by gameplay.
          </div>

          <svg className={"shell-overlayharness__svg is-" + weatherPreview.visualVariant} viewBox="0 0 360 240" role="img" aria-label="Operational overlay harness scene">
            <defs>
              <pattern id="overlay-harness-grid" width="24" height="20.78" patternUnits="userSpaceOnUse">
                <path d="M12 0 L24 6.93 V20.78 L12 27.71 L0 20.78 V6.93 Z" className="shell-overlayharness__grid-line" />
              </pattern>
              <pattern id="overlay-harness-terrain" width="96" height="48" patternUnits="userSpaceOnUse">
                <path d="M0 14 Q18 2 36 14 T72 14 T108 14" className="shell-overlayharness__terrain-line" />
                <path d="M-6 34 Q18 24 42 34 T90 34 T138 34" className="shell-overlayharness__terrain-line is-soft" />
              </pattern>
              <pattern id="overlay-harness-fog" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(25)">
                <path d="M0 0 V24" className="shell-overlayharness__fog-line" />
              </pattern>
              <marker id="overlay-harness-arrow-move" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path className="shell-map__movement-arrowhead is-move" d="M0 0 L8 4 L0 8 Z" />
              </marker>
              <marker id="overlay-harness-arrow-attack" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path className="shell-map__movement-arrowhead is-attack" d="M0 0 L8 4 L0 8 Z" />
              </marker>
              <marker id="overlay-harness-arrow-advance" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path className="shell-map__movement-arrowhead is-advance" d="M0 0 L8 4 L0 8 Z" />
              </marker>
              <marker id="overlay-harness-arrow-fallback" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path className="shell-map__movement-arrowhead is-fallback" d="M0 0 L8 4 L0 8 Z" />
              </marker>
            </defs>

            <rect className="shell-overlayharness__field" x="0" y="0" width="360" height="240" />
            {overlayManager.toggles.grid ? <rect x="0" y="0" width="360" height="240" fill="url(#overlay-harness-grid)" className="shell-overlayharness__grid" /> : null}
            {overlayManager.toggles.terrainEmphasis ? <rect x="0" y="0" width="360" height="240" fill="url(#overlay-harness-terrain)" className="shell-overlayharness__terrain" /> : null}
            <rect className={`shell-overlayharness__weatherwash is-${weatherPreview.visualVariant}`} x="0" y="0" width="360" height="240" />

            {overlayManager.toggles.barriers ? (
              <g className="shell-map__barrier-overlay" aria-hidden="true">
                {BARRIER_LINES.map((segment) => (
                  <path key={segment.id} d={segment.d} className={`shell-map__barrier-segment is-${segment.type}`} />
                ))}
                {BARRIER_FEATURES.map((feature) => (
                  <g key={feature.id} className={`shell-map__barrier-feature is-${feature.type}`} transform={`translate(${feature.x}, ${feature.y})`}>
                    {feature.type === "crossing" ? (
                      <>
                        <circle className="shell-map__barrier-crossing-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.barrierCrossing} />
                        <path className="shell-map__barrier-crossing-mark" d="M-5 0 H5 M0 -5 V5" />
                      </>
                    ) : null}
                    {feature.type === "escarpment" ? <path className="shell-map__barrier-escarpment-mark" d="M-8 6 L-2 -6 L4 6 M2 6 L8 -6" /> : null}
                    {feature.type === "impassable" ? <path className="shell-map__barrier-impassable-mark" d="M-6 -6 L6 6 M6 -6 L-6 6" /> : null}
                  </g>
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.infrastructure ? (
              <g className="shell-map__infrastructure-overlay" aria-hidden="true">
                {INFRASTRUCTURE_LINES.primaryRoads.map((line) => (
                  <path key={line.id} d={line.d} className="shell-map__infrastructure-road is-primary" />
                ))}
                {INFRASTRUCTURE_LINES.secondaryRoads.map((line) => (
                  <path key={line.id} d={line.d} className="shell-map__infrastructure-road is-secondary" />
                ))}
                {INFRASTRUCTURE_LINES.railLines.map((line) => (
                  <path key={line.id} d={line.d} className="shell-map__infrastructure-rail" />
                ))}
                {INFRASTRUCTURE_NODES.map((node) => (
                  <g
                    key={node.id}
                    className={`shell-map__infrastructure-node is-${node.kind}`}
                    transform={`translate(${node.x}, ${node.y})`}
                  >
                    <circle
                      className="shell-map__infrastructure-node-ring"
                      r={node.kind === "crossing"
                        ? MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureCrossing
                        : MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureNode}
                    />
                    {node.kind === "crossing" ? (
                      <path className="shell-map__infrastructure-node-mark" d="M-6 0 H6 M0 -6 V6" />
                    ) : (
                      <circle className="shell-map__infrastructure-node-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.infrastructureCore} />
                    )}
                  </g>
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.command ? (
              <g className="shell-map__command-overlay" aria-hidden="true">
                {COMMAND_HQS.map((hq) => (
                  <circle
                    key={hq.id}
                    className={"shell-map__command-radius" + (hq.focused ? " is-focused" : "")}
                    cx={hq.x}
                    cy={hq.y}
                    r={hq.radius}
                  />
                ))}
                {COMMAND_LINKS.map((link) => (
                  <line
                    key={link.id}
                    className={"shell-map__command-link" + (link.degraded ? " is-degraded" : "") + (link.focused ? " is-focused" : "")}
                    x1={link.from.x}
                    y1={link.from.y}
                    x2={link.to.x}
                    y2={link.to.y}
                  />
                ))}
                {COMMAND_SUBORDINATES.map((unit) => (
                  <circle
                    key={unit.id}
                    className={"shell-map__command-subordinate" + (unit.degraded ? " is-degraded" : "")}
                    cx={unit.x}
                    cy={unit.y}
                    r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.commandSubordinate}
                  />
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.frontline ? (
              <g className="shell-map__front-overlay" aria-hidden="true">
                {FRONT_SECTORS.map((sector) => (
                  <g
                    key={sector.id}
                    className={`shell-map__front-sector is-${sector.state}${sector.stress ? ` has-${sector.stress}` : ""}`}
                    transform={`translate(${sector.x}, ${sector.y})`}
                  >
                    <circle className="shell-map__front-sector-fill" r={sector.radius} />
                    <circle className="shell-map__front-sector-ring" r={sector.radius} />
                    {sector.stress === "breakthrough" ? <path className="shell-map__front-sector-stress is-breakthrough" d="M-7 0 H7 M0 -7 V7" /> : null}
                    {sector.stress === "thin" ? <path className="shell-map__front-sector-stress is-thin" d="M-7 -5 L7 5 M7 -5 L-7 5" /> : null}
                  </g>
                ))}
                {FRONT_SEGMENTS.map((segment) => (
                  <line
                    key={segment.id}
                    className={`shell-map__front-segment is-${segment.state}`}
                    x1={segment.from.x}
                    y1={segment.from.y}
                    x2={segment.to.x}
                    y2={segment.to.y}
                  />
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.movementIntent ? (
              <g className="shell-map__movement-overlay" aria-hidden="true">
                {MOVEMENT_PATHS.map((path) => (
                  <g key={path.id} className={`shell-map__movement-path is-${path.intent} is-${path.commitment}`}>
                    <path
                      className="shell-map__movement-stroke"
                      d={path.route.map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`).join(" ")}
                      markerEnd={path.intent === "attack"
                        ? "url(#overlay-harness-arrow-attack)"
                        : path.intent === "advance"
                          ? "url(#overlay-harness-arrow-advance)"
                        : path.intent === "fallback"
                          ? "url(#overlay-harness-arrow-fallback)"
                          : "url(#overlay-harness-arrow-move)"}
                    />
                    {path.intent === "advance" ? <path className="shell-map__movement-axis" d={path.route.map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`).join(" ")} /> : null}
                    {path.waypoints.map((waypoint, index) => (
                      <circle
                        key={`${path.id}:waypoint:${index}`}
                        className="shell-map__movement-waypoint"
                        cx={waypoint.x}
                        cy={waypoint.y}
                        r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.movementWaypoint}
                      />
                    ))}
                  </g>
                ))}
                {movementDebugCallouts.map((callout) => (
                  <g key={callout.id} className={`shell-overlayharness__route-callout is-${callout.tone}`} transform={`translate(${callout.x}, ${callout.y})`}>
                    <rect className="shell-overlayharness__route-callout-box" x="-18" y="-22" width="64" height="24" rx="4" />
                    <text className="shell-overlayharness__route-callout-label" x="-12" y="-7">{callout.label}</text>
                    <text className="shell-overlayharness__route-callout-detail" x="-12" y="6">{callout.detail}</text>
                  </g>
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.supply ? (
              <g className="shell-map__supply-overlay" aria-hidden="true">
                {SUPPLY_CORRIDORS.map((corridor) => (
                  <line
                    key={corridor.id}
                    className={`shell-map__supply-corridor is-${corridor.state}`}
                    x1={corridor.from.x}
                    y1={corridor.from.y}
                    x2={corridor.to.x}
                    y2={corridor.to.y}
                  />
                ))}
                {SUPPLY_SOURCES.map((source) => (
                  <g key={source.id} className={`shell-map__supply-source is-${source.kind} is-${source.side}`} transform={`translate(${source.x}, ${source.y})`}>
                    <circle className="shell-map__supply-source-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplySource} />
                    <circle className="shell-map__supply-source-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplySourceCore} />
                  </g>
                ))}
                {[
                  { id: "marker-1", x: 134, y: 142, state: "well" },
                  { id: "marker-2", x: 212, y: 138, state: "strained" },
                  { id: "marker-3", x: 292, y: 168, state: "isolated" },
                ].map((marker) => (
                  <g key={marker.id} className={`shell-map__supply-marker is-${marker.state}`} transform={`translate(${marker.x}, ${marker.y})`}>
                    <circle className="shell-map__supply-marker-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplyMarker} />
                    <circle className="shell-map__supply-marker-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.supplyMarkerCore} />
                  </g>
                ))}
              </g>
            ) : null}

            {overlayManager.toggles.greasePlanning ? (
              <GreaseMarkupOverlay
                idPrefix="overlay-harness"
                items={GREASE_ITEMS}
                selectedId="grease-4"
              />
            ) : null}

            {overlayManager.toggles.objectives ? (
              <g aria-hidden="true">
                {OBJECTIVES.map((objective) => (
                  <g key={objective.id} transform={`translate(${objective.x}, ${objective.y})`}>
                    <ObjectiveOverlayBadge category={objective.category} importanceTier={objective.category === "strategic" ? 3 : objective.category === "primary" || objective.category === "supply" ? 2 : 1} contested={objective.controlState === "contested"} zoom={1.05} />
                    <SettlementIcon tier={objective.tier} controlState={objective.controlState} zoom={1.05} showValueMarks />
                  </g>
                ))}
                <g transform="translate(250 78)">
                  <AirfieldIcon tier="major_airbase" controlState="friendly" readinessBand="ready" sortieActive zoom={1.05} />
                </g>
              </g>
            ) : null}

            {COUNTERS.map((counter) => (
              <g
                key={counter.id}
                className={`shell-map__unit ${counter.className}`}
                transform={`translate(${counter.x}, ${counter.y})`}
                style={buildUnitCounterPaletteStyle(counter.palette) as CSSProperties}
              >
                <UnitCounterFrame
                  echelon={counter.frame.echelon}
                  isHeadquarters={counter.frame.isHeadquarters}
                  symbol={counter.frame.symbol}
                  code={counter.frame.code}
                  zoom={1.02}
                />
                <UnitCounterStatusOverlay
                  overlay={counter.overlay}
                  echelon={counter.frame.echelon}
                  isHeadquarters={counter.frame.isHeadquarters}
                  zoom={1.02}
                />
              </g>
            ))}

            {overlayManager.toggles.fogIntel ? (
              <>
                <g className="shell-map__fog-overlay" aria-hidden="true">
                  <rect x="0" y="0" width="360" height="240" className="shell-map__fog-wash" />
                  <rect x="0" y="0" width="360" height="240" fill="url(#overlay-harness-fog)" className="shell-map__fog-hatch" />
                </g>
                <g className="shell-map__intel-overlay" aria-hidden="true">
                  {INTEL_CONTACTS.map((contact) => (
                    <g
                      key={contact.id}
                      className={`shell-map__intel-contact is-${contact.state}${contact.uncertainStrength ? " has-uncertain-strength" : ""}`}
                      transform={`translate(${contact.x}, ${contact.y})`}
                    >
                      <circle className="shell-map__intel-contact-ring" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelContact} />
                      <circle className="shell-map__intel-contact-core" r={MAP_OPERATIONAL_OVERLAY_TOKENS.markerSizePx.intelCore} />
                      {contact.uncertainStrength ? <path className="shell-map__intel-contact-uncertain" d="M0 -6.2 C2.1 -6.2 3.7 -5.1 3.7 -3.3 C3.7 -1.5 2.4 -0.8 1 0.2 C0 0.9 -0.5 1.7 -0.5 2.6 M0 5.6 H0.1" /> : null}
                    </g>
                  ))}
                </g>
              </>
            ) : null}
          </svg>

          <div className="shell-overlayharness__movement-debug" aria-label="Movement route debug preview">
            <div className="shell-overlayharness__movement-head">
              <span className="shell-map__legend-title">Movement Debug</span>
              <span className="shell-map__legend-state">
                {overlayManager.toggles.movementIntent ? `${weatherPreview.label} preview` : "Hidden with movement layer"}
              </span>
            </div>
            <div className="shell-overlayharness__weatherstate">
              <div className="shell-overlayharness__movement-meta">
                <strong>Weather</strong>
                <span>{weatherPreview.weatherState}</span>
              </div>
              <div className="shell-overlayharness__movement-meta">
                <strong>Ground</strong>
                <span>{weatherPreview.groundState}</span>
              </div>
              <div className="shell-overlayharness__movement-meta">
                <strong>Visibility</strong>
                <span>{weatherPreview.visibilityState}</span>
              </div>
              <div className="shell-overlayharness__weathercopy">{weatherPreview.note}</div>
            </div>
            <div className="shell-overlayharness__movement-grid">
              {movementDebugCases.map((route) => (
                <div key={route.id} className={`shell-overlayharness__movement-card is-${route.tone}`}>
                  <div className="shell-overlayharness__movement-card-head">
                    <strong>{route.title}</strong>
                    <span>{route.cost}</span>
                  </div>
                  <div className="shell-overlayharness__movement-card-summary">{route.summary}</div>
                  <div className="shell-overlayharness__movement-meta">
                    <strong>{route.outcomeLabel}</strong>
                    <span>{route.outcome}</span>
                  </div>
                  <div className="shell-overlayharness__movement-driver-row">
                    {route.drivers.map((driver) => (
                      <span key={driver} className="shell-overlayharness__movement-driver">{driver}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
