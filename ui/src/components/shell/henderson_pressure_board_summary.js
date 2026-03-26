import { buildObjectiveDisplayName, humanizePressureReason, humanizeToken } from "../../lib/view_snapshot.js";
import { orderRecentReports, summarizeObjectives } from "./dashboard_summary.js";
import { humanizeObjectiveState } from "./map_scene.js";
import { summarizeLocalAirSupport } from "./air_operations_summary.js";
import { summarizeLocalSustainment } from "./logistics_branch_summary.js";
import { summarizeLocalNavalSupport } from "./naval_operations_summary.js";
import { summarizeTrackedOperations } from "./operations_planner.js";

function normalizeText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function objectiveDisplayIndex(snapshot) {
  const objectives = Array.isArray(snapshot?.objectives) ? snapshot.objectives : [];
  const duplicateNames = new Set(
    objectives
      .map((objective) => String(objective?.name ?? "").trim())
      .filter(Boolean)
      .filter((name, index, items) => items.indexOf(name) !== index),
  );

  return new Map(
    objectives.map((objective) => [
      String(objective?.id || ""),
      {
        id: String(objective?.id || ""),
        name: buildObjectiveDisplayName(objective, duplicateNames),
        side: String(objective?.side || ""),
        state: humanizeObjectiveState(objective?.state),
        rawState: String(objective?.state ?? ""),
        value: typeof objective?.value === "number" ? objective.value : 0,
      },
    ]),
  );
}

function localPressureAreas(snapshot) {
  return Array.isArray(snapshot?.local_pressure_areas)
    ? snapshot.local_pressure_areas.map((area) => ({
        id: String(area?.id || ""),
        label: String(area?.label || area?.id || "Local Area"),
        kind: String(area?.kind || "location"),
        locationId: typeof area?.location_id === "string" ? area.location_id : null,
        objectiveId: typeof area?.objective_id === "string" ? area.objective_id : null,
        pressureReasons: Array.isArray(area?.pressure_reasons) ? area.pressure_reasons.map((reason) => String(reason)) : [],
        defensivePreparation: area?.defensive_preparation && typeof area.defensive_preparation === "object"
          ? {
              state: typeof area.defensive_preparation.state === "string" ? area.defensive_preparation.state : null,
              fortificationState: typeof area.defensive_preparation.fortification_state === "string" ? area.defensive_preparation.fortification_state : null,
              obstacleState: typeof area.defensive_preparation.obstacle_state === "string" ? area.defensive_preparation.obstacle_state : null,
              engineerState: typeof area.defensive_preparation.engineer_state === "string" ? area.defensive_preparation.engineer_state : null,
            }
          : null,
      }))
    : [];
}

function collectLocalReports(snapshot, areaIds) {
  return orderRecentReports(snapshot?.reports?.recent)
    .filter((report) => typeof report?.local_area_id === "string" && areaIds.has(report.local_area_id))
    .slice(0, 3)
    .map((report) => ({
      id: String(report?.id || ""),
      title: String(report?.title || "Report"),
      summary: String(report?.summary || "Operational update."),
      severity: String(report?.severity || "info").toUpperCase(),
      localAreaId: typeof report?.local_area_id === "string" ? report.local_area_id : null,
    }));
}

function areaReasonMatches(area, pressureReasons) {
  return pressureReasons.filter((reason) => area.pressureReasons.includes(reason));
}

function buildPressureAxes(areas, objectivesById, localReports, pressureReasons) {
  const axes = [];

  for (const area of areas) {
    const objective = area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null;
    const matchedReport = localReports.find((report) => report.localAreaId === area.id) ?? null;
    const matchedReasons = areaReasonMatches(area, pressureReasons);
    const objectiveRisk = objective?.side === "ALLIED" && objective?.rawState === "unheld";

    if (!objectiveRisk && !matchedReport && !matchedReasons.length) {
      continue;
    }

    axes.push({
      id: area.id,
      label: area.label,
      kindLabel: humanizeToken(area.kind),
      status: objectiveRisk ? "At Risk" : "Under Pressure",
      detail: matchedReport?.summary
        ?? (matchedReasons.length ? matchedReasons.map((reason) => humanizePressureReason(reason)).join(" • ") : objective?.state ?? "No current local pressure note."),
    });
  }

  return axes.slice(0, 4);
}

