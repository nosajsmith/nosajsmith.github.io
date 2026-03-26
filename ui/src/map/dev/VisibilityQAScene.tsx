import { useMemo, useState } from "react";

type VisibilityQASceneProps = {
  theaterId: string | null;
};

type ScenarioId = "ridge" | "advantage" | "concealment" | "operational";
type WeatherPreviewId = "dry" | "rain" | "mud" | "snow" | "frozen_ground" | "fog";
type WeatherVisualVariant = "normal" | "damp" | "churned" | "snow_cover" | "frozen" | "fogged";

const SCENARIOS: Record<ScenarioId, {
  title: string;
  status: string;
  assumptions: string[];
}> = {
  ridge: {
    title: "Ridge Mask",
    status: "Exact LOS",
    assumptions: ["Axial center-line sample", "Elevation + slope obstruction", "Higher ground check", "Selected-interaction fidelity"],
  },
  advantage: {
    title: "High-Ground Observation",
    status: "Exact Spotting",
    assumptions: ["Higher observer elevation", "Exact LOS stays clear", "Observation advantage band", "Shared range-band hooks"],
  },
  concealment: {
    title: "Forest / Urban Concealment",
    status: "Spotting",
    assumptions: ["Target terrain concealment", "Target signature by type", "Range-band difficulty", "Weather / time hooks"],
  },
  operational: {
    title: "Operational Visibility Query",
    status: "Cached Approximation",
    assumptions: ["Cached query key", "LOS proxy seed", "Range penalty", "Stale-intel decay"],
  },
};

const WEATHER_PREVIEWS: Record<WeatherPreviewId, {
  label: string;
  weatherState: string;
  groundState: string;
  visibilityState: string;
  visualVariant: WeatherVisualVariant;
  note: string;
}> = {
  dry: {
    label: "Dry",
    weatherState: "clear",
    groundState: "dry",
    visibilityState: "clear",
    visualVariant: "normal",
    note: "Baseline clear-ground visibility with no extra concealment or range penalty.",
  },
  rain: {
    label: "Rain",
    weatherState: "rain",
    groundState: "wet",
    visibilityState: "reduced",
    visualVariant: "damp",
    note: "Wet haze trims long-range confidence before terrain masking changes the answer.",
  },
  mud: {
    label: "Mud",
    weatherState: "mud",
    groundState: "mud",
    visibilityState: "reduced",
    visualVariant: "churned",
    note: "Churned ground and damp air leave LOS geometry intact but drag spotting certainty down.",
  },
  snow: {
    label: "Snow",
    weatherState: "snow",
    groundState: "snow",
    visibilityState: "reduced",
    visualVariant: "snow_cover",
    note: "Snow cover increases detection difficulty even when the terrain shape remains readable.",
  },
  frozen_ground: {
    label: "Frozen Ground",
    weatherState: "frozen_ground",
    groundState: "frozen_ground",
    visibilityState: "clear",
    visualVariant: "frozen",
    note: "Hard winter conditions restore clear sight more than mud, with frozen-river hooks available to later crossing logic.",
  },
  fog: {
    label: "Fog",
    weatherState: "fog",
    groundState: "wet",
    visibilityState: "fog",
    visualVariant: "fogged",
    note: "Fog cuts the useful spotting band first, so contacts fade before the ridge line becomes the dominant blocker.",
  },
};

