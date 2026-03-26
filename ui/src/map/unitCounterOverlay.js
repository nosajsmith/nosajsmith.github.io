import { MAP_COUNTER_OVERLAY_TOKENS } from "./designTokens.js";
import { inferUnitCounterState } from "./unitCounterPalette.js";

export const UNIT_COUNTER_OVERLAY_RULES = {
  priority: MAP_COUNTER_OVERLAY_TOKENS.priority,
  thresholds: {
    readinessDamagePct: MAP_COUNTER_OVERLAY_TOKENS.readinessDamagePct,
    readinessCriticalPct: MAP_COUNTER_OVERLAY_TOKENS.readinessCriticalPct,
    cohesionDamagePct: MAP_COUNTER_OVERLAY_TOKENS.cohesionDamagePct,
    cohesionCriticalPct: MAP_COUNTER_OVERLAY_TOKENS.cohesionCriticalPct,
    moraleDamagePct: MAP_COUNTER_OVERLAY_TOKENS.moraleDamagePct,
    moraleCriticalPct: MAP_COUNTER_OVERLAY_TOKENS.moraleCriticalPct,
    fatigueDamagePct: MAP_COUNTER_OVERLAY_TOKENS.fatigueDamagePct,
    fatigueCriticalPct: MAP_COUNTER_OVERLAY_TOKENS.fatigueCriticalPct,
    supplyLowPct: MAP_COUNTER_OVERLAY_TOKENS.supplyLowPct,
    supplyCriticalPct: MAP_COUNTER_OVERLAY_TOKENS.supplyCriticalPct,
    supplyDaysLow: MAP_COUNTER_OVERLAY_TOKENS.supplyDaysLow,
    supplyDaysCritical: MAP_COUNTER_OVERLAY_TOKENS.supplyDaysCritical,
  },
  movingTerms: ["move", "moving", "march", "advance", "redeploy", "reposition", "relocat", "transit", "withdraw", "retire", "start line"],
  engagedTerms: ["engaged", "contact", "combat", "assault", "counterattack", "under fire", "firefight", "attack underway", "in contact"],
  idleTerms: ["idle", "holding", "holding position", "rest", "reserve", "awaiting orders", "paused"],
  damagedTerms: ["damaged", "disrupted", "degraded", "battered", "shaken", "recovering"],
  criticalTerms: ["critical", "broken", "shattered", "collapse", "routed", "cut off", "isolated"],
};

export const UNIT_COUNTER_OVERLAY_REFERENCE_CASES = [
  {
    id: "moving",
    label: "Moving",
    faction: "friendly",
    service: "army",
    echelon: "regiment",
    symbol: "infantry",
    code: "1 INF",
    unit: {
      status: "moving to start line",
      inspector: {
        operational_state: { readiness: 68, fatigue: 18, morale: 72, cohesion: 67, loc: { state: "connected" } },
        supply: { supply_pct: 76, supply_days_current: 3.8 },
        orders: { action: "move", lifecycle_state: "moving to start line", status: "executing" },
      },
    },
  },
  {
    id: "engaged",
    label: "Engaged",
    faction: "enemy",
    service: "army",
    echelon: "battalion",
    symbol: "armor",
    code: "3 TK",
    unit: {
      status: "engaged in contact",
      inspector: {
        operational_state: { readiness: 63, fatigue: 26, morale: 58, cohesion: 61, loc: { state: "connected" } },
        supply: { supply_pct: 64, supply_days_current: 3.1 },
        orders: { action: "attack", status: "engaged" },
      },
    },
  },
  {
    id: "damaged",
    label: "Damaged",
    faction: "friendly",
    service: "army",
    echelon: "battalion",
    symbol: "artillery",
    code: "11 FA",
    unit: {
      status: "degraded after contact",
      inspector: {
        operational_state: { readiness: 49, fatigue: 43, morale: 51, cohesion: 53, loc: { state: "connected" } },
        supply: { supply_pct: 62, supply_days_current: 2.9 },
        orders: { action: "hold", status: "recovering" },
      },
    },
  },
  {
    id: "critical",
    label: "Critical",
    faction: "friendly",
    service: "marines",
    echelon: "regiment",
    symbol: "infantry",
    code: "2 MAR",
    unit: {
      status: "critical",
      inspector: {
        operational_state: { readiness: 28, fatigue: 74, morale: 33, cohesion: 30, loc: { state: "threatened" } },
        supply: { supply_pct: 24, supply_days_current: 1.1 },
        orders: { action: "hold", status: "critical" },
      },
    },
  },
  {
    id: "low-supply",
    label: "Low Supply",
    faction: "partner",
    service: "army",
    echelon: "brigade",
    symbol: "mechanized",
    code: "ROK",
    unit: {
      status: "active",
      inspector: {
        operational_state: { readiness: 61, fatigue: 24, morale: 60, cohesion: 59, loc: { state: "connected" } },
        supply: { supply_pct: 42, supply_days_current: 1.9 },
        orders: { action: "hold", status: "active" },
      },
    },
  },
  {
    id: "out-of-command",
    label: "Out of Command",
    faction: "friendly",
    service: "navy",
    echelon: "battalion",
    symbol: "engineer",
    code: "ENG",
    unit: {
      status: "active",
      inspector: {
        operational_state: { readiness: 58, fatigue: 29, morale: 57, cohesion: 50, loc: { state: "broken" } },
        supply: { supply_pct: 57, supply_days_current: 2.6 },
        orders: { action: "hold", status: "paused" },
      },
    },
  },
  {
    id: "selected",
    label: "Selected",
    faction: "friendly",
    service: "air_force",
    echelon: "division",
    symbol: "headquarters",
    code: "HQ",
    isHeadquarters: true,
    selected: true,
    unit: {
      status: "active",
      inspector: {
        operational_state: { readiness: 72, fatigue: 12, morale: 74, cohesion: 71, loc: { state: "connected" } },
        supply: { supply_pct: 81, supply_days_current: 4.4 },
        orders: { action: "reserve", status: "awaiting orders" },
      },
    },
  },
  {
    id: "stacked",
    label: "Critical + Supply",
    faction: "enemy",
    service: "army",
    echelon: "battalion",
    symbol: "recon",
    code: "RCN",
    unit: {
      status: "engaged and critical",
      inspector: {
        operational_state: { readiness: 32, fatigue: 69, morale: 38, cohesion: 34, loc: { state: "broken" } },
        supply: { supply_pct: 29, supply_days_current: 1.4 },
        orders: { action: "counterattack", status: "engaged" },
      },
    },
  },
];

function metricNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function includesAny(text, terms) {
  return terms.some((term) => text.includes(term));
}

function statusText(unit) {
  return [
    unit?.status,
    unit?.readiness_band,
    unit?.morale_band,
    unit?.inspector?.operational_state?.status,
    unit?.inspector?.orders?.action,
    unit?.inspector?.orders?.status,
    unit?.inspector?.orders?.lifecycle_state,
    unit?.inspector?.orders?.delay_reason,
    unit?.inspector?.orders?.note,
  ]
    .filter((value) => typeof value === "string" && value.trim())
    .join(" ")
    .toLowerCase();
}

export function buildUnitCounterOverlayPresentation(unit = {}, options = {}) {
  const overlayText = statusText(unit);
  const state = inferUnitCounterState(unit);
  const readiness = metricNumber(unit?.inspector?.operational_state?.readiness ?? unit?.readiness);
  const fatigue = metricNumber(unit?.inspector?.operational_state?.fatigue);
  const morale = metricNumber(unit?.inspector?.operational_state?.morale ?? unit?.morale);
  const cohesion = metricNumber(unit?.inspector?.operational_state?.cohesion);
  const supplyPct = metricNumber(unit?.inspector?.supply?.supply_pct);
  const supplyDays = metricNumber(unit?.inspector?.supply?.supply_days_current);
  const disabled = Boolean(options.disabled ?? state.disabled);
  const outOfCommand = Boolean(options.outOfCommand ?? state.outOfCommand);
  const explicitCritical = includesAny(overlayText, UNIT_COUNTER_OVERLAY_RULES.criticalTerms);
  const explicitDamaged = includesAny(overlayText, UNIT_COUNTER_OVERLAY_RULES.damagedTerms);
  const moving = !disabled && includesAny(overlayText, UNIT_COUNTER_OVERLAY_RULES.movingTerms);
  const engaged = !disabled && includesAny(overlayText, UNIT_COUNTER_OVERLAY_RULES.engagedTerms);
  const idle = !disabled && !moving && !engaged && includesAny(overlayText, UNIT_COUNTER_OVERLAY_RULES.idleTerms);
  const lowSupply = (
    (supplyPct != null && supplyPct <= MAP_COUNTER_OVERLAY_TOKENS.supplyLowPct)
    || (supplyDays != null && supplyDays <= MAP_COUNTER_OVERLAY_TOKENS.supplyDaysLow)
  );
  const critical = Boolean(
    disabled
    || outOfCommand
    || explicitCritical
    || (readiness != null && readiness <= MAP_COUNTER_OVERLAY_TOKENS.readinessCriticalPct)
    || (cohesion != null && cohesion <= MAP_COUNTER_OVERLAY_TOKENS.cohesionCriticalPct)
    || (morale != null && morale <= MAP_COUNTER_OVERLAY_TOKENS.moraleCriticalPct)
    || (fatigue != null && fatigue >= MAP_COUNTER_OVERLAY_TOKENS.fatigueCriticalPct)
    || (supplyPct != null && supplyPct <= MAP_COUNTER_OVERLAY_TOKENS.supplyCriticalPct)
    || (supplyDays != null && supplyDays <= MAP_COUNTER_OVERLAY_TOKENS.supplyDaysCritical)
  );
  const damaged = !critical && Boolean(
    explicitDamaged
    || (readiness != null && readiness <= MAP_COUNTER_OVERLAY_TOKENS.readinessDamagePct)
    || (cohesion != null && cohesion <= MAP_COUNTER_OVERLAY_TOKENS.cohesionDamagePct)
    || (morale != null && morale <= MAP_COUNTER_OVERLAY_TOKENS.moraleDamagePct)
    || (fatigue != null && fatigue >= MAP_COUNTER_OVERLAY_TOKENS.fatigueDamagePct)
  );
  const edgeState = critical
    ? "critical"
    : engaged
      ? "engaged"
      : moving
        ? "moving"
        : idle
          ? "idle"
          : null;

  return {
    selected: Boolean(options.selected),
    disabled,
    outOfCommand,
    lowSupply: !disabled && lowSupply,
    moving: !disabled && moving,
    engaged: !disabled && engaged,
    damaged,
    critical,
    idle: !disabled && idle,
    edgeState,
    active: Boolean(edgeState || damaged || lowSupply || outOfCommand || options.selected),
  };
}
