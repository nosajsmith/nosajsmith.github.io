import { useEffect, useMemo, useRef, useState } from "react";
import { WS_URL_DEFAULT, makeReq, safeJsonParse } from "../lib/bridge";

/**
 * Bridge connection + lightweight RPC.
 * - Auto-connects
 * - Tracks status
 * - Captures message log
 * - Provides `send(cmd,args)` + convenience `listScenarios()`
 */
export function useBridge(opts = {}) {
  const wsUrl = opts.wsUrl || WS_URL_DEFAULT;

  const wsRef = useRef(null);
  const pendingRef = useRef(new Map()); // id -> {resolve,reject,timeout}
  const [status, setStatus] = useState("disconnected"); // disconnected|connecting|connected|error
  const [lastError, setLastError] = useState(null);
  const [log, setLog] = useState([]);

  const api = useMemo(() => {
    const send = (cmd, args = {}, { id, timeoutMs = 2500 } = {}) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        return Promise.reject(new Error("WS not connected"));
      }

      const req = makeReq(cmd, args, id);

      return new Promise((resolve, reject) => {
        const t = setTimeout(() => {
          pendingRef.current.delete(req.id);
          reject(new Error(`timeout waiting for response id=${req.id} cmd=${cmd}`));
        }, timeoutMs);

        pendingRef.current.set(req.id, { resolve, reject, timeout: t });
        ws.send(JSON.stringify(req));
      });
    };

    return {
      send,
      listScenarios: () => send("list_scenarios", {}, { id: "ui-list" }),
      ping: () => send("ping", {}, { id: "ui-ping" }),
    };
  }, []);

  useEffect(() => {
    setStatus("connecting");
    setLastError(null);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");

    ws.onmessage = (ev) => {
      const parsed = safeJsonParse(ev.data);

      if (!parsed.ok) {
        setLog((l) => [...l, { _raw: ev.data, _parseError: parsed.error }]);
        return;
      }

      const msg = parsed.value;
      setLog((l) => [...l, msg]);

      // resolve RPC if id matches
      const pending = pendingRef.current.get(msg.id);
      if (pending) {
        clearTimeout(pending.timeout);
        pendingRef.current.delete(msg.id);
        pending.resolve(msg);
      }
    };

    ws.onerror = () => {
      setStatus("error");
      setLastError("WebSocket error");
    };

    ws.onclose = () => {
      setStatus("disconnected");
      // reject any pending
      for (const [id, p] of pendingRef.current.entries()) {
        clearTimeout(p.timeout);
        p.reject(new Error(`WS closed while waiting for id=${id}`));
      }
      pendingRef.current.clear();
    };

    return () => {
      try { ws.close(); } catch {}
      wsRef.current = null;
    };
  }, [wsUrl]);

  return { status, lastError, log, api };
}
