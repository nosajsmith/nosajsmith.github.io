// Simple WebSocket bridge stub for MWE Command Center ↔ Python Turn Engine

let socket;
let handlers = [];

export function connectBridge(url = "ws://localhost:8765") {
  socket = new WebSocket(url);
  socket.onopen = () => console.log("[Bridge] Connected to backend");
  socket.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    handlers.forEach((h) => h(data));
  };
  socket.onclose = () => console.warn("[Bridge] Disconnected");
}

export function onEngineEvent(handler) {
  handlers.push(handler);
}

export function sendCommand(cmd, payload = {}) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ cmd, payload }));
  }
}
