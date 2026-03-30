// ui/src/lib/scenario_adapter.js
// Normalizes scenario JSON from the bridge into UI-friendly shape.
// Output units: { id, name, side, q, r, px, py, raw }

import { axialToPixel } from "./hex.js";

function isNum(n) { return typeof n === "number" && Number.isFinite(n); }

export const DEFAULT_PITCH_SCENARIO = "inchon_mvp";

export function canonicalScenarioKey(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\.json$/i, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function scenarioKeysMatch(left, right) {
  const leftKey = canonicalScenarioKey(left);
  const rightKey = canonicalScenarioKey(right);
  return Boolean(leftKey && rightKey && leftKey === rightKey);
}

function pitchScenarioScore(value) {
  const text = canonicalScenarioKey(value).replace(/_/g, " ");
  if (!text) {
    return Number.POSITIVE_INFINITY;
  }
  if (text === "inchon mvp") {
    return 0;
  }
  if (/inchon|incheon|chromite/.test(text)) {
    return 1;
  }
  if (/korea|waegwan|naktong|nakdong|seoul|kimpo|pusan/.test(text)) {
    return 2;
  }
  return 3;
}

export function pickPreferredPitchScenario(scenarios) {
  if (!Array.isArray(scenarios) || !scenarios.length) {
    return null;
  }
  return [...scenarios]
    .sort((left, right) => pitchScenarioScore(left) - pitchScenarioScore(right) || left.localeCompare(right))[0] ?? null;
}

function seedCoords(units) {
  // deterministic spread if coords missing
  let bi = 0, ri = 0, ni = 0;
  for (const u of units) {
    if (isNum(u.q) && isNum(u.r)) continue;

    const side = String(u.side || "").toUpperCase();
    if (side === "BLUE") {
      const col = bi % 6, row = Math.floor(bi / 6);
      u.q = 3 + col; u.r = 4 + row; bi++;
    } else if (side === "RED") {
      const col = ri % 6, row = Math.floor(ri / 6);
      u.q = 16 + col; u.r = 4 + row; ri++;
    } else {
      const col = ni % 6, row = Math.floor(ni / 6);
      u.q = 9 + col; u.r = 2 + row; ni++;
    }
  }
}

export function adaptScenario(rawScenario, opts = {}) {
  const hexSize = Number(opts.hexSize ?? rawScenario?.meta?.hexSize ?? 22);
  const padX = Number(opts.padX ?? rawScenario?.meta?.padX ?? 60);
  const padY = Number(opts.padY ?? rawScenario?.meta?.padY ?? 80);

  const unitsIn = Array.isArray(rawScenario?.units) ? rawScenario.units : [];

  const units = unitsIn.map((u, idx) => {
    const id = u.id ?? u.unit_id ?? u.name ?? `unit-${idx}`;
    const name = u.name ?? String(id);
    const side = u.side ?? "NEUTRAL";

    // Prefer position:[q,r], fall back to x/y, then null (seed later)
    const q =
      (Array.isArray(u.position) ? u.position[0] : undefined) ??
      (isNum(u.x) ? u.x : undefined);

    const r =
      (Array.isArray(u.position) ? u.position[1] : undefined) ??
      (isNum(u.y) ? u.y : undefined);

    return { id, name, side, q, r, raw: u };
  });

  seedCoords(units);

  for (const u of units) {
    const { x, y } = axialToPixel(u.q, u.r, hexSize);
    u.px = x + padX;
    u.py = y + padY;
  }

  return {
    name: rawScenario?.name ?? rawScenario?.scenario_id ?? "scenario",
    meta: {
      ...(rawScenario?.meta || {}),
      hexSize,
      padX,
      padY,
    },
    units,
    raw: rawScenario,
  };
}

export function adaptMapState(rawMapState, opts = {}) {
  const mapMeta = rawMapState?.map?.meta ?? {};
  return adaptScenario(
    {
      units: rawMapState?.units ?? [],
      meta: {
        ...mapMeta,
        ...(opts || {}),
      },
    },
    opts,
  );
}
