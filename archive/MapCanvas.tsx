import React, { useEffect, useRef, useState } from "react";

type Unit = { id: string; name: string; type: string; pos: [number, number] };
type AIOrder = { id: string; unit_id: string; order_type: string; target_hex: [number, number] | null; priority: number; notes: string };
type Snapshot = {
  engine: any;
  scenario: { units: Unit[]; objectives: [number, number][] };
};

function drawArrow(ctx: CanvasRenderingContext2D, x1:number,y1:number,x2:number,y2:number) {
  const headlen = 10;
  const dx = x2 - x1, dy = y2 - y1;
  const angle = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - headlen * Math.cos(angle - Math.PI/6), y2 - headlen * Math.sin(angle - Math.PI/6));
  ctx.lineTo(x2 - headlen * Math.cos(angle + Math.PI/6), y2 - headlen * Math.sin(angle + Math.PI/6));
  ctx.closePath();
  ctx.fill();
}

export default function MapCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [orders, setOrders] = useState<AIOrder[]>([]);
  const [sock, setSock] = useState<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765");
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") setSnap(msg.data as Snapshot);
      if (msg.type === "ai_orders") setOrders(msg.data.orders as AIOrder[]);
      if (msg.type === "kpi_updated" || msg.type === "phase_changed") {
        // Optionally request new snapshot
      }
    };
    setSock(ws);
    return () => ws.close();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !snap) return;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // grid
    ctx.save();
    ctx.globalAlpha = 0.2;
    ctx.strokeStyle = "#999";
    for (let x = 0; x < W; x += 20) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 20) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.restore();

    // objectives
    ctx.fillStyle = "black";
    snap.scenario.objectives.forEach(([ox, oy]) => {
      ctx.beginPath();
      ctx.arc(ox*10, oy*10, 6, 0, Math.PI*2);
      ctx.fill();
    });

    // units
    snap.scenario.units.forEach(u => {
      const [x,y] = u.pos;
      ctx.fillStyle = u.type === "arm" ? "gray" : u.type === "eng" ? "darkgreen" : "navy";
      ctx.fillRect(x*10 - 6, y*10 - 6, 12, 12);
      ctx.fillStyle = "black";
      ctx.fillText(u.name, x*10 + 8, y*10);
    });

    // AI orders overlay
    ctx.strokeStyle = "red";
    ctx.fillStyle = "red";
    orders.forEach(o => {
      const unit = snap.scenario.units.find(u => u.id === o.unit_id);
      if (!unit || !o.target_hex) return;
      const [x1,y1] = unit.pos;
      const [x2,y2] = o.target_hex;
      drawArrow(ctx, x1*10, y1*10, x2*10, y2*10);
    });
  }, [snap, orders]);

  return (
    <div className="w-full h-full p-2">
      <div className="flex items-center gap-2 mb-2">
        <button onClick={() => sock?.send(JSON.stringify({cmd:"next_turn", payload:{}}))} className="px-2 py-1 border rounded">Next Turn</button>
        <button onClick={() => sock?.send(JSON.stringify({cmd:"plan_orders", payload:{}}))} className="px-2 py-1 border rounded">Plan Orders</button>
        <button onClick={() => sock?.send(JSON.stringify({cmd:"run", payload:{}}))} className="px-2 py-1 border rounded">Run</button>
        <button onClick={() => sock?.send(JSON.stringify({cmd:"pause", payload:{}}))} className="px-2 py-1 border rounded">Pause</button>
      </div>
      <canvas ref={canvasRef} width={800} height={480} className="border rounded w-full max-w-[800px] h-[480px]" />
    </div>
  );
}
