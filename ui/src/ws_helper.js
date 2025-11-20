// Auto-reconnect WebSocket helper
export function makeBridge(url, { onOpen, onMessage, onClose, token, pingMs = 15000 }) {
  let ws, timer;
  const connect = () => {
    ws = new WebSocket(url);
    ws.addEventListener('open', () => {
      if (token) ws.send(JSON.stringify({ cmd: "auth", payload: { token } }));
      onOpen?.(ws);
      timer = setInterval(() => ws?.readyState === 1 && ws.send(JSON.stringify({ cmd: "ping" })), pingMs);
    });
    ws.addEventListener('message', e => {
      try { onMessage?.(JSON.parse(e.data)); } catch { /* ignore parse errors */ }
    });
    ws.addEventListener('close', () => { clearInterval(timer); onClose?.(); setTimeout(connect, 1000); });
    ws.addEventListener('error', () => ws.close());
  };
  connect();
  return {
    send: (obj) => ws?.readyState === 1 && ws.send(JSON.stringify(obj)),
    close: () => { clearInterval(timer); ws?.close(); }
  };
}
