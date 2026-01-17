import { useEffect, useMemo, useState } from "react";
import { useBridge } from "./hooks/useBridge";

function pickScenarioFromResp(resp) {
  // Our convention: resp.data.scenario is best
  if (resp?.data?.scenario && typeof resp.data.scenario === "object") return resp.data.scenario;

  // fallback: some versions might return scenario as the whole data
  if (resp?.data && typeof resp.data === "object" && (resp.data.units || resp.data.name || resp.data.id)) {
    return resp.data;
  }

  return null;
}

export default function App() {
  const { status, lastError, log, api } = useBridge();

  const [scenarios, setScenarios] = useState([]);
  const [selected, setSelected] = useState(null);         // filename
  const [loadedScenario, setLoadedScenario] = useState(null); // object
  const [uiError, setUiError] = useState(null);
  const [busy, setBusy] = useState(false);

  const unitCount = useMemo(() => {
    const u = loadedScenario?.units;
    return Array.isArray(u) ? u.length : 0;
  }, [loadedScenario]);

  useEffect(() => {
    setUiError(null);
    if (status !== "connected") return;

    api.listScenarios()
      .then((r) => {
        if (r.status !== "ok") {
          setUiError(`list_scenarios failed: ${JSON.stringify(r)}`);
          return;
        }
        const list = r.data?.scenarios || [];
        setScenarios(list);
        // auto-select first item
        if (!selected && list.length) setSelected(list[0]);
      })
      .catch((e) => setUiError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const doLoad = async () => {
    if (!selected) return;
    setBusy(true);
    setUiError(null);
    try {
      const r = await api.send("load_scenario", { name: selected }, { id: "ui-load", timeoutMs: 4000 });
      if (r.status !== "ok") {
        setLoadedScenario(null);
        setUiError(`load_scenario failed: ${JSON.stringify(r)}`);
        return;
      }
      const scen = pickScenarioFromResp(r);
      if (!scen) {
        setLoadedScenario(null);
        setUiError(`load_scenario returned ok but no scenario payload: ${JSON.stringify(r)}`);
        return;
      }
      setLoadedScenario(scen);
    } catch (e) {
      setLoadedScenario(null);
      setUiError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif", maxWidth: 1100 }}>
      <h1 style={{ marginTop: 0 }}>MWE — Phase 6 UI</h1>

      <p>
        <b>Bridge status:</b> {status}
        {lastError ? <span style={{ marginLeft: 10 }}>( {lastError} )</span> : null}
      </p>

      {uiError ? (
        <div style={{ padding: 10, border: "1px solid #c00", color: "#c00", marginBottom: 12 }}>
          <b>UI Error:</b> {uiError}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        {/* LEFT: scenario list */}
        <div style={{ minWidth: 320 }}>
          <h2 style={{ marginTop: 0 }}>Scenarios</h2>

          <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <button onClick={() => api.ping().catch(() => {})} disabled={status !== "connected"}>
              Ping
            </button>

            <button onClick={doLoad} disabled={status !== "connected" || busy || !selected}>
              {busy ? "Loading..." : "Load"}
            </button>
          </div>

          <ul style={{ listStyle: "none", paddingLeft: 0, margin: 0 }}>
            {scenarios.map((s) => (
              <li key={s} style={{ marginBottom: 6 }}>
                <button
                  onClick={() => setSelected(s)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "6px 10px",
                    border: "1px solid #333",
                    background: selected === s ? "#222" : "#111",
                    color: "#eee",
                    cursor: "pointer",
                  }}
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* RIGHT: loaded scenario */}
        <div style={{ flex: 1 }}>
          <h2 style={{ marginTop: 0 }}>Loaded Scenario</h2>

          {loadedScenario ? (
            <>
              <p style={{ marginTop: 0 }}>
                <b>Name:</b> {loadedScenario.name || loadedScenario.title || "(unnamed)"}{" "}
                <span style={{ opacity: 0.8 }}>—</span>{" "}
                <b>Units:</b> {unitCount}
              </p>

              <details open>
                <summary>Raw JSON</summary>
                <pre style={{ background: "#111", color: "#0f0", padding: 10, overflow: "auto" }}>
                  {JSON.stringify(loadedScenario, null, 2)}
                </pre>
              </details>
            </>
          ) : (
            <p style={{ opacity: 0.8 }}>Nothing loaded yet. Select a scenario and click “Load”.</p>
          )}

          <h2>Last Messages</h2>
          <pre style={{ background: "#111", color: "#0f0", padding: 10, overflow: "auto" }}>
            {JSON.stringify(log.slice(-5), null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
