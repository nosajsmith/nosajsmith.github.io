import { formatReportPresentation } from "../../lib/view_snapshot.js";
import { orderRecentReports } from "./dashboard_summary.js";

const DEMO_82ND_AIRBORNE = {
  id: "demo-82nd-airborne",
  title: "82nd Airborne Situation Report",
  kind: "Demo Example",
  showKind: true,
  summary: "82nd Airborne reports scattered but organized drop elements consolidating near the objective corridor.",
  body:
    "Frontend demo example for visual evaluation only. 82nd Airborne elements report consolidation underway, perimeter control improving, and immediate resupply requests pending by drop zone conditions.",
  severity: "info",
  timeLabel: "Demo presentation example",
  senderLabel: "82nd Airborne",
  insigniaCode: "AA",
  isDemo: true,
};

export function formatCommunicationTime(value) {
  return value != null ? `Recorded at T+${value}h` : "Time unavailable";
}

export function summarizeCommunications(reports = { pending_count: null, recent: [] }) {
  const ordered = orderRecentReports(reports?.recent);
  const messages = ordered.map((report) => {
    const display = formatReportPresentation(report);
    const summary = display.summary || "No message body is available on the current shell path.";

    return {
      id: String(report?.id ?? ""),
      title: display.title,
      kind: display.kind,
      showKind: display.showKind,
      summary,
      body: summary,
      severity: String(report?.severity || "info"),
      timeLabel: formatCommunicationTime(report?.time ?? null),
      senderLabel: typeof report?.sender_label === "string" && report.sender_label.trim() ? report.sender_label.trim() : null,
      insigniaCode: null,
      isDemo: false,
    };
  });

  return {
    pending: reports?.pending_count ?? null,
    latest: messages[0] ?? null,
    history: messages,
    demoExample: DEMO_82ND_AIRBORNE,
  };
}
