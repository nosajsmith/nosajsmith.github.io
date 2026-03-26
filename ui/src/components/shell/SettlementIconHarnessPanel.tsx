import { useState } from "react";
import { MAP_ZOOM_TIERS } from "../../map/designTokens.js";
import { SETTLEMENT_ICON_REFERENCE_CASES, summarizeSettlementZoomPolicy } from "../../map/settlementIcon.js";
import SettlementIcon from "./SettlementIcon";

const ZOOM_PRESETS = MAP_ZOOM_TIERS.map((tier) => ({
  id: tier.id,
  label: tier.label,
  zoom: Number(((tier.min + tier.max) / 2).toFixed(2)),
}));

export default function SettlementIconHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [zoomPreset, setZoomPreset] = useState(ZOOM_PRESETS[1]);
  const zoomPolicy = summarizeSettlementZoomPolicy();

  return (
    <div className={"shell-settlements" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-settlements__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-settlement-icon-grid"
      >
        <span className="shell-map__legend-title">Settlement Icons</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-settlements__body" id="shell-settlement-icon-grid">
          <div className="shell-settlements__toolbar" role="group" aria-label="Settlement zoom tier preview">
            {ZOOM_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={"shell-settlements__chip" + (zoomPreset.id === preset.id ? " is-active" : "")}
                onClick={() => setZoomPreset(preset)}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="shell-settlements__note">
            Current live map applies settlement silhouettes to objective localities using exposed objective value and state until dedicated settlement records are available.
          </div>

          <div className="shell-settlements__grid">
            {SETTLEMENT_ICON_REFERENCE_CASES.map((entry) => (
              <div className="shell-settlements__card" key={entry.id}>
                <svg className="shell-settlements__svg" viewBox="-18 -18 36 36" role="img" aria-label={entry.label}>
                  <SettlementIcon
                    tier={entry.tier}
                    controlState={entry.controlState}
                    damaged={entry.damaged}
                    supplyHub={entry.supplyHub}
                    zoom={zoomPreset.zoom}
                    placement="harness"
                  />
                </svg>
                <strong>{entry.label}</strong>
                <span>{entry.note}</span>
              </div>
            ))}
          </div>

          <section className="shell-settlements__zoom">
            <div className="shell-map__legend-subtitle">Zoom Behavior</div>
            <div className="shell-settlements__zoom-grid">
              {zoomPolicy.map((entry) => (
                <div className="shell-settlements__zoom-card" key={entry.id}>
                  <strong>{entry.label}</strong>
                  <span>{entry.zoomRange}</span>
                  <span>{entry.behavior}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
