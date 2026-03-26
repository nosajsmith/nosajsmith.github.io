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
  const withoutSkeleton = normalized.replace(/\bSkeleton\b/gi, "").replace(/\s+/g, " ").trim();
  return humanizeToken(withoutSkeleton || normalized);
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
