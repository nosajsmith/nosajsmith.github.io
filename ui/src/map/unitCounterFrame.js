import { MAP_COUNTER_FRAME_TOKENS, MAP_COUNTER_LABEL_POLICY, getMapZoomTier } from "./designTokens.js";

export const COUNTER_FRAME_VIEWBOX = Object.freeze({
  width: 72,
  height: 56,
  viewBox: "-36 -24 72 56",
});

export const COUNTER_FRAME_ORDER = ["company", "battalion", "regiment", "brigade", "division", "corps"];

export const COUNTER_FRAME_REFERENCE_CASES = [
  { id: "company", label: "Company", echelon: "company", code: "A CO" },
  { id: "battalion", label: "Battalion", echelon: "battalion", code: "1 BN" },
  { id: "regiment", label: "Regiment", echelon: "regiment", code: "1 MAR" },
  { id: "brigade", label: "Brigade", echelon: "brigade", code: "2 BDE" },
  { id: "division", label: "Division", echelon: "division", code: "1 DIV" },
  { id: "corps", label: "Corps", echelon: "corps", code: "I COR" },
  { id: "hq-division", label: "HQ", echelon: "division", code: "HQ", isHeadquarters: true },
];

function upperText(value) {
  return String(value || "").trim().toUpperCase();
}

function buildBeveledFrame(width, height, bevel) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  return [
    `M${(-halfWidth + bevel).toFixed(2)} ${(-halfHeight).toFixed(2)}`,
    `H${(halfWidth - bevel).toFixed(2)}`,
    `L${halfWidth.toFixed(2)} 0`,
    `L${(halfWidth - bevel).toFixed(2)} ${halfHeight.toFixed(2)}`,
    `H${(-halfWidth + bevel).toFixed(2)}`,
    `L${(-halfWidth).toFixed(2)} 0`,
    "Z",
  ].join(" ");
}

function buildWingedFrame(width, height, bevel, wingWidth = 3) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  return [
    `M${(-halfWidth + bevel).toFixed(2)} ${(-halfHeight).toFixed(2)}`,
    `H${(halfWidth - bevel - wingWidth).toFixed(2)}`,
    `L${(halfWidth - wingWidth).toFixed(2)} ${(-halfHeight + 4).toFixed(2)}`,
    `L${halfWidth.toFixed(2)} 0`,
    `L${(halfWidth - wingWidth).toFixed(2)} ${(halfHeight - 4).toFixed(2)}`,
    `L${(halfWidth - bevel - wingWidth).toFixed(2)} ${halfHeight.toFixed(2)}`,
    `H${(-halfWidth + bevel).toFixed(2)}`,
    `L${(-halfWidth + wingWidth).toFixed(2)} ${(halfHeight - 4).toFixed(2)}`,
    `L${(-halfWidth).toFixed(2)} 0`,
    `L${(-halfWidth + wingWidth).toFixed(2)} ${(-halfHeight + 4).toFixed(2)}`,
    "Z",
  ].join(" ");
}

function buildInsetFrame(width, height, bevel, inset = 2.6) {
  return buildBeveledFrame(Math.max(12, width - inset * 2), Math.max(10, height - inset * 2), Math.max(2, bevel - 1));
}

function buildDividerPath(width) {
  const inner = Math.max(8, width / 2 - 4);
  return `M${(-inner).toFixed(2)} 0 H${inner.toFixed(2)}`;
}

function buildHeaderRulePath(width) {
  const inner = Math.max(8, width / 2 - 7);
  return `M${(-inner).toFixed(2)} -5.5 H${inner.toFixed(2)}`;
}

function buildHqPennantPath(width, height) {
  const top = -(height / 2);
  const mastY = top - 7;
  const pennantY = mastY + 1.2;
  const pennantEnd = Math.min(11, width / 2 - 6);
  return {
    staff: `M0 ${mastY.toFixed(2)} V${(top + 1).toFixed(2)}`,
    pennant: `M0 ${pennantY.toFixed(2)} H${pennantEnd.toFixed(2)} L${(pennantEnd - 4).toFixed(2)} ${(pennantY + 3.2).toFixed(2)} H0 Z`,
  };
}

