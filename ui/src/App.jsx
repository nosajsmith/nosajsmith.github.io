import React, { useEffect, useMemo, useState } from "react";
import { makeWsRpc } from "./lib/ws_rpc";
import { adaptMapState } from "./lib/scenario_adapter";
import { pickDefaultScenario, summarizeObjectives } from "./lib/demo_briefing.js";
import { nextActionCue } from "./lib/demo_polish.js";
import MapCanvas from "./components/MapCanvas";
import Inspector from "./components/Inspector";
import OobTree from "./components/OobTree";
import LogPanel from "./components/LogPanel";
import "./app.css";

const WS_URL = "ws://127.0.0.1:8766";

export default function App() {
  const ws = useMemo(() => makeWsRpc(WS_URL, { proto: "1.0" }), []);
  const [wsConnected, setWsConnected] = useState(false);

  const [scenarios, setScenarios] = useState([]);
  const [scenarioName, setScenarioName] = useState("");
  const [gameState, setGameState] = useState(null);
  const [mapState, setMapState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [selectedUnitId, setSelectedUnitId] = useState("");
  const [selectedUnit, setSelectedUnit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [orderBusy, setOrderBusy] = useState(false);
  const [errorText, setErrorText] = useState("");

  const adaptedMap = useMemo(() => adaptMapState(mapState), [mapState]);
  const meta = adaptedMap?.meta;
  const units = adaptedMap?.units ?? [];
  const terrain = mapState?.map?.terrain ?? {};
  const objectives = mapState?.objectives ?? [];
  const briefingObjectives = useMemo(() => summarizeObjectives(objectives), [objectives]);
  const playerOob = gameState?.player_oob ?? null;
  const game = gameState?.game ?? null;
  const actionCue = useMemo(() => nextActionCue(game, objectives, selectedUnit), [game, objectives, selectedUnit]);

  function toInspectorUnit(unit) {
    if (!unit || typeof unit !== "object") {
      return null;
    }
    const pos = Array.isArray(unit.position) ? unit.position : [];
    return {
      id: unit.id ?? unit.unit_id ?? unit.name,
      name: unit.name ?? unit.id ?? unit.unit_id ?? "",
      x: unit.x ?? pos[0],
      y: unit.y ?? pos[1],
      raw: unit,
    };
  }

  async function rpc(cmd, payload = {}) {
    const r = await ws.rpc(cmd, payload);
    if (!r?.ok) {
      throw new Error(r?.error?.message ?? `${cmd} failed`);
    }
    return r.payload ?? {};
  }

  async function refreshList() {
    const payload = await rpc("list_scenarios", {});
    const list = payload?.scenarios ?? [];
    setScenarios(list);
    if (!scenarioName && list.length) setScenarioName(pickDefaultScenario(list));
  }

  async function ping() {
    return rpc("ping", {});
  }

  async function refreshActiveState(unitId = selectedUnitId) {
    const [nextGame, nextMap, nextLogs] = await Promise.all([
      rpc("get_game_state", {}),
      rpc("get_map_state", {}),
      rpc("get_logs", {}),
    ]);
    setGameState(nextGame);
    setMapState(nextMap);
    setLogs(nextLogs.logs ?? []);

    if (unitId) {
      try {
        const unitPayload = await rpc("get_unit_state", { unit_id: unitId });
        setSelectedUnit(toInspectorUnit(unitPayload.unit));
      } catch {
        setSelectedUnit(null);
      }
    }
  }

  async function loadScenario(name) {
    if (!name) return;
    setBusy(true);
    setErrorText("");
    try {
      await rpc("load_scenario", { name });
      const startPayload = await rpc("start_game", {});
      setGameState(startPayload);
      setSelectedUnitId("");
      setSelectedUnit(null);
      await refreshActiveState("");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSelectedUnit(unitId) {
    setSelectedUnitId(unitId);
    if (!unitId) {
      setSelectedUnit(null);
      return;
    }
    const payload = await rpc("get_unit_state", { unit_id: unitId });
    setSelectedUnit(toInspectorUnit(payload.unit));
  }

  async function endTurn() {
    setBusy(true);
    setErrorText("");
    try {
      await rpc("end_turn", {});
      await refreshActiveState(selectedUnitId);
    } finally {
      setBusy(false);
    }
  }

  async function issueOrder(kind) {
    if (!selectedUnitId) {
      return;
    }
    const intentByKind = {
      attack: "Probe enemy positions and create local pressure.",
      reposition: "Advance to improve position and tempo.",
      rest: "Recover readiness and reduce fatigue.",
    };
    setOrderBusy(true);
    setErrorText("");
    try {
      await rpc("orders.submit", {
        kind,
        unit_id: selectedUnitId,
        intent: intentByKind[kind] || `Player ordered ${kind}.`,
        eta_hours: 6,
      });
      await refreshActiveState(selectedUnitId);
    } finally {
      setOrderBusy(false);
    }
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
        setErrorText(String(e?.message ?? e));
      }
    })();

    const t = setInterval(() => setWsConnected(ws.isConnected()), 500);
    return () => clearInterval(t);
  }, [ws]);

  useEffect(() => {
    (async () => {
      try {
        if (scenarioName) {
          await loadScenario(scenarioName);
        }
      } catch (e) {
        console.error(e);
        setErrorText(String(e?.message ?? e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioName]);

  return (
    <div className="layout">
      <aside className="panel left">
        <div className="brand">
          <div className="brand-title">Operation: Let&apos;s Go</div>
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
            <button className="btn" onClick={() => refreshList().catch((e) => setErrorText(String(e?.message ?? e)))}>Refresh</button>
            <button className="btn" onClick={() => loadScenario(scenarioName).catch((e) => setErrorText(String(e?.message ?? e)))} disabled={busy}>Start</button>
          </div>

          <div className="row">
            <button className="btn" onClick={() => endTurn().catch((e) => setErrorText(String(e?.message ?? e)))} disabled={busy || !game?.started}>
              {busy ? "Working..." : "End Turn"}
            </button>
            <button className="btn" onClick={() => ping().catch((e) => setErrorText(String(e?.message ?? e)))}>Ping</button>
          </div>

          <div className="hint">
            {game?.scenario_name ? `Scenario: ${game.scenario_name}` : "No scenario loaded."}
            <br />
            {game?.started ? `Time ${game.time_now ?? 0}h • Status ${game.campaign_status ?? "unknown"}` : "Game not started."}
          </div>
          <div className="hint">
            Map: {meta?.width ?? "?"}×{meta?.height ?? "?"} • Units: {units.length}
            <br />
            Pending reports: {game?.pending_reports ?? 0} • AI: {game?.ai_enabled ? "On" : "Off"}
          </div>
          {errorText ? <div className="error-banner">{errorText}</div> : null}
        </div>

        <div className="section">
          <div className="label">Scenario Brief</div>
          <div className="briefing-card">
            <div className="briefing-title">{game?.scenario_name ?? (scenarioName || "Scenario")}</div>
            <div className="briefing-line">
              <span>Time remaining</span>
              <strong>{game?.time_remaining ?? "?"}h</strong>
            </div>
            <div className="briefing-line">
              <span>Score</span>
              <strong>A {game?.score_by_side?.ALLIED ?? 0} / X {game?.score_by_side?.AXIS ?? 0}</strong>
            </div>
            <div className="briefing-line">
              <span>Win target</span>
              <strong>{game?.win_score ?? "?"}</strong>
            </div>
            <div className="briefing-objectives">
              {briefingObjectives.length ? (
                briefingObjectives.map((objective) => (
                  <div className="briefing-objective" key={objective.id || objective.label}>
                    <span className={"briefing-dot " + (objective.controlled ? "held" : "open")} />
                    <span>{objective.label}</span>
                  </div>
                ))
              ) : (
                <div className="inspector-muted">Objectives will appear after game start.</div>
              )}
            </div>
          </div>
        </div>

        <div className="section">
          <div className="label">Next Step</div>
          <div className="briefing-card next-step-card">
            <div className="next-step-text">{actionCue}</div>
          </div>
        </div>

        <div className="section">
          <div className="label">Order of Battle</div>
          <OobTree oob={playerOob} />
        </div>
      </aside>

      <main className="center game-shell">
        <div className="game-topbar">
          <div className="topbar-block">
            <div className="topbar-label">Turn Status</div>
            <div className="topbar-value">{game?.campaign_status ?? "not ready"}</div>
          </div>
          <div className="topbar-block">
            <div className="topbar-label">Time</div>
            <div className="topbar-value">{game?.time_now ?? 0}h</div>
          </div>
          <div className="topbar-block">
            <div className="topbar-label">Score</div>
            <div className="topbar-value">
              A {game?.score_by_side?.ALLIED ?? 0} / X {game?.score_by_side?.AXIS ?? 0}
            </div>
          </div>
        </div>
        <MapCanvas
          meta={meta}
          terrain={terrain}
          objectives={objectives}
          units={units}
          selectedUnit={selectedUnit}
          onSelectUnit={(u) => refreshSelectedUnit(u.id).catch((e) => setErrorText(String(e?.message ?? e)))}
          onClearSelection={() => refreshSelectedUnit("").catch(() => {})}
        />
      </main>

      <aside className="panel right">
        <Inspector unit={selectedUnit} onIssueOrder={(kind) => issueOrder(kind).catch((e) => setErrorText(String(e?.message ?? e)))} orderBusy={orderBusy} />
        <div className="inspector-block">
          <LogPanel logs={logs} />
        </div>
      </aside>
    </div>
  );
}
