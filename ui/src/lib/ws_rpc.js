export function makeWsRpc(url, { proto = "1.0" } = {}) {
  let ws = null;
  let nextId = 1;
  const pending = new Map();

  async function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    ws = new WebSocket(url);

    await new Promise((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = (e) => reject(e);
    });

    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch (e) {
        console.error("bad ws json", e);
        return;
      }

      const id = msg.id ?? msg.req_id;
      if (!id) return;

      const p = pending.get(id);
      if (!p) return;

      pending.delete(id);

      const normalized = {
        status: msg.ok ? "ok" : "error",
        data: msg.data ?? msg.payload,
        error: msg.error ?? null,
        raw: msg,
      };

      if (msg.ok) {
        p.resolve(normalized);
      } else {
        p.resolve(normalized);
      }
    };

    ws.onclose = () => {
      for (const [, p] of pending) {
        p.reject(new Error("ws closed"));
      }
      pending.clear();
      ws = null;
    };
  }

  async function rpc(cmd, args = {}) {
    await connect();

    return await new Promise((resolve, reject) => {
      const id = `ui-${nextId++}`;
      pending.set(id, { resolve, reject });

      const payload = JSON.stringify({
        id,
        proto,
        cmd,
        payload: args,
      });

      ws.send(payload);
    });
  }

  function isConnected() {
    return !!ws && ws.readyState === WebSocket.OPEN;
  }

  function close() {
    try { ws?.close(); } catch {}
  }

  return { connect, rpc, isConnected, close };
}
