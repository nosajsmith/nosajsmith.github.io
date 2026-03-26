import { buildUnitCounterFramePresentation } from "../../map/unitCounterFrame.js";
import UnitCounterSymbol from "./UnitCounterSymbol";

type UnitCounterFrameProps = {
  echelon: "company" | "battalion" | "regiment" | "brigade" | "division" | "corps";
  isHeadquarters?: boolean;
  symbol?: "formation" | "infantry" | "headquarters" | "recon" | "artillery" | "engineer" | "armor" | "mechanized" | "anti_tank" | "support" | null;
  code?: string | null;
  showCode?: boolean;
  zoom?: number;
};

export default function UnitCounterFrame({ echelon, isHeadquarters = false, symbol = null, code = null, showCode = true, zoom = 1 }: UnitCounterFrameProps) {
  const frame = buildUnitCounterFramePresentation({ echelon, isHeadquarters, zoom });

  return (
    <>
      <path className="shell-map__unit-body" d={frame.outerPath} />
      {frame.innerPath ? <path className="shell-map__unit-frame-inner" d={frame.innerPath} /> : null}
      {frame.headerRulePath ? <path className="shell-map__unit-frame-rule" d={frame.headerRulePath} /> : null}
      <UnitCounterSymbol symbol={symbol} zoom={zoom} placement="counter" />
      <path className="shell-map__unit-divider" d={frame.dividerPath} />
      {frame.hqPennant ? (
        <>
          <path className="shell-map__unit-hq-staff" d={frame.hqPennant.staff} />
          <path className="shell-map__unit-hq-pennant" d={frame.hqPennant.pennant} />
        </>
      ) : null}
      {showCode && code ? (
        <text className="shell-map__unit-code" x="0" y={frame.codeY} textAnchor="middle">
          {code}
        </text>
      ) : null}
    </>
  );
}
