function isRecord(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function toLabel(value, fallback = "Unavailable") {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  return fallback;
}

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatTemp(value) {
  return value == null ? "N/A" : `${Math.round(value)}°C`;
}

function formatWind(value) {
  return value == null ? "Wind unavailable" : `${Math.round(value)} kph`;
}

function formatTimeLabel(value, fallbackIndex) {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return `T+${value}h`;
  }
  return `+${fallbackIndex * 6}h`;
}

function buildForecastRows(forecast) {
  if (!Array.isArray(forecast) || !forecast.length) {
    return Array.from({ length: 4 }, (_, index) => ({
      id: `unavailable-${index}`,
      timeLabel: `+${index * 6}h`,
      icon: "??",
      condition: "Unavailable",
      temp: "N/A",
      wind: "Unavailable",
      support: "Authoritative forecast unavailable",
      unavailable: true,
    }));
  }

  return forecast.slice(0, 4).map((entry, index) => {
    const row = isRecord(entry) ? entry : {};
    const temp = toNumber(row.temp_c ?? row.temperature_c ?? row.temp);
    const wind = toNumber(row.wind_kph ?? row.wind ?? row.wind_speed_kph);
    const precip = toNumber(row.precip_mm ?? row.precip);
    const visibility = typeof row.visibility === "string" ? row.visibility : null;
    const seaState = typeof row.sea_state === "string" ? row.sea_state : null;
    const condition = toLabel(row.condition);
    const support = precip != null
      ? `${Math.round(precip)} mm precip`
      : visibility
        ? `Visibility ${visibility}`
        : seaState
          ? `Sea ${seaState}`
          : "No additional field";

    return {
      id: String(row.id ?? `forecast-${index}`),
      timeLabel: formatTimeLabel(row.time ?? row.hour ?? row.label, index),
      icon: weatherIcon(condition),
      condition,
      temp: formatTemp(temp),
      wind: formatWind(wind),
      support,
      unavailable: false,
    };
  });
}

export function weatherIcon(condition) {
  const key = String(condition || "").toLowerCase();
  if (key.includes("storm")) return "ST";
  if (key.includes("rain")) return "RN";
  if (key.includes("cloud") || key.includes("overcast")) return "OC";
  if (key.includes("fog")) return "FG";
  if (key.includes("wind")) return "WD";
  if (key.includes("clear") || key.includes("fair")) return "CL";
  return "??";
}

export function summarizeWeather(snapshot) {
  const weather = isRecord(snapshot?.weather) ? snapshot.weather : null;
  const forecast = weather && Array.isArray(weather.forecast) ? weather.forecast : null;
  const condition = toLabel(weather?.condition, "Weather unavailable");
  const temp = formatTemp(toNumber(weather?.temp_c ?? weather?.temperature_c ?? weather?.temp));
  const wind = formatWind(toNumber(weather?.wind_kph ?? weather?.wind ?? weather?.wind_speed_kph));
  const operationalCue = typeof weather?.ground === "string" && weather.ground.trim()
    ? `Ground ${weather.ground.trim()}`
    : typeof weather?.summary === "string" && weather.summary.trim()
      ? weather.summary.trim()
      : "No operational weather cue exposed";

  return {
    available: !!weather,
    icon: weatherIcon(condition),
    condition,
    temp,
    wind,
    cue: operationalCue,
    forecast: buildForecastRows(forecast),
  };
}

export function summarizeWeatherOverlay(snapshot) {
  const summary = summarizeWeather(snapshot);
  const key = String(summary.condition || "").toLowerCase();

  let tone = "is-unavailable";
  if (summary.available) {
    if (key.includes("storm") || key.includes("rain")) {
      tone = "is-rain";
    } else if (key.includes("fog")) {
      tone = "is-fog";
    } else if (key.includes("cloud") || key.includes("overcast")) {
      tone = "is-overcast";
    } else if (key.includes("clear") || key.includes("fair")) {
      tone = "is-clear";
    } else if (key.includes("wind")) {
      tone = "is-wind";
    } else {
      tone = "is-general";
    }
  }

  return {
    available: summary.available,
    tone,
    title: summary.available ? summary.condition : "Weather unavailable",
    support: summary.available ? summary.cue : "No authoritative weather feed is exposed on the current shell path.",
    meta: [summary.temp, summary.wind].filter(Boolean),
  };
}
