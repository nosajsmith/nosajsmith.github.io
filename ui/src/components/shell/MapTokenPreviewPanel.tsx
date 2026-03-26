import { useState, type CSSProperties } from "react";
import {
  MAP_ANIMATION_TOKENS,
  MAP_BRANCH_PALETTE,
  MAP_FACTION_PALETTE,
  MAP_GREASE_MARKUP_TOKENS,
  MAP_GLOW_TOKENS,
  MAP_ICON_SCALE_TIERS,
  MAP_SIGNAL_COLORS,
  MAP_SIZE_TOKENS,
  MAP_STATE_STYLES,
  MAP_STROKE_WIDTH_BY_ZOOM_TIER,
  MAP_TERRAIN_PALETTE,
  MAP_TEXT_COLORS,
  MAP_ZOOM_TIERS,
} from "../../map/designTokens.js";
import { MAP_LAYER_REGISTRY } from "../../map/overlayManager.js";

function swatchStyle(cssVar: string): CSSProperties {
  return {
    background: `var(${cssVar})`,
  };
}

export default function MapTokenPreviewPanel() {
  const [open, setOpen] = useState(false);

  return (
    <div className={"shell-maptokens" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-maptokens__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-map-token-preview"
      >
        <span className="shell-map__legend-title">Map UI Tokens</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-maptokens__body" id="shell-map-token-preview">
          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Terrain + Text</div>
            <div className="shell-maptokens__swatch-grid">
              {[...MAP_TERRAIN_PALETTE, ...MAP_TEXT_COLORS].map((token) => (
                <div className="shell-maptokens__swatch" key={token.id}>
                  <span className="shell-maptokens__swatch-chip" style={swatchStyle(token.cssVar)} aria-hidden="true" />
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{token.label}</strong>
                    <span>{token.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">State Language</div>
            <div className="shell-maptokens__swatch-grid">
              {[...MAP_FACTION_PALETTE, ...MAP_STATE_STYLES].map((token) => (
                <div className="shell-maptokens__swatch" key={token.id}>
                  <span className="shell-maptokens__swatch-chip" style={swatchStyle(token.cssVar)} aria-hidden="true" />
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{token.label}</strong>
                    <span>{"pattern" in token ? token.pattern : token.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Branch + Signal</div>
            <div className="shell-maptokens__swatch-grid">
              {[...MAP_BRANCH_PALETTE, ...MAP_SIGNAL_COLORS, ...MAP_GLOW_TOKENS].map((token) => (
                <div className="shell-maptokens__swatch" key={token.id}>
                  <span
                    className="shell-maptokens__swatch-chip"
                    style={{ background: "fill" in token ? token.fill : "value" in token ? token.value : token.color }}
                    aria-hidden="true"
                  />
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{token.label}</strong>
                    <span>{"accent" in token ? token.accent : "blurPx" in token ? `${token.blurPx}px blur` : token.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Grease Markup</div>
            <div className="shell-maptokens__swatch-grid">
              {Object.entries(MAP_GREASE_MARKUP_TOKENS.styles).map(([id, style]) => (
                <div className="shell-maptokens__swatch" key={id}>
                  <span className="shell-maptokens__swatch-chip" style={{ background: style.stroke }} aria-hidden="true" />
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{style.label}</strong>
                    <span>{style.stroke}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Standard Sizes</div>
            <div className="shell-maptokens__scale-list">
              <div className="shell-maptokens__scale-row">
                <div className="shell-maptokens__scale-sample is-line" style={{ height: `${MAP_SIZE_TOKENS.hexOutline.majorPx}px` }} aria-hidden="true" />
                <div className="shell-maptokens__swatch-copy">
                  <strong>Hex outline</strong>
                  <span>{MAP_SIZE_TOKENS.hexOutline.minorPx}px minor / {MAP_SIZE_TOKENS.hexOutline.majorPx}px major</span>
                </div>
              </div>
              <div className="shell-maptokens__scale-row">
                <div
                  className="shell-maptokens__scale-sample is-unit"
                  style={{
                    width: `${MAP_SIZE_TOKENS.unitIconBox.widthPx}px`,
                    height: `${MAP_SIZE_TOKENS.unitIconBox.heightPx}px`,
                  }}
                  aria-hidden="true"
                />
                <div className="shell-maptokens__swatch-copy">
                  <strong>Unit box</strong>
                  <span>{MAP_SIZE_TOKENS.unitIconBox.widthPx}x{MAP_SIZE_TOKENS.unitIconBox.heightPx}px</span>
                </div>
              </div>
              <div className="shell-maptokens__scale-row">
                <div
                  className="shell-maptokens__scale-sample is-city"
                  style={{
                    width: `${MAP_SIZE_TOKENS.cityIcon.diameterPx}px`,
                    height: `${MAP_SIZE_TOKENS.cityIcon.diameterPx}px`,
                  }}
                  aria-hidden="true"
                />
                <div className="shell-maptokens__swatch-copy">
                  <strong>City icon</strong>
                  <span>{MAP_SIZE_TOKENS.cityIcon.diameterPx}px diameter</span>
                </div>
              </div>
              <div className="shell-maptokens__scale-row">
                <div
                  className="shell-maptokens__scale-sample is-airfield"
                  style={{
                    width: `${MAP_SIZE_TOKENS.airfieldIcon.widthPx}px`,
                    height: `${MAP_SIZE_TOKENS.airfieldIcon.heightPx}px`,
                  }}
                  aria-hidden="true"
                />
                <div className="shell-maptokens__swatch-copy">
                  <strong>Airfield icon</strong>
                  <span>{MAP_SIZE_TOKENS.airfieldIcon.widthPx}x{MAP_SIZE_TOKENS.airfieldIcon.heightPx}px</span>
                </div>
              </div>
              <div className="shell-maptokens__scale-row">
                <div
                  className="shell-maptokens__scale-sample is-overlay"
                  style={{
                    width: `${MAP_SIZE_TOKENS.overlayMarkers.locRingRadiusPx * 2}px`,
                    height: `${MAP_SIZE_TOKENS.overlayMarkers.locRingRadiusPx * 2}px`,
                  }}
                  aria-hidden="true"
                />
                <div className="shell-maptokens__swatch-copy">
                  <strong>Overlay markers</strong>
                  <span>{MAP_SIZE_TOKENS.overlayMarkers.locRingRadiusPx}px LOC / {MAP_SIZE_TOKENS.overlayMarkers.artilleryRingRadiusPx}px artillery</span>
                </div>
              </div>
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Zoom Tiers</div>
            <div className="shell-maptokens__zoom-grid">
              {MAP_ZOOM_TIERS.map((tier) => (
                <div className="shell-maptokens__zoom-card" key={tier.id}>
                  <strong>{tier.label}</strong>
                  <span>{tier.min.toFixed(2)}-{tier.max.toFixed(2)} zoom</span>
                  <span>Unit {tier.targetUnitBoxPx}px</span>
                  <span>City {tier.targetCityIconPx}px</span>
                  <span>{tier.labelDensity}</span>
                </div>
              ))}
            </div>
            <div className="shell-maptokens__icon-tier-row">
              {MAP_ICON_SCALE_TIERS.map((tier) => (
                <div className="shell-maptokens__icon-tier" key={tier.id}>
                  <strong>{tier.label}</strong>
                  <span>{tier.px}px</span>
                </div>
              ))}
            </div>
            <div className="shell-maptokens__icon-tier-row">
              {MAP_STROKE_WIDTH_BY_ZOOM_TIER.map((tier) => (
                <div className="shell-maptokens__icon-tier" key={tier.id}>
                  <strong>{tier.id}</strong>
                  <span>{tier.hexMajorPx}px hex / {tier.unitPx}px unit</span>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Layer Order</div>
            <div className="shell-maptokens__motion-list">
              {MAP_LAYER_REGISTRY.map((layer) => (
                <div className="shell-maptokens__motion-row" key={layer.id}>
                  <span className="shell-maptokens__layer-chip" aria-hidden="true">{layer.priority}</span>
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{layer.label}</strong>
                    <span>{layer.group} • {layer.defaultEnabled ? "default on" : "default off"}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="shell-maptokens__section">
            <div className="shell-map__legend-subtitle">Motion</div>
            <div className="shell-maptokens__motion-list">
              {MAP_ANIMATION_TOKENS.map((token) => (
                <div className="shell-maptokens__motion-row" key={token.id}>
                  <span
                    className={"shell-maptokens__motion-dot is-" + token.id}
                    style={{ animationDuration: `${token.durationMs}ms` }}
                    aria-hidden="true"
                  />
                  <div className="shell-maptokens__swatch-copy">
                    <strong>{token.label}</strong>
                    <span>{token.durationMs}ms • {token.easing} • {token.behavior}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
