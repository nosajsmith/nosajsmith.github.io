import { MAP_COUNTER_BRANCH_PALETTE } from "./designTokens.js";

export const UNIT_COUNTER_PALETTE_ASSIGNMENTS = MAP_COUNTER_BRANCH_PALETTE;

export const UNIT_COUNTER_PALETTE_REFERENCE_CASES = [
  { id: "army", label: "Army", faction: "friendly", service: "army", echelon: "battalion", code: "1 BN" },
  { id: "marines", label: "Marines", faction: "friendly", service: "marines", echelon: "regiment", code: "1 MAR" },
  { id: "air-force", label: "Air Force", faction: "friendly", service: "air_force", echelon: "brigade", code: "AIR" },
  { id: "navy", label: "Navy", faction: "friendly", service: "navy", echelon: "brigade", code: "NAV" },
  { id: "partner", label: "UN Partner", faction: "partner", service: "army", echelon: "regiment", code: "ROK" },
  { id: "enemy", label: "Enemy", faction: "enemy", service: "army", echelon: "regiment", code: "IJA" },
  { id: "unknown", label: "Unknown", faction: "unknown", service: "army", echelon: "battalion", code: "UNK" },
  { id: "neutral", label: "Neutral", faction: "neutral", service: "army", echelon: "battalion", code: "NEU" },
  { id: "out-of-command", label: "Out of Command", faction: "friendly", service: "marines", echelon: "regiment", code: "1 MAR", outOfCommand: true },
  { id: "disabled", label: "Disabled", faction: "friendly", service: "army", echelon: "battalion", code: "1 BN", disabled: true },
];

function upperText(value) {
  return String(value || "").trim().toUpperCase();
}

function lowerText(value) {
  return String(value || "").trim().toLowerCase();
}

export function normalizeUnitCounterFaction(side) {
  const raw = upperText(side);
  if (!raw || raw === "UNKNOWN" || raw === "UNDETECTED") {
    return "unknown";
  }
  if (raw === "NEUTRAL" || raw === "CIVILIAN" || raw === "NONCOMBAT") {
    return "neutral";
  }
  if (raw === "AXIS" || raw === "ENEMY" || raw === "RED") {
    return "enemy";
  }
  if (raw === "ALLIED" || raw === "FRIENDLY" || raw === "BLUE") {
    return "friendly";
  }
  return "partner";
}

export function inferUnitCounterService(unit) {
  const unitType = upperText(unit?.unit_type);
  const kind = upperText(unit?.kind);
  const name = upperText(unit?.name);

  if (kind.includes("NAVAL") || kind.includes("NAVY") || kind.includes("SEA") || kind.includes("FLEET") || kind.includes("TASK FORCE")) {
    return "navy";
  }
  if (kind.includes("AIR") || kind.includes("AVIATION") || unitType.includes("AIR")) {
    return "air_force";
  }
  if (name.includes("MARINE") || unitType.includes("MARINE")) {
    return "marines";
  }
  return "army";
}

export function inferUnitCounterState(unit) {
  const status = lowerText(unit?.status);
  const locState = lowerText(unit?.inspector?.operational_state?.loc?.state);
  const disabled = status.includes("disabled") || status.includes("destroyed") || status.includes("inactive");
  return {
    disabled,
    outOfCommand: !disabled && (locState === "broken" || status.includes("out of command")),
  };
}

function paletteKeyFor(faction, service) {
  if (faction === "friendly") {
    if (service === "marines") {
      return "friendly_marines";
    }
    if (service === "air_force") {
      return "friendly_air_force";
    }
    if (service === "navy") {
      return "friendly_navy";
    }
    return "friendly_army";
  }
  if (faction === "partner") {
    return "partner";
  }
  if (faction === "enemy") {
    return "enemy";
  }
  if (faction === "neutral") {
    return "neutral";
  }
  return "unknown";
}

export function buildUnitCounterPalettePresentation(options = {}) {
  const faction = options.faction || normalizeUnitCounterFaction(options.side);
  const service = options.service || inferUnitCounterService(options);
  const disabled = Boolean(options.disabled);
  const outOfCommand = !disabled && Boolean(options.outOfCommand);
  const key = paletteKeyFor(faction, service);
  const base = UNIT_COUNTER_PALETTE_ASSIGNMENTS[key];
  const fill = disabled
    ? base.disabledFill
    : outOfCommand
      ? base.outOfCommandFill
      : base.fill;
  const border = disabled
    ? base.disabledBorder
    : outOfCommand
      ? base.outOfCommandBorder
      : base.border;

  return {
    key,
    faction,
    service,
    disabled,
    outOfCommand,
    label: base.label,
    fill,
    border,
    inner: disabled ? "rgba(209, 205, 194, 0.56)" : base.inner,
    code: disabled ? "rgba(224, 219, 208, 0.82)" : base.code,
    name: disabled ? "rgba(211, 206, 196, 0.72)" : base.name,
    bodyOpacity: disabled ? 0.84 : 1,
  };
}

export function buildUnitCounterPaletteStyle(options = {}) {
  const appearance = buildUnitCounterPalettePresentation(options);
  return {
    "--shell-counter-fill": appearance.fill,
    "--shell-counter-border": appearance.border,
    "--shell-counter-inner": appearance.inner,
    "--shell-counter-code": appearance.code,
    "--shell-counter-name": appearance.name,
    "--shell-counter-body-opacity": String(appearance.bodyOpacity),
  };
}
