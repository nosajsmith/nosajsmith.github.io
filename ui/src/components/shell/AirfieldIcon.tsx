import type { CSSProperties } from "react";
import { buildAirfieldIconPresentation } from "../../map/airfieldIcon.js";

type AirfieldTier = "minor_airstrip" | "operational_airfield" | "major_airbase";
type AirfieldControlState = "friendly" | "enemy" | "contested" | "neutral" | "unknown";
type AirfieldDamageState = "ready" | "damaged" | "destroyed";
type AirfieldReadinessBand = "ready" | "limited" | "low" | "unknown";

type AirfieldIconProps = {
  tier?: AirfieldTier | null;
  controlState?: AirfieldControlState | null;
  damageState?: AirfieldDamageState | null;
  readinessBand?: AirfieldReadinessBand | null;
  sortieActive?: boolean;
  zoom?: number;
  placement?: "map" | "legend" | "harness";
};

function RunwayCore({ tier }: { tier: AirfieldTier }) {
  if (tier === "minor_airstrip") {
    return (
      <>
        <rect className="shell-map__airfield-strip" x="-7.8" y="-2.2" width="15.6" height="4.4" rx="1.2" />
        <path className="shell-map__airfield-runway" d="M-6.1 0 H6.1" />
      </>
    );
  }

  if (tier === "major_airbase") {
    return (
      <>
        <rect className="shell-map__airfield-frame is-major" x="-12" y="-8.4" width="24" height="16.8" rx="3.1" />
        <rect className="shell-map__airfield-strip" x="-3.2" y="-7.4" width="6.4" height="14.8" rx="1.4" />
        <rect className="shell-map__airfield-strip is-cross" x="-9.2" y="-2.1" width="18.4" height="4.2" rx="1.2" />
      </>
    );
  }

  return (
    <>
      <rect className="shell-map__airfield-frame" x="-10" y="-7.1" width="20" height="14.2" rx="2.6" />
      <rect className="shell-map__airfield-strip" x="-2.3" y="-6.1" width="4.6" height="12.2" rx="1.2" />
    </>
  );
}

function ReadinessMarker({ band }: { band: AirfieldReadinessBand }) {
  if (band === "unknown") {
    return null;
  }
  return <path className={`shell-map__airfield-readiness is-${band}`} d="M-7.4 9.4 H7.4" />;
}

export default function AirfieldIcon({
  tier = "operational_airfield",
  controlState = "unknown",
  damageState = "ready",
  readinessBand = "unknown",
  sortieActive = false,
  zoom = 1,
  placement = "map",
}: AirfieldIconProps) {
  const presentation = buildAirfieldIconPresentation({
    tier,
    controlState,
    damageState,
    readinessBand,
    sortieActive,
    zoom,
    placement,
  });
  const style = {
    "--shell-airfield-stroke": String(presentation.strokeWidth),
  } as CSSProperties;

  return (
    <g
      className={
        `shell-map__airfield-icon is-${presentation.tier} is-${presentation.controlState} is-${presentation.damageState} is-${presentation.readinessBand}`
        + (presentation.sortieActive ? " is-sortie-active" : "")
      }
      transform={`scale(${presentation.scale})`}
      style={style}
      aria-hidden="true"
    >
      <RunwayCore tier={presentation.tier as AirfieldTier} />
      {presentation.showStatus ? <ReadinessMarker band={presentation.readinessBand as AirfieldReadinessBand} /> : null}
      {presentation.sortieActive && presentation.showStatus ? (
        <path className="shell-map__airfield-sortie" d="M8.5 -7.5 L12 -7.5 L12 -4 L15.2 -4 L10.2 1.1 L10.2 -2.1 L7 -2.1 Z" />
      ) : null}
      {presentation.showStatus && presentation.damageState === "damaged" ? (
        <path className="shell-map__airfield-damage is-damaged" d="M-10.1 7.7 L10.1 -7.7" />
      ) : null}
      {presentation.showStatus && presentation.damageState === "destroyed" ? (
        <path className="shell-map__airfield-damage is-destroyed" d="M-9.8 -7.3 L9.8 7.3 M9.8 -7.3 L-9.8 7.3" />
      ) : null}
    </g>
  );
}
