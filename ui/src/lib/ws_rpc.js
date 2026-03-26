export function makeWsRpc(url, { proto = "1.0", timeoutMs = 5000 } = {}) {
  let ws = null;
  let openPromise = null;
  const pending = new Map(); // req_id -> {resolve,reject,timer}

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return openPromise ?? Promise.resolve();
    }

    ws = new WebSocket(url);

    openPromise = new Promise((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = (e) => reject(e);
    });

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      const id = msg?.req_id;
      if (!id) return;
      const p = pending.get(id);
      if (!p) return;
      clearTimeout(p.timer);
      pending.delete(id);
      p.resolve(msg);
    };

    ws.onclose = () => {
      // fail any in-flight requests
      for (const [, p] of pending) {
        clearTimeout(p.timer);
        p.reject(new Error("ws closed"));
      }
      pending.clear();
      ws = null;
      openPromise = null;
    };

    return openPromise;
  }

  async function rpc(cmd, payload = {}, id = crypto.randomUUID()) {
    await connect();

    const req = { req_id: id, v: proto, cmd, payload };
    const body = JSON.stringify(req);

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`timeout waiting for ${cmd}`));
      }, timeoutMs);

      pending.set(id, { resolve, reject, timer });
      ws.send(body);
    });
  }

  function isConnected() {
    return !!ws && ws.readyState === WebSocket.OPEN;
  }

  function close() {
    try { ws?.close(); } catch {}
  }

  return { rpc, connect, close, isConnected };
}
