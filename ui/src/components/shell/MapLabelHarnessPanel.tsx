import { useMemo, useState } from "react";
import { MAP_SIZE_TOKENS, MAP_ZOOM_TIERS } from "../../map/designTokens.js";
import { buildDeclutteredLabels, buildMarkerObstacleRect } from "../../map/labelDeclutter.js";

const ZOOM_PRESETS = MAP_ZOOM_TIERS.map((tier) => ({
  id: tier.id,
  label: tier.label,
  zoom: Number(((tier.min + tier.max) / 2).toFixed(2)),
}));

const PREVIEW_MARKERS = [
  { id: "objective:henderson", kind: "objective", x: 104, y: 78 },
  { id: "objective:bloody", kind: "objective", x: 178, y: 116 },
  { id: "objective:ilu", kind: "objective", x: 208, y: 78 },
  { id: "airfield:henderson", kind: "airfield", x: 132, y: 60 },
  { id: "port:lunga", kind: "port", x: 78, y: 56 },
  { id: "unit:marines", kind: "unit", x: 132, y: 136 },
  { id: "unit:hq", kind: "unit", x: 184, y: 146 },
  { id: "unit:recon", kind: "unit", x: 232, y: 128 },
];

function buildPreviewObstacles(scale: number) {
  return PREVIEW_MARKERS.map((marker) => {
    if (marker.kind === "objective") {
      return buildMarkerObstacleRect({
        id: marker.id,
        kind: "objective",
        x: marker.x,
        y: marker.y,
        width: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.5,
        height: MAP_SIZE_TOKENS.cityIcon.diameterPx * 1.5,
        scale,
      });
    }
    if (marker.kind === "airfield") {
      return buildMarkerObstacleRect({
        id: marker.id,
        kind: "airfield",
        x: marker.x,
        y: marker.y,
        width: MAP_SIZE_TOKENS.airfieldIcon.widthPx,
        height: MAP_SIZE_TOKENS.airfieldIcon.heightPx,
        scale,
      });
    }
    if (marker.kind === "port") {
      return buildMarkerObstacleRect({
        id: marker.id,
        kind: "port",
        x: marker.x,
        y: marker.y,
        width: 20,
        height: 16,
        scale,
      });
    }
    return buildMarkerObstacleRect({
      id: marker.id,
      kind: "unit",
      x: marker.x,
      y: marker.y,
      width: MAP_SIZE_TOKENS.unitIconBox.widthPx,
      height: MAP_SIZE_TOKENS.unitIconBox.heightPx + 4,
      scale,
    });
  });
}

function buildPreviewCandidates(scale: number) {
  return [
    {
      id: "objective:henderson:label",
      ownerId: "objective:henderson",
      ownerObstacleId: "objective:henderson",
      kind: "objectiveLabel",
      text: "Henderson Field",
      x: 116 + 12 * scale,
      y: 78 - 12 * scale,
      textAnchor: "start",
      scale,
      important: true,
    },
    {
      id: "objective:henderson:state",
      ownerId: "objective:henderson",
      ownerObstacleId: "objective:henderson",
      kind: "objectiveState",
      text: "Held Allied",
      x: 116 + 12 * scale,
      y: 78 + 14 * scale,
      textAnchor: "start",
      scale,
      important: true,
    },
    {
      id: "objective:bloody:label",
      ownerId: "objective:bloody",
      ownerObstacleId: "objective:bloody",
      kind: "objectiveLabel",
      text: "Bloody Ridge",
      x: 178 - 18 * scale,
      y: 116 + 17 * scale,
      textAnchor: "end",
      scale,
    },
    {
      id: "objective:ilu:label",
      ownerId: "objective:ilu",
      ownerObstacleId: "objective:ilu",
      kind: "objectiveLabel",
      text: "Ilu Crossing",
      x: 208 + 18 * scale,
      y: 78 - 12 * scale,
      textAnchor: "start",
      scale,
    },
    {
      id: "airfield:henderson:label",
      ownerId: "airfield:henderson",
      ownerObstacleId: "airfield:henderson",
      kind: "airfieldLabel",
      text: "Henderson Airfield",
      x: 132,
      y: 60 - 14 * scale,
      textAnchor: "middle",
      scale,
      important: true,
    },
    {
      id: "port:lunga:label",
      ownerId: "port:lunga",
      ownerObstacleId: "port:lunga",
      kind: "portLabel",
      text: "Lunga Point",
      x: 78 + 22 * scale,
      y: 56 + 4 * scale,
      textAnchor: "start",
      scale,
    },
    {
      id: "unit:marines:label",
      ownerId: "unit:marines",
      ownerObstacleId: "unit:marines",
      kind: "unitLabel",
      text: "1st Marines",
      x: 132,
      y: 136 - 12 * scale,
      textAnchor: "middle",
      scale,
      selected: true,
      forceVisible: true,
    },
    {
      id: "unit:hq:label",
      ownerId: "unit:hq",
      ownerObstacleId: "unit:hq",
      kind: "unitLabel",
      text: "Americal HQ",
      x: 184 + 24 * scale,
      y: 146 + 4 * scale,
      textAnchor: "start",
      scale,
      important: true,
    },
    {
      id: "unit:recon:label",
      ownerId: "unit:recon",
      ownerObstacleId: "unit:recon",
      kind: "unitLabel",
      text: "Recon Troop",
      x: 232 + 24 * scale,
      y: 128 + 4 * scale,
      textAnchor: "start",
      scale,
    },
    {
      id: "region:lunga:label",
      ownerId: "region:lunga",
      kind: "regionLabel",
      text: "Lunga Perimeter",
      x: 150,
      y: 34,
      textAnchor: "middle",
      scale,
      important: true,
    },
    {
      id: "water:sound:label",
      ownerId: "water:sound",
      kind: "waterLabel",
      text: "Ironbottom Sound",
      x: 62,
      y: 176,
      textAnchor: "start",
      scale,
      important: true,
    },
  ];
}

