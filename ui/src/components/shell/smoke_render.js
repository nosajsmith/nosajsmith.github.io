import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  formatHours,
  humanizeCampaignStatus,
  humanizeIntent,
  humanizePressureReason,
  humanizeReportKind,
  humanizeSideLabel,
  inferScenarioPresentation,
} from "../../lib/view_snapshot.js";

export function renderReadyShellSmoke(snapshot) {
  const presentation = inferScenarioPresentation(snapshot);
  const scoreRows = Object.entries(snapshot.campaign.score_by_side || {}).map(([side, value]) =>
    React.createElement("div", { key: side }, `${humanizeSideLabel(side)} ${value}`),
  );
  const reportRows = (snapshot.reports.recent || []).map((report) =>
    React.createElement(
      "article",
      { key: report.id },
      `${humanizeReportKind(report.kind)} ${report.summary}`,
    ),
  );

  return renderToStaticMarkup(
    React.createElement(
      "main",
      null,
      React.createElement("header", null, `${presentation.shellTitle} ${presentation.scenarioLabel}`),
      React.createElement("section", null, `Campaign ${humanizeCampaignStatus(snapshot.campaign.status)}`),
      React.createElement(
        "section",
        null,
        snapshot.pressure.reasons.length
          ? snapshot.pressure.reasons.map((reason) => humanizePressureReason(reason)).join(" • ")
          : "Pressure summary unavailable",
      ),
      React.createElement("section", null, humanizeIntent(snapshot.ai.last_intent)),
      React.createElement("section", null, `Time ${formatHours(snapshot.time.current_hours)}`),
      React.createElement("section", null, scoreRows),
      React.createElement("section", null, reportRows),
    ),
  );
}

export function renderStateScreenSmoke(title, message) {
  return renderToStaticMarkup(
    React.createElement(
      "section",
      null,
      React.createElement("div", null, "Command Post"),
      React.createElement("h2", null, title),
      React.createElement("p", null, message),
    ),
  );
}

export function renderLauncherSmoke({
  title = "Theater of Operations",
  subtitle = "Inchon",
  theaterLabel = "Korea Theater • Operation Chromite",
  scenarioName = "Inchon MVP",
  bridgeStatus = "Connected",
  objective = "Seoul",
  musicLabel = "Theme active",
  musicVolume = "34%",
} = {}) {
  return renderToStaticMarkup(
    React.createElement(
      "section",
      null,
      React.createElement("div", null, "Publisher Demo Vertical Slice"),
      React.createElement("h1", null, `${title} ${subtitle}`),
      React.createElement("div", null, theaterLabel),
      React.createElement("div", null, "Current Vertical Slice: Inchon"),
      React.createElement("div", null, "Shell Handoff Direct shell handoff ready"),
      React.createElement("div", null, "Franchise Key Art"),
      React.createElement("div", null, scenarioName),
      React.createElement("div", null, `Bridge ${bridgeStatus}`),
      React.createElement("div", null, `Objective ${objective}`),
      React.createElement("div", null, `Launcher Audio ${musicLabel}`),
      React.createElement("div", null, `Optional Menu Theme ${musicVolume}`),
    ),
  );
}
