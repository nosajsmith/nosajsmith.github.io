import type { CSSProperties } from "react";
import { buildSettlementIconPresentation } from "../../map/settlementIcon.js";

type SettlementTier = "village" | "town" | "city" | "major_city" | "capital";
type SettlementControlState = "friendly" | "enemy" | "contested" | "neutral" | "unknown";

type SettlementIconProps = {
  tier?: SettlementTier | null;
  controlState?: SettlementControlState | null;
  zoom?: number;
  placement?: "map" | "legend" | "harness";
  damaged?: boolean;
  supplyHub?: boolean;
  showValueMarks?: boolean;
};

function VillageBody() {
  return (
    <>
      <path className="shell-map__settlement-roof" d="M-5.1 -1.2 L0 -5.9 L5.1 -1.2 Z" />
      <rect className="shell-map__settlement-body" x="-4.3" y="-1.2" width="8.6" height="6.2" rx="1.2" />
    </>
  );
}

function TownBody() {
  return (
    <>
      <path className="shell-map__settlement-roof" d="M-7.2 -1.3 L-2.1 -5.4 L2.1 -5.4 L7.2 -1.3 Z" />
      <rect className="shell-map__settlement-body" x="-6.2" y="-1.3" width="12.4" height="6.7" rx="1.35" />
      <rect className="shell-map__settlement-body is-annex" x="-8.1" y="1.1" width="3.1" height="4.1" rx="0.8" />
    </>
  );
}

function CityBody() {
  return (
    <>
      <rect className="shell-map__settlement-body" x="-7.2" y="-0.2" width="4.4" height="5.9" rx="0.95" />
      <rect className="shell-map__settlement-body" x="-2.2" y="-3.8" width="4.6" height="9.5" rx="0.95" />
      <rect className="shell-map__settlement-body" x="3" y="0.8" width="4.2" height="4.9" rx="0.95" />
    </>
  );
}

function MajorRing() {
  return <rect className="shell-map__settlement-ring is-major" x="-10.3" y="-8.8" width="20.6" height="17.6" rx="3.6" />;
}

function CapitalAccent() {
  return (
    <path
      className="shell-map__settlement-key"
      d="M0 -11.4 L1.9 -8.2 L5.4 -8.4 L3 -5.8 L4.3 -2.5 L0 -4.4 L-4.3 -2.5 L-3 -5.8 L-5.4 -8.4 L-1.9 -8.2 Z"
    />
  );
}

function ControlCue({ controlState }: { controlState: SettlementControlState }) {
  if (controlState === "friendly") {
    return <path className="shell-map__settlement-control is-friendly" d="M-6.5 -8.2 H6.5" />;
  }
  if (controlState === "enemy") {
    return <path className="shell-map__settlement-control is-enemy" d="M-6.5 8.2 H6.5" />;
  }
  if (controlState === "contested") {
    return <path className="shell-map__settlement-control is-contested" d="M-8 -4.2 V4.2 M8 -4.2 V4.2" />;
  }
  if (controlState === "neutral") {
    return <circle className="shell-map__settlement-control is-neutral" cx="0" cy="0" r="9.1" />;
  }
  return <path className="shell-map__settlement-control is-unknown" d="M-5.6 0 H5.6 M0 -5.6 V5.6" />;
}

export default function SettlementIcon({
  tier = "town",
  controlState = "unknown",
  zoom = 1,
  placement = "map",
  damaged = false,
  supplyHub = false,
  showValueMarks = true,
}: SettlementIconProps) {
  const presentation = buildSettlementIconPresentation({
    tier,
    controlState,
    zoom,
    placement,
    damaged,
    supplyHub,
    showValueMarks,
  });
  const style = {
    "--shell-settlement-stroke": String(presentation.strokeWidth),
  } as CSSProperties;

  return (
    <g
      className={
        `shell-map__settlement-icon is-${presentation.tier} is-${presentation.controlState}`
        + (presentation.damaged ? " is-damaged" : "")
        + (presentation.supplyHub ? " is-supply-hub" : "")
      }
      transform={`scale(${presentation.scale})`}
      style={style}
      aria-hidden="true"
    >
      {presentation.tier === "major_city" || presentation.tier === "capital" ? <MajorRing /> : null}
      <ControlCue controlState={presentation.controlState as SettlementControlState} />
      {presentation.tier === "village" ? <VillageBody /> : null}
      {presentation.tier === "town" ? <TownBody /> : null}
      {presentation.tier === "city" || presentation.tier === "major_city" || presentation.tier === "capital" ? <CityBody /> : null}
      {presentation.tier === "capital" ? <CapitalAccent /> : null}

      {presentation.showValueMarks ? (
        <g className="shell-map__settlement-values">
          {Array.from({ length: presentation.valueMarkCount }).map((_, index) => {
            const offset = (index - (presentation.valueMarkCount - 1) / 2) * 4.2;
            return <circle className="shell-map__settlement-value" key={index} cx={offset} cy="9.8" r="1.15" />;
          })}
        </g>
      ) : null}

      {presentation.supplyHub ? (
        <path className="shell-map__settlement-supply" d="M7.4 -1.2 H10.8 V2.2 H7.4 Z M6.2 2.2 H12 V5.4 H6.2 Z" />
      ) : null}
      {presentation.damaged ? (
        <path className="shell-map__settlement-damage" d="M-10.8 -8.9 H-4.6 V-2.7 Z" />
      ) : null}
    </g>
  );
}
