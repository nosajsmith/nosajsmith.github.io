import { summarizeCommunications } from "./communications_summary.js";

function normalizeReason(reason) {
  return String(reason ?? "")
    .replace(/[_:.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim() || "Unknown reporting gap";
}

export function summarizeIntelligenceBranch(snapshot) {
  const communications = summarizeCommunications(snapshot?.reports);
  const reasons = Array.isArray(snapshot?.pressure?.reasons) ? snapshot.pressure.reasons : [];
  const recent = communications.history.slice(0, 6);

  return {
    overview: {
      pending: communications.pending,
      latestTitle: communications.latest?.title ?? "No current dispatch",
      latestSummary: communications.latest?.summary ?? "No communications are available in the current snapshot.",
      pressureActive: !!snapshot?.pressure?.active,
      staffSummary: snapshot?.staff?.summary ?? "Staff summary unavailable",
      statusLine: recent.length
        ? "Intelligence picture built from the current communications feed and pressure-reason path."
        : "No current intelligence dispatches are exposed on the active shell path.",
    },
    dispatches: recent,
    recon: {
      sightings: reasons.map((reason, index) => ({
        id: `reason-${index}-${reason}`,
        title: normalizeReason(reason),
        detail: "Derived from current pressure reasons; source confidence is not exposed.",
      })),
      detail: reasons.length
        ? "Enemy activity cues are limited to authoritative pressure reasons and communications text."
        : "No dedicated recon sightings are exposed on the current shell path.",
    },
    confidence: {
      status: "Confidence and uncertainty values not exposed",
      detail: "Confidence bands, source attribution, and quantified enemy estimates are not exposed on the current shell path.",
    },
    concerns: reasons.length
      ? reasons.map((reason) => `${normalizeReason(reason)} remains unresolved on the current shell path.`)
      : ["No explicit intelligence concerns are exposed beyond the current communications feed."],
  };
}
