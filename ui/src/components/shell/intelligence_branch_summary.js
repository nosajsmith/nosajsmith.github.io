import { summarizeCommunications } from "./communications_summary.js";

function normalizeReason(reason) {
  return String(reason ?? "")
    .replace(/[_:.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim() || "Unknown reporting gap";
}

function localPressureAreas(snapshot) {
  return Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
}

function uniqueRows(items) {
  const seen = new Set();
  const rows = [];
  for (const item of items) {
    const title = String(item?.title ?? "").trim().toLowerCase();
    const detail = String(item?.detail ?? "").trim().toLowerCase();
    const key = `${title}|${detail}`;
    if (!title || seen.has(key)) {
      continue;
    }
    seen.add(key);
    rows.push(item);
  }
  return rows;
}

export function summarizeIntelligenceBranch(snapshot, operations = []) {
  const communications = summarizeCommunications(snapshot, operations);
  const pressureReasons = Array.isArray(snapshot?.pressure?.reasons) ? snapshot.pressure.reasons : [];
  const areas = localPressureAreas(snapshot);
  const areaSightings = areas.flatMap((area, index) => {
    const label = String(area?.label ?? "").trim();
    const defensiveState = String(area?.defensive_preparation?.state ?? "").trim();
    const fortified = String(area?.defensive_preparation?.fortification_state ?? "").trim();
    const reasons = Array.isArray(area?.pressure_reasons) ? area.pressure_reasons : [];
    const leadReason = reasons[0] ? normalizeReason(reasons[0]) : "";

    if (!label) {
      return [];
    }

    return [{
      id: `area-${index}-${label}`,
      title: label,
      detail: [
        defensiveState ? `${normalizeReason(defensiveState)} state` : "",
        fortified ? normalizeReason(fortified) : "",
        leadReason ? `Pressure cue ${leadReason}` : "",
      ].filter(Boolean).join(" • ") || "Named local pressure area exposed on the current shell path.",
    }];
  });
  const reasonSightings = pressureReasons.map((reason, index) => ({
    id: `reason-${index}-${reason}`,
    title: normalizeReason(reason),
    detail: "Derived from current pressure reasons; source confidence is not exposed.",
  }));
  const sightings = uniqueRows([...areaSightings, ...reasonSightings]).slice(0, 6);
  const recent = communications.history.slice(0, 6);
  const reportCount = recent.length;
  const orderCount = Array.isArray(snapshot?.bai_report?.unit_orders) ? snapshot.bai_report.unit_orders.length : 0;
  const playerOrderCount = Array.isArray(operations) ? operations.length : 0;
  const aiSummary = String(snapshot?.staff?.summary ?? "").trim();

  return {
    overview: {
      pending: communications.pending,
      latestTitle: communications.latest?.title ?? "No current dispatch",
      latestSummary: communications.latest?.summary ?? "No communications are available in the current snapshot.",
      pressureActive: !!snapshot?.pressure?.active,
      staffSummary: aiSummary || "Staff summary unavailable",
      statusLine: recent.length || sightings.length
        ? "Intelligence picture built from live dispatch traffic, local pressure areas, and exposed AI order flow."
        : "No current intelligence dispatches or pressure cues are exposed on the active shell path.",
    },
    dispatches: recent,
    recon: {
      sightings,
      detail: sightings.length
        ? "Recon picture is built from named local pressure areas, exposed preparation states, and authoritative pressure reasons."
        : "No dedicated recon sightings are exposed on the current shell path.",
    },
    confidence: {
      status: reportCount || sightings.length || orderCount || playerOrderCount
        ? "Live picture partial"
        : "Confidence and uncertainty values not exposed",
      detail: reportCount || sightings.length || orderCount || playerOrderCount
        ? `${reportCount} dispatch${reportCount === 1 ? "" : "es"}, ${sightings.length} local cue${sightings.length === 1 ? "" : "s"}, ${orderCount} AI order${orderCount === 1 ? "" : "s"}${playerOrderCount ? `, and ${playerOrderCount} player operation${playerOrderCount === 1 ? "" : "s"}` : ""} currently inform the picture. Quantified source confidence is not exposed.`
        : "Confidence bands, source attribution, and quantified enemy estimates are not exposed on the current shell path.",
    },
    concerns: sightings.length
      ? sightings.slice(0, 4).map((entry) => `${entry.title} remains unresolved on the current shell path.`)
      : ["No explicit intelligence concerns are exposed beyond the current communications feed."],
  };
}