function markerClass(kind: string) {
  if (kind === "objective") {
    return "shell-maplabels__marker is-objective";
  }
  if (kind === "airfield") {
    return "shell-maplabels__marker is-airfield";
  }
  if (kind === "port") {
    return "shell-maplabels__marker is-port";
  }
  return "shell-maplabels__marker is-unit";
}

export default function MapLabelHarnessPanel() {
  const [open, setOpen] = useState(false);
  const [zoomPreset, setZoomPreset] = useState(ZOOM_PRESETS[1]);
  const scale = zoomPreset.id === "far" ? 0.94 : zoomPreset.id === "close" ? 1.06 : 1;
  const declutter = useMemo(
    () => buildDeclutteredLabels(buildPreviewCandidates(scale), buildPreviewObstacles(scale), { zoom: zoomPreset.zoom }),
    [scale, zoomPreset],
  );
  const visibleIds = declutter.visibleIds;

  return (
    <div className={"shell-maplabels" + (open ? " is-open" : "")}>
      <button
        type="button"
        className="shell-maplabels__toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="shell-map-label-preview"
      >
        <span className="shell-map__legend-title">Label Declutter</span>
        <span className="shell-map__legend-state">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="shell-maplabels__body" id="shell-map-label-preview">
          <div className="shell-maplabels__toolbar" role="group" aria-label="Map label zoom preview">
            {ZOOM_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={"shell-maplabels__chip" + (zoomPreset.id === preset.id ? " is-active" : "")}
                onClick={() => setZoomPreset(preset)}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="shell-maplabels__note">
            {declutter.policy.note} Visible {declutter.accepted.length}, suppressed {declutter.blocked.length}.
          </div>

          <svg className="shell-maplabels__scene" viewBox="0 0 280 200" role="img" aria-label="Dense operational map label declutter preview">
            <rect className="shell-maplabels__field" x="0" y="0" width="280" height="200" rx="8" />
            <path className="shell-maplabels__river" d="M10 100 C60 86, 112 90, 176 106 S252 136, 272 126" />
            {PREVIEW_MARKERS.map((marker) => (
              <g className={markerClass(marker.kind)} key={marker.id} transform={`translate(${marker.x}, ${marker.y})`}>
                {marker.kind === "objective" ? <circle r="7" /> : null}
                {marker.kind === "airfield" ? <rect x="-10" y="-6" width="20" height="12" rx="2" /> : null}
                {marker.kind === "port" ? <rect x="-9" y="-7" width="18" height="14" rx="3" /> : null}
                {marker.kind === "unit" ? <rect x="-14" y="-8" width="28" height="16" rx="3" /> : null}
              </g>
            ))}
            {buildPreviewCandidates(scale).map((label) => (
              visibleIds.has(label.id) ? (
                <text
                  key={label.id}
                  className={"shell-maplabels__text is-" + label.kind}
                  x={label.x}
                  y={label.y}
                  textAnchor={label.textAnchor as "start" | "middle" | "end"}
                >
                  {label.text}
                </text>
              ) : null
            ))}
          </svg>

          <div className="shell-maplabels__policy-grid">
            <div className="shell-maplabels__policy-card">
              <strong>Settlements</strong>
              <span>{declutter.policy.settlementLabels}</span>
            </div>
            <div className="shell-maplabels__policy-card">
              <strong>Airfields</strong>
              <span>{declutter.policy.airfieldLabels}</span>
            </div>
            <div className="shell-maplabels__policy-card">
              <strong>Units</strong>
              <span>{declutter.policy.unitLabels}</span>
            </div>
            <div className="shell-maplabels__policy-card">
              <strong>Regions</strong>
              <span>{declutter.policy.regionLabels}</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
