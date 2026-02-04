import React, { useEffect, useMemo, useState } from "react";
import { makeWsRpc } from "./lib/ws_rpc";
import { adaptScenario } from "./lib/scenario_adapter";
import MapCanvas from "./components/MapCanvas";
import Inspector from "./components/Inspector";
import "./app.css";

const WS_URL = "ws://127.0.0.1:8766";

export default function App() {
  const ws = useMemo(() => makeWsRpc(WS_URL, { proto: "1.0" }), []);
  const [wsConnected, setWsConnected] = useState(false);

  const [scenarios, setScenarios] = useState([]);
  const [scenarioName, setScenarioName] = useState("");
  const [scenarioData, setScenarioData] = useState(null);

  const [selectedUnit, setSelectedUnit] = useState(null);
  const [hoverUnit, setHoverUnit] = useState(null);

  const [snapToHex, setSnapToHex] = useState(true);

  const adapted = useMemo(() => adaptScenario(scenarioData), [scenarioData]);
  const meta = adapted?.meta;
  const units = adapted?.units ?? [];

  React.useEffect(() => { console.log("MWE units:", units); }, [units]);

  async function refreshList() {
    const r = await ws.rpc("list_scenarios", {});
    if (r.status !== "ok") throw new Error(r.error?.message ?? "list_scenarios failed");
    const list = r.data?.scenarios ?? [];
    setScenarios(list);
    if (!scenarioName && list.length) setScenarioName(list[0]);
  }

  async function ping() {
    const r = await ws.rpc("ping", {});
    if (r.status !== "ok") throw new Error(r.error?.message ?? "ping failed");
    return r;
  }

  async function loadScenario(name) {
    if (!name) return;
    const r = await ws.rpc("load_scenario", { name });
    if (r.status !== "ok") throw new Error(r.error?.message ?? "load_scenario failed");
    setScenarioData(r.data?.scenario ?? r.data);
    setSelectedUnit(null);
    setHoverUnit(null);
  }

  useEffect(() => {
    (async () => {
      try {
        await ws.connect();
        setWsConnected(true);
        await refreshList();
      } catch (e) {
        console.error(e);
        setWsConnected(false);
      }
    })();

    const t = setInterval(() => setWsConnected(ws.isConnected()), 500);
    return () => clearInterval(t);
  }, [ws]);

  useEffect(() => {
    (async () => {
      try { await loadScenario(scenarioName); } catch (e) { console.error(e); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioName]);

  return (
    <div className="layout">
      <aside className="panel left">
        <div className="brand">
          <div className="brand-title">MWE UI</div>
          <div className={"pill " + (wsConnected ? "ok" : "bad")}>
            {wsConnected ? "WS: connected" : "WS: offline"}
          </div>
        </div>

        <div className="section">
          <div className="label">Scenario</div>
          <select className="select" value={scenarioName} onChange={(e) => setScenarioName(e.target.value)}>
            {scenarios.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>

          <div className="row">
            <button className="btn" onClick={() => refreshList().catch(console.error)}>Refresh</button>
            <button className="btn" onClick={() => ping().catch(console.error)}>Ping</button>
          </div>

          <label className="toggle">
            <input type="checkbox" checked={snapToHex} onChange={(e) => setSnapToHex(e.target.checked)} />
            <span>Snap preview to hex</span>
          </label>

          <div className="hint">
            Phase 6.9: real hex grid + axial math + snap preview.
            <br />
            Hex size: {meta?.hexSize} • World: {meta?.width}×{meta?.height}
          </div>
            <div className="hint">Units in UI: {units.length}</div>
        </div>
      </aside>

      <main className="center">
        <MapCanvas
          meta={meta}
          units={units}
          selectedUnit={selectedUnit}
          hoverUnit={hoverUnit}
          onHoverUnit={setHoverUnit}
          onSelectUnit={(u) => setSelectedUnit(u)}
          onClearSelection={() => setSelectedUnit(null)}
          snapToHex={snapToHex}
        />
      </main>

      <aside className="panel right">
        <Inspector unit={selectedUnit} />
      </aside>
    </div>
  );
}
