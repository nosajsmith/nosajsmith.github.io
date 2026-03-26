import { MAP_AIRFIELD_TIER_TOKENS, MAP_ZOOM_TIERS, MAP_ZOOM_VISIBILITY, getMapZoomTier } from "./designTokens.js";
import { normalizeUnitCounterFaction } from "./unitCounterPalette.js";
import { inferSettlementControlState } from "./settlementIcon.js";

export const AIRFIELD_ICON_REFERENCE_CASES = [
  {
    id: "minor-airstrip",
    label: "Minor Airstrip",
    tier: "minor_airstrip",
    controlState: "friendly",
    readinessBand: "limited",
    note: "Small strip footprint with readiness stripe.",
  },
  {
    id: "operational-airfield",
    label: "Operational Airfield",
    tier: "operational_airfield",
    controlState: "friendly",
    readinessBand: "ready",
    note: "Standard runway field for most active basing context.",
  },
  {
    id: "major-airbase",
    label: "Major Airbase",
    tier: "major_airbase",
    controlState: "friendly",
    readinessBand: "ready",
    sortieActive: true,
    note: "Expanded runway silhouette with active sortie cue.",
  },
  {
    id: "damaged-airfield",
    label: "Damaged Airfield",
    tier: "operational_airfield",
    controlState: "enemy",
    readinessBand: "limited",
    damageState: "damaged",
    note: "Damage slash stays readable without overpowering the runway silhouette.",
  },
  {
    id: "destroyed-airfield",
    label: "Destroyed Airfield",
    tier: "minor_airstrip",
    controlState: "contested",
    readinessBand: "low",
    damageState: "destroyed",
    note: "Destroyed state uses a hard cross and deadened runway frame.",
  },
  {
    id: "inactive-airbase",
    label: "Inactive Airbase",
    tier: "major_airbase",
    controlState: "unknown",
    readinessBand: "low",
    note: "Inactive major base keeps silhouette prominence without the sortie cue.",
  },
];

const AIRFIELD_TIER_PRIORITY = MAP_AIRFIELD_TIER_TOKENS.map((entry) => entry.id);
const CONTROL_PRIORITY = ["friendly", "enemy", "contested", "neutral", "unknown"];
const DAMAGE_PRIORITY = ["destroyed", "damaged", "ready"];
const ACTIVE_SORTIE_RE = /(sortie|launch|airborne|strike|cap|intercept|scramble|patrol)/i;
const EXPLICIT_ACTIVE_RE = /(^|\b)(active|sortie|launch)(\b|$)/i;

function upperText(value) {
  return String(value ?? "").trim().toUpperCase();
}

function lowerText(value) {
  return String(value ?? "").trim().toLowerCase();
}