function buildOverallStatus(areas, objectivesById, localReports, pressureReasons) {
  const atRiskObjective = areas.find((area) => {
    const objective = area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null;
    return objective?.side === "ALLIED" && objective.rawState === "unheld";
  });

  if (atRiskObjective) {
    return "At Risk";
  }
  if (localReports.length || pressureReasons.length) {
    return "Under Pressure";
  }
  return "Holding";
}

function buildImmediateConcern(areas, objectivesById, localReports, axes) {
  const atRiskArea = areas
    .map((area) => ({
      area,
      objective: area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null,
    }))
    .filter((row) => row.objective?.side === "ALLIED" && row.objective.rawState === "unheld")
    .sort((left, right) => (right.objective?.value ?? 0) - (left.objective?.value ?? 0))[0];

  if (atRiskArea) {
    return `${atRiskArea.area.label} At Risk`;
  }

  for (const report of localReports) {
    const axis = axes.find((item) => item.id === report.localAreaId);
    if (axis) {
      return `${axis.label} ${axis.status}`;
    }
  }

  if (axes[0]) {
    return `${axes[0].label} ${axes[0].status}`;
  }

  const highestValueObjective = areas
    .map((area) => ({
      area,
      objective: area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null,
    }))
    .filter((row) => row.objective)
    .sort((left, right) => (right.objective?.value ?? 0) - (left.objective?.value ?? 0))[0];

  return highestValueObjective ? `${highestValueObjective.area.label} ${highestValueObjective.objective.state}` : "No immediate perimeter concern exposed";
}

function buildReserveStatus(localReports) {
  const report = localReports.find((item) => normalizeText(item.summary).includes("reserve"));
  if (!report) {
    return "Not exposed on the current shell path.";
  }
  return report.summary;
}

function buildOperationsOverview(snapshot, operations, options = {}) {
  const trackedOperations = summarizeTrackedOperations(snapshot, operations);
  const objectives = summarizeObjectives(snapshot?.objectives);
  const keyObjective = objectives.key[0] ?? null;
  const objectiveSituation = trackedOperations.lead?.objective
    ? `${trackedOperations.lead.objective} • ${trackedOperations.lead.objectiveState}`
    : keyObjective
      ? `${keyObjective.name} • ${keyObjective.state}`
      : objectives.byState[0]
        ? `${objectives.byState[0].state} ${objectives.byState[0].count}`
        : "No objective situation exposed on the current shell path.";
  const localBattle = options.available
    ? `${options.overallStatus ?? "Local battle status unavailable"} • ${options.hotspotsSummary ?? "No named local engagement focus is exposed."}`
    : "Local battle unavailable outside the current perimeter slice.";
  const immediateConcern = options.immediateConcern ?? "No immediate local battle concern is exposed on the current shell path.";

  return {
    title: trackedOperations.lead?.name ?? (options.available ? "Henderson Operations" : "Operations Picture"),
    activeOperation: trackedOperations.lead
      ? `${trackedOperations.lead.name} • ${trackedOperations.lead.status}`
      : "No approved operation tracked",
    objectiveSituation,
    localBattle,
    immediateConcern,
    note: trackedOperations.lead
      ? trackedOperations.lead.statusDetail
      : trackedOperations.note,
  };
}

