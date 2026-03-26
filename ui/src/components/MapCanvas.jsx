import React from "react";
import HexGrid from "./HexGrid.jsx";
import TerrainLayer from "./TerrainLayer.jsx";
import ObjectiveLayer from "./ObjectiveLayer.jsx";
import UnitLayer from "./UnitLayer.jsx";
import PanZoomSvg from "./PanZoomSvg.jsx";

export default function MapCanvas({
  meta,
  terrain,
  objectives,
  units,
  selectedUnit,
  onSelectUnit,
  onClearSelection,
}) {
  return (
    <div style={{ width: "100%", height: "100%" }}>
      <PanZoomSvg onBackgroundClick={onClearSelection}>
        <TerrainLayer meta={meta} terrain={terrain} />
        <HexGrid meta={meta} />
        <ObjectiveLayer meta={meta} objectives={objectives} />
        <UnitLayer
          meta={meta}
          units={units}
          selectedId={selectedUnit?.id}
          onSelect={onSelectUnit}
        />
      </PanZoomSvg>
    </div>
  );
}
