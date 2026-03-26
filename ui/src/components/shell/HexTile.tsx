import { useId } from "react";
import type { CSSProperties, SVGProps } from "react";
import { buildHexTilePresentation, HEX_TILE_PATHS, HEX_TILE_VIEWBOX } from "../../map/hexTile.js";

type HexTileProps = {
  terrain?: "plain" | "plains" | "forest" | "mountain" | "urban" | "water" | "river" | "river-crossing" | "rough" | "hill" | "hills" | "coast" | "ridge" | "sea" | "field";
  zoom?: number;
  gridVisible?: boolean;
  showTexture?: boolean;
  riverCrossing?: boolean;
  hovered?: boolean;
  selected?: boolean;
  friendlyZoc?: boolean;
  enemyZoc?: boolean;
  contested?: boolean;
  moveTarget?: boolean;
  attackTarget?: boolean;
  disabled?: boolean;
  className?: string;
  label?: string;
};

function overlayPathForShape(shape: string) {
  if (shape === "inner") {
    return HEX_TILE_PATHS.inner;
  }
  if (shape === "selectionTicks") {
    return HEX_TILE_PATHS.selectionTicks;
  }
  if (shape === "movePips") {
    return HEX_TILE_PATHS.movePips;
  }
  if (shape === "attackCrosshair") {
    return HEX_TILE_PATHS.attackCrosshair;
  }
  if (shape === "attackBrackets") {
    return HEX_TILE_PATHS.attackBrackets;
  }
  if (shape === "riverChannel") {
    return HEX_TILE_PATHS.riverChannel;
  }
  if (shape === "riverCrossing") {
    return HEX_TILE_PATHS.riverCrossing;
  }
  return HEX_TILE_PATHS.outer;
}

function texturePatternProps(terrain: string): SVGProps<SVGPatternElement>["children"] {
  if (terrain === "mountain") {
    return (
      <>
        <path d="M-4 16 L16 -4 M8 24 L28 4 M20 32 L40 12" className="shell-hextile__texture-line" />
        <path d="M0 20 L20 0 M12 28 L32 8" className="shell-hextile__texture-line" />
      </>
    );
  }
  if (terrain === "coast" || terrain === "water") {
    return (
      <>
        <path d="M0 6 C4 4,8 8,12 6 S20 8,24 6" className="shell-hextile__texture-line" />
        <path d="M0 14 C4 12,8 16,12 14 S20 16,24 14" className="shell-hextile__texture-line" />
      </>
    );
  }
  if (terrain === "forest") {
    return (
      <>
        <path d="M2 18 L8 10 L14 18 M12 20 L18 12 L24 20" className="shell-hextile__texture-line" />
        <path d="M6 30 L12 22 L18 30 M18 32 L24 24 L30 32" className="shell-hextile__texture-line" />
      </>
    );
  }
  if (terrain === "urban") {
    return (
      <>
        <path d="M4 6 H10 V14 H4 Z M14 8 H20 V16 H14 Z M8 18 H16 V26 H8 Z" className="shell-hextile__texture-block" />
        <path d="M18 20 H24 V28 H18 Z M4 28 H10 V36 H4 Z M14 30 H22 V38 H14 Z" className="shell-hextile__texture-block" />
      </>
    );
  }
  if (terrain === "hills") {
    return (
      <>
        <path d="M0 12 C6 6,14 6,20 12" className="shell-hextile__texture-line" />
        <path d="M4 24 C10 18,18 18,24 24" className="shell-hextile__texture-line" />
      </>
    );
  }
  if (terrain === "rough") {
    return (
      <>
        <path d="M2 10 L8 14 L14 8 L20 12" className="shell-hextile__texture-line" />
        <path d="M4 24 L10 20 L16 26 L22 22" className="shell-hextile__texture-line" />
        <path d="M6 34 L12 30 L18 36 L24 32" className="shell-hextile__texture-line" />
      </>
    );
  }
  return (
    <>
      <path d="M4 0 V24 M12 0 V24 M20 0 V24" className="shell-hextile__texture-line" />
      <path d="M0 6 H24 M0 14 H24" className="shell-hextile__texture-line is-soft" />
    </>
  );
}

export default function HexTile(props: HexTileProps) {
  const textureId = useId().replace(/:/g, "");
  const presentation = buildHexTilePresentation(props);
  const svgStyle = {
    opacity: presentation.fadeOpacity,
  } satisfies CSSProperties;

  return (
    <svg
      className={"shell-hextile" + (props.className ? ` ${props.className}` : "")}
      viewBox={HEX_TILE_VIEWBOX.viewBox}
      role="img"
      aria-label={props.label || "Hex tile"}
      style={svgStyle}
    >
      <defs>
        <pattern id={`hex-texture-${textureId}`} width="24" height="24" patternUnits="userSpaceOnUse">
          {texturePatternProps(presentation.terrain)}
        </pattern>
      </defs>

      <path className={`shell-hextile__terrain ${presentation.terrainClass}`} d={HEX_TILE_PATHS.outer} />

      {presentation.textureVisible ? (
        <path className="shell-hextile__texture" d={HEX_TILE_PATHS.outer} fill={`url(#hex-texture-${textureId})`} />
      ) : null}

      <path
        className="shell-hextile__stroke shell-hextile__stroke--minor"
        d={HEX_TILE_PATHS.outer}
        style={{
          strokeWidth: `${presentation.minorBorderWidth}px`,
          opacity: presentation.minorBorderOpacity,
        }}
      />
      <path
        className="shell-hextile__stroke shell-hextile__stroke--major"
        d={HEX_TILE_PATHS.outer}
        style={{
          strokeWidth: `${presentation.majorBorderWidth}px`,
          opacity: presentation.majorBorderOpacity,
        }}
      />

      {presentation.overlays.map((overlay) => (
        <path
          key={overlay.id}
          className={`shell-hextile__stroke shell-hextile__stroke--${overlay.id}`}
          d={overlayPathForShape(overlay.shape)}
          style={{
            stroke: `var(${overlay.strokeVar})`,
            strokeWidth: `${overlay.strokeWidth}px`,
            opacity: overlay.opacity,
            strokeDasharray: overlay.dashArray || undefined,
          }}
        />
      ))}
    </svg>
  );
}
