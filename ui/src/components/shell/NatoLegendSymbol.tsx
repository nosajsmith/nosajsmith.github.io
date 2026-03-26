import AirfieldIcon from "./AirfieldIcon";
import UnitCounterSymbol from "./UnitCounterSymbol";
import SettlementIcon from "./SettlementIcon";

type LegendForceSlot = "primary" | "secondary" | "neutral";
type LegendUnitSymbol =
  | "formation"
  | "infantry"
  | "mechanized"
  | "headquarters"
  | "recon"
  | "artillery"
  | "engineer"
  | "armor"
  | "anti_tank"
  | "support";
type LegendSettlementTier = "village" | "town" | "city" | "major_city" | "capital";
type LegendSettlementControlState = "friendly" | "enemy" | "contested" | "neutral" | "unknown";
type LegendAirfieldTier = "minor_airstrip" | "operational_airfield" | "major_airbase";
type LegendAirfieldDamageState = "ready" | "damaged" | "destroyed";
type LegendAirfieldReadinessBand = "ready" | "limited" | "low" | "unknown";

type NatoLegendSymbolProps =
  | {
      kind: "force";
      slot: LegendForceSlot;
    }
  | {
      kind: "unit";
      symbol: LegendUnitSymbol;
    }
  | {
      kind: "settlement";
      tier: LegendSettlementTier;
      controlState: LegendSettlementControlState;
    }
  | {
      kind: "airfield";
      tier?: LegendAirfieldTier;
      controlState?: LegendSettlementControlState;
      damageState?: LegendAirfieldDamageState;
      readinessBand?: LegendAirfieldReadinessBand;
      sortieActive?: boolean;
    }
  | {
      kind: "port" | "leader";
    };

function FormationFrame({ slot, symbol }: { slot: LegendForceSlot; symbol?: LegendUnitSymbol }) {
  return (
    <svg className="shell-map__legend-symbol" viewBox="0 0 32 20" aria-hidden="true">
      {symbol === "headquarters" ? <path className="shell-map__legend-glyph" d="M16 0 L16 4 M16 1 L22 1" /> : null}
      <rect className={`shell-map__legend-frame is-${slot}`} x="4" y="4" width="24" height="12" rx="2" />
      {symbol ? <UnitCounterSymbol symbol={symbol} placement="legend" x={16} y={10} /> : null}
    </svg>
  );
}

export default function NatoLegendSymbol(props: NatoLegendSymbolProps) {
  if (props.kind === "force") {
    return <FormationFrame slot={props.slot} />;
  }

  if (props.kind === "unit") {
    return <FormationFrame slot="neutral" symbol={props.symbol} />;
  }

  if (props.kind === "settlement") {
    return (
      <svg className="shell-map__legend-symbol" viewBox="0 0 32 20" aria-hidden="true">
        <g transform="translate(16 10)">
          <SettlementIcon tier={props.tier} controlState={props.controlState} placement="legend" />
        </g>
      </svg>
    );
  }

  if (props.kind === "airfield") {
    return (
      <svg className="shell-map__legend-symbol" viewBox="0 0 32 20" aria-hidden="true">
        <g transform="translate(16 10)">
          <AirfieldIcon
            tier={props.tier}
            controlState={props.controlState}
            damageState={props.damageState}
            readinessBand={props.readinessBand}
            sortieActive={props.sortieActive}
            placement="legend"
          />
        </g>
      </svg>
    );
  }

  if (props.kind === "port") {
    return (
      <svg className="shell-map__legend-symbol" viewBox="0 0 32 20" aria-hidden="true">
        <rect className="shell-map__legend-site shell-map__legend-site--port" x="6" y="4" width="20" height="12" rx="2" />
        <path className="shell-map__legend-glyph" d="M16 6 V13 M12 8 C12 11,20 11,20 8 M11 13 H21" />
      </svg>
    );
  }

  return (
    <svg className="shell-map__legend-symbol" viewBox="0 0 32 20" aria-hidden="true">
      <path className="shell-map__legend-leader" d="M4 10 H28" />
    </svg>
  );
}
