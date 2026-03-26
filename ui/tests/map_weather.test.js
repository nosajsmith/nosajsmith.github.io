import test from "node:test";
import assert from "node:assert/strict";

import { summarizeWeather, summarizeWeatherOverlay } from "../src/components/shell/map_weather.js";

test("weather summary exposes explicit unavailable state without inventing values", () => {
  const summary = summarizeWeather({});

  assert.equal(summary.available, false);
  assert.equal(summary.condition, "Weather unavailable");
  assert.equal(summary.temp, "N/A");
  assert.equal(summary.wind, "Wind unavailable");
  assert.equal(summary.forecast.length, 4);
  assert.equal(summary.forecast[0].support, "Authoritative forecast unavailable");
});

test("weather summary uses authoritative weather fields when present", () => {
  const summary = summarizeWeather({
    weather: {
      condition: "Overcast",
      temp_c: 12,
      wind_kph: 18,
      ground: "mud",
      forecast: [
        { id: "f1", time: 0, condition: "Overcast", temp_c: 12, wind_kph: 18, visibility: "limited" },
      ],
    },
  });

  assert.equal(summary.available, true);
  assert.equal(summary.icon, "OC");
  assert.equal(summary.temp, "12°C");
  assert.equal(summary.wind, "18 kph");
  assert.equal(summary.cue, "Ground mud");
  assert.equal(summary.forecast[0].support, "Visibility limited");
});

test("weather overlay summary stays truthful for available and unavailable weather", () => {
  const unavailable = summarizeWeatherOverlay({});
  const available = summarizeWeatherOverlay({
    weather: {
      condition: "Overcast",
      temp_c: 12,
      wind_kph: 18,
      ground: "mud",
    },
  });

  assert.equal(unavailable.available, false);
  assert.equal(unavailable.tone, "is-unavailable");
  assert.match(unavailable.support, /not exposed/);
  assert.equal(available.available, true);
  assert.equal(available.tone, "is-overcast");
  assert.equal(available.title, "Overcast");
  assert.deepEqual(available.meta, ["12°C", "18 kph"]);
});