function localResponseUnits(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  return units
    .filter((unit) => String(unit?.side || "").toUpperCase() === "ALLIED")
    .filter((unit) => String(unit?.unit_type || "").toUpperCase() !== "HEADQUARTERS")
    .filter((unit) => {
      const kind = String(unit?.kind || "").trim().toLowerCase();
      return !kind.includes("air") && !kind.includes("naval") && !kind.includes("sea");
    })
    .map((unit) => {
      const operational = unit?.inspector?.operational_state ?? {};
      const supply = unit?.inspector?.supply ?? {};
      const movement = unit?.inspector?.movement ?? {};
      return {
        id: String(unit?.id || ""),
        name: String(unit?.name || "Formation"),
        locationId: typeof unit?.location_id === "string" ? unit.location_id : null,
        posture: String(operational?.posture || ""),
        readiness: typeof operational?.readiness === "number" ? operational.readiness : null,
        fatigue: typeof operational?.fatigue === "number" ? operational.fatigue : null,
        morale: typeof operational?.morale === "number" ? operational.morale : null,
        cohesion: typeof operational?.cohesion === "number" ? operational.cohesion : null,
        supplyPct: typeof supply?.supply_pct === "number" ? supply.supply_pct : null,
        movementRemaining: typeof movement?.remaining === "string" ? movement.remaining : null,
        kmRemaining: typeof movement?.km_remaining === "number" ? movement.km_remaining : null,
        locState: String(operational?.loc?.state || ""),
        locDetail: String(operational?.loc?.detail || ""),
      };
    });
}

function classifyResponse(unit) {
  const posture = String(unit.posture || "").trim().toUpperCase();
  if (posture === "ATTACK") {
    return {
      readiness: "Committed",
      note: "Already committed on current posture.",
      rank: 0,
    };
  }

  if (unit.readiness == null || unit.fatigue == null || unit.supplyPct == null) {
    return {
      readiness: "Unavailable",
      note: "Response readiness is not exposed for this formation.",
      rank: 1,
    };
  }

  if (unit.readiness >= 65 && unit.fatigue <= 20 && unit.supplyPct >= 70) {
    return {
      readiness: "Ready",
      note: "Can respond quickly from current readiness, fatigue, and supply state.",
      rank: 4,
    };
  }

  if (unit.readiness >= 50 && unit.fatigue <= 35 && unit.supplyPct >= 55) {
    return {
      readiness: "Limited",
      note: "Could respond, but not as an immediate counterattack force.",
      rank: 3,
    };
  }

  return {
    readiness: "Spent",
    note: "Too strained for a prompt local counterattack.",
    rank: 2,
  };
}

function buildResponseReadiness(snapshot) {
  const units = localResponseUnits(snapshot)
    .map((unit) => {
      const response = classifyResponse(unit);
      return {
        id: unit.id,
        name: unit.name,
        location: unit.locationId ? humanizeToken(String(unit.locationId).toLowerCase()) : "Location unavailable",
        posture: unit.posture ? humanizeToken(unit.posture) : "Posture unavailable",
        readiness: response.readiness,
        note: response.note,
        rank: response.rank,
      };
    })
    .sort((left, right) => right.rank - left.rank || left.name.localeCompare(right.name));

  const ready = units.filter((unit) => unit.readiness === "Ready").length;
  const limited = units.filter((unit) => unit.readiness === "Limited").length;
  const spent = units.filter((unit) => unit.readiness === "Spent" || unit.readiness === "Committed").length;

  let summary = "No local response-capable formation state is exposed.";
  if (ready || limited || spent) {
    summary = `${ready} ready • ${limited} limited • ${spent} spent or committed`;
  }
  if (!ready && !limited && units.length) {
    summary = "No credible immediate local response option is exposed from current unit state.";
  }

  return {
    summary,
    note: "Response readiness is a shell reading of current posture, readiness, fatigue, and supply only; it is not a hidden combat-power score.",
    units: units.slice(0, 4),
  };
}

function movementLabel(unit) {
  const remaining = String(unit?.movementRemaining || "").trim();
  const kmRemaining = typeof unit?.kmRemaining === "number" ? unit.kmRemaining : null;
  if (remaining && kmRemaining != null) {
    return `${humanizeToken(remaining)} • ${kmRemaining} km remaining`;
  }
  if (kmRemaining != null) {
    return `${kmRemaining} km remaining`;
  }
  if (remaining) {
    return `${humanizeToken(remaining)} movement`;
  }
  return "Movement not exposed";
}

