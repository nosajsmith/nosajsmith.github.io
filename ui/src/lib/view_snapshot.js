export function humanizeToken(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return "Unknown";
  }
  return raw
    .replace(/[_:.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function humanizeScenarioLabel(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return "Scenario";
  }
  const withoutExtension = raw.replace(/\.json$/i, "");
  const normalized = withoutExtension
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const withoutSkeleton = normalized
    .replace(/\bSkeleton\b/gi, "")
    .replace(/\bMvp\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  return humanizeToken(withoutSkeleton || normalized);
}

function normalizeScenarioSearchText(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function labelFromRecord(value) {
  if (typeof value === "string" || typeof value === "number") {
    return String(value).trim();
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  for (const key of ["name", "label", "title", "summary", "objective", "main_objective", "target_objective", "id"]) {
    const candidate = value[key];
    if (candidate != null) {
      const text = String(candidate).trim();
      if (text) {
        return text;
      }
    }
  }
  return "";
}

function scenarioSearchText(input) {
  if (typeof input === "string") {
    return normalizeScenarioSearchText(input);
  }
  if (input && typeof input === "object") {
    const snapshot = input.scenario && typeof input.scenario === "object" ? input : null;
    const scenario = snapshot?.scenario ?? input;
    const context = snapshot ? [
      ...(Array.isArray(snapshot.objectives) ? snapshot.objectives.map((objective) => labelFromRecord(objective)) : []),
      ...(Array.isArray(snapshot.airfields) ? snapshot.airfields.map((airfield) => labelFromRecord(airfield)) : []),
      ...(Array.isArray(snapshot.ports) ? snapshot.ports.map((port) => labelFromRecord(port)) : []),
      ...(Array.isArray(snapshot.local_pressure_areas) ? snapshot.local_pressure_areas.map((area) => labelFromRecord(area)) : []),
      labelFromRecord(snapshot.grease_board?.objective),
      labelFromRecord(snapshot.grease_board?.main_effort),
      labelFromRecord(snapshot.bai_report?.main_objective),
      labelFromRecord(snapshot.bai_report?.chosen_operation),
    ] : [];
    return normalizeScenarioSearchText([scenario?.id ?? "", scenario?.name ?? "", ...context].join(" "));
  }
  return "";
}

function scenarioDisplayLabel(input) {
  if (input && typeof input === "object") {
    const scenario = input.scenario && typeof input.scenario === "object" ? input.scenario : input;
    return humanizeScenarioLabel(scenario?.name ?? scenario?.id ?? "Scenario");
  }
  return humanizeScenarioLabel(input);
}

export function isKoreaScenarioContext(input) {
  const searchText = scenarioSearchText(input);
  return /(^| )(korea|korean war|inchon|incheon|seoul|kimpo|waegwan|naktong|nakdong|pusan|chromite)( |$)/.test(searchText);
}

export function containsLegacySouthPacificText(value) {
  const text = typeof value === "string" || typeof value === "number"
    ? normalizeScenarioSearchText(value)
    : normalizeScenarioSearchText(labelFromRecord(value));
  if (!text) {
    return false;
  }
  return /(^| )(guadalcanal|henderson|lunga|bloody ridge|alligator creek|matanikau|tulagi|kokumbona)( |$)/.test(text);
}

export function inferScenarioPresentation(input) {
  const searchText = scenarioSearchText(input);
  const displayLabel = scenarioDisplayLabel(input);
  const genericScenarioLabel = !displayLabel
    || /^(Scenario|Unknown|Operational Theater|Operational Picture)$/i.test(displayLabel);
  const koreaSpecificDisplayLabel = /\b(korea|korean war|inchon|incheon|chromite|seoul|kimpo|waegwan|naktong|nakdong|pusan)\b/i.test(displayLabel);
  const isKorea = isKoreaScenarioContext(input);
  const isInchon = /(^| )(inchon|incheon|chromite|kimpo|seoul)( |$)/.test(searchText);
  const isGuadalcanal = /(^| )(guadalcanal|lunga|henderson|tulagi|kokumbona)( |$)/.test(searchText);

  if (isKorea) {
    const scenarioLabel = isInchon
      ? (!koreaSpecificDisplayLabel || genericScenarioLabel ? "Operation Chromite Vertical Slice" : displayLabel)
      : (!koreaSpecificDisplayLabel || genericScenarioLabel ? "Korea Vertical Slice" : displayLabel);
    return {
      scenarioLabel,
      shellTitle: isInchon ? "Theater of Operations: Inchon" : "Theater of Operations: Korea",
      theaterLabel: isInchon ? "Korea Theater • Operation Chromite" : "Korea Theater",
      frontLabel: isInchon ? "Inchon / Seoul Axis" : "Korea Front",
      localBattleTitle: isInchon ? "Inchon Landing Front" : "Korea Front",
      operationsTitle: isInchon ? "Inchon Operations" : "Korea Operations",
      calendarEpoch: { year: 1950, monthIndex: 8, day: isInchon ? 15 : 1 },
      referenceClocks: [
        { label: "Seoul", timeZone: "Asia/Seoul" },
        { label: "Tokyo", timeZone: "Asia/Tokyo" },
      ],
      basemapLabel: "Korea operational package",
    };
  }

  if (isGuadalcanal) {
    return {
      scenarioLabel: displayLabel,
      shellTitle: "Theater of Operations: Guadalcanal",
      theaterLabel: "South Pacific Theater • Guadalcanal",
      frontLabel: "Henderson / Lunga Perimeter",
      localBattleTitle: "Henderson Perimeter",
      operationsTitle: "Henderson Operations",
      calendarEpoch: { year: 1942, monthIndex: 8, day: 1 },
      referenceClocks: [
        { label: "Honiara", timeZone: "Pacific/Guadalcanal" },
        { label: "Washington", timeZone: "America/New_York" },
      ],
      basemapLabel: "Guadalcanal operational package",
    };
  }

  return {
    scenarioLabel: displayLabel,
    shellTitle: `Theater of Operations: ${displayLabel}`,
    theaterLabel: "Operational Theater",
    frontLabel: "Current Front",
    localBattleTitle: "Local Battle",
    operationsTitle: "Operations Picture",
    calendarEpoch: null,
    referenceClocks: [
      { label: "UTC", timeZone: "UTC" },
      { label: "New York", timeZone: "America/New_York" },
    ],
    basemapLabel: "Operational basemap package",
  };
}

export function humanizeReportKind(kind) {
  return humanizeToken(kind);
}

function normalizeVisibleLabel(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function cleanReportSummary(summary) {
  const raw = String(summary ?? "").trim();
  if (!raw) {
    return "Operational update.";
  }
  return raw
    .replace(/Operational AI enabled for visible shell progression\.?/gi, "Operational AI enabled.")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatReportPresentation(report) {
  const kind = humanizeReportKind(report?.kind);
  const rawTitle = String(report?.title ?? "").trim();
  const title = rawTitle || kind;
  const showKind = normalizeVisibleLabel(title) !== normalizeVisibleLabel(kind);

  return {
    title,
    kind,
    showKind,
    summary: cleanReportSummary(report?.summary),
  };
}

export function humanizePressureReason(reason) {
  return humanizeToken(reason);
}

export function humanizeIntent(intent) {
  const raw = String(intent ?? "").trim();
  if (!raw) {
    return "No current AI intent recorded.";
  }
  const cleaned = raw.replace(/[_:.-]+/g, " ").replace(/\s+/g, " ").trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function humanizeCampaignStatus(status) {
  return humanizeToken(status);
}

export function humanizeSideLabel(side) {
  const raw = String(side ?? "").trim().toUpperCase();
  if (raw === "ALLIED") {
    return "Allied";
  }
  if (raw === "AXIS") {
    return "Axis";
  }
  return humanizeToken(side);
}

export function buildObjectiveDisplayName(objective, duplicateNames = new Set()) {
  const baseName = String(objective?.name ?? "Objective").trim() || "Objective";
  if (duplicateNames.has(baseName) && objective?.side) {
    return `${baseName} (${humanizeSideLabel(objective.side)})`;
  }
  return baseName;
}

export function formatHours(value) {
  if (value == null) {
    return "Unknown";
  }
  return `T+${value}h`;
}

export function pressureFallback(summary) {
  if (summary.summary) {
    return summary.summary;
  }
  if (summary.reasons.length) {
    return summary.reasons.map(humanizePressureReason).join(" • ");
  }
  return "Pressure summary unavailable";
}
