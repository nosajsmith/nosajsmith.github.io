import { useMemo, useState } from "react";

type InfrastructureGameplaySceneProps = {
  theaterId: string | null;
};

type ScenarioId = "crossings" | "roads" | "rail" | "anchors" | "interdiction";

const SCENARIOS: Record<ScenarioId, {
  title: string;
  status: string;
  note: string;
  routes: Array<{
    id: string;
    label: string;
    routeClass: string;
    status: string;
    effective: string;
    corridor: string;
    anchors: string;
    factors: string[];
  }>;
}> = {
  crossings: {
    title: "Crossing States",
    status: "Bridge / Engineer",
    note: "Crossings now gate both mobility and throughput. A destroyed bridge cuts the route, a damaged bridge constrains it, and a temporary crossing restores passage at reduced capacity and higher vulnerability.",
    routes: [
      {
        id: "crossing-intact",
        label: "Main Bridge",
        routeClass: "Primary Road",
        status: "Active",
        effective: "80 / 80",
        corridor: "92",
        anchors: "Depot -> Depot",
        factors: ["Intact bridge", "No route damage", "No interdiction", "Full throughput"],
      },
      {
        id: "crossing-temp",
        label: "Pontoon Bypass",
        routeClass: "Ferry / Temporary",
        status: "Degraded",
        effective: "41 / 80",
        corridor: "46",
        anchors: "Depot -> Forward Dump",
        factors: ["Temporary crossing", "Reduced throughput", "Engineer-emplaced", "Higher vulnerability"],
      },
      {
        id: "crossing-cut",
        label: "Demolished Span",
        routeClass: "Primary Road",
        status: "Cut",
        effective: "0 / 80",
        corridor: "0",
        anchors: "Depot -> Depot",
        factors: ["Destroyed bridge", "Movement blocked", "Supply cut", "Engineer repair required"],
      },
    ],
  },
  roads: {
    title: "Road Corridor",
    status: "Movement / Supply",
    note: "Primary and secondary roads keep tempo up, but they never reach rail capacity. The route cards expose why a corridor is cheap to traverse yet still only moderately effective for sustained supply.",
    routes: [
      {
        id: "road-main",
        label: "Main Highway",
        routeClass: "Primary Road",
        status: "Active",
        effective: "80 / 80",
        corridor: "94",
        anchors: "Depot -> Depot",
        factors: ["Primary-road capacity", "Road movement bias", "No interdiction", "Clear crossings"],
      },
      {
        id: "road-secondary",
        label: "Secondary Spur",
        routeClass: "Secondary Road",
        status: "Degraded",
        effective: "39 / 60",
        corridor: "52",
        anchors: "Depot -> Forward Dump",
        factors: ["Secondary-road cap", "Light air harassment", "One strained bridge", "Lower anchor importance"],
      },
    ],
  },
  rail: {
    title: "Rail Backbone",
    status: "High Throughput",
    note: "Rail routes are intentionally distinct from roads: they carry more supply, score higher as operational corridors, and are faster in their native movement mode, but they also become more brittle under concentrated interdiction.",
    routes: [
      {
        id: "rail-main",
        label: "Main Rail Line",
        routeClass: "Rail",
        status: "Active",
        effective: "132 / 80",
        corridor: "128",
        anchors: "Off-map -> Depot",
        factors: ["Rail capacity multiplier", "Off-map anchor", "No crossing limit", "Clear interdiction state"],
      },
      {
        id: "rail-branch",
        label: "Rail Branch",
        routeClass: "Rail",
        status: "Critical",
        effective: "34 / 70",
        corridor: "48",
        anchors: "Depot -> Depot",
        factors: ["Rail advantage", "Severe interdiction", "Bridge bottleneck", "Damage accumulation"],
      },
    ],
  },
  anchors: {
    title: "Supply Anchors",
    status: "Ports / Off-map",
    note: "Ports, harbors, and off-map links now act as explicit supply anchors. They do not replace the route itself, but they raise throughput and corridor importance when scenarios use them as entry points.",
    routes: [
      {
        id: "anchor-port",
        label: "Harbor Corridor",
        routeClass: "Port Link",
        status: "Active",
        effective: "86 / 70",
        corridor: "101",
        anchors: "Port -> Depot",
        factors: ["Port anchor bonus", "Port-link class", "No disruption", "Short internal line"],
      },
      {
        id: "anchor-offmap",
        label: "Off-map Main",
        routeClass: "Primary Road",
        status: "Active",
        effective: "77 / 60",
        corridor: "109",
        anchors: "Off-map -> Depot",
        factors: ["Off-map anchor bonus", "Primary-road class", "High strategic importance", "Clear crossing state"],
      },
    ],
  },
  interdiction: {
    title: "Interdiction",
    status: "Disruption",
    note: "Route interdiction is no longer just raw damage. Air, artillery, or system actions create a temporary interdiction state that pushes capacity down immediately, then decays or gets repaired over time.",
    routes: [
      {
        id: "int-main",
        label: "Main Road",
        routeClass: "Primary Road",
        status: "Interdicted",
        effective: "41 / 90",
        corridor: "44",
        anchors: "Depot -> Depot",
        factors: ["Artillery interdiction", "Damage carry-over", "Minor crossing limit", "Corridor penalty"],
      },
      {
        id: "int-cut",
        label: "Rail Bridge",
        routeClass: "Rail",
        status: "Cut",
        effective: "0 / 80",
        corridor: "0",
        anchors: "Port -> Depot",
        factors: ["Severed interdiction state", "Destroyed bridge", "Rail vulnerability", "No bypass available"],
      },
    ],
  },
};

