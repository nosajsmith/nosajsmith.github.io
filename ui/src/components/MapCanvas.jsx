import React, { useMemo, useState } from "react";
import HexGrid from "./HexGrid.jsx";
import UnitLayer from "./UnitLayer.jsx";
import PanZoomSvg from "./PanZoomSvg.jsx";

export default function MapCanvas({
  meta,
  units,
  selectedUnit,
  onSelectUnit,
  onClearSelection,

  // new
  scenarioName,
  ws,
  onScenarioUpdated,
}) {
  const [panLocked, setPanLocked] = useState(false);

  // optimistic overlay so it feels instant
  const [ovr, setOvr] = useState({}); // { [id]: {q,r,px,py,x,y} }

  const mergedUnits = useMemo(() => {
    return (units ?? []).map((u) => {
      const m = ovr[u.id];
      return m ? { ...u, ...m } : u;
    });
  }, [units, ovr]);

  async function persistMove(id, pos) {
    if (!ws || !scenarioName) return;

    // optimistic
    setOvr((m) => ({ ...m, [id]: { ...pos, x: pos.q, y: pos.r } }));

    const r = await ws.rpc("move_unit", {
      name: scenarioName,
      unit_id: id,
      q: pos.q,
      r: pos.r,
    });

    if (r.status !== "ok") {
      console.error("move_unit failed:", r);
      return;
    }

    // Your bridge likely returns {scenario: scn}
    const scn = r.data?.scenario ?? r.data;

    // tell App to replace scenarioData so reload keeps it
    if (onScenarioUpdated) onScenarioUpdated(scn);
  }

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <PanZoomSvg panLocked={panLocked} onBackgroundClick={onClearSelection}>
        <HexGrid meta={meta} />
        <UnitLayer
          meta={meta}
          units={mergedUnits}
          selectedId={selectedUnit?.id}
          onSelect={onSelectUnit}
          onDragStateChange={setPanLocked}
          onUnitMove={persistMove}
        />
      </PanZoomSvg>
    </div>
  );
}