function counterattackStatus(unit) {
  const posture = String(unit?.posture || "").trim().toUpperCase();
  if (posture === "ATTACK") {
    return {
      status: "Committed",
      note: "Already committed on current posture.",
      rank: 0,
    };
  }

  if (unit.readiness == null || unit.fatigue == null || unit.supplyPct == null) {
    return {
      status: "Unavailable",
      note: "Core counterattack state is not fully exposed for this formation.",
      rank: 1,
    };
  }

  let tier = 2;
  const constraints = [];
  const locState = String(unit?.locState || "").trim().toUpperCase();
  const movementState = String(unit?.movementRemaining || "").trim().toUpperCase();

  if (unit.readiness < 65) {
    tier = Math.min(tier, 1);
    constraints.push("Readiness below prompt counterattack threshold");
  }
  if (unit.fatigue > 20) {
    tier = Math.min(tier, 1);
    constraints.push("Fatigue elevated");
  }
  if (unit.supplyPct < 70) {
    tier = Math.min(tier, 1);
    constraints.push("Supply below immediate response margin");
  }

  if (unit.readiness < 50) {
    tier = 0;
  }
  if (unit.fatigue > 35) {
    tier = 0;
  }
  if (unit.supplyPct < 55) {
    tier = 0;
  }

  if (unit.morale != null && unit.morale < 50) {
    tier = Math.min(tier, unit.morale < 40 ? 0 : 1);
    constraints.push("Morale below steady offensive standard");
  }
  if (unit.cohesion != null && unit.cohesion < 50) {
    tier = Math.min(tier, unit.cohesion < 40 ? 0 : 1);
    constraints.push("Cohesion degraded");
  }

  if (locState === "THREATENED") {
    tier = Math.min(tier, 1);
    constraints.push("LOC threatened");
  } else if (locState === "BROKEN") {
    tier = 0;
    constraints.push("LOC broken");
  }

  if (movementState === "RESTRICTED") {
    tier = Math.min(tier, 1);
    constraints.push("Movement restricted");
  }
  if (typeof unit.kmRemaining === "number" && unit.kmRemaining <= 4) {
    tier = Math.min(tier, 1);
    constraints.push("Very short movement margin");
  }

  if (tier === 2) {
    return {
      status: "Ready",
      note: "Best current local candidate from exposed posture, readiness, fatigue, supply, and LOC state.",
      rank: 4,
    };
  }
  if (tier === 1) {
    return {
      status: "Limited",
      note: constraints.slice(0, 2).join(" • ") || "Current state limits an immediate offensive response.",
      rank: 3,
    };
  }
  return {
    status: "Not Ready",
    note: constraints.slice(0, 3).join(" • ") || "Current state argues against an immediate counterattack.",
    rank: 2,
  };
}

function buildCounterattackPlanning(snapshot) {
  const candidates = localResponseUnits(snapshot)
    .map((unit) => {
      const counterattack = counterattackStatus(unit);
      const factors = [
        unit.readiness != null ? `${Math.round(unit.readiness)} readiness` : "Readiness not exposed",
        unit.fatigue != null ? `${Math.round(unit.fatigue)} fatigue` : "Fatigue not exposed",
        unit.supplyPct != null ? `${Math.round(unit.supplyPct)}% supply` : "Supply not exposed",
        movementLabel(unit),
      ];
      return {
        id: unit.id,
        name: unit.name,
        location: unit.locationId ? humanizeToken(String(unit.locationId).toLowerCase()) : "Location unavailable",
        posture: unit.posture ? humanizeToken(unit.posture) : "Posture unavailable",
        status: counterattack.status,
        note: counterattack.note,
        factors: factors.join(" • "),
        locDetail: unit.locDetail || "LOC detail not exposed",
        rank: counterattack.rank,
        readinessValue: typeof unit.readiness === "number" ? unit.readiness : -1,
        fatigueValue: typeof unit.fatigue === "number" ? unit.fatigue : Number.POSITIVE_INFINITY,
        supplyValue: typeof unit.supplyPct === "number" ? unit.supplyPct : -1,
      };
    })
    .sort((left, right) => {
      if (right.rank !== left.rank) {
        return right.rank - left.rank;
      }
      if (right.readinessValue !== left.readinessValue) {
        return right.readinessValue - left.readinessValue;
      }
      if (left.fatigueValue !== right.fatigueValue) {
        return left.fatigueValue - right.fatigueValue;
      }
      if (right.supplyValue !== left.supplyValue) {
        return right.supplyValue - left.supplyValue;
      }
      return left.name.localeCompare(right.name);
    });

  const ready = candidates.filter((unit) => unit.status === "Ready").length;
  const limited = candidates.filter((unit) => unit.status === "Limited").length;
  const notReady = candidates.filter((unit) => unit.status === "Not Ready").length;
  const committed = candidates.filter((unit) => unit.status === "Committed").length;
  const bestCandidate = candidates.find((unit) => unit.status === "Ready" || unit.status === "Limited") ?? null;

  let summary = "No local candidate formation is exposed for counterattack planning.";
  if (candidates.length) {
    summary = `${ready} ready • ${limited} limited • ${notReady} not ready`;
    if (committed) {
      summary += ` • ${committed} committed`;
    }
  }
  if (!ready && !limited && candidates.length) {
    summary = "No credible immediate counterattack candidate is exposed from current unit state.";
  }

  return {
    summary,
    note: "Counterattack planning uses only exposed posture, readiness, fatigue, supply, LOC, morale/cohesion, and movement state; it is not a combat-odds estimate.",
    bestCandidate: bestCandidate
      ? `${bestCandidate.name} is the best-positioned local response formation on the current shell path.`
      : "No best-positioned local counterattack formation is exposed.",
    candidates: candidates.slice(0, 4).map(({ rank, readinessValue, fatigueValue, supplyValue, ...candidate }) => candidate),
  };
}

