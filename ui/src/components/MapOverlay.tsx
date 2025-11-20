import React from "react";

type Unit = { id:string; name:string; type:string; strength:number; fatigue:number; pos:[number,number]; hq:string };

function axialToPixel([q, r]: [number, number], size=18) {
  const x = size * (Math.sqrt(3) * q + (Math.sqrt(3)/2) * r);
  const y = size * ( (3/2) * r );
  return [x, y];
}

export default function MapOverlay({
  blueUnits = [], redUnits = [], objectives = [], lastMovements = []
}: {
  blueUnits?: Unit[], redUnits?: {pos:[number,number]}[], objectives?: [number,number][], lastMovements?: any[]
}) {
  const ref = React.useRef<HTMLCanvasElement|null>(null);

  React.useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width = canvas.clientWidth;
    const H = canvas.height = canvas.clientHeight;

    ctx.clearRect(0,0,W,H);
    ctx.fillStyle = "#0b1220";
    ctx.fillRect(0,0,W,H);

    const drawDot = (ax:[number,number], color:string, label?:string) => {
      const [x,y] = axialToPixel(ax, 18);
      ctx.beginPath();
      ctx.fillStyle = color;
      ctx.arc(x+W/2, y+H/2, 6, 0, Math.PI*2);
      ctx.fill();
      if (label) {
        ctx.fillStyle = "#cbd5e1";
        ctx.font = "12px sans-serif";
        ctx.fillText(label, x+W/2+10, y+H/2+4);
      }
    };

    objectives.forEach(o => drawDot(o as any, "#f59e0b", "OBJ"));
    redUnits.forEach((u,i) => drawDot(u.pos as any, "#ef4444", `R${i+1}`));
    blueUnits.forEach((u,i) => drawDot(u.pos as any, "#60a5fa", u.id));

    lastMovements.forEach((m:any) => {
      if (!m?.from || !m?.to) return;
      const [x1,y1] = axialToPixel(m.from, 18);
      const [x2,y2] = axialToPixel(m.to, 18);
      const ox = W/2, oy = H/2;
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x1+ox, y1+oy);
      ctx.lineTo(x2+ox, y2+oy);
      ctx.stroke();
      const ang = Math.atan2((y2 - y1),(x2 - x1));
      ctx.beginPath();
      ctx.moveTo(x2+ox, y2+oy);
      ctx.lineTo(x2+ox-8*Math.cos(ang-0.3), y2+oy-8*Math.sin(ang-0.3));
      ctx.lineTo(x2+ox-8*Math.cos(ang+0.3), y2+oy-8*Math.sin(ang+0.3));
      ctx.closePath();
      ctx.fillStyle = "#22d3ee";
      ctx.fill();
    });
  }, [blueUnits, redUnits, objectives, lastMovements]);

  return (
    <div className="border rounded-xl overflow-hidden bg-slate-900">
      <div className="px-3 py-2 text-sm text-slate-300 border-b">Map Overlay (hex axial, coarse)</div>
      <canvas ref={ref} style={{width:"100%", height:"420px", display:"block"}} />
    </div>
  );
}