function scenarioPresentation(scenarioId: ScenarioId, weatherId: WeatherPreviewId) {
  const weather = WEATHER_PREVIEWS[weatherId];
  if (scenarioId === "advantage") {
    return {
      note: `Clear LOS from higher ground still lowers detection difficulty, but ${weather.note.toLowerCase()}`,
      metrics: [
        { label: "Weather", value: weather.label },
        { label: "High ground", value: weatherId === "fog" ? "Reduced edge" : "Elevated advantage" },
        { label: "Result", value: weatherId === "fog" ? "Visible with low confidence" : "Visible with better confidence" },
      ],
    };
  }
  if (scenarioId === "concealment") {
    return {
      note: `LOS can stay open while dense vegetation or built-up clutter still pushes detection difficulty up. Under ${weather.label.toLowerCase()}, background concealment gets heavier without changing the core terrain hierarchy.`,
      metrics: [
        { label: "Weather", value: weather.label },
        { label: "Open target", value: weatherId === "fog" ? "Medium confidence" : "High confidence" },
        { label: "Forest / urban", value: weatherId === "fog" ? "Drops first" : "Still hardest" },
      ],
    };
  }
  if (scenarioId === "operational") {
    return {
      note: `Operational scans use the baked LOS proxy seed, range, weather, and stale-intel penalties to answer broad visibility questions cheaply. ${weather.note}`,
      metrics: [
        { label: "Weather", value: weather.label },
        { label: "Inner band", value: weatherId === "fog" ? "Medium confidence" : "High confidence" },
        { label: "Outer band", value: weatherId === "fog" ? "Drops first" : weatherId === "snow" || weatherId === "rain" || weatherId === "mud" ? "Low confidence" : "Medium / low" },
      ],
    };
  }
  return {
    note: `Intervening severe slope and rocky prominence block center-to-center sight even though the target is inside nominal range. ${weather.note}`,
    metrics: [
      { label: "Weather", value: weather.label },
      { label: "Range", value: weatherId === "fog" ? "3 hex practical" : "4 hex" },
      { label: "Result", value: weatherId === "fog" ? "Masked before ridge exit" : "Blocked at ridge" },
    ],
  };
}

function RidgeScene({ visualVariant }: { visualVariant: WeatherVisualVariant }) {
  return (
    <svg className="shell-visibilityqa__svg" viewBox="0 0 320 196" role="img" aria-label="Ridge masking line-of-sight preview">
      <rect className="shell-visibilityqa__field" x="0" y="0" width="320" height="196" />
      <rect className={`shell-visibilityqa__weatherwash is-${visualVariant}`} x="0" y="0" width="320" height="196" />
      <path className="shell-visibilityqa__terrain-swell" d="M0 152 C50 144 82 136 118 116 S170 70 194 72 S248 108 320 126 L320 196 L0 196 Z" />
      <path className="shell-visibilityqa__terrain-ridge" d="M126 124 L160 66 L192 124 Z" />
      <line className="shell-visibilityqa__los-line is-clear" x1="48" y1="136" x2="148" y2="92" />
      <line className="shell-visibilityqa__los-line is-blocked" x1="148" y1="92" x2="268" y2="72" />
      <circle className="shell-visibilityqa__observer" cx="48" cy="136" r="7" />
      <circle className="shell-visibilityqa__target" cx="268" cy="72" r="6" />
      <circle className="shell-visibilityqa__blocker" cx="160" cy="92" r="5" />
      <text className="shell-visibilityqa__label" x="34" y="154">OBS</text>
      <text className="shell-visibilityqa__label" x="254" y="58">TGT</text>
      <text className="shell-visibilityqa__annotation" x="132" y="54">RIDGE MASK</text>
      <text className="shell-visibilityqa__annotation is-muted" x="118" y="168">clear segment</text>
      <text className="shell-visibilityqa__annotation is-danger" x="194" y="166">blocked segment</text>
    </svg>
  );
}

function ConcealmentScene({ visualVariant }: { visualVariant: WeatherVisualVariant }) {
  return (
    <svg className="shell-visibilityqa__svg" viewBox="0 0 320 196" role="img" aria-label="Concealment and spotting comparison preview">
      <rect className="shell-visibilityqa__field" x="0" y="0" width="320" height="196" />
      <rect className={`shell-visibilityqa__weatherwash is-${visualVariant}`} x="0" y="0" width="320" height="196" />
      <circle className="shell-visibilityqa__observer" cx="50" cy="108" r="7" />
      <line className="shell-visibilityqa__los-line is-clear" x1="58" y1="106" x2="122" y2="86" />
      <line className="shell-visibilityqa__los-line is-clear is-faint" x1="58" y1="110" x2="194" y2="92" />
      <line className="shell-visibilityqa__los-line is-clear is-faint" x1="58" y1="114" x2="268" y2="108" />
      <circle className="shell-visibilityqa__target is-open" cx="122" cy="86" r="5.5" />
      <g transform="translate(194 92)">
        <circle className="shell-visibilityqa__concealment-ring is-forest" r="18" />
        <circle className="shell-visibilityqa__target is-forest" r="5.5" />
      </g>
      <g transform="translate(268 108)">
        <rect className="shell-visibilityqa__concealment-ring is-urban" x="-18" y="-16" width="36" height="32" rx="4" />
        <circle className="shell-visibilityqa__target is-urban" r="5.5" />
      </g>
      <text className="shell-visibilityqa__label" x="36" y="126">OBS</text>
      <text className="shell-visibilityqa__annotation is-good" x="104" y="68">OPEN / EASY</text>
      <text className="shell-visibilityqa__annotation is-muted" x="164" y="62">FOREST / HARDER</text>
      <text className="shell-visibilityqa__annotation is-muted" x="240" y="148">URBAN / MASKED</text>
    </svg>
  );
}