function joinLabels(labels) {
  const items = labels.filter(Boolean);
  if (!items.length) {
    return "";
  }
  if (items.length === 1) {
    return items[0];
  }
  if (items.length === 2) {
    return `${items[0]} and ${items[1]}`;
  }
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

function buildEngagementAreas(areas, objectivesById, localReports, pressureReasons) {
  return areas
    .map((area) => {
      const objective = area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null;
      const matchedReports = localReports.filter((report) => report.localAreaId === area.id);
      const matchedReasons = areaReasonMatches(area, pressureReasons);
      const objectiveRisk = objective?.side === "ALLIED" && objective?.rawState === "unheld";
      const reportIndex = matchedReports[0] ? localReports.findIndex((report) => report.id === matchedReports[0].id) : Number.MAX_SAFE_INTEGER;
      let status = "Under Pressure";
      let priority = matchedReasons.length ? 1 : 0;

      if (matchedReports.length) {
        status = "In Contact";
        priority = 3;
      } else if (objectiveRisk) {
        status = "At Risk";
        priority = 2;
      }

      return {
        id: area.id,
        label: area.label,
        kindLabel: humanizeToken(area.kind),
        locationId: area.locationId ? String(area.locationId).trim().toUpperCase() : null,
        status,
        detail: matchedReports[0]?.summary
          ?? (matchedReasons.length
            ? matchedReasons.map((reason) => humanizePressureReason(reason)).join(" • ")
            : objective?.state ?? "No current local engagement detail is exposed."),
        priority,
        reportIndex,
        value: objective?.value ?? 0,
        matchedReports: matchedReports.length,
        matchedReasons: matchedReasons.length,
      };
    })
    .filter((row) => row.priority > 0 || row.matchedReasons || row.matchedReports)
    .sort((left, right) => {
      if (left.reportIndex !== right.reportIndex) {
        return left.reportIndex - right.reportIndex;
      }
      if (right.priority !== left.priority) {
        return right.priority - left.priority;
      }
      if (right.matchedReports !== left.matchedReports) {
        return right.matchedReports - left.matchedReports;
      }
      if (right.matchedReasons !== left.matchedReasons) {
        return right.matchedReasons - left.matchedReasons;
      }
      if (right.value !== left.value) {
        return right.value - left.value;
      }
      return left.label.localeCompare(right.label);
    });
}

function buildEngagementFormationState(unit) {
  const posture = normalizeText(unit?.posture);
  const locState = normalizeText(unit?.locState);

  if (posture === "attack") {
    return "Committed";
  }
  if (unit?.readiness == null && unit?.fatigue == null && unit?.supplyPct == null) {
    return "Condition Partial";
  }
  if (locState === "broken" || unit?.readiness < 50 || unit?.fatigue > 35 || unit?.supplyPct < 55) {
    return "Strained";
  }
  if (posture === "defend") {
    return "Holding";
  }
  return "Engaged";
}

function buildEngagementFormationDetail(unit) {
  const details = [];

  if (typeof unit?.readiness === "number") {
    details.push(`${Math.round(unit.readiness)} readiness`);
  }
  if (typeof unit?.fatigue === "number") {
    details.push(`${Math.round(unit.fatigue)} fatigue`);
  }
  if (typeof unit?.supplyPct === "number") {
    details.push(`${Math.round(unit.supplyPct)}% supply`);
  }
  if (unit?.locState) {
    details.push(`LOC ${humanizeToken(unit.locState)}`);
  }

  return details.join(" • ") || "Condition not exposed on the current shell path.";
}

function buildEngagementSummary(snapshot, areas, objectivesById, localReports, pressureReasons) {
  const engagementAreas = buildEngagementAreas(areas, objectivesById, localReports, pressureReasons);
  const areaByLocationId = new Map(
    engagementAreas
      .filter((area) => area.locationId)
      .map((area, index) => [area.locationId, { area, order: index }]),
  );

  const formations = localResponseUnits(snapshot)
    .map((unit) => ({
      ...unit,
      locationKey: unit.locationId ? String(unit.locationId).trim().toUpperCase() : null,
    }))
    .filter((unit) => unit.locationKey && areaByLocationId.has(unit.locationKey))
    .sort((left, right) => {
      const leftArea = areaByLocationId.get(left.locationKey);
      const rightArea = areaByLocationId.get(right.locationKey);
      if ((leftArea?.order ?? Number.MAX_SAFE_INTEGER) !== (rightArea?.order ?? Number.MAX_SAFE_INTEGER)) {
        return (leftArea?.order ?? Number.MAX_SAFE_INTEGER) - (rightArea?.order ?? Number.MAX_SAFE_INTEGER);
      }
      if ((right.readiness ?? -1) !== (left.readiness ?? -1)) {
        return (right.readiness ?? -1) - (left.readiness ?? -1);
      }
      return left.name.localeCompare(right.name);
    })
    .slice(0, 4)
    .map((unit) => {
      const matchedArea = areaByLocationId.get(unit.locationKey)?.area ?? null;
      return {
        id: unit.id,
        name: unit.name,
        location: matchedArea?.label ?? (unit.locationId ? humanizeToken(String(unit.locationId).toLowerCase()) : "Location unavailable"),
        posture: unit.posture ? humanizeToken(unit.posture) : "Posture unavailable",
        status: buildEngagementFormationState(unit),
        detail: buildEngagementFormationDetail(unit),
      };
    });

  const hotspotLabels = engagementAreas.slice(0, 3).map((area) => area.label);
  const formationLabels = formations.slice(0, 3).map((unit) => unit.name);
  let summary = "No active local engagement is exposed beyond the current perimeter status.";

  if (hotspotLabels.length && formationLabels.length) {
    summary = `Contact is active at ${joinLabels(hotspotLabels)}; ${joinLabels(formationLabels)} are the exposed formations carrying the fight.`;
  } else if (hotspotLabels.length) {
    summary = `Contact is active at ${joinLabels(hotspotLabels)}, but no current formation is directly tied to those reports on the shell path.`;
  }

  return {
    summary,
    note: "Built only from named local contact/pressure areas plus current formations located at those same exposed local positions. No inferred frontage or hidden engagement state is added.",
    hotspotsSummary: hotspotLabels.length ? hotspotLabels.join(" • ") : "No named local engagement focus is exposed.",
    formationSummary: formationLabels.length ? formationLabels.join(" • ") : "No formation is directly tied to the exposed local fight.",
    hotspots: engagementAreas.slice(0, 4).map(({ priority, reportIndex, value, matchedReports, matchedReasons, locationId, ...area }) => area),
    formations,
  };
}

function defensivePreparationRank(state) {
  switch (normalizeText(state)) {
    case "prepared":
      return 3;
    case "developing":
      return 2;
    case "light":
      return 1;
    default:
      return 0;
  }
}

function buildDefensePreparation(areas, objectivesById) {
  const preparedAreas = areas
    .filter((area) => area.defensivePreparation)
    .map((area) => {
      const objective = area.objectiveId ? objectivesById.get(area.objectiveId) ?? null : null;
      const preparation = area.defensivePreparation;
      return {
        id: area.id,
        label: area.label,
        state: preparation?.state || "Unavailable",
        fortification: preparation?.fortificationState || "Fortification state not exposed.",
        obstacles: preparation?.obstacleState || "Obstacle detail not separately exposed.",
        engineer: preparation?.engineerState || "Engineer preparation state not separately exposed.",
        hasObstacleState: !!preparation?.obstacleState,
        hasEngineerState: !!preparation?.engineerState,
        rank: defensivePreparationRank(preparation?.state),
        value: objective?.value ?? 0,
      };
    });

  if (!preparedAreas.length) {
    return {
      available: false,
      fortificationState: "Unavailable",
      obstacles: "Not exposed",
      engineer: "Not exposed",
      mostPrepared: "No prepared local objective exposed.",
      leastPrepared: "No lightly prepared local objective exposed.",
      note: "Local fortification, obstacle, and engineer-preparation state is not exposed on the current shell path.",
      areas: [],
    };
  }

  const rankedAreas = [...preparedAreas].sort((left, right) => {
    if (right.rank !== left.rank) {
      return right.rank - left.rank;
    }
    if (right.value !== left.value) {
      return right.value - left.value;
    }
    return left.label.localeCompare(right.label);
  });
  const leastPreparedAreas = [...preparedAreas].sort((left, right) => {
    if (left.rank !== right.rank) {
      return left.rank - right.rank;
    }
    if (left.value !== right.value) {
      return left.value - right.value;
    }
    return left.label.localeCompare(right.label);
  });
  const uniqueStates = Array.from(new Set(preparedAreas.map((area) => area.state).filter(Boolean)));
  const obstacleCount = preparedAreas.filter((area) => area.hasObstacleState).length;
  const engineerCount = preparedAreas.filter((area) => area.hasEngineerState).length;

  return {
    available: true,
    fortificationState: uniqueStates.length === 1 ? uniqueStates[0] : "Mixed",
    obstacles: obstacleCount ? `${obstacleCount} local areas reported` : "Not exposed",
    engineer: engineerCount ? `${engineerCount} local areas reported` : "Not exposed",
    mostPrepared: rankedAreas[0] ? `${rankedAreas[0].label} (${rankedAreas[0].state})` : "No prepared local objective exposed.",
    leastPrepared: leastPreparedAreas[0] ? `${leastPreparedAreas[0].label} (${leastPreparedAreas[0].state})` : "No lightly prepared local objective exposed.",
    note: "Built from scenario-authored local fortification, obstacle, and engineer-preparation notes only.",
    areas: rankedAreas.map(({ rank, value, hasObstacleState, hasEngineerState, ...area }) => area),
  };
}

function buildConcernSummary(localReports, pressureReasons) {
  if (localReports[0]?.summary) {
    return localReports[0].summary;
  }
  if (pressureReasons.length) {
    return pressureReasons.map((reason) => humanizePressureReason(reason)).join(" • ");
  }
  return "No explicit local perimeter concern is exposed in the current snapshot.";
}

export function summarizeHendersonPressureBoard(snapshot, operations = []) {
  const areas = localPressureAreas(snapshot);
  if (!areas.length) {
    return {
      available: false,
      title: "Henderson Perimeter",
      operationsOverview: buildOperationsOverview(snapshot, operations),
      note: "Local Henderson/Lunga perimeter pressure is unavailable outside the current perimeter slice.",
      perimeterStatus: [],
      pressureAxes: [],
      engagementSummary: {
        summary: "No current engagement summary is exposed.",
        note: "Engagement summary is unavailable because the active scenario does not expose local Henderson perimeter areas.",
        hotspotsSummary: "No named local engagement focus is exposed.",
        formationSummary: "No formation is directly tied to the exposed local fight.",
        hotspots: [],
        formations: [],
      },
      reserveStatus: "Not exposed on the current shell path.",
      responseReadiness: {
        summary: "No current response-readiness data.",
        note: "Response readiness is unavailable because the active scenario does not expose local Henderson perimeter areas.",
        units: [],
      },
      counterattackPlanning: {
        summary: "No current counterattack-planning data.",
        note: "Counterattack planning is unavailable because the active scenario does not expose local Henderson perimeter areas.",
        bestCandidate: "No best-positioned local counterattack formation is exposed.",
        candidates: [],
      },
      defensePreparation: {
        available: false,
        fortificationState: "Unavailable",
        obstacles: "Not exposed",
        engineer: "Not exposed",
        mostPrepared: "No prepared local objective exposed.",
        leastPrepared: "No lightly prepared local objective exposed.",
        note: "Local fortification, obstacle, and engineer-preparation state is unavailable because the active scenario does not expose local Henderson perimeter areas.",
        areas: [],
      },
      localSustainment: {
        available: false,
        status: "Unavailable",
        note: "Local sustainment is unavailable because the active scenario does not expose the Henderson perimeter picture.",
        resources: [
          { label: "Supply", value: "Not exposed" },
          { label: "Ammo", value: "Not exposed" },
          { label: "Fuel", value: "Not exposed" },
          { label: "Rations", value: "Not exposed" },
          { label: "Support", value: "Not exposed" },
        ],
        atRisk: [],
        concerns: ["No local sustainment warning is exposed on the current shell path."],
      },
      airSupport: {
        available: false,
        availability: "Unavailable",
        note: "Local air-support context is unavailable because the active scenario does not expose the Henderson perimeter picture.",
        sortiePosture: "Sortie posture unavailable",
        constraint: "Weather-linked local air-response limits are unavailable outside the Henderson slice.",
        supportingFormation: "No supporting air formation exposed.",
      },
      navalSupport: {
        available: false,
        availability: "Unavailable",
        note: "Local naval-support context is unavailable because the active scenario does not expose the Henderson perimeter picture.",
        supportPosture: "Support posture unavailable",
        constraint: "Offshore-support limits are unavailable outside the Henderson slice.",
        supportingFormation: "No supporting naval formation exposed.",
      },
      recentContacts: [],
    };
  }

  const objectivesById = objectiveDisplayIndex(snapshot);
  const areaIds = new Set(areas.map((area) => area.id));
  const localReports = collectLocalReports(snapshot, areaIds);
  const pressureReasons = Array.isArray(snapshot?.pressure?.reasons)
    ? snapshot.pressure.reasons.filter((reason) => areas.some((area) => area.pressureReasons.includes(String(reason))))
    : [];
  const pressureAxes = buildPressureAxes(areas, objectivesById, localReports, pressureReasons);
  const engagementSummary = buildEngagementSummary(snapshot, areas, objectivesById, localReports, pressureReasons);
  const responseReadiness = buildResponseReadiness(snapshot);
  const counterattackPlanning = buildCounterattackPlanning(snapshot);
  const defensePreparation = buildDefensePreparation(areas, objectivesById);
  const localSustainment = summarizeLocalSustainment(snapshot);
  const airSupport = summarizeLocalAirSupport(snapshot);
  const navalSupport = summarizeLocalNavalSupport(snapshot);
  const overallStatus = buildOverallStatus(areas, objectivesById, localReports, pressureReasons);
  const immediateConcern = buildImmediateConcern(areas, objectivesById, localReports, pressureAxes);

  return {
    available: true,
    title: "Henderson Perimeter",
    operationsOverview: buildOperationsOverview(snapshot, operations, {
      available: true,
      overallStatus,
      immediateConcern,
      hotspotsSummary: engagementSummary.hotspotsSummary,
    }),
    note: "Built from scenario-authored local pressure areas, named objectives, and current local dispatches already exposed on the shell path.",
    perimeterStatus: [
      { label: "Overall Status", value: overallStatus },
      { label: "Immediate Concern", value: immediateConcern },
      { label: "Staff Concern", value: buildConcernSummary(localReports, pressureReasons) },
    ],
    pressureAxes,
    engagementSummary,
    reserveStatus: buildReserveStatus(localReports),
    responseReadiness,
    counterattackPlanning,
    defensePreparation,
    localSustainment,
    airSupport,
    navalSupport,
    recentContacts: localReports,
  };
}
