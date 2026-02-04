const URI = "ws://127.0.0.1:8766";
const PROTO = "1.0";

export function makeBridge() {
  let ws = null;
  let pending = new Map(); // id -> {resolve, reject, timeout}
  let isOpen = false;

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    ws = new WebSocket(URI);

    ws.onopen = () => { isOpen = true; };
    ws.onclose = () => {
      isOpen = false;
      // fail all pending
      for (const [id, p] of pending.entries()) {
        clearTimeout(p.timeout);
        p.reject(new Error(`WS closed while waiting for ${id}`));
      }
      pending.clear();
      // auto-reconnect after short delay
      setTimeout(connect, 500);
    };
    ws.onerror = () => { /* onclose will handle */ };

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); }
      catch { return; }

      const id = msg?.id;
      if (!id) return;

      const p = pending.get(id);
      if (!p) return;

      pending.delete(id);
      clearTimeout(p.timeout);
      p.resolve(msg);
    };
  }

  function rpc(cmd, args = {}, id = crypto.randomUUID(), timeoutMs = 2500) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error("WS not connected (yet)"));
    }

    const payload = { id, proto: PROTO, cmd, args };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`RPC timeout: ${cmd} (${id})`));
      }, timeoutMs);

      pending.set(id, { resolve, reject, timeout });
      ws.send(JSON.stringify(payload));
    });
  }

  function ready() {
    return isOpen && ws && ws.readyState === WebSocket.OPEN;
  }

  connect();

  return { connect, rpc, ready };
}
