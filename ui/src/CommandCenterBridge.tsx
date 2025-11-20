import React from "react";
import { makeBridge } from "./ws_helper";

type BridgeMsg =
  | { type: "snapshot"; data: any }
  | { type: "movement_report"; data: { movements: any[] } }
  | { type: "combat_report"; data: { combats: any[] } }
  | { type: "turn_advanced"; data: { turn: number } }
  | { type: "scenario_list"; data: { files: string[] } }
  | { type: "scenario_loaded"; data: { name: string } }
  | { type: "scenario_saved"; data: { name: string; path: string } }
  | { type: "error"; data: { code: string; message: string; details?: any } }
  | { type: string; data: any };

type Props = {
  url?: string; token?: string;
  onMsg: (m: BridgeMsg) => void;
  onReady?: (send: (obj:any)=>void) => void; // 👈 NEW
};

export default function CommandCenterBridge({ url="ws://localhost:8766", token, onMsg, onReady }: Props) {
  const ref = React.useRef<{send:(o:any)=>void, close:()=>void} | null>(null);

  React.useEffect(() => {
    const bridge = makeBridge(url, {
      token,
      onOpen: () => {},
      onMessage: (m:any) => onMsg(m as BridgeMsg),
      onClose: () => {},
    });
    ref.current = bridge;
    onReady?.((obj:any) => bridge.send(obj)); // 👈 expose sender upward
    return () => bridge.close();
  }, [url, token, onMsg, onReady]);

  return (
    <div className="text-xs text-gray-500 space-x-2">
      <button className="px-2 py-1 border rounded" onClick={() => ref.current?.send({cmd:"auto_execute"})}>Auto Execute</button>
      <button className="px-2 py-1 border rounded" onClick={() => ref.current?.send({cmd:"next_turn"})}>Next Turn</button>
    </div>
  );
}