function AdvantageScene({ visualVariant }: { visualVariant: WeatherVisualVariant }) {
  return (
    <svg className="shell-visibilityqa__svg" viewBox="0 0 320 196" role="img" aria-label="High-ground observation advantage preview">
      <rect className="shell-visibilityqa__field" x="0" y="0" width="320" height="196" />
      <rect className={`shell-visibilityqa__weatherwash is-${visualVariant}`} x="0" y="0" width="320" height="196" />
      <path className="shell-visibilityqa__terrain-swell" d="M0 164 C52 150 100 120 148 82 S230 58 320 74 L320 196 L0 196 Z" />
      <line className="shell-visibilityqa__los-line is-clear" x1="68" y1="78" x2="252" y2="118" />
      <line className="shell-visibilityqa__los-line is-clear is-faint" x1="68" y1="138" x2="252" y2="118" />
      <circle className="shell-visibilityqa__observer" cx="68" cy="78" r="7" />
      <circle className="shell-visibilityqa__observer is-muted" cx="68" cy="138" r="6" />
      <circle className="shell-visibilityqa__target is-open" cx="252" cy="118" r="5.5" />
      <text className="shell-visibilityqa__label" x="52" y="60">OBS+</text>
      <text className="shell-visibilityqa__label is-muted" x="48" y="158">OBS</text>
      <text className="shell-visibilityqa__label" x="238" y="138">TGT</text>
      <text className="shell-visibilityqa__annotation is-good" x="94" y="56">BETTER SCORE</text>
      <text className="shell-visibilityqa__annotation is-muted" x="94" y="168">level-ground baseline</text>
    </svg>
  );
}

function OperationalScene({ visualVariant }: { visualVariant: WeatherVisualVariant }) {
  return (
    <svg className="shell-visibilityqa__svg" viewBox="0 0 320 196" role="img" aria-label="Operational visibility approximation preview">
      <defs>
        <pattern id="visibilityqa-grid" width="30" height="26" patternUnits="userSpaceOnUse">
          <path className="shell-visibilityqa__grid-line" d="M15 0 L30 8.66 V25.98 L15 34.64 L0 25.98 V8.66 Z" />
        </pattern>
      </defs>
      <rect className="shell-visibilityqa__field" x="0" y="0" width="320" height="196" />
      <rect x="0" y="0" width="320" height="196" fill="url(#visibilityqa-grid)" />
      <rect className={`shell-visibilityqa__weatherwash is-${visualVariant}`} x="0" y="0" width="320" height="196" />
      <circle className="shell-visibilityqa__query-band is-high" cx="152" cy="98" r="42" />
      <circle className="shell-visibilityqa__query-band is-medium" cx="152" cy="98" r="68" />
      <circle className="shell-visibilityqa__query-band is-low" cx="152" cy="98" r="92" />
      <circle className="shell-visibilityqa__observer" cx="152" cy="98" r="7" />
      <circle className="shell-visibilityqa__contact is-high" cx="118" cy="82" r="5" />
      <circle className="shell-visibilityqa__contact is-medium" cx="206" cy="88" r="5" />
      <circle className="shell-visibilityqa__contact is-low" cx="238" cy="132" r="5" />
      <circle className="shell-visibilityqa__contact is-faded" cx="86" cy="142" r="5" />
      <text className="shell-visibilityqa__annotation" x="172" y="54">HIGH</text>
      <text className="shell-visibilityqa__annotation is-muted" x="228" y="80">MED</text>
      <text className="shell-visibilityqa__annotation is-muted" x="248" y="142">LOW</text>
      <text className="shell-visibilityqa__annotation is-danger" x="46" y="160">NIGHT / STALE</text>
    </svg>
  );
}

