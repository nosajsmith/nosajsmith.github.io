import { formatCommunicationTime, summarizeCommunications } from "./communications_summary.js";
import { summarizeCampaign, summarizeObjectives, summarizeScore } from "./dashboard_summary.js";
import { summarizeHendersonPressureBoard } from "./henderson_pressure_board_summary.js";
import { summarizeIntelligenceBranch } from "./intelligence_branch_summary.js";
import { buildWeatherImpactState } from "./map_scene.js";
import { summarizeTrackedOperations } from "./operations_planner.js";
import { summarizeReinforcementsBoard } from "./reinforcements_board_summary.js";
import { humanizeIntent, humanizeToken, pressureFallback } from "../../lib/view_snapshot.js";

function average(numbers) {
  const values = numbers.filter((value) => typeof value === "number" && Number.isFinite(value));
  if (!values.length) {
    return null;
  }
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function parseSupplyDays(value) {
  const match = String(value ?? "").match(/(\d+(?:\.\d+)?)/);
  return match ? Number.parseFloat(match[1]) : null;
}

function normalizeText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isCombatFormation(unit) {
  const unitType = String(unit?.unit_type ?? "").trim().toUpperCase();
  if (unitType === "HEADQUARTERS") {
    return false;
  }

  const rawKind = String(unit?.kind ?? "").trim().toLowerCase();
  return !rawKind.includes("air")
    && !rawKind.includes("naval")
    && !rawKind.includes("sea")
    && !rawKind.includes("logistics")
    && !rawKind.includes("supply")
    && !rawKind.includes("transport");
}

function commandFormations(units) {
  const combatUnits = units.filter(isCombatFormation);
  const alliedUnits = combatUnits.filter((unit) => String(unit?.side ?? "").toUpperCase() === "ALLIED");
  return alliedUnits.length ? alliedUnits : combatUnits;
}

function formatMetric(value, label) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(value)} ${label}`
    : `${label} not exposed`;
}

function formatPercent(value, label) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(value)}% ${label}`
    : `${label} not exposed`;
}

function formatSupplyPrimary(unit, supply) {
  if (typeof supply?.supply_display === "string" && supply.supply_display.trim()) {
    return supply.supply_display.trim();
  }
  if (typeof supply?.supply_days_current === "number" && Number.isFinite(supply.supply_days_current)) {
    return `${supply.supply_days_current.toFixed(1)} days`;
  }
  if (typeof supply?.supply_pct === "number" && Number.isFinite(supply.supply_pct)) {
    return `${Math.round(supply.supply_pct)}% supply`;
  }
  if (typeof unit?.supply === "string" && unit.supply.trim()) {
    return unit.supply.trim();
  }
  return "Supply not exposed";
}

function formatLocLabel(operational) {
  if (typeof operational?.loc?.label === "string" && operational.loc.label.trim()) {
    return operational.loc.label.trim();
  }
  if (typeof operational?.loc?.state === "string" && operational.loc.state.trim()) {
    return `LOC ${humanizeToken(operational.loc.state)}`;
  }
  return "LOC unavailable";
}

function buildForceQualityNote(operational, supply, replacementQuality) {
  const notes = [];
  const locState = normalizeText(operational?.loc?.state);

  if (locState === "broken") {
    notes.push("LOC broken");
  } else if (locState === "threatened") {
    notes.push("LOC threatened");
  }
  if (typeof supply?.supply_pct === "number" && supply.supply_pct < 60) {
    notes.push("Supply strained");
  }
  if (typeof operational?.readiness === "number" && operational.readiness < 50) {
    notes.push("Readiness low");
  }
  if (typeof operational?.fatigue === "number" && operational.fatigue > 35) {
    notes.push("Fatigue high");
  }
  if (typeof operational?.morale === "number" && operational.morale < 50) {
    notes.push("Morale reduced");
  }
  if (typeof operational?.cohesion === "number" && operational.cohesion < 50) {
    notes.push("Cohesion degraded");
  }
  if (typeof replacementQuality?.reconstitution_state === "string" && normalizeText(replacementQuality.reconstitution_state) !== "stable") {
    notes.push(humanizeToken(replacementQuality.reconstitution_state));
  }
  if (typeof replacementQuality?.newcomer_pct === "number" && replacementQuality.newcomer_pct >= 40) {
    notes.push("Newcomer-heavy");
  }
  if (!notes.length && typeof replacementQuality?.veteran_core_pct === "number" && replacementQuality.veteran_core_pct >= 60) {
    notes.push("Veteran cadre preserved");
  }

  return notes.slice(0, 3).join(" • ") || "No immediate warning from exposed fields.";
}

