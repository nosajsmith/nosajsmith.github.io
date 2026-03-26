import { useState } from "react";
import { MAP_ZOOM_TIERS } from "../../map/designTokens.js";
import { buildUnitCounterOverlayPresentation, UNIT_COUNTER_OVERLAY_REFERENCE_CASES } from "../../map/unitCounterOverlay.js";
import { buildUnitCounterPaletteStyle, UNIT_COUNTER_PALETTE_REFERENCE_CASES } from "../../map/unitCounterPalette.js";
import { UNIT_COUNTER_SYMBOL_REFERENCE_CASES } from "../../map/unitCounterSymbol.js";
import {
  COUNTER_FRAME_REFERENCE_CASES,
  COUNTER_FRAME_VIEWBOX,
  buildUnitCounterFramePresentation,
  summarizeUnitCounterLabelPolicy,
} from "../../map/unitCounterFrame.js";
import UnitCounterFrame from "./UnitCounterFrame";
import UnitCounterStatusOverlay from "./UnitCounterStatusOverlay";

const ZOOM_PRESETS = MAP_ZOOM_TIERS.map((tier) => ({
  id: tier.id,
  label: tier.label,
  zoom: Number(((tier.min + tier.max) / 2).toFixed(2)),
}));

export default function UnitCounterFrameHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [zoomPreset, setZoomPreset] = useState(ZOOM_PRESETS[1]);
  const labelPolicy = summarizeUnitCounterLabelPolicy(zoomPreset.zoom);

  return (
    <div className={"shell-counterframes" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-counterframes__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-counter-frame-grid"
      >
        <span className="shell-map__legend-title">Counter Frames</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-counterframes__body" id="shell-counter-frame-grid">
          <div className="shell-counterframes__toolbar">
            <div className="shell-counterframes__tierpicker" role="group" aria-label="Counter frame zoom tier">
              {ZOOM_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={"shell-counterframes__chip" + (zoomPreset.id === preset.id ? " is-active" : "")}
                  onClick={() => setZoomPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={"shell-counterframes__chip" + (showCode ? " is-active" : "")}
              onClick={() => setShowCode((current) => !current)}
            >
              Code {showCode ? "On" : "Off"}
            </button>
          </div>

          <div className="shell-counterframes__note">
            Labels by zoom: {labelPolicy.label} view keeps counter code {labelPolicy.counterCode.toLowerCase()} and unit name {labelPolicy.unitName.toLowerCase()}. {labelPolicy.note}
          </div>

          <div className="shell-counterframes__grid">
            {COUNTER_FRAME_REFERENCE_CASES.map((entry) => {
              const frame = buildUnitCounterFramePresentation({
                echelon: entry.echelon,
                isHeadquarters: entry.isHeadquarters,
                zoom: zoomPreset.zoom,
              });
              return (
                <div className="shell-counterframes__card" key={entry.id}>
                  <svg className="shell-counterframes__svg" viewBox={COUNTER_FRAME_VIEWBOX.viewBox} role="img" aria-label={entry.label}>
                    <g className={"shell-map__unit is-primary" + (entry.isHeadquarters ? " is-headquarters" : "") + ` is-${entry.echelon}`}>
                      <UnitCounterFrame
                        echelon={entry.echelon}
                        isHeadquarters={entry.isHeadquarters}
                        code={entry.code}
                        showCode={showCode}
                        zoom={zoomPreset.zoom}
                      />
                    </g>
                  </svg>
                  <strong>{entry.label}</strong>
                  <span>{frame.treatment}</span>
                </div>
              );
            })}
          </div>

          <section className="shell-counterframes__palette">
            <div className="shell-map__legend-subtitle">Branch + Faction</div>
            <div className="shell-counterframes__grid">
              {UNIT_COUNTER_PALETTE_REFERENCE_CASES.map((entry) => (
                <div className="shell-counterframes__card" key={entry.id}>
                  <svg className="shell-counterframes__svg" viewBox={COUNTER_FRAME_VIEWBOX.viewBox} role="img" aria-label={entry.label}>
                    <g
                      className={
                        "shell-map__unit"
                        + ` is-${entry.echelon}`
                        + (entry.disabled ? " is-disabled" : "")
                        + (entry.outOfCommand ? " is-out-of-command" : "")
                      }
                      style={buildUnitCounterPaletteStyle(entry)}
                    >
                      <UnitCounterFrame
                        echelon={entry.echelon}
                        code={entry.code}
                        showCode
                        zoom={zoomPreset.zoom}
                      />
                    </g>
                  </svg>
                  <strong>{entry.label}</strong>
                  <span>
                    {entry.disabled
                      ? "desaturated disabled"
                      : entry.outOfCommand
                        ? "amber command warning"
                        : `${entry.faction} • ${entry.service.replace("_", " ")}`}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-counterframes__palette">
            <div className="shell-map__legend-subtitle">Role Symbols</div>
            <div className="shell-counterframes__grid">
              {UNIT_COUNTER_SYMBOL_REFERENCE_CASES.map((entry) => (
                <div className="shell-counterframes__card" key={entry.id}>
                  <svg className="shell-counterframes__svg" viewBox={COUNTER_FRAME_VIEWBOX.viewBox} role="img" aria-label={entry.label}>
                    <g
                      className={"shell-map__unit" + ` is-${entry.echelon}` + (entry.isHeadquarters ? " is-headquarters" : "")}
                      style={buildUnitCounterPaletteStyle(entry)}
                    >
                      <UnitCounterFrame
                        echelon={entry.echelon}
                        isHeadquarters={entry.isHeadquarters}
                        symbol={entry.symbol}
                        code={entry.code}
                        showCode={showCode}
                        zoom={zoomPreset.zoom}
                      />
                    </g>
                  </svg>
                  <strong>{entry.label}</strong>
                  <span>{entry.service.replace("_", " ")} branch</span>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-counterframes__palette">
            <div className="shell-map__legend-subtitle">Status Overlays</div>
            <div className="shell-counterframes__grid">
              {UNIT_COUNTER_OVERLAY_REFERENCE_CASES.map((entry) => {
                const overlay = buildUnitCounterOverlayPresentation(entry.unit, { selected: entry.selected });
                return (
                  <div className="shell-counterframes__card" key={entry.id}>
                    <svg className="shell-counterframes__svg" viewBox={COUNTER_FRAME_VIEWBOX.viewBox} role="img" aria-label={entry.label}>
                      <g
                        className={
                          "shell-map__unit"
                          + ` is-${entry.echelon}`
                          + (entry.isHeadquarters ? " is-headquarters" : "")
                          + (entry.selected ? " is-selected" : "")
                          + (overlay.outOfCommand ? " is-out-of-command" : "")
                          + (overlay.disabled ? " is-disabled" : "")
                        }
                        style={buildUnitCounterPaletteStyle(entry)}
                      >
                        <UnitCounterFrame
                          echelon={entry.echelon}
                          isHeadquarters={entry.isHeadquarters}
                          symbol={entry.symbol}
                          code={entry.code}
                          showCode={showCode}
                          zoom={zoomPreset.zoom}
                        />
                        <UnitCounterStatusOverlay
                          overlay={{ ...overlay, selected: Boolean(entry.selected), active: overlay.active || Boolean(entry.selected) }}
                          echelon={entry.echelon}
                          isHeadquarters={entry.isHeadquarters}
                          zoom={zoomPreset.zoom}
                        />
                      </g>
                    </svg>
                    <strong>{entry.label}</strong>
                    <span>
                      {overlay.critical
                        ? "critical overrides"
                        : overlay.edgeState
                          ? `${overlay.edgeState} cue`
                          : "badge-only status"}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
