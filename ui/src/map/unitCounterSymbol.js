import { MAP_COUNTER_SYMBOL_TOKENS, getMapZoomTier } from "./designTokens.js";

export const UNIT_COUNTER_SYMBOL_PRIORITY = [
  "headquarters",
  "mechanized",
  "infantry",
  "armor",
  "artillery",
  "recon",
  "engineer",
  "anti_tank",
  "support",
  "formation",
];

export const UNIT_COUNTER_SYMBOL_REFERENCE_CASES = [
  { id: "infantry", label: "Infantry", symbol: "infantry", faction: "friendly", service: "army", echelon: "regiment", code: "1 INF" },
  { id: "armor", label: "Armor", symbol: "armor", faction: "enemy", service: "army", echelon: "battalion", code: "3 TK" },
  { id: "mechanized", label: "Mechanized", symbol: "mechanized", faction: "partner", service: "army", echelon: "brigade", code: "MEC" },
  { id: "artillery", label: "Artillery", symbol: "artillery", faction: "friendly", service: "army", echelon: "battalion", code: "11 FA" },
  { id: "headquarters", label: "HQ", symbol: "headquarters", faction: "friendly", service: "air_force", echelon: "division", code: "HQ", isHeadquarters: true },
  { id: "recon", label: "Recon", symbol: "recon", faction: "friendly", service: "marines", echelon: "company", code: "RCN" },
  { id: "engineer", label: "Engineer", symbol: "engineer", faction: "friendly", service: "navy", echelon: "battalion", code: "ENG" },
];

function upperText(value) {
  return String(value || "").trim().toUpperCase();
}

export function inferUnitCounterSymbol(unit) {
  const unitType = upperText(unit?.unit_type);
  const kind = upperText(unit?.kind);
  const name = upperText(unit?.name);

  if (unitType === "HEADQUARTERS" || kind === "HEADQUARTERS" || /\bHQ\b|\bHEADQUARTERS?\b/.test(name)) {
    return { id: "headquarters", label: "HQ / command" };
  }
  if (unitType.includes("MECH") || kind === "MECHANIZED") {
    return { id: "mechanized", label: "Mechanized" };
  }
  if (unitType.includes("ARMOR") || unitType.includes("ARMOUR") || unitType.includes("TANK") || kind === "ARMORED") {
    return { id: "armor", label: "Armor / tank" };
  }
  if (unitType.includes("ARTILLERY") || kind === "ARTILLERY") {
    return { id: "artillery", label: "Artillery" };
  }
  if (unitType.includes("RECON") || kind === "RECON") {
    return { id: "recon", label: "Recon" };
  }
  if (unitType.includes("ENGINEER") || kind === "ENGINEER") {
    return { id: "engineer", label: "Engineer" };
  }
  if (unitType.includes("INFANTRY") || name.includes("MARINE")) {
    return {
      id: "infantry",
      label: name.includes("MARINE") ? "Marine / infantry" : "Infantry",
    };
  }
  if (unitType.includes("ANTI") && unitType.includes("TANK")) {
    return { id: "anti_tank", label: "Anti-tank" };
  }
  if (kind === "LOGISTICS" || unitType.includes("LOGISTICS") || unitType.includes("SUPPORT")) {
    return { id: "support", label: "Support" };
  }
  if (kind || unitType) {
    return { id: "formation", label: "Formation" };
  }
  return null;
}

export function buildUnitCounterSymbolPresentation(options = {}) {
  const symbol = UNIT_COUNTER_SYMBOL_PRIORITY.includes(options.symbol) ? options.symbol : "formation";
  const placement = options.placement === "legend" ? "legend" : "counter";
  const tier = getMapZoomTier(options.zoom ?? 1);
  const scale = placement === "legend" ? 1 : MAP_COUNTER_SYMBOL_TOKENS.scaleByTier[tier.id];
  const offsetY = placement === "legend" ? 0 : MAP_COUNTER_SYMBOL_TOKENS.offsetYByTier[tier.id];
  const strokeWidth = placement === "legend" ? 1.25 : MAP_COUNTER_SYMBOL_TOKENS.strokeWidthByTier[tier.id];
  return {
    id: symbol,
    tier: tier.id,
    scale: Number(scale.toFixed(2)),
    offsetY: Number(offsetY.toFixed(2)),
    strokeWidth: Number(strokeWidth.toFixed(2)),
  };
}