export default function VisibilityQAScene({ theaterId }: VisibilityQASceneProps) {
  const [open, setOpen] = useState(false);
  const [scenarioId, setScenarioId] = useState<ScenarioId>("ridge");
  const [weatherId, setWeatherId] = useState<WeatherPreviewId>("dry");
  const scenario = SCENARIOS[scenarioId];
  const weather = WEATHER_PREVIEWS[weatherId];
  const presentation = useMemo(() => scenarioPresentation(scenarioId, weatherId), [scenarioId, weatherId]);
  const sceneGraphic = useMemo(() => {
    if (scenarioId === "advantage") {
      return <AdvantageScene visualVariant={weather.visualVariant} />;
    }
    if (scenarioId === "concealment") {
      return <ConcealmentScene visualVariant={weather.visualVariant} />;
    }
    if (scenarioId === "operational") {
      return <OperationalScene visualVariant={weather.visualVariant} />;
    }
    return <RidgeScene visualVariant={weather.visualVariant} />;
  }, [scenarioId, weather.visualVariant]);

  return (
    <div className={"shell-visibilityqa" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-visibilityqa__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-visibility-qa"
      >
        <span className="shell-map__legend-title">Visibility QA</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-visibilityqa__body" id="shell-visibility-qa">
          <div className="shell-visibilityqa__toolbar" role="group" aria-label="Visibility QA scenario selection">
            {(["ridge", "advantage", "concealment", "operational"] as ScenarioId[]).map((id) => (
              <button
                key={id}
                type="button"
                className={"shell-visibilityqa__chip" + (scenarioId === id ? " is-active" : "")}
                onClick={() => setScenarioId(id)}
              >
                {SCENARIOS[id].title}
              </button>
            ))}
          </div>

          <div className="shell-visibilityqa__toolbar" role="group" aria-label="Visibility QA weather selection">
            {(["dry", "rain", "mud", "snow", "frozen_ground", "fog"] as WeatherPreviewId[]).map((id) => (
              <button
                key={id}
                type="button"
                className={"shell-visibilityqa__chip" + (weatherId === id ? " is-active" : "")}
                onClick={() => setWeatherId(id)}
              >
                {WEATHER_PREVIEWS[id].label}
              </button>
            ))}
          </div>

          <div className="shell-visibilityqa__note">
            These are representative previews of the gameplay LOS and spotting rules. Exact LOS and cached operational visibility use the same terrain-elevation doctrine, and the weather selector below mirrors the canonical `weather_state` / `ground_state` hooks without requiring a separate scenario fork.
            {theaterId ? ` Current packaged theater: ${theaterId}.` : ""}
          </div>

          <div className="shell-visibilityqa__layout">
            <div className={"shell-visibilityqa__canvaswrap is-" + weather.visualVariant}>{sceneGraphic}</div>

            <div className="shell-visibilityqa__inspect">
              <div className="shell-visibilityqa__summary">
                <strong>{scenario.title}</strong>
                <span className="shell-visibilityqa__statuspill">{scenario.status}</span>
              </div>

              <div className="shell-visibilityqa__section">
                <div className="shell-visibilityqa__metagrid">
                  <div className="shell-visibilityqa__meta">
                    <strong>Weather</strong>
                    <span>{weather.weatherState}</span>
                  </div>
                  <div className="shell-visibilityqa__meta">
                    <strong>Ground</strong>
                    <span>{weather.groundState}</span>
                  </div>
                  <div className="shell-visibilityqa__meta">
                    <strong>Visibility</strong>
                    <span>{weather.visibilityState}</span>
                  </div>
                </div>
              </div>

              <div className="shell-visibilityqa__section">
                <div className="shell-visibilityqa__note">{presentation.note}</div>
                <div className="shell-visibilityqa__metagrid">
                  {presentation.metrics.map((metric) => (
                    <div key={metric.label} className="shell-visibilityqa__meta">
                      <strong>{metric.label}</strong>
                      <span>{metric.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="shell-visibilityqa__section">
                <div className="shell-visibilityqa__summary">
                  <strong>Assumptions</strong>
                </div>
                <div className="shell-visibilityqa__chiprow">
                  {scenario.assumptions.map((assumption) => (
                    <span key={assumption} className="shell-visibilityqa__chip is-static">{assumption}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
