import { useState } from "react";
import { AIRFIELD_ICON_REFERENCE_CASES, summarizeAirfieldZoomPolicy } from "../../map/airfieldIcon.js";
import { MAP_ZOOM_TIERS } from "../../map/designTokens.js";
import AirfieldIcon from "./AirfieldIcon";

const ZOOM_PRESETS = MAP_ZOOM_TIERS.map((tier) => ({
  id: tier.id,
  label: tier.label,
  zoom: Number(((tier.min + tier.max) / 2).toFixed(2)),
}));

export default function AirfieldIconHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [zoomPreset, setZoomPreset] = useState(ZOOM_PRESETS[1]);
  const zoomPolicy = summarizeAirfieldZoomPolicy();

  return (
    <div className={"shell-airfields" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-airfields__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-airfield-icon-grid"
      >
        <span className="shell-map__legend-title">Airfield Icons</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-airfields__body" id="shell-airfield-icon-grid">
          <div className="shell-airfields__toolbar" role="group" aria-label="Airfield zoom tier preview">
            {ZOOM_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={"shell-airfields__chip" + (zoomPreset.id === preset.id ? " is-active" : "")}
                onClick={() => setZoomPreset(preset)}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="shell-airfields__note">
            Live airfields currently expose only location identity. Damage, destroyed, and sortie-active cues render only when those fields or based-air-unit records are truthfully available.
          </div>

          <div className="shell-airfields__grid">
            {AIRFIELD_ICON_REFERENCE_CASES.map((entry) => (
              <div className="shell-airfields__card" key={entry.id}>
                <svg className="shell-airfields__svg" viewBox="-18 -18 36 36" role="img" aria-label={entry.label}>
                  <AirfieldIcon
                    tier={entry.tier}
                    controlState={entry.controlState}
                    readinessBand={entry.readinessBand}
                    damageState={entry.damageState}
                    sortieActive={entry.sortieActive}
                    zoom={zoomPreset.zoom}
                    placement="harness"
                  />
                </svg>
                <strong>{entry.label}</strong>
                <span>{entry.note}</span>
              </div>
            ))}
          </div>

          <section className="shell-airfields__zoom">
            <div className="shell-map__legend-subtitle">Zoom Behavior</div>
            <div className="shell-airfields__zoom-grid">
              {zoomPolicy.map((entry) => (
                <div className="shell-airfields__zoom-card" key={entry.id}>
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
