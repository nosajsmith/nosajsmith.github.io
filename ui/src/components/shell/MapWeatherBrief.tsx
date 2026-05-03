import { summarizeWeather } from "./map_weather.js";
import { buildWeatherImpactState } from "./map_scene.js";

type MapWeatherBriefProps = {
  snapshot: unknown;
};

function normalizeWeatherValue(value: string, fallback = "Not reported") {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return fallback;
  }
  const normalized = raw.toLowerCase();
  if (normalized === "not exposed") {
    return "Not reported";
  }
  if (normalized === "not modeled") {
    return "Not shown";
  }
  if (normalized === "weather cue only") {
    return "Current cue only";
  }
  if (normalized === "summary exposed") {
    return "Summary available";
  }
  if (normalized === "context exposed") {
    return "Local context";
  }
  return raw;
}

function toSentence(value: string, fallback: string) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return fallback;
  }
  return /[.!?]$/.test(raw) ? raw : `${raw}.`;
}

export default function MapWeatherBrief({ snapshot }: MapWeatherBriefProps) {
  const weather = summarizeWeather(snapshot);
  const weatherImpact = buildWeatherImpactState(snapshot);
  const stateLine = normalizeWeatherValue(weatherImpact.current || weather.condition, "Weather picture pending");
  const supportLine = weather.available
    ? toSentence(weather.cue, "No operational weather cue is exposed on the current shell path.")
    : "No authoritative weather picture is exposed for this scenario yet.";
  const detailRows = [
    { label: "Temp", value: weather.temp },
    { label: "Wind", value: weather.wind },
    { label: "Time", value: weatherImpact.timeState },
    { label: "Sight", value: normalizeWeatherValue(weatherImpact.visibility) },
    { label: "Ground", value: normalizeWeatherValue(weatherImpact.groundMovement) },
    { label: "Air", value: normalizeWeatherValue(weatherImpact.air) },
  ];

  return (
    <div className="shell-weather">
      <div className="shell-weather__summary">
        <div className="shell-weather__summary-head">
          <div className="shell-weather__summary-title">Weather</div>
          <div className="shell-weather__summary-badge" aria-hidden="true">
            {weather.icon}
          </div>
        </div>
        <div className="shell-weather__summary-state">{stateLine}</div>
        <div className="shell-weather__summary-support">{supportLine}</div>
      </div>
      <div className="shell-weather__detail">
        <div className="shell-weather__detail-grid">
          {detailRows.map((row) => (
            <div className="shell-weather__detail-row" key={row.label}>
              <strong>{row.label}</strong>
              <span>{row.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
