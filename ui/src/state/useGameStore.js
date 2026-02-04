import { useEffect, useMemo, useState } from "react";
import { makeBridge } from "../lib/bridge";

export function useGameStore() {
  const bridge = useMemo(() => makeBridge(), []);

  const [connected, setConnected] = useState(false);
  const [scenarioList, setScenarioList] = useState([]);
  const [scenarioName, setScenarioName] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [error, setError] = useState(null);

  // connection heartbeat
  useEffect(() => {
    const t = setInterval(() => setConnected(bridge.ready()), 250);
    return () => clearInterval(t);
  }, [bridge]);

  async function ping() {
    setError(null);
    const r = await bridge.rpc("ping", {}, "ui-ping");
    if (r.status !== "ok") throw new Error(r?.error?.message || "ping failed");
    return r;
  }

  async function refreshScenarioList() {
    setError(null);
    const r = await bridge.rpc("list_scenarios", {}, "ui-list");
    if (r.status !== "ok") throw new Error(r?.error?.message || "list_scenarios failed");
    setScenarioList(r.data?.scenarios || []);
    return r.data?.scenarios || [];
  }

  async function loadScenario(name) {
    setError(null);
    setScenarioName(name);
    setSelectedUnitId(null);

    const r = await bridge.rpc("load_scenario", { name }, "ui-load");
    if (r.status !== "ok") throw new Error(r?.error?.message || "load_scenario failed");

    // Expect data.scenario to be a plain JSON object (dict)
    const sc = r.data?.scenario || null;
    setScenario(sc);
    return sc;
  }

  function selectUnit(id) {
    setSelectedUnitId(id);
  }

  const selectedUnit =
    scenario?.units?.find(u => u.id === selectedUnitId) || null;

  return {
    bridge,
    connected,
    scenarioList,
    scenarioName,
    scenario,
    selectedUnitId,
    selectedUnit,
    error,

    actions: {
      ping,
      refreshScenarioList,
      loadScenario,
      selectUnit,
      setError,
    }
  };
}
