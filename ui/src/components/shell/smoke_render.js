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
  title = "Theater of Operations: Korea",
  subtitle = "Operational Publisher Preview",
  theaterLabel = "Korea Theater • Operation Chromite",
  scenarioName = "Inchon MVP",
  bridgeStatus = "Connected",
  objective = "Seoul",
  musicLabel = "Theme playing",
  musicVolume = "34%",
} = {}) {
  return renderToStaticMarkup(
    React.createElement(
      "section",
      null,
      React.createElement("div", null, "Publisher Preview Build"),
      React.createElement("h1", null, `${title} ${subtitle}`),
      React.createElement("div", null, theaterLabel),
      React.createElement("div", null, "Playable Publisher Preview"),
      React.createElement("div", null, "Operational Command Shell"),
      React.createElement("div", null, "One-Turn Playable Loop"),
      React.createElement("div", null, "Command Shell Command shell ready"),
      React.createElement("div", null, "Publisher Preview Key Art"),
      React.createElement("div", null, scenarioName),
      React.createElement("div", null, `Bridge ${bridgeStatus}`),
      React.createElement("div", null, `Objective ${objective}`),
      React.createElement("div", null, `Preview Audio ${musicLabel}`),
      React.createElement("div", null, `Opening Theme ${musicVolume}`),
    ),
  );
}