function InfrastructureSceneSvg({ scenarioId }: { scenarioId: ScenarioId }) {
  if (scenarioId === "crossings") {
    return (
      <svg className="shell-infraqa__svg" viewBox="0 0 320 200" role="img" aria-label="Crossing state and engineer interaction preview">
        <rect className="shell-infraqa__field" x="0" y="0" width="320" height="200" />
        <path className="shell-infraqa__route is-road" d="M22 68 C72 76 118 88 162 102 S240 132 298 156" />
        <path className="shell-infraqa__route is-road is-temporary" d="M22 148 C72 138 120 126 168 108 S246 84 298 60" />
        <path className="shell-infraqa__river" d="M116 26 C138 58 144 98 146 170" />
        <path className="shell-infraqa__river is-major" d="M132 20 C154 56 160 98 162 176" />
        <circle className="shell-infraqa__anchor is-depot" cx="22" cy="68" r="8" />
        <circle className="shell-infraqa__anchor is-depot" cx="298" cy="156" r="8" />
        <circle className="shell-infraqa__anchor is-depot" cx="22" cy="148" r="8" />
        <circle className="shell-infraqa__anchor is-depot" cx="298" cy="60" r="8" />
        <circle className="shell-infraqa__crossing-node is-intact" cx="154" cy="98" r="7" />
        <circle className="shell-infraqa__crossing-node is-temporary" cx="146" cy="114" r="7" />
        <line className="shell-infraqa__cutline" x1="148" y1="88" x2="168" y2="104" />
        <line className="shell-infraqa__cutline" x1="168" y1="88" x2="148" y2="104" />
        <text className="shell-infraqa__label" x="92" y="48">DESTROYED</text>
        <text className="shell-infraqa__label is-good" x="170" y="122">PONTOON</text>
        <text className="shell-infraqa__label" x="192" y="84">INTACT</text>
      </svg>
    );
  }

  if (scenarioId === "rail") {
    return (
      <svg className="shell-infraqa__svg" viewBox="0 0 320 200" role="img" aria-label="Rail and road throughput preview">
        <rect className="shell-infraqa__field" x="0" y="0" width="320" height="200" />
        <path className="shell-infraqa__route is-road" d="M22 150 C72 138 114 126 162 112 S236 88 298 62" />
        <path className="shell-infraqa__route is-rail" d="M18 54 C82 62 138 74 196 92 S264 122 302 156" />
        <circle className="shell-infraqa__anchor is-offmap" cx="18" cy="54" r="10" />
        <circle className="shell-infraqa__anchor is-depot" cx="302" cy="156" r="8" />
        <circle className="shell-infraqa__anchor is-depot" cx="298" cy="62" r="8" />
        <text className="shell-infraqa__label" x="34" y="40">OFF-MAP</text>
        <text className="shell-infraqa__label" x="244" y="54">ROAD</text>
        <text className="shell-infraqa__label" x="220" y="140">RAIL</text>
      </svg>
    );
  }

  if (scenarioId === "anchors") {
    return (
      <svg className="shell-infraqa__svg" viewBox="0 0 320 200" role="img" aria-label="Port and off-map supply anchor preview">
        <rect className="shell-infraqa__field" x="0" y="0" width="320" height="200" />
        <path className="shell-infraqa__route is-port" d="M42 152 C84 136 128 124 176 110 S252 90 296 78" />
        <path className="shell-infraqa__route is-road" d="M32 46 C82 56 126 74 176 96 S248 132 292 154" />
        <circle className="shell-infraqa__anchor is-port" cx="42" cy="152" r="10" />
        <circle className="shell-infraqa__anchor is-offmap" cx="32" cy="46" r="10" />
        <circle className="shell-infraqa__anchor is-depot" cx="296" cy="78" r="8" />
        <circle className="shell-infraqa__anchor is-depot" cx="292" cy="154" r="8" />
        <text className="shell-infraqa__label" x="18" y="170">PORT</text>
        <text className="shell-infraqa__label" x="16" y="28">OFF-MAP</text>
        <text className="shell-infraqa__label" x="216" y="72">DEPOT</text>
      </svg>
    );
  }

  if (scenarioId === "interdiction") {
    return (
      <svg className="shell-infraqa__svg" viewBox="0 0 320 200" role="img" aria-label="Interdicted infrastructure preview">
        <rect className="shell-infraqa__field" x="0" y="0" width="320" height="200" />
        <path className="shell-infraqa__route is-road" d="M28 138 C74 128 126 118 174 110 S248 92 298 72" />
        <path className="shell-infraqa__route is-rail is-cut" d="M24 62 C84 70 136 84 190 102 S258 130 302 152" />
        <circle className="shell-infraqa__interdict is-artillery" cx="166" cy="110" r="18" />
        <circle className="shell-infraqa__interdict is-air" cx="220" cy="118" r="24" />
        <line className="shell-infraqa__cutline" x1="244" y1="126" x2="264" y2="142" />
        <line className="shell-infraqa__cutline" x1="264" y1="126" x2="244" y2="142" />
        <text className="shell-infraqa__label" x="144" y="84">ARTY</text>
        <text className="shell-infraqa__label" x="204" y="88">AIR</text>
        <text className="shell-infraqa__label" x="234" y="162">CUT</text>
      </svg>
    );
  }

  return (
    <svg className="shell-infraqa__svg" viewBox="0 0 320 200" role="img" aria-label="Road infrastructure gameplay preview">
      <rect className="shell-infraqa__field" x="0" y="0" width="320" height="200" />
      <path className="shell-infraqa__route is-road" d="M18 144 C66 134 112 120 154 100 S226 72 302 52" />
      <path className="shell-infraqa__route is-secondary" d="M44 66 C88 82 126 92 160 94" />
      <circle className="shell-infraqa__anchor is-depot" cx="18" cy="144" r="8" />
      <circle className="shell-infraqa__anchor is-depot" cx="302" cy="52" r="8" />
      <circle className="shell-infraqa__interdict is-bridge" cx="170" cy="96" r="12" />
      <text className="shell-infraqa__label" x="30" y="160">DEPOT</text>
      <text className="shell-infraqa__label" x="244" y="44">FORWARD</text>
      <text className="shell-infraqa__label" x="148" y="76">BRIDGE</text>
    </svg>
  );
}