function numericValue(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeLocalityName(value) {
  return upperText(value)
    .replace(/\b(AIRFIELD|AIR BASE|AIRBASE|FIELD|AIRSTRIP|STRIP|BASE)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function coordMatch(left, right) {
  return Number(left?.x) === Number(right?.x) && Number(left?.y) === Number(right?.y);
}

function supportingObjectiveForAirfield(airfield, objectives = []) {
  const airfieldId = upperText(airfield?.id);
  const nameKey = normalizeLocalityName(airfield?.name);
  return objectives.find((objective) => {
    const objectiveId = upperText(objective?.id);
    const objectiveNameKey = normalizeLocalityName(objective?.name);
    return coordMatch(airfield, objective)
      || (airfieldId && objectiveId && airfieldId === objectiveId)
      || (nameKey && objectiveNameKey && nameKey === objectiveNameKey);
  }) || null;
}

function collectBasedAirUnits(airfield, units = []) {
  const airfieldId = upperText(airfield?.id);
  return units.filter((unit) => {
    const kind = lowerText(unit?.kind);
    const locationId = upperText(unit?.location_id);
    return (kind.includes("air") || kind.includes("aviation")) && airfieldId && locationId === airfieldId;
  });
}

export function inferAirfieldTier(airfield, objectives = []) {
  const explicit = lowerText(airfield?.tier || airfield?.airfield_tier || airfield?.type);
  if (explicit === "minor_airstrip" || explicit === "operational_airfield" || explicit === "major_airbase") {
    return explicit;
  }

  const name = upperText(airfield?.name);
  if (name.includes("AIRSTRIP") || /\bSTRIP\b/.test(name)) {
    return "minor_airstrip";
  }
  if (name.includes("AIR BASE") || name.includes("AIRBASE") || /\bBASE\b/.test(name)) {
    return "major_airbase";
  }

  const objective = supportingObjectiveForAirfield(airfield, objectives);
  const value = numericValue(objective?.value);
  if (value != null && value >= 75) {
    return "major_airbase";
  }
  return "operational_airfield";
}

export function inferAirfieldControlState(airfield, objectives = []) {
  const explicitState = lowerText(airfield?.state || airfield?.control_state);
  if (explicitState.includes("contested")) {
    return "contested";
  }
  if (explicitState.includes("friendly") || explicitState.includes("allied")) {
    return "friendly";
  }
  if (explicitState.includes("enemy") || explicitState.includes("axis")) {
    return "enemy";
  }
  if (explicitState.includes("neutral")) {
    return "neutral";
  }

  const objective = supportingObjectiveForAirfield(airfield, objectives);
  if (objective) {
    return inferSettlementControlState(objective);
  }

  const faction = normalizeUnitCounterFaction(airfield?.side);
  if (faction === "friendly" || faction === "partner") {
    return "friendly";
  }
  if (faction === "enemy") {
    return "enemy";
  }
  if (faction === "neutral") {
    return "neutral";
  }
  return "unknown";
}

export function inferAirfieldDamageState(airfield) {
  const raw = lowerText(airfield?.damage_state || airfield?.state);
  if (Boolean(airfield?.destroyed) || raw.includes("destroyed")) {
    return "destroyed";
  }
  if (Boolean(airfield?.damaged) || raw.includes("damaged") || raw.includes("disabled")) {
    return "damaged";
  }
  return "ready";
}

export function inferAirfieldReadinessBand(airfield, units = []) {
  const explicitBand = lowerText(airfield?.readiness_band);
  if (["ready", "limited", "low"].includes(explicitBand)) {
    return explicitBand;
  }

  const readiness = numericValue(airfield?.readiness);
  if (readiness != null) {
    return readiness >= 70 ? "ready" : readiness >= 50 ? "limited" : "low";
  }

  const basedUnits = collectBasedAirUnits(airfield, units);
  const readinessValues = basedUnits
    .map((unit) => numericValue(unit?.readiness ?? unit?.inspector?.operational_state?.readiness))
    .filter((value) => value != null);
  if (!readinessValues.length) {
    return "unknown";
  }
  const average = readinessValues.reduce((sum, value) => sum + value, 0) / readinessValues.length;
  return average >= 70 ? "ready" : average >= 50 ? "limited" : "low";
}

export function inferAirfieldSortieState(airfield, units = []) {
  const explicit = airfield?.sortie_active;
  if (typeof explicit === "boolean") {
    return explicit;
  }

  const status = lowerText(airfield?.sortie_status || airfield?.activity_state);
  if (status) {
    return EXPLICIT_ACTIVE_RE.test(status) && !status.includes("inactive");
  }

  const basedUnits = collectBasedAirUnits(airfield, units);
  return basedUnits.some((unit) => {
    const posture = String(unit?.inspector?.operational_state?.posture ?? "").trim();
    const action = String(unit?.inspector?.orders?.action ?? "").trim();
    const state = String(unit?.inspector?.orders?.status ?? "").trim();
    return ACTIVE_SORTIE_RE.test(posture) || ACTIVE_SORTIE_RE.test(action) || ACTIVE_SORTIE_RE.test(state);
  });
}

export function summarizeAirfieldLocation(airfield, context = {}) {
  const objectives = Array.isArray(context?.objectives) ? context.objectives : [];
  const units = Array.isArray(context?.units) ? context.units : [];
  const objective = supportingObjectiveForAirfield(airfield, objectives);
  const basedUnits = collectBasedAirUnits(airfield, units);
  const tier = inferAirfieldTier(airfield, objectives);
  const token = MAP_AIRFIELD_TIER_TOKENS.find((entry) => entry.id === tier) || MAP_AIRFIELD_TIER_TOKENS[1];
  return {
    tier,
    tierLabel: token.label,
    controlState: inferAirfieldControlState(airfield, objectives),
    damageState: inferAirfieldDamageState(airfield),
    readinessBand: inferAirfieldReadinessBand(airfield, units),
    sortieActive: inferAirfieldSortieState(airfield, units),
    supportingObjectiveId: objective?.id ?? null,
    basedAirUnits: basedUnits.length,
    note: token.note,
  };
}

export function compareAirfieldTier(leftTier, rightTier) {
  return AIRFIELD_TIER_PRIORITY.indexOf(leftTier) - AIRFIELD_TIER_PRIORITY.indexOf(rightTier);
}

export function compareAirfieldControl(leftState, rightState) {
  return CONTROL_PRIORITY.indexOf(leftState) - CONTROL_PRIORITY.indexOf(rightState);
}

export function compareAirfieldDamage(leftState, rightState) {
  return DAMAGE_PRIORITY.indexOf(leftState) - DAMAGE_PRIORITY.indexOf(rightState);
}

export function buildAirfieldIconPresentation(options = {}) {
  const tier = AIRFIELD_TIER_PRIORITY.includes(options.tier) ? options.tier : "operational_airfield";
  const controlState = CONTROL_PRIORITY.includes(options.controlState) ? options.controlState : "unknown";
  const damageState = DAMAGE_PRIORITY.includes(options.damageState) ? options.damageState : "ready";
  const readinessBand = ["ready", "limited", "low", "unknown"].includes(options.readinessBand) ? options.readinessBand : "unknown";
  const placement = options.placement === "legend" || options.placement === "harness" ? options.placement : "map";
  const zoom = Number.isFinite(Number(options.zoom)) ? Number(options.zoom) : 1;
  const zoomTier = getMapZoomTier(zoom);
  const token = MAP_AIRFIELD_TIER_TOKENS.find((entry) => entry.id === tier) || MAP_AIRFIELD_TIER_TOKENS[1];

  return {
    tier,
    controlState,
    damageState,
    readinessBand,
    sortieActive: Boolean(options.sortieActive),
    placement,
    zoomTier: zoomTier.id,
    scale: placement === "legend" ? 1 : token.scaleByZoomTier[zoomTier.id],
    strokeWidth: placement === "legend" ? 1.08 : token.strokeWidthByZoomTier[zoomTier.id],
    showLabel: placement !== "legend" && zoom >= MAP_ZOOM_VISIBILITY.airfieldLabels,
    showStatus: placement !== "legend" && zoom >= MAP_ZOOM_VISIBILITY.airfieldMarkers,
    label: token.label,
  };
}

export function summarizeAirfieldZoomPolicy() {
  return MAP_ZOOM_TIERS.map((tier) => ({
    id: tier.id,
    label: tier.label,
    zoomRange: `${tier.min.toFixed(2)}-${tier.max.toFixed(2)}`,
    behavior: tier.id === "far"
      ? "Runway icon only"
      : tier.id === "operational"
        ? "Runway icon plus readiness / damage marker"
        : "Runway icon plus label and optional activity cue",
  }));
}
