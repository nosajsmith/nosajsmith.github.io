/**
 * ws_client.js
 *
 * Thin WebSocket RPC client for MWE Bridge v1.0
 */

const URI = "ws://127.0.0.1:8766";
const PROTO = "1.0";

let socket = null;

export function connect() {
  if (socket && socket.readyState === WebSocket.OPEN) return socket;

  socket = new WebSocket(URI);
  return socket;
}

export function rpc(cmd, args = {}) {
  return new Promise((resolve, reject) => {
    const ws = connect();
    const id = crypto.randomUUID();

    const msg = {
      id,
      proto: PROTO,
      cmd,
      args,
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.id === id) resolve(data);
      } catch (e) {
        reject(e);
      }
    };

    ws.onerror = reject;

    ws.send(JSON.stringify(msg));
  });
}
