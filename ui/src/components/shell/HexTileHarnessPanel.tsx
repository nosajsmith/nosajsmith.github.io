import { useMemo, useState } from "react";
import HexTile from "./HexTile";
import { HEX_TILE_REFERENCE_CASES, HEX_TERRAIN_PREVIEW_MAP } from "../../map/hexTile.js";
import { MAP_TERRAIN_STYLES, MAP_ZOOM_TIERS } from "../../map/designTokens.js";

const ZOOM_PRESETS = MAP_ZOOM_TIERS.map((tier) => ({
  id: tier.id,
  label: tier.label,
  zoom: Number(((tier.min + tier.max) / 2).toFixed(2)),
}));

export default function HexTileHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [gridVisible, setGridVisible] = useState(true);
  const [showTexture, setShowTexture] = useState(true);
  const [zoomPreset, setZoomPreset] = useState(ZOOM_PRESETS[1]);
  const captureCases = useMemo(
    () => HEX_TILE_REFERENCE_CASES,
    [],
  );

  return (
    <div className={"shell-hextilepanel" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-hextilepanel__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-hex-tile-harness"
      >
        <span className="shell-map__legend-title">Hex State Harness</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-hextilepanel__body" id="shell-hex-tile-harness">
          <div className="shell-hextilepanel__toolbar">
            <div className="shell-hextilepanel__tierpicker" role="group" aria-label="Hex zoom tier preview">
              {ZOOM_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={"shell-hextilepanel__chip" + (zoomPreset.id === preset.id ? " is-active" : "")}
                  onClick={() => setZoomPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <div className="shell-hextilepanel__tierpicker" role="group" aria-label="Hex grid and texture visibility">
              <button
                type="button"
                className={"shell-hextilepanel__chip" + (gridVisible ? " is-active" : "")}
                onClick={() => setGridVisible((current) => !current)}
              >
                Grid {gridVisible ? "On" : "Off"}
              </button>
              <button
                type="button"
                className={"shell-hextilepanel__chip" + (showTexture ? " is-active" : "")}
                onClick={() => setShowTexture((current) => !current)}
              >
                Texture {showTexture ? "On" : "Off"}
              </button>
            </div>
          </div>

          <div className="shell-hextilepanel__note">
            Operational readability target: selection uses glow + ticks, ZOC uses distinct ring patterns, and far zoom fades the grid before it disappears.
          </div>

          <section className="shell-hextilepanel__terrainmap">
            <div className="shell-map__legend-subtitle">Terrain Preview Map</div>
            <div className="shell-hextilepanel__terrainboard">
              {HEX_TERRAIN_PREVIEW_MAP.map((tile) => (
                <div
                  className={"shell-hextilepanel__terrainhex" + (tile.id === "t6" || tile.id === "t11" ? " has-counter" : "")}
                  key={tile.id}
                  style={{
                    left: `${tile.col * 58 + (tile.row % 2 ? 29 : 0)}px`,
                    top: `${tile.row * 48}px`,
                  }}
                >
                  <HexTile
                    label={tile.label}
                    terrain={tile.terrain}
                    zoom={zoomPreset.zoom}
                    gridVisible={gridVisible}
                    showTexture={showTexture}
                  />
                  {tile.id === "t6" || tile.id === "t11" ? <span className="shell-hextilepanel__counter">2/7</span> : null}
                </div>
              ))}
            </div>
            <div className="shell-hextilepanel__terrainkey">
              {MAP_TERRAIN_STYLES.map((terrain) => (
                <div className="shell-hextilepanel__terrainrow" key={terrain.id}>
                  <span className={`shell-hextilepanel__terrainchip is-${terrain.id}`} aria-hidden="true" />
                  <div className="shell-hextilepanel__terraincopy">
                    <strong>{terrain.label}</strong>
                    <span>{terrain.texture}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="shell-hextilepanel__grid">
            {captureCases.map((capture) => (
              <div className="shell-hextilepanel__card" key={capture.id}>
                <HexTile
                  label={capture.label}
                  terrain={capture.terrain}
                  hovered={capture.hovered}
                  selected={capture.selected}
                  friendlyZoc={capture.friendlyZoc}
                  enemyZoc={capture.enemyZoc}
                  contested={capture.contested}
                  moveTarget={capture.moveTarget}
                  attackTarget={capture.attackTarget}
                  zoom={zoomPreset.zoom}
                  gridVisible={gridVisible}
                  showTexture={showTexture}
                />
                <strong>{capture.label}</strong>
                <span>{capture.note}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