function summarizeForceQualityMatrix(units) {
  const formations = commandFormations(units);
  if (!formations.length) {
    return {
      available: false,
      rowCount: 0,
      note: "No visible combat-formation fidelity is exposed for a force-quality comparison on the current shell path.",
      rows: [],
    };
  }

  return {
    available: true,
    rowCount: formations.length,
    note: "Compares only exposed posture, condition, supply, LOC, and replacement-quality fields. No composite combat-power score is applied.",
    rows: formations.map((unit) => {
      const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
      const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
      const supply = inspector?.supply && typeof inspector.supply === "object" ? inspector.supply : {};
      const orders = inspector?.orders && typeof inspector.orders === "object" ? inspector.orders : {};
      const replacementQuality = inspector?.replacement_quality && typeof inspector.replacement_quality === "object" ? inspector.replacement_quality : {};

      const posture = typeof operational?.posture === "string" && operational.posture.trim()
        ? humanizeToken(operational.posture)
        : "Posture not exposed";
      const order = typeof orders?.action === "string" && orders.action.trim()
        ? humanizeToken(orders.action)
        : "No order text exposed";
      const orderStatus = typeof orders?.lifecycle_state === "string" && orders.lifecycle_state.trim()
        ? humanizeToken(orders.lifecycle_state)
        : (typeof orders?.status === "string" && orders.status.trim() ? humanizeToken(orders.status) : "Status unavailable");
      const reconstitutionPrimary = typeof replacementQuality?.reconstitution_state === "string" && replacementQuality.reconstitution_state.trim()
        ? humanizeToken(replacementQuality.reconstitution_state)
        : "Reconstitution not exposed";
      const qualityBands = [
        typeof replacementQuality?.experience_band === "string" && replacementQuality.experience_band.trim()
          ? humanizeToken(replacementQuality.experience_band)
          : null,
        typeof replacementQuality?.replacement_quality_band === "string" && replacementQuality.replacement_quality_band.trim()
          ? humanizeToken(replacementQuality.replacement_quality_band)
          : null,
      ].filter(Boolean);

      return {
        id: String(unit?.id ?? unit?.name ?? ""),
        name: String(unit?.name ?? "Formation"),
        posture,
        order,
        orderStatus,
        conditionPrimary: [
          formatMetric(operational?.readiness ?? unit?.readiness, "readiness"),
          formatMetric(operational?.fatigue, "fatigue"),
        ].join(" • "),
        conditionSecondary: [
          formatMetric(operational?.morale ?? unit?.morale, "morale"),
          formatMetric(operational?.cohesion, "cohesion"),
        ].join(" • "),
        supplyPrimary: formatSupplyPrimary(unit, supply),
        supplySecondary: formatLocLabel(operational),
        reconstitutionPrimary,
        reconstitutionSecondary: qualityBands.length ? qualityBands.join(" • ") : "Experience / replacement quality not exposed",
        veteranPrimary: formatPercent(replacementQuality?.veteran_core_pct, "veteran core"),
        veteranSecondary: formatPercent(replacementQuality?.newcomer_pct, "newcomers"),
        note: buildForceQualityNote(operational, supply, replacementQuality),
      };
    }),
  };
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function compactList(items, limit = 2) {
  const values = items
    .map((item) => String(item ?? "").trim())
    .filter(Boolean);
  if (!values.length) {
    return null;
  }
  if (values.length <= limit) {
    return values.join(", ");
  }
  return `${values.slice(0, limit).join(", ")} +${values.length - limit} more`;
}

function extractLandFormationState(unit) {
  const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
  const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
  const command = inspector?.command && typeof inspector.command === "object" ? inspector.command : {};
  const attachmentsSupport = inspector?.attachments_support && typeof inspector.attachments_support === "object" ? inspector.attachments_support : {};
  const orders = inspector?.orders && typeof inspector.orders === "object" ? inspector.orders : {};

  const hqId = typeof command?.hq_unit_id === "string" && command.hq_unit_id.trim() ? command.hq_unit_id.trim() : null;
  const superiorName = typeof command?.superior?.name === "string" && command.superior.name.trim()
    ? command.superior.name.trim()
    : (typeof command?.superior?.id === "string" && command.superior.id.trim() ? command.superior.id.trim() : null);
  const commandLabel = superiorName || hqId || null;
  const support = Array.isArray(attachmentsSupport?.support) ? attachmentsSupport.support.map((item) => String(item ?? "").trim()).filter(Boolean) : [];
  const attachments = Array.isArray(attachmentsSupport?.attachments) ? attachmentsSupport.attachments.map((item) => String(item ?? "").trim()).filter(Boolean) : [];
  const detached = Array.isArray(attachmentsSupport?.detached) ? attachmentsSupport.detached.map((item) => String(item ?? "").trim()).filter(Boolean) : [];

  return {
    id: String(unit?.id ?? unit?.name ?? ""),
    name: String(unit?.name ?? "Formation"),
    hqId,
    commandLabel,
    support,
    attachments,
    detached,
    locState: normalizeText(operational?.loc?.state),
    locLabel: typeof operational?.loc?.label === "string" && operational.loc.label.trim()
      ? operational.loc.label.trim()
      : (operational?.loc?.state ? `LOC ${humanizeToken(operational.loc.state)}` : "LOC unavailable"),
    posture: typeof operational?.posture === "string" && operational.posture.trim() ? operational.posture.trim() : null,
    orderAction: typeof orders?.action === "string" && orders.action.trim() ? orders.action.trim() : null,
    commander: typeof command?.commander === "string" && command.commander.trim() ? command.commander.trim() : null,
  };
}

function summarizeCampaignPicture(campaign, objectives, score, pressureSummary) {
  const objectiveProgress = objectives?.byState?.length
    ? objectives.byState.map((row) => `${row.state} ${row.count}`).join(" • ")
    : "Objective-state detail unavailable.";
  const keyObjective = objectives?.key?.[0]
    ? `${objectives.key[0].name} (${objectives.key[0].state})`
    : "No key objective is exposed on the current shell path.";
  const scoreSummary = Array.isArray(score) && score.length
    ? score.map((row) => `${row.label} ${row.value}`).join(" • ")
    : "Score unavailable.";

  return {
    available: true,
    note: "Campaign block uses only current campaign status, objective state, score, and pressure fields already exposed on the shell path.",
    objectiveProgress,
    keyObjective,
    scoreSummary,
    pressureSummary: pressureSummary || "Pressure summary unavailable.",
    winTarget: campaign?.winTarget ?? null,
  };
}

export function summarizeLandForcesModule(units) {
  const formations = commandFormations(units);
  if (!formations.length) {
    return {
      available: false,
      note: "No visible land-force organization is exposed on the current shell path.",
      metrics: [
        { label: "Visible Formations", value: "0" },
        { label: "HQ Linked", value: "0" },
        { label: "HQ Records", value: "Not exposed" },
        { label: "LOC Alerts", value: "0" },
      ],
      oob: {
        headline: "No higher-headquarters linkage is exposed on the current shell path.",
        rows: [{ label: "OOB", value: "Unavailable", note: "No visible command-organization picture is exposed." }],
      },
      support: {
        headline: "No support battalion assignments are exposed on the current shell path.",
        rows: [{ label: "Support", value: "Unavailable", note: "Attached support detail unavailable." }],
      },
      loc: {
        headline: "No threatened or broken LOC state is exposed on current formations.",
        rows: [{ label: "LOC", value: "Unavailable", note: "LOC alert detail unavailable." }],
      },
      organization: {
        headline: "Reserve and command-organization detail are limited on the current shell path.",
        rows: [{ label: "Command Net", value: "Unavailable", note: "No authoritative command organization is exposed." }],
      },
    };
  }

  const states = formations.map(extractLandFormationState);
  const hqLinked = states.filter((state) => state.hqId).length;
  const distinctHq = [...new Set(states.map((state) => state.hqId).filter(Boolean))];
  const locAlerts = states
    .filter((state) => state.locState === "broken" || state.locState === "threatened")
    .sort((left, right) => {
      const leftRank = left.locState === "broken" ? 0 : 1;
      const rightRank = right.locState === "broken" ? 0 : 1;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.name.localeCompare(right.name);
    });
  const supportStates = states.filter((state) => state.support.length || state.attachments.length || state.detached.length);
  const reserveCount = states.filter((state) => normalizeText(state.posture) === "reserve").length;
  const activeOrders = states.filter((state) => state.orderAction).length;
  const commanderNamed = states.filter((state) => state.commander).length;
  const unlinkedCount = states.length - hqLinked;

  const oobGroups = new Map();
  states.forEach((state) => {
    const key = state.commandLabel || "No HQ linkage exposed";
    const entry = oobGroups.get(key) ?? { label: key, items: [] };
    entry.items.push(state);
    oobGroups.set(key, entry);
  });

  const oobRows = Array.from(oobGroups.values())
    .sort((left, right) => right.items.length - left.items.length || left.label.localeCompare(right.label))
    .slice(0, 3)
    .map((group) => ({
      label: group.label,
      value: pluralize(group.items.length, "formation"),
      note: compactList(group.items.map((item) => item.name)) ?? "Formation names unavailable.",
    }));

  const supportRows = supportStates.length
    ? supportStates.slice(0, 3).map((state) => ({
        label: state.name,
        value: compactList(state.support.length ? state.support : state.attachments, 2) ?? "Support detail unavailable",
        note: state.detached.length
          ? `Detached ${compactList(state.detached, 2) ?? "elements"}`
          : (state.commandLabel ?? "No HQ linkage exposed"),
      }))
    : [{ label: "Support", value: "Unavailable", note: "No support battalion or attachment record is exposed on the current shell path." }];

  const locRows = locAlerts.length
    ? locAlerts.slice(0, 3).map((state) => ({
        label: state.name,
        value: state.locLabel,
        note: state.commandLabel ?? "No HQ linkage exposed",
      }))
    : [{ label: "LOC Alerts", value: "None", note: "No threatened or broken LOC state is exposed on current formations." }];

  const organizationRows = [
    {
      label: "Command Net",
      value: distinctHq.length ? `${pluralize(distinctHq.length, "HQ record")} visible` : "HQ records not exposed",
      note: distinctHq.length ? compactList(distinctHq, 2) ?? "HQ IDs unavailable." : "Visible formations do not carry authoritative HQ IDs on the current shell path.",
    },
    {
      label: "Reserve / Orders",
      value: `${pluralize(reserveCount, "reserve posture")} • ${pluralize(activeOrders, "active order")}`,
      note: commanderNamed
        ? `${pluralize(commanderNamed, "formation")} with named commander identity exposed.`
        : "Named commander identity is not exposed for current formations.",
    },
    {
      label: "Organization Warning",
      value: unlinkedCount ? `${pluralize(unlinkedCount, "formation")} without exposed HQ link` : "All visible formations carry an HQ linkage",
      note: supportStates.length
        ? `${pluralize(supportStates.length, "formation")} show attached or detached support exposure.`
        : "No support battalion assignment is exposed on the current shell path.",
    },
  ];

  return {
    available: true,
    note: "Land Forces uses only exposed command, attachment, order, and LOC fields. No deeper OOB hierarchy is inferred.",
    metrics: [
      { label: "Visible Formations", value: String(formations.length) },
      { label: "HQ Linked", value: String(hqLinked) },
      { label: "HQ Records", value: distinctHq.length ? String(distinctHq.length) : "Not exposed" },
      { label: "LOC Alerts", value: locAlerts.length ? String(locAlerts.length) : "0" },
    ],
    oob: {
      headline: distinctHq.length
        ? `${pluralize(distinctHq.length, "HQ record")} across ${pluralize(hqLinked, "linked formation")}.`
        : "No higher-headquarters linkage is exposed on the current shell path.",
      rows: oobRows,
    },
    support: {
      headline: supportStates.length
        ? `${pluralize(supportStates.length, "formation")} with support or attachment exposure.`
        : "No support battalion assignments are exposed on the current shell path.",
      rows: supportRows,
    },
    loc: {
      headline: locAlerts.length
        ? `${pluralize(locAlerts.length, "visible LOC alert")}.`
        : "No threatened or broken LOC state is exposed on current formations.",
      rows: locRows,
    },
    organization: {
      headline: `${pluralize(reserveCount, "reserve posture")} • ${pluralize(activeOrders, "active order")}.`,
      rows: organizationRows,
    },
  };
}

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function scenarioKey(snapshot) {
  const id = String(snapshot?.scenario?.id ?? "").trim();
  const name = String(snapshot?.scenario?.name ?? "").trim();
  return id || name || "";
}

function formatSnapshotSourceLabel(snapshot) {
  const parts = ["Previous snapshot"];
  if (snapshot?.time?.turn != null) {
    parts.push(`Turn ${snapshot.time.turn}`);
  }
  if (snapshot?.time?.current_hours != null) {
    parts.push(`T+${snapshot.time.current_hours}h`);
  }
  return parts.join(" • ");
}

function compareNumericField(current, previous, label, options = {}) {
  const currentValue = finiteNumber(current);
  const previousValue = finiteNumber(previous);
  if (currentValue == null || previousValue == null) {
    return null;
  }

  const precision = typeof options.precision === "number" ? options.precision : 0;
  const threshold = typeof options.threshold === "number" ? options.threshold : (precision > 0 ? 0.05 : 0.5);
  const delta = currentValue - previousValue;
  if (Math.abs(delta) < threshold) {
    return null;
  }

  const formatted = precision > 0 ? delta.toFixed(precision) : String(Math.round(delta));
  const sign = delta > 0 ? "+" : "";
  const suffix = typeof options.suffix === "string" ? options.suffix : "";
  return `${label} ${sign}${formatted}${suffix}`;
}

function statusRank(value, ranks) {
  const key = normalizeText(value);
  return Object.prototype.hasOwnProperty.call(ranks, key) ? ranks[key] : null;
}

function locRank(value) {
  return statusRank(value, { broken: 0, threatened: 1, connected: 2 });
}

function supportAvailabilityRank(value) {
  return statusRank(value, { unavailable: 0, "not exposed": 1, limited: 2, available: 3 });
}

function sustainmentRank(value) {
  return statusRank(value, { unavailable: 0, critical: 1, strained: 2, stable: 3 });
}

function battleStatusRank(value) {
  return statusRank(value, { unavailable: 0, holding: 1, "under pressure": 2, "at risk": 3 });
}

function visibilityRank(detail) {
  const normalized = normalizeText(detail);
  if (!normalized) {
    return null;
  }
  if (normalized.includes("good")) {
    return 3;
  }
  if (normalized.includes("reduced") || normalized.includes("limited")) {
    return 2;
  }
  if (normalized.includes("poor")) {
    return 1;
  }
  return null;
}

function extractVisibilityLabel(detail) {
  const text = String(detail ?? "").split("•")[0].trim();
  return text || "Visibility unavailable";
}

function extractForceComparisonState(unit) {
  const inspector = unit?.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
  const operational = inspector?.operational_state && typeof inspector.operational_state === "object" ? inspector.operational_state : {};
  const supply = inspector?.supply && typeof inspector.supply === "object" ? inspector.supply : {};
  const replacementQuality = inspector?.replacement_quality && typeof inspector.replacement_quality === "object" ? inspector.replacement_quality : {};

  return {
    id: String(unit?.id ?? unit?.name ?? ""),
    name: String(unit?.name ?? "Formation"),
    readiness: finiteNumber(operational?.readiness ?? unit?.readiness),
    fatigue: finiteNumber(operational?.fatigue),
    morale: finiteNumber(operational?.morale ?? unit?.morale),
    cohesion: finiteNumber(operational?.cohesion),
    supplyDays: finiteNumber(supply?.supply_days_current) ?? parseSupplyDays(supply?.supply_display ?? unit?.supply),
    locState: typeof operational?.loc?.state === "string" && operational.loc.state.trim() ? operational.loc.state.trim() : null,
    posture: typeof operational?.posture === "string" && operational.posture.trim() ? operational.posture.trim() : null,
    reconstitution: typeof replacementQuality?.reconstitution_state === "string" && replacementQuality.reconstitution_state.trim()
      ? replacementQuality.reconstitution_state.trim()
      : null,
  };
}

function summarizeForceQualityComparison(units, previousUnits) {
  const currentFormations = commandFormations(Array.isArray(units) ? units : []);
  const previousFormations = commandFormations(Array.isArray(previousUnits) ? previousUnits : []);
  const previousById = new Map(previousFormations.map((unit) => {
    const state = extractForceComparisonState(unit);
    return [state.id, state];
  }));
  const currentIds = new Set();
  const rows = {};
  let changedRows = 0;
  let improvedRows = 0;
  let degradedRows = 0;

  currentFormations.forEach((unit) => {
    const current = extractForceComparisonState(unit);
    currentIds.add(current.id);
    const previous = previousById.get(current.id) ?? null;

    if (!previous) {
      changedRows += 1;
      rows[current.id] = {
        name: current.name,
        changed: true,
        tone: "changed",
        summary: "Newly visible in the current snapshot.",
      };
      return;
    }

    const terms = [];
    let score = 0;

    const readinessDelta = compareNumericField(current.readiness, previous.readiness, "Readiness");
    if (readinessDelta) {
      terms.push(readinessDelta);
      score += current.readiness > previous.readiness ? 1 : -1;
    }

    const fatigueDelta = compareNumericField(current.fatigue, previous.fatigue, "Fatigue");
    if (fatigueDelta) {
      terms.push(fatigueDelta);
      score += current.fatigue < previous.fatigue ? 1 : -1;
    }

    const supplyDelta = compareNumericField(current.supplyDays, previous.supplyDays, "Supply", { precision: 1, threshold: 0.1, suffix: "d" });
    if (supplyDelta) {
      terms.push(supplyDelta);
      score += current.supplyDays > previous.supplyDays ? 1 : -1;
    }

    const currentLoc = normalizeText(current.locState);
    const previousLoc = normalizeText(previous.locState);
    if (currentLoc && previousLoc && currentLoc !== previousLoc) {
      terms.push(`LOC ${humanizeToken(previousLoc)} -> ${humanizeToken(currentLoc)}`);
      const currentLocRank = locRank(currentLoc);
      const previousLocRank = locRank(previousLoc);
      if (currentLocRank != null && previousLocRank != null && currentLocRank !== previousLocRank) {
        score += currentLocRank > previousLocRank ? 1 : -1;
      }
    }

    if (terms.length < 3) {
      const moraleDelta = compareNumericField(current.morale, previous.morale, "Morale");
      if (moraleDelta) {
        terms.push(moraleDelta);
        score += current.morale > previous.morale ? 1 : -1;
      }
    }

    if (terms.length < 3) {
      const cohesionDelta = compareNumericField(current.cohesion, previous.cohesion, "Cohesion");
      if (cohesionDelta) {
        terms.push(cohesionDelta);
        score += current.cohesion > previous.cohesion ? 1 : -1;
      }
    }

    if (!terms.length && current.posture && previous.posture && normalizeText(current.posture) !== normalizeText(previous.posture)) {
      terms.push(`Posture ${humanizeToken(previous.posture)} -> ${humanizeToken(current.posture)}`);
    }

    if (!terms.length && current.reconstitution && previous.reconstitution && normalizeText(current.reconstitution) !== normalizeText(previous.reconstitution)) {
      terms.push(`Reconstitution ${humanizeToken(previous.reconstitution)} -> ${humanizeToken(current.reconstitution)}`);
    }

    const changed = terms.length > 0;
    if (changed) {
      changedRows += 1;
    }

    let tone = "flat";
    if (changed) {
      if (score > 0) {
        tone = "up";
        improvedRows += 1;
      } else if (score < 0) {
        tone = "down";
        degradedRows += 1;
      } else {
        tone = "changed";
      }
    }

    rows[current.id] = {
      name: current.name,
      changed,
      tone,
      summary: changed ? terms.slice(0, 3).join(" • ") : "No material change from previous snapshot.",
    };
  });

  const removedRows = previousFormations.filter((unit) => !currentIds.has(String(unit?.id ?? unit?.name ?? ""))).length;

  return {
    available: true,
    changedRows,
    improvedRows,
    degradedRows,
    removedRows,
    rows,
    note: "Compares each visible formation only against the immediately previous snapshot captured in this session.",
  };
}

function summarizeSupportPictureComparison(currentSupportPicture, previousSupportPicture) {
  const currentRows = Array.isArray(currentSupportPicture?.rows) ? currentSupportPicture.rows : [];
  const previousRows = new Map((Array.isArray(previousSupportPicture?.rows) ? previousSupportPicture.rows : []).map((row) => [row.id, row]));
  const rows = {};
  let changedRows = 0;

  currentRows.forEach((row) => {
    const previous = previousRows.get(row.id) ?? null;
    if (!previous) {
      changedRows += 1;
      rows[row.id] = { changed: true, tone: "changed", summary: "Newly exposed in the current snapshot." };
      return;
    }

    if (row.status === previous.status && row.detail === previous.detail && row.note === previous.note) {
      rows[row.id] = { changed: false, tone: "flat", summary: "No material change from previous snapshot." };
      return;
    }

    let tone = "changed";
    let summary = `${row.label} changed from ${previous.status} to ${row.status}.`;

    if (row.id === "sustainment") {
      const currentRank = sustainmentRank(row.status);
      const previousRank = sustainmentRank(previous.status);
      if (currentRank != null && previousRank != null && currentRank !== previousRank) {
        tone = currentRank > previousRank ? "up" : "down";
        summary = `Sustainment ${currentRank > previousRank ? "improved" : "worsened"} from ${previous.status} to ${row.status}.`;
      } else if (row.status === previous.status) {
        summary = "Sustainment detail changed.";
      }
    } else if (row.id === "air" || row.id === "naval") {
      const currentRank = supportAvailabilityRank(row.status);
      const previousRank = supportAvailabilityRank(previous.status);
      if (currentRank != null && previousRank != null && currentRank !== previousRank) {
        tone = currentRank > previousRank ? "up" : "down";
        summary = `${row.label} ${currentRank > previousRank ? "improved" : "worsened"} from ${previous.status} to ${row.status}.`;
      } else if (row.status === previous.status) {
        summary = `${row.label} context changed.`;
      }
    } else if (row.id === "weather") {
      const currentVisibility = visibilityRank(row.detail);
      const previousVisibility = visibilityRank(previous.detail);
      if (currentVisibility != null && previousVisibility != null && currentVisibility !== previousVisibility) {
        tone = currentVisibility > previousVisibility ? "up" : "down";
        summary = `Visibility ${currentVisibility > previousVisibility ? "improved" : "worsened"} from ${extractVisibilityLabel(previous.detail)} to ${extractVisibilityLabel(row.detail)}.`;
      } else {
        summary = row.status === previous.status
          ? "Weather cue changed."
          : `Weather picture changed from ${previous.status} to ${row.status}.`;
      }
    } else if (row.id === "engineers") {
      summary = `Defense works changed from ${previous.status} to ${row.status}.`;
    }

    changedRows += 1;
    rows[row.id] = { changed: true, tone, summary };
  });

  return {
    available: true,
    changedRows,
    rows,
    note: "Support deltas compare only the current support picture against the immediately previous snapshot captured in this session.",
  };
}

function summarizeLocalBattleComparison(currentLocalBattle, previousLocalBattle) {
  if (!currentLocalBattle?.available && !previousLocalBattle?.available) {
    return { available: false, tone: "unavailable", summary: "No local-battle picture is exposed in either snapshot." };
  }
  if (currentLocalBattle?.available && !previousLocalBattle?.available) {
    return { available: true, tone: "changed", summary: "Local battle picture is newly exposed in the current snapshot." };
  }
  if (!currentLocalBattle?.available && previousLocalBattle?.available) {
    return { available: true, tone: "changed", summary: "Local battle picture is no longer exposed in the current snapshot." };
  }

  const currentStatus = findStatusValue(currentLocalBattle?.perimeterStatus, "Overall Status", "Unavailable");
  const previousStatus = findStatusValue(previousLocalBattle?.perimeterStatus, "Overall Status", "Unavailable");
  const currentRank = battleStatusRank(currentStatus);
  const previousRank = battleStatusRank(previousStatus);
  if (currentRank != null && previousRank != null && currentRank !== previousRank) {
    return {
      available: true,
      tone: currentRank > previousRank ? "down" : "up",
      summary: `Perimeter ${currentRank > previousRank ? "worsened" : "improved"} from ${previousStatus} to ${currentStatus}.`,
    };
  }

  const currentLeadAxis = currentLocalBattle?.pressureAxes?.[0] ?? null;
  const previousLeadAxis = previousLocalBattle?.pressureAxes?.[0] ?? null;
  if ((currentLeadAxis?.label ?? "") !== (previousLeadAxis?.label ?? "") || (currentLeadAxis?.status ?? "") !== (previousLeadAxis?.status ?? "")) {
    return {
      available: true,
      tone: "changed",
      summary: currentLeadAxis
        ? `Active pressure now centered on ${currentLeadAxis.label} (${currentLeadAxis.status}).`
        : "No active local pressure axis is exposed in the current snapshot.",
    };
  }

  const currentContact = currentLocalBattle?.recentContacts?.[0]?.title ?? "";
  const previousContact = previousLocalBattle?.recentContacts?.[0]?.title ?? "";
  if (currentContact !== previousContact && currentContact) {
    return {
      available: true,
      tone: "changed",
      summary: `New local contact: ${currentContact}.`,
    };
  }

  return {
    available: true,
    tone: "flat",
    summary: "No material change in the exposed local-battle picture.",
  };
}

function summarizeCommunicationsComparison(currentCommunicationsIntel, previousCommunicationsIntel) {
  const currentLatestId = String(currentCommunicationsIntel?.latestDispatch?.id ?? "");
  const previousLatestId = String(previousCommunicationsIntel?.latestDispatch?.id ?? "");
  if (currentLatestId && previousLatestId && currentLatestId !== previousLatestId) {
    return {
      available: true,
      tone: "changed",
      summary: `New latest dispatch: ${currentCommunicationsIntel.latestDispatch.title}.`,
    };
  }

  if (String(currentCommunicationsIntel?.keyConcern ?? "") !== String(previousCommunicationsIntel?.keyConcern ?? "")) {
    return {
      available: true,
      tone: "changed",
      summary: `Key intelligence concern shifted to ${currentCommunicationsIntel.keyConcern}.`,
    };
  }

  if (String(currentCommunicationsIntel?.localContact ?? "") !== String(previousCommunicationsIntel?.localContact ?? "")) {
    return {
      available: true,
      tone: "changed",
      summary: `Reporting focus changed to ${currentCommunicationsIntel.localContact}.`,
    };
  }

  return {
    available: true,
    tone: "flat",
    summary: "No material change in the exposed reporting picture.",
  };
}

function summarizeReinforcementsComparison(currentReinforcements, previousReinforcements) {
  const currentHeadline = String(currentReinforcements?.nextChange?.headline ?? "");
  const previousHeadline = String(previousReinforcements?.nextChange?.headline ?? "");
  const currentDetail = String(currentReinforcements?.nextChange?.detail ?? "");
  const previousDetail = String(previousReinforcements?.nextChange?.detail ?? "");

  if (currentHeadline !== previousHeadline || currentDetail !== previousDetail) {
    return {
      available: true,
      tone: "changed",
      summary: `Next force change now ${currentHeadline || "unavailable"}.`,
    };
  }

  return {
    available: true,
    tone: "flat",
    summary: "No material change in the exposed force-change schedule.",
  };
}

function buildComparisonHighlights(comparison) {
  const highlights = [];
  const seen = new Set();
  const push = (message) => {
    const clean = String(message ?? "").trim();
    if (!clean) {
      return;
    }
    const key = normalizeText(clean);
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    highlights.push(clean);
  };

  if (comparison.localBattle?.tone && comparison.localBattle.tone !== "flat" && comparison.localBattle.tone !== "unavailable") {
    push(comparison.localBattle.summary);
  }

  const degradedFormation = Object.values(comparison.forceQuality?.rows ?? {}).find((row) => row?.tone === "down");
  if (degradedFormation) {
    push(`${degradedFormation.name}: ${degradedFormation.summary}.`);
  }

  const improvedFormation = Object.values(comparison.forceQuality?.rows ?? {}).find((row) => row?.tone === "up");
  if (improvedFormation) {
    push(`${improvedFormation.name}: ${improvedFormation.summary}.`);
  }

  const sustainmentDelta = comparison.supportPicture?.rows?.sustainment ?? null;
  if (sustainmentDelta?.tone && sustainmentDelta.tone !== "flat") {
    push(sustainmentDelta.summary);
  }

  if (comparison.communicationsIntel?.tone && comparison.communicationsIntel.tone !== "flat") {
    push(comparison.communicationsIntel.summary);
  }

  if (comparison.reinforcementsWithdrawals?.tone && comparison.reinforcementsWithdrawals.tone !== "flat") {
    push(comparison.reinforcementsWithdrawals.summary);
  }

  if (!highlights.length) {
    push("No material change from the previous snapshot across exposed dashboard fields.");
  }

  return highlights.slice(0, 4);
}

function summarizeDashboardComparison(snapshot, previousSnapshot, currentSummary) {
  if (!previousSnapshot) {
    return {
      available: false,
      sourceLabel: "Previous snapshot unavailable",
      note: "Comparison unavailable until the next authoritative update is captured in this session.",
      highlights: [],
      localBattle: { available: false, tone: "unavailable", summary: "No previous snapshot captured in this session." },
      supportPicture: { available: false, changedRows: 0, rows: {}, note: "No previous support picture captured in this session." },
      communicationsIntel: { available: false, tone: "unavailable", summary: "No previous reporting picture captured in this session." },
      reinforcementsWithdrawals: { available: false, tone: "unavailable", summary: "No previous force-change picture captured in this session." },
      forceQuality: { available: false, changedRows: 0, improvedRows: 0, degradedRows: 0, removedRows: 0, rows: {}, note: "No previous formation picture captured in this session." },
    };
  }

  const currentScenario = scenarioKey(snapshot);
  const previousScenario = scenarioKey(previousSnapshot);
  if (currentScenario && previousScenario && currentScenario !== previousScenario) {
    return {
      available: false,
      sourceLabel: "Previous snapshot unavailable",
      note: "Comparison unavailable because the current snapshot is from a different scenario than the last captured update.",
      highlights: [],
      localBattle: { available: false, tone: "unavailable", summary: "No same-scenario previous snapshot is available for local-battle comparison." },
      supportPicture: { available: false, changedRows: 0, rows: {}, note: "No same-scenario previous support picture is available." },
      communicationsIntel: { available: false, tone: "unavailable", summary: "No same-scenario previous reporting picture is available." },
      reinforcementsWithdrawals: { available: false, tone: "unavailable", summary: "No same-scenario previous force-change picture is available." },
      forceQuality: { available: false, changedRows: 0, improvedRows: 0, degradedRows: 0, removedRows: 0, rows: {}, note: "No same-scenario previous formation picture is available." },
    };
  }

  const previousCommunications = summarizeCommunications(previousSnapshot);
  const previousIntelligence = summarizeIntelligenceBranch(previousSnapshot);
  const previousLocalBattle = summarizeHendersonPressureBoard(previousSnapshot);
  const previousCommunicationsIntel = summarizeCommunicationsIntel(previousCommunications, previousIntelligence, previousLocalBattle);
  const previousSupportPicture = summarizeSupportPicture(previousSnapshot, previousLocalBattle);
  const previousReinforcements = summarizeReinforcementsModule(previousSnapshot);

  const comparison = {
    available: true,
    sourceLabel: formatSnapshotSourceLabel(previousSnapshot),
    note: "Compares the current dashboard only against the immediately previous authoritative snapshot captured in this session.",
    localBattle: summarizeLocalBattleComparison(currentSummary.localBattle, previousLocalBattle),
    supportPicture: summarizeSupportPictureComparison(currentSummary.supportPicture, previousSupportPicture),
    communicationsIntel: summarizeCommunicationsComparison(currentSummary.communicationsIntel, previousCommunicationsIntel),
    reinforcementsWithdrawals: summarizeReinforcementsComparison(currentSummary.reinforcementsWithdrawals, previousReinforcements),
    forceQuality: summarizeForceQualityComparison(snapshot?.units, previousSnapshot?.units),
  };
  comparison.highlights = buildComparisonHighlights(comparison);
  return comparison;
}

function resourceValue(resources, label, fallback = "Not exposed") {
  const row = (Array.isArray(resources) ? resources : []).find((item) => String(item?.label ?? "").trim().toLowerCase() === label.toLowerCase());
  return typeof row?.value === "string" && row.value.trim() ? row.value.trim() : fallback;
}

function firstConstraint(candidates, fallback) {
  for (const candidate of candidates) {
    const text = String(candidate ?? "").trim();
    if (text) {
      return text;
    }
  }
  return fallback;
}

function summarizeSupportPicture(snapshot, localBattle) {
  const weatherImpact = buildWeatherImpactState(snapshot);
  const sustainment = localBattle?.localSustainment ?? {
    status: "Unavailable",
    note: "Local sustainment is unavailable on the current shell path.",
    resources: [],
    concerns: [],
  };
  const airSupport = localBattle?.airSupport ?? {
    availability: "Unavailable",
    sortiePosture: "Sortie posture unavailable",
    supportingFormation: "No supporting air formation exposed.",
    constraint: "Local air-support context is unavailable on the current shell path.",
  };
  const navalSupport = localBattle?.navalSupport ?? {
    availability: "Unavailable",
    supportPosture: "Support posture unavailable",
    supportingFormation: "No supporting naval formation exposed.",
    constraint: "Local naval-support context is unavailable on the current shell path.",
  };
  const defensePreparation = localBattle?.defensePreparation ?? {
    fortificationState: "Unavailable",
    obstacles: "Not exposed",
    engineer: "Not exposed",
    mostPrepared: "No prepared local objective exposed.",
    leastPrepared: "No lightly prepared local objective exposed.",
    note: "Local defense-preparation state is unavailable on the current shell path.",
    available: false,
  };

  const immediateConstraint = firstConstraint(
    [
      sustainment.status === "Critical" || sustainment.status === "Strained" ? sustainment.concerns?.[0] : null,
      airSupport.availability !== "Available" ? airSupport.constraint : null,
      navalSupport.availability !== "Available" ? navalSupport.constraint : null,
      weatherImpact.available ? weatherImpact.note : null,
      defensePreparation.available ? `${defensePreparation.leastPrepared} is the least prepared local area on the current shell path.` : null,
      localBattle?.note,
    ],
    "No immediate support constraint is exposed beyond current local support summaries.",
  );

  return {
    available: !!(localBattle?.available || weatherImpact?.available),
    note: "Consolidates current weather-impact, sustainment, air, naval, and defense-preparation summaries already exposed elsewhere on the shell path.",
    immediateConstraint,
    rows: [
      {
        id: "weather",
        label: "Weather / Visibility",
        status: weatherImpact.available ? `${weatherImpact.current} • ${weatherImpact.timeState}` : "Unavailable",
        detail: `${weatherImpact.visibility} visibility • ${weatherImpact.groundMovement} ground • Night Ops ${weatherImpact.nightOperations}`,
        note: weatherImpact.note,
      },
      {
        id: "air",
        label: "Air Support",
        status: airSupport.availability,
        detail: `${airSupport.sortiePosture} • ${airSupport.supportingFormation}`,
        note: airSupport.constraint,
      },
      {
        id: "naval",
        label: "Naval Support",
        status: navalSupport.availability,
        detail: `${navalSupport.supportPosture} • ${navalSupport.supportingFormation}`,
        note: navalSupport.constraint,
      },
      {
        id: "sustainment",
        label: "Sustainment",
        status: sustainment.status,
        detail: `${resourceValue(sustainment.resources, "Supply")} • ${resourceValue(sustainment.resources, "Support", "Support posture not exposed")}`,
        note: firstConstraint([sustainment.concerns?.[0], sustainment.note], "No local sustainment concern is exposed."),
      },
      {
        id: "engineers",
        label: "Engineer / Fortification",
        status: defensePreparation.fortificationState,
        detail: `Obstacles ${defensePreparation.obstacles} • Engineers ${defensePreparation.engineer}`,
        note: defensePreparation.available
          ? `Most prepared ${defensePreparation.mostPrepared} • Least prepared ${defensePreparation.leastPrepared}`
          : defensePreparation.note,
      },
    ],
  };
}

function summarizeCommunicationsIntel(communications, intelligenceBranch, localBattle) {
  const latest = communications?.latest ?? null;
  const localContactReport = localBattle?.recentContacts?.[0] ?? null;
  const localContactMessage = localContactReport
    ? (communications?.history ?? []).find((message) => message.id === localContactReport.id) ?? null
    : null;
  const recentItems = [];
  const seen = new Set();
  const pushRecent = (item) => {
    const id = String(item?.id ?? "");
    if (!id || seen.has(id)) {
      return;
    }
    seen.add(id);
    recentItems.push({
      id,
      title: String(item?.title || "Dispatch"),
      summary: String(item?.summary || "Operational update."),
      timeLabel: String(item?.timeLabel || "Time unavailable"),
      senderLabel: typeof item?.senderLabel === "string" && item.senderLabel.trim() ? item.senderLabel.trim() : null,
    });
  };

  if (localContactMessage) {
    pushRecent(localContactMessage);
  }
  (communications?.history ?? []).slice(0, 3).forEach(pushRecent);

  const dispatchCount = Array.isArray(communications?.history) ? communications.history.length : 0;
  const pending = communications?.pending;
  const reportingPicture = dispatchCount
    ? `${dispatchCount} recent dispatch${dispatchCount === 1 ? "" : "es"} exposed${pending != null ? ` • ${pending} pending` : ""}.`
    : "Reporting picture limited; no current dispatch history is exposed on the shell path.";

  return {
    available: !!(latest || recentItems.length || (intelligenceBranch?.concerns ?? []).length),
    latestDispatch: {
      id: latest?.id ?? null,
      title: latest?.title ?? intelligenceBranch?.overview?.latestTitle ?? "No current dispatch",
      summary: latest?.summary ?? intelligenceBranch?.overview?.latestSummary ?? "No communications are available in the current snapshot.",
      timeLabel: latest?.timeLabel ?? "Time unavailable",
      senderLabel: latest?.senderLabel ?? null,
    },
    recentItems: recentItems.slice(0, 3),
    localContact: localContactMessage?.title ?? localContactReport?.title ?? "No recent local contact report.",
    reportingPicture,
    reconLimitation: intelligenceBranch?.recon?.detail ?? "No dedicated recon limitation is exposed on the current shell path.",
    reportingLimitation: intelligenceBranch?.confidence?.detail ?? "Confidence and reporting limitations are not exposed on the current shell path.",
    keyConcern: intelligenceBranch?.concerns?.[0] ?? "No explicit intelligence concerns are exposed beyond the current communications feed.",
    note: intelligenceBranch?.overview?.statusLine ?? "No current intelligence dispatches are exposed on the active shell path.",
  };
}

function summarizeReinforcementsModule(snapshot) {
  const board = summarizeReinforcementsBoard(snapshot);
  const currentDay = board.currentDay;
  const incoming = board.arrivals.slice(0, 2);
  const outgoing = board.withdrawals.slice(0, 2);
  const replacementEvent = board.replacementEvents[0] ?? null;
  const combined = [
    ...board.arrivals.map((row) => ({ ...row, changeType: "Arrival" })),
    ...board.withdrawals.map((row) => ({ ...row, changeType: "Withdrawal" })),
    ...board.replacementEvents.map((row) => ({ ...row, changeType: "Replacement Impact" })),
  ].sort((left, right) => {
    const leftDay = typeof left?.day === "number" && Number.isFinite(left.day) ? left.day : Number.POSITIVE_INFINITY;
    const rightDay = typeof right?.day === "number" && Number.isFinite(right.day) ? right.day : Number.POSITIVE_INFINITY;
    if (leftDay !== rightDay) {
      return leftDay - rightDay;
    }
    return String(left?.name ?? "").localeCompare(String(right?.name ?? ""));
  });

  const nextChange = currentDay == null
    ? combined[0] ?? null
    : combined.find((row) => typeof row?.day === "number" && row.day >= currentDay)
      ?? combined.find((row) => row?.day == null)
      ?? combined[0]
      ?? null;

  return {
    available: combined.length > 0,
    currentDay,
    note: board.overview.staffNote,
    nextChange: nextChange
      ? {
          headline: `${nextChange.changeType} • ${nextChange.name}`,
          detail: nextChange.timing,
          context: "destination" in nextChange
            ? `${nextChange.destination} • ${nextChange.command}`
            : "Destination and command context not exposed.",
        }
      : {
          headline: "No scheduled force change exposed",
          detail: currentDay != null ? `Current day ${currentDay}` : "Current day unavailable",
          context: "No authoritative reinforcement, withdrawal, or replacement-impact row is exposed on the current shell path.",
        },
    incoming,
    outgoing,
    planningWarning: replacementEvent
      ? `${replacementEvent.name} • ${replacementEvent.timing}`
      : board.placeholders.replacements,
    placeholders: {
      incoming: incoming.length ? null : "No authoritative reinforcement rows are exposed on the current shell path for this scenario.",
      outgoing: outgoing.length ? null : board.placeholders.withdrawals,
    },
  };
}

function findStatusValue(rows, label, fallback = null) {
  const row = (Array.isArray(rows) ? rows : []).find((item) => String(item?.label ?? "").trim().toLowerCase() === label.toLowerCase());
  return typeof row?.value === "string" && row.value.trim() ? row.value.trim() : fallback;
}

function leadingDetail(detail) {
  return String(detail ?? "").split("•")[0].trim();
}

function summarizeTurnBriefModule(campaign, localBattle, supportPicture, communicationsIntel, reinforcementsWithdrawals, forceQuality, staff) {
  const overallStatus = findStatusValue(localBattle?.perimeterStatus, "Overall Status");
  const immediateConcern = findStatusValue(localBattle?.perimeterStatus, "Immediate Concern");
  const staffConcern = findStatusValue(localBattle?.perimeterStatus, "Staff Concern");
  const sustainmentRow = (supportPicture?.rows ?? []).find((row) => row.id === "sustainment") ?? null;
  const weatherRow = (supportPicture?.rows ?? []).find((row) => row.id === "weather") ?? null;
  const defaultIntelConcern = "No explicit intelligence concerns are exposed beyond the current communications feed.";
  const defaultForceChangeHeadline = "No scheduled force change exposed";
  const issues = [];
  const seen = new Set();
  const addIssue = (priority, message, focus = null) => {
    const clean = String(message ?? "").trim();
    if (!clean) {
      return;
    }
    const key = normalizeText(clean);
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    issues.push({ priority, message: clean, focus: String(focus ?? clean).trim() || clean });
  };

  if (localBattle?.available && overallStatus && overallStatus !== "Holding" && immediateConcern) {
    addIssue(overallStatus === "At Risk" ? 100 : 95, `${immediateConcern}.`, immediateConcern);
  }

  if (sustainmentRow && (sustainmentRow.status === "Critical" || sustainmentRow.status === "Strained")) {
    addIssue(sustainmentRow.status === "Critical" ? 92 : 84, `Sustainment ${sustainmentRow.status.toLowerCase()} across local formations.`, sustainmentRow.status === "Critical" ? "Sustainment Critical" : "Sustainment Strained");
  }

  const responseSummary = String(localBattle?.responseReadiness?.summary ?? "").trim();
  if (responseSummary.startsWith("0 ready") || responseSummary.startsWith("No credible immediate")) {
    addIssue(82, "Reserve response limited on the current shell path.", "Reserve Response Limited");
  }

  if (weatherRow && weatherRow.status !== "Unavailable") {
    const visibilityClause = leadingDetail(weatherRow.detail);
    const statusLower = weatherRow.status.toLowerCase();
    const visibilityLower = visibilityClause.toLowerCase();
    if (statusLower.includes("night") || statusLower.includes("dawn") || statusLower.includes("dusk")) {
      addIssue(76, `${weatherRow.status} conditions are in effect.`, weatherRow.status);
    } else if (visibilityClause && !visibilityLower.startsWith("not exposed")) {
      addIssue(72, `${visibilityClause} is the current exposed weather limitation.`, visibilityClause);
    }
  }

  if (communicationsIntel?.keyConcern && communicationsIntel.keyConcern !== defaultIntelConcern) {
    addIssue(78, communicationsIntel.keyConcern, communicationsIntel.keyConcern);
  }

  if (reinforcementsWithdrawals?.nextChange?.headline && reinforcementsWithdrawals.nextChange.headline !== defaultForceChangeHeadline) {
    const detail = String(reinforcementsWithdrawals.nextChange.detail ?? "").trim();
    const message = `${reinforcementsWithdrawals.nextChange.headline} ${detail}.`.replace(/\s+/g, " ").trim();
    addIssue(/due this day|due in 1 day/i.test(detail) ? 74 : 64, message, reinforcementsWithdrawals.nextChange.headline);
  }

  const formationWatch = (forceQuality?.rows ?? []).find((row) => {
    const note = String(row?.note ?? "").trim();
    if (!note || note === "No immediate warning from exposed fields.") {
      return false;
    }
    const lowered = note.toLowerCase();
    return lowered.includes("loc broken") || lowered.includes("loc threatened") || lowered.includes("supply strained");
  });
  if (formationWatch) {
    addIssue(68, `${formationWatch.name} ${formationWatch.note}.`, formationWatch.name);
  }

  if (!issues.length && staff?.summary) {
    addIssue(10, staff.summary, "Staff Summary");
  }
  if (!issues.length) {
    addIssue(1, "No dominant operational alarm is exposed beyond current staff and reporting summaries.", "Current Staff Picture");
  }

  issues.sort((left, right) => right.priority - left.priority || left.message.localeCompare(right.message));

  const lines = [];
  const pushLine = (line) => {
    const clean = String(line ?? "").trim();
    if (!clean) {
      return;
    }
    const key = normalizeText(clean);
    if (!key || lines.some((existing) => normalizeText(existing) === key)) {
      return;
    }
    lines.push(clean);
  };

  pushLine(issues[0]?.message);
  pushLine(issues[1]?.message);
  if (reinforcementsWithdrawals?.nextChange?.headline && reinforcementsWithdrawals.nextChange.headline !== defaultForceChangeHeadline) {
    pushLine(`Next force change: ${reinforcementsWithdrawals.nextChange.headline} ${reinforcementsWithdrawals.nextChange.detail}.`);
  }
  if (communicationsIntel?.latestDispatch?.title && communicationsIntel.latestDispatch.title !== "No current dispatch") {
    pushLine(`Latest dispatch: ${communicationsIntel.latestDispatch.title}.`);
  }

  return {
    available: true,
    priorityFocus: issues[0]?.focus ?? "Current Staff Picture",
    note: `Turn ${campaign?.turn ?? "current"} brief built only from exposed pressure, support, reporting, force-change, and readiness concerns already on the shell path.`,
    lines: lines.slice(0, 4),
    actionItems: issues.slice(0, 5).map((issue) => issue.message),
  };
}

export function summarizeTheaterDashboard(snapshot, previousSnapshot = null, operations = []) {
  const campaign = summarizeCampaign(snapshot);
  const objectives = summarizeObjectives(snapshot?.objectives);
  const score = summarizeScore(snapshot?.campaign?.score_by_side);
  const communications = summarizeCommunications(snapshot, operations);
  const intelligenceBranch = summarizeIntelligenceBranch(snapshot, operations);
  const localBattle = summarizeHendersonPressureBoard(snapshot, operations);
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const alliedUnits = units.filter((unit) => String(unit?.side ?? "").toUpperCase() === "ALLIED");
  const axisUnits = units.filter((unit) => String(unit?.side ?? "").toUpperCase() === "AXIS");
  const supplyAverage = average(units.map((unit) => parseSupplyDays(unit?.supply)));
  const communicationsIntel = summarizeCommunicationsIntel(communications, intelligenceBranch, localBattle);
  const reinforcementsWithdrawals = summarizeReinforcementsModule(snapshot);
  const forceQuality = summarizeForceQualityMatrix(units);
  const supportPicture = summarizeSupportPicture(snapshot, localBattle);
  const campaignPicture = summarizeCampaignPicture(campaign, objectives, score, pressureFallback(snapshot?.pressure ?? { summary: null, reasons: [] }));
  const landForces = summarizeLandForcesModule(units);
  const operationsSummary = summarizeTrackedOperations(snapshot, operations);
  const staff = {
    summary: snapshot?.staff?.summary ?? "Staff summary unavailable",
    load: snapshot?.staff?.load ?? null,
    ai: snapshot?.ai?.enabled ? "Enabled" : "Disabled",
    intent: humanizeIntent(snapshot?.ai?.last_intent),
  };
  const comparison = summarizeDashboardComparison(snapshot, previousSnapshot, {
    localBattle,
    supportPicture,
    communicationsIntel,
    reinforcementsWithdrawals,
  });

  return {
    campaign,
    score,
    objectives,
    campaignPicture,
    context: {
      unitsTracked: units.length,
      objectivesTracked: objectives.total,
      pressureSummary: pressureFallback(snapshot?.pressure ?? { summary: null, reasons: [] }),
    },
    land: {
      totalUnits: units.length,
      alliedUnits: alliedUnits.length,
      axisUnits: axisUnits.length,
      averageReadiness: average(units.map((unit) => unit?.readiness)),
      averageMorale: average(units.map((unit) => unit?.morale)),
    },
    landForces,
    operations: operationsSummary,
    logistics: {
      supplyAverage,
      supportText: supplyAverage != null ? `${supplyAverage.toFixed(1)} days estimated across visible formations.` : "Unit supply-day detail is limited on the current shell path.",
      load: snapshot?.staff?.load ?? null,
    },
    intelligence: {
      latestTitle: intelligenceBranch.overview.latestTitle,
      latestSummary: intelligenceBranch.overview.latestSummary,
      pending: intelligenceBranch.overview.pending,
      reasons: Array.isArray(snapshot?.pressure?.reasons) ? snapshot.pressure.reasons : [],
    },
    turnBrief: summarizeTurnBriefModule(campaign, localBattle, supportPicture, communicationsIntel, reinforcementsWithdrawals, forceQuality, staff),
    communicationsIntel,
    reinforcementsWithdrawals,
    forceQuality,
    localBattle,
    supportPicture,
    comparison,
    staff,
    timeline: (Array.isArray(snapshot?.reports?.recent) ? [...snapshot.reports.recent].reverse() : []).slice(0, 5).map((report) => ({
      id: String(report?.id ?? ""),
      title: String(report?.title || report?.kind || "Report"),
      summary: String(report?.summary || "Operational update."),
      timeLabel: formatCommunicationTime(report?.time ?? null),
      severity: String(report?.severity || "info"),
    })),
  };
}