export default function InfrastructureGameplayScene({ theaterId }: InfrastructureGameplaySceneProps) {
  const [open, setOpen] = useState(false);
  const [scenarioId, setScenarioId] = useState<ScenarioId>("crossings");
  const scenario = SCENARIOS[scenarioId];
  const graphic = useMemo(() => <InfrastructureSceneSvg scenarioId={scenarioId} />, [scenarioId]);

  return (
    <div className={"shell-infraqa" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-infraqa__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-infra-qa"
      >
        <span className="shell-map__legend-title">Infrastructure QA</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-infraqa__body" id="shell-infra-qa">
          <div className="shell-infraqa__toolbar" role="group" aria-label="Infrastructure gameplay scenario selection">
            {(["crossings", "roads", "rail", "anchors", "interdiction"] as ScenarioId[]).map((id) => (
              <button
                key={id}
                type="button"
                className={"shell-infraqa__chip" + (scenarioId === id ? " is-active" : "")}
                onClick={() => setScenarioId(id)}
              >
                {SCENARIOS[id].title}
              </button>
            ))}
          </div>

          <div className="shell-infraqa__note">
            These are representative previews of the gameplay route model. Capacity, anchor type, crossing bottlenecks, and interdiction state now combine into one route summary instead of separate hidden systems.
            {theaterId ? ` Current packaged theater: ${theaterId}.` : ""}
          </div>

          <div className="shell-infraqa__layout">
            <div className="shell-infraqa__canvaswrap">{graphic}</div>

            <div className="shell-infraqa__inspect">
              <div className="shell-infraqa__summary">
                <strong>{scenario.title}</strong>
                <span className="shell-infraqa__statuspill">{scenario.status}</span>
              </div>

              <div className="shell-infraqa__note">{scenario.note}</div>

              <div className="shell-infraqa__routegrid">
                {scenario.routes.map((route) => (
                  <div
                    key={route.id}
                    className={
                      "shell-infraqa__routecard"
                      + (route.status === "Cut" ? " is-cut" : "")
                      + (route.status === "Critical" || route.status === "Interdicted" ? " is-degraded" : "")
                    }
                  >
                    <div className="shell-infraqa__routehead">
                      <strong>{route.label}</strong>
                      <span>{route.routeClass}</span>
                    </div>
                    <div className="shell-infraqa__routemeta">
                      <div><strong>Status</strong><span>{route.status}</span></div>
                      <div><strong>Effective</strong><span>{route.effective}</span></div>
                      <div><strong>Corridor</strong><span>{route.corridor}</span></div>
                      <div><strong>Anchors</strong><span>{route.anchors}</span></div>
                    </div>
                    <div className="shell-infraqa__factorrow">
                      {route.factors.map((factor) => (
                        <span key={factor} className="shell-infraqa__factorpill">{factor}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
