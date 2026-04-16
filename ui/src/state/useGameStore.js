import { useEffect, useMemo, useState } from "react";
import { makeBridge } from "../lib/bridge";
import { inferScenarioPresentation } from "../lib/view_snapshot.js";

function unwrapBridgePayload(response) {
  let current = response;

  for (let depth = 0; depth < 4; depth += 1) {
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      return current;
    }
    if (current.status === "error") {
      throw new Error(current?.error?.message || "bridge rpc failed");
    }
    if (current.type === "error") {
      throw new Error(current?.data?.message || "bridge rpc failed");
    }
    if (current.ok && Object.prototype.hasOwnProperty.call(current, "payload")) {
      current = current.payload;
      continue;
    }
    if (current.status === "ok" && Object.prototype.hasOwnProperty.call(current, "data")) {
      current = current.data;
      continue;
    }
    if (current.type && Object.prototype.hasOwnProperty.call(current, "data")) {
      current = current.data;
      continue;
    }
    return current;
  }

  return current;
}

function inferScenarioList(payload) {
  if (Array.isArray(payload?.scenarios)) {
    return payload.scenarios.map((item) => String(item));
  }
  if (Array.isArray(payload?.files)) {
    return payload.files.map((item) => String(item));
  }

  const scenario = payload?.scenario;
  const scenarioId = typeof scenario?.id === "string" && scenario.id.trim() ? scenario.id.trim() : "";
  if (scenarioId) {
    return [scenarioId];
  }

  const scenarioName = typeof scenario?.name === "string" && scenario.name.trim() ? scenario.name.trim() : "";
  if (scenarioName) {
    return [scenarioName];
  }

  const inferred = inferScenarioPresentation(payload);
  return inferred?.scenarioLabel ? [String(inferred.scenarioLabel)] : [];
}

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
    return unwrapBridgePayload(r);
  }

  async function refreshScenarioList() {
    setError(null);
    const r = await bridge.rpc("list_scenarios", {}, "ui-list");
    const payload = unwrapBridgePayload(r) || {};
    const nextScenarioList = inferScenarioList(payload);
    setScenarioList(nextScenarioList);
    return nextScenarioList;
  }

  async function loadScenario(name) {
    setError(null);
    setScenarioName(name);
    setSelectedUnitId(null);

    const r = await bridge.rpc("load_scenario", { name }, "ui-load");
    const payload = unwrapBridgePayload(r) || {};

    // Expect data.scenario to be a plain JSON object (dict)
    const sc = payload?.scenario || payload || null;
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
