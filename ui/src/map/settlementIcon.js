import { MAP_SETTLEMENT_TIER_TOKENS, MAP_ZOOM_TIERS, MAP_ZOOM_VISIBILITY, getMapZoomTier } from "./designTokens.js";
import { normalizeUnitCounterFaction } from "./unitCounterPalette.js";

export const SETTLEMENT_ICON_REFERENCE_CASES = [
  { id: "village-friendly", label: "Village", tier: "village", controlState: "friendly", note: "Minor locality at far zoom." },
  { id: "town-enemy", label: "Town", tier: "town", controlState: "enemy", note: "Enemy-held town with underbar control cue." },
  { id: "city-contested", label: "City", tier: "city", controlState: "contested", note: "Contested city uses a broken alert ring." },
  { id: "major-city", label: "Major City", tier: "major_city", controlState: "friendly", note: "District ring marks a major urban anchor." },
  { id: "capital-key", label: "Key Objective City", tier: "capital", controlState: "friendly", supplyHub: true, note: "Key objective accent with optional support marker." },
  { id: "damaged-town", label: "Damaged Town", tier: "town", controlState: "enemy", damaged: true, note: "Damage corner is reserved for authoritative damage state." },
];

const CONTROL_PRIORITY = ["friendly", "enemy", "contested", "neutral", "unknown"];
const TIER_PRIORITY = MAP_SETTLEMENT_TIER_TOKENS.map((entry) => entry.id);
const FRIENDLY_CONTROL_TOKENS = new Set(["allied", "friendly", "blue", "rok", "un", "us"]);
const ENEMY_CONTROL_TOKENS = new Set(["axis", "enemy", "red", "nkpa", "nva", "ija"]);

function numericValue(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function upperText(value) {
  return String(value ?? "").trim().toUpperCase();
}

function lowerText(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function inferSettlementTier(objective) {
  const value = numericValue(objective?.value);
  const match = MAP_SETTLEMENT_TIER_TOKENS.find((entry) => {
    if (value == null) {
      return entry.id === "town";
    }
    return value >= entry.minValue;
  });
  return match?.id ?? "town";
}

export function inferSettlementControlState(objective) {
  const rawState = lowerText(objective?.state);
  const controlled = objective?.controlled;
  const side = upperText(objective?.side);

  if (rawState === "unheld" || rawState.includes("contested") || controlled === false) {
    return "contested";
  }

  if (rawState.startsWith("held_")) {
    const heldBy = rawState.slice(5);
    if (FRIENDLY_CONTROL_TOKENS.has(heldBy)) {
      return "friendly";
    }
    if (ENEMY_CONTROL_TOKENS.has(heldBy)) {
      return "enemy";
    }
  }

  const faction = normalizeUnitCounterFaction(side);
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

export function summarizeSettlementLocation(objective) {
  const tier = inferSettlementTier(objective);
  const token = MAP_SETTLEMENT_TIER_TOKENS.find((entry) => entry.id === tier) || MAP_SETTLEMENT_TIER_TOKENS[1];
  const controlState = inferSettlementControlState(objective);
  const value = numericValue(objective?.value);
  const damaged = Boolean(objective?.damaged || objective?.damage_state);
  const supplyHub = Boolean(objective?.supply_hub || objective?.is_supply_hub);

  return {
    tier,
    tierLabel: token.label,
    controlState,
    value,
    importanceMarks: token.importanceMarks,
    isKeyObjective: token.id === "capital" || token.id === "major_city",
    damaged,
    supplyHub,
    note: token.note,
  };
}

export function compareSettlementTier(leftTier, rightTier) {
  return TIER_PRIORITY.indexOf(leftTier) - TIER_PRIORITY.indexOf(rightTier);
}

export function compareSettlementControl(leftState, rightState) {
  return CONTROL_PRIORITY.indexOf(leftState) - CONTROL_PRIORITY.indexOf(rightState);
}

export function buildSettlementIconPresentation(options = {}) {
  const tier = TIER_PRIORITY.includes(options.tier) ? options.tier : "town";
  const controlState = CONTROL_PRIORITY.includes(options.controlState) ? options.controlState : "unknown";
  const placement = options.placement === "legend" || options.placement === "harness" ? options.placement : "map";
  const zoom = Number.isFinite(Number(options.zoom)) ? Number(options.zoom) : 1;
  const zoomTier = getMapZoomTier(zoom);
  const tierToken = MAP_SETTLEMENT_TIER_TOKENS.find((entry) => entry.id === tier) || MAP_SETTLEMENT_TIER_TOKENS[1];
  const zoomScale = placement === "legend" ? 1 : tierToken.scaleByZoomTier[zoomTier.id];
  const strokeWidth = placement === "legend" ? 1.1 : tierToken.strokeWidthByZoomTier[zoomTier.id];
  const valueMarksEnabled = options.showValueMarks !== false;
  const valueMarkCount = valueMarksEnabled ? tierToken.importanceMarks : 0;

  return {
    tier,
    controlState,
    placement,
    zoomTier: zoomTier.id,
    scale: Number(zoomScale.toFixed(2)),
    strokeWidth: Number(strokeWidth.toFixed(2)),
    showLabel: placement !== "legend" && zoom >= MAP_ZOOM_VISIBILITY.objectiveLabels,
    showValueMarks: placement !== "legend" && valueMarksEnabled && zoom >= MAP_ZOOM_VISIBILITY.objectiveMarkers,
    showStateText: placement !== "legend" && zoom >= MAP_ZOOM_VISIBILITY.objectiveState,
    valueMarkCount,
    damaged: Boolean(options.damaged),
    supplyHub: Boolean(options.supplyHub),
    label: tierToken.label,
  };
}

export function summarizeSettlementZoomPolicy() {
  return MAP_ZOOM_TIERS.map((tier) => ({
    id: tier.id,
    label: tier.label,
    zoomRange: `${tier.min.toFixed(2)}-${tier.max.toFixed(2)}`,
    behavior: tier.id === "far"
      ? "Icon only"
      : tier.id === "operational"
        ? "Icon plus limited value markers"
        : "Icon plus label and optional status markers",
  }));
}
