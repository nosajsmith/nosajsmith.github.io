import React, { useEffect, useRef, useState } from "react";

export default function PanZoomSvg({
  children,
  onBackgroundClick,
  panLocked = false,
}) {
  const ref = useRef(null);

  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: 1200, h: 800 });
  const [panning, setPanning] = useState(false);
  const last = useRef({ x: 0, y: 0 });

  function onMouseDown(e) {
    if (panLocked) return;
    setPanning(true);
    last.current = { x: e.clientX, y: e.clientY };
  }

  function onMouseMove(e) {
    if (!panning || panLocked) return;
    const dx = e.clientX - last.current.x;
    const dy = e.clientY - last.current.y;
    last.current = { x: e.clientX, y: e.clientY };

    setViewBox((vb) => ({ ...vb, x: vb.x - dx, y: vb.y - dy }));
  }

  function onMouseUp() {
    setPanning(false);
  }

  // wheel zoom (keep simple)
  function onWheel(e) {
    if (panLocked) return;
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    setViewBox((vb) => {
      const nw = vb.w * factor;
      const nh = vb.h * factor;
      return {
        x: vb.x + (vb.w - nw) / 2,
        y: vb.y + (vb.h - nh) / 2,
        w: nw,
        h: nh,
      };
    });
  }

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = (e) => onWheel(e);
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, [panLocked]);

  return (
    <svg
      ref={ref}
      style={{ width: "100%", height: "100%" }}
      viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onClick={() => onBackgroundClick && onBackgroundClick()}
    >
      {children}
    </svg>
  );
}
