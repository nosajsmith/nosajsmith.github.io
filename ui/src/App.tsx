import React from "react";
import CommandCenterBridge from "./CommandCenterBridge";
import KPICards from "./components/KPICards";
import MapOverlay from "./components/MapOverlay";
import CombatLog from "./components/CombatLog";
import ScenarioPanel from "./components/ScenarioPanel";

type Snapshot = { engine:any; blue:{ units:any[]; objectives:[number,number][]; }; red:{ units:any[] } };

export default function App() {
  const [snapshot, setSnapshot] = React.useState<Snapshot|null>(null);
  const [lastMoveReport, setLastMoveReport] = React.useState<any>({ movements: [] });
  const [combats, setCombats] = React.useState<any[]>([]);
  const [status, setStatus] = React.useState<string>("Connecting…");
  const [scenarioFiles, setScenarioFiles] = React.useState<string[]>([]);
  const senderRef = React.useRef<((o:any)=>void) | null>(null);

  const onMsg = React.useCallback((m:any) => {
    switch (m.type) {
      case "snapshot":
        setSnapshot(m.data); setStatus("Live"); break;
      case "movement_report":
        setLastMoveReport(m.data); break;
      case "combat_report":
        setCombats(m.data.combats || []); break;
      case "turn_advanced":
        setSnapshot((s:any) => s ? ({...s, engine:{...s.engine, clock:{...s.engine.clock, turn_number: m.data.turn}}}) : s); break;
      case "scenario_list":
        setScenarioFiles(m.data.files || []); break;
      case "scenario_loaded":
        setStatus(`Loaded: ${m.data.name}`); break;
      case "scenario_saved":
        setStatus(`Saved: ${m.data.name}`); break;
      case "error":
        setStatus(`Error: ${m.data?.message || m.data?.code}`); break;
      default: break;
    }
  }, []);

  const onReady = React.useCallback((send:(o:any)=>void) => { senderRef.current = send; }, []);

  const refreshList = React.useCallback(() => {
    senderRef.current?.({ cmd: "list_scenarios" });
  }, []);
  const loadScenario = React.useCallback((name:string) => {
    const fname = name.endsWith(".json") ? name : `${name}.json`;
    senderRef.current?.({ cmd: "load_scenario", name: fname });
  }, []);
  const saveScenario = React.useCallback((name:string) => {
    senderRef.current?.({ cmd: "save_scenario", name });
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">MWE Command Center</h1>
        <div className={`text-xs ${status.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>{status}</div>
      </div>

      <CommandCenterBridge onMsg={onMsg} onReady={onReady} />

      <KPICards kpis={snapshot?.engine?.kpis} clock={snapshot?.engine?.clock} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <MapOverlay
            blueUnits={snapshot?.blue?.units}
            redUnits={snapshot?.red?.units}
            objectives={snapshot?.blue?.objectives as any || []}
            lastMovements={lastMoveReport?.movements || []}
          />
        </div>
        <div className="space-y-4">
          <div className="border rounded-xl p-3 bg-slate-900">
            <div className="text-sm font-semibold mb-2">Combat Log</div>
            <CombatLog combats={combats} />
          </div>
          <ScenarioPanel
            send={senderRef.current ?? undefined}
            files={scenarioFiles}
            onRefresh={refreshList}
            onLoad={loadScenario}
            onSave={saveScenario}
          />
        </div>
      </div>
    </div>
  );
}