export function isHeadquartersUnit(unit) {
  const unitType = upperText(unit?.unit_type);
  const kind = upperText(unit?.kind);
  const name = upperText(unit?.name);
  return unitType === "HEADQUARTERS" || kind === "HEADQUARTERS" || /\bHQ\b|\bHEADQUARTERS?\b/.test(name);
}

export function inferUnitCounterEchelon(unit) {
  const name = upperText(unit?.name);
  const id = upperText(unit?.id);
  const text = `${name} ${id}`.trim();
  const unitType = upperText(unit?.unit_type);
  const kind = upperText(unit?.kind);

  if (/\bCORPS\b/.test(text)) {
    return "corps";
  }
  if (/\bDIV(?:ISION)?\b/.test(text)) {
    return "division";
  }
  if (/\bBRIGADE\b|\bBDE\b/.test(text)) {
    return "brigade";
  }
  if (/\bREG(?:IMENT)?\b|\bRGT\b|\bRCT\b|\bMARINES\b/.test(text)) {
    return "regiment";
  }
  if (/\bCOMPANY\b|\bCO\b|\bTROOP\b|\bBATTERY\b/.test(text)) {
    return "company";
  }
  if (/\bBATT(?:ALION)?\b|\bBN\b/.test(text)) {
    return "battalion";
  }

  if (unitType === "HEADQUARTERS") {
    return "division";
  }
  if (unitType.includes("ARTILLERY") || unitType.includes("ENGINEER") || unitType.includes("RECON") || unitType.includes("ANTI") || unitType.includes("TANK")) {
    return "battalion";
  }
  if (kind === "LOGISTICS" || unitType.includes("SUPPORT")) {
    return "battalion";
  }
  if (unitType === "INFANTRY") {
    return "regiment";
  }
  return "battalion";
}

export function summarizeUnitCounterLabelPolicy(zoom) {
  const tier = getMapZoomTier(zoom);
  return MAP_COUNTER_LABEL_POLICY.find((entry) => entry.id === tier.id) || MAP_COUNTER_LABEL_POLICY[1];
}

export function buildUnitCounterFramePresentation(options = {}) {
  const echelon = COUNTER_FRAME_ORDER.includes(options.echelon) ? options.echelon : "battalion";
  const spec = MAP_COUNTER_FRAME_TOKENS[echelon];
  const tier = getMapZoomTier(options.zoom ?? 1);
  const isHeadquarters = Boolean(options.isHeadquarters);
  const scale = tier.id === "far" ? 0.96 : tier.id === "close" ? 1.04 : 1;
  const width = Number((spec.widthPx * scale).toFixed(2));
  const height = Number((spec.heightPx * scale).toFixed(2));
  const bevel = Number((spec.bevelPx * scale).toFixed(2));
  const outerPath = echelon === "corps"
    ? buildWingedFrame(width, height, bevel, 3.2 * scale)
    : buildBeveledFrame(width, height, bevel);
  const innerPath = ["brigade", "division", "corps"].includes(echelon)
    ? buildInsetFrame(width, height, bevel, 2.6 * scale)
    : null;
  const headerRulePath = ["division", "corps"].includes(echelon)
    ? buildHeaderRulePath(width)
    : null;
  const dividerPath = buildDividerPath(width);
  const hqPennant = isHeadquarters ? buildHqPennantPath(width, height) : null;

  return {
    echelon,
    label: spec.label,
    width,
    height,
    outerPath,
    innerPath,
    dividerPath,
    headerRulePath,
    hqPennant,
    isHeadquarters,
    codeY: Number((height / 2 - 4.3).toFixed(2)),
    treatment: spec.treatment,
    tier: tier.id,
  };
}
