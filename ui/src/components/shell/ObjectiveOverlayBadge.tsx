import { MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER, getMapZoomTier } from "../../map/designTokens.js";

type ObjectiveOverlayBadgeProps = {
  category?: "primary" | "secondary" | "supply" | "political" | "strategic" | null;
  importanceTier?: number | null;
  contested?: boolean;
  zoom?: number;
};

export default function ObjectiveOverlayBadge({
  category = "secondary",
  importanceTier = 1,
  contested = false,
  zoom = 1,
}: ObjectiveOverlayBadgeProps) {
  const scale = MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER[getMapZoomTier(zoom).id] ?? MAP_OBJECTIVE_BADGE_SCALE_BY_ZOOM_TIER.operational;
  const pips = Math.max(0, Math.min(3, Number(importanceTier || 0)));

  return (
    <g
      className={
        "shell-map__objective-badge"
        + ` is-${category || "secondary"}`
        + (contested ? " is-contested" : "")
      }
      transform={`scale(${scale})`}
      aria-hidden="true"
    >
      {category === "strategic" ? (
        <>
          <circle className="shell-map__objective-badge-ring" r="13.6" />
          <path className="shell-map__objective-badge-accent" d="M-7.4 -13.8 H7.4" />
        </>
      ) : null}
      {category === "political" ? (
        <>
          <circle className="shell-map__objective-badge-ring" r="12.8" />
          <path className="shell-map__objective-badge-accent" d="M0 -13.2 V13.2 M-5.8 0 H5.8" />
        </>
      ) : null}
      {category === "primary" ? (
        <>
          <path className="shell-map__objective-badge-ring" d="M0 -13.2 L12.6 0 L0 13.2 L-12.6 0 Z" />
          <path className="shell-map__objective-badge-accent" d="M-6.6 -13.2 H6.6 M-6.6 13.2 H6.6" />
        </>
      ) : null}
      {category === "secondary" ? (
        <circle className="shell-map__objective-badge-ring" r="11.7" />
      ) : null}
      {category === "supply" ? (
        <>
          <rect className="shell-map__objective-badge-ring" x="-11.8" y="-11.8" width="23.6" height="23.6" rx="4.4" />
          <path className="shell-map__objective-badge-accent" d="M8.4 -2.2 H12.6 V2.2 H8.4 Z M7.2 2.8 H13.8 V6.2 H7.2 Z" />
        </>
      ) : null}
      {pips > 0 ? (
        <g className="shell-map__objective-badge-pips">
          {Array.from({ length: pips }).map((_, index) => {
            const x = (index - (pips - 1) / 2) * 5.4;
            return <circle className="shell-map__objective-badge-pip" cx={x} cy="-16.8" r="2" key={index} />;
          })}
        </g>
      ) : null}
    </g>
  );
}
