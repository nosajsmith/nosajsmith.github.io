import type { GreaseBoardPayload } from "../../types/greaseBoard";

type GreaseBoardProps = {
  data: GreaseBoardPayload;
  embedded?: boolean;
};

function renderList(items: string[], itemClassName: string, emptyLabel: string) {
  if (!items.length) {
    return <div className="shell-map__greaseboard-empty">{emptyLabel}</div>;
  }

  return (
    <ul className="shell-map__greaseboard-list">
      {items.map((item, index) => (
        <li className={itemClassName} key={`${item}-${index}`}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function GreaseBoard({ data, embedded = false }: GreaseBoardProps) {
  return (
    <section
      className={"shell-map__greaseboard" + (embedded ? " shell-map__greaseboard--embedded" : "")}
      aria-label="Grease board"
    >
      <header className="shell-map__greaseboard-head">
        <div className="shell-map__greaseboard-kicker">Grease Board</div>
        <div className="shell-map__greaseboard-title">Theater Command Brief</div>
      </header>

      <div className="shell-map__greaseboard-section">
        <div className="shell-map__greaseboard-subhead">Situation Overview</div>
        <div className="shell-map__greaseboard-grid">
          <div className="shell-map__greaseboard-row">
            <span>Turn</span>
            <strong>{data.turn}</strong>
          </div>
          <div className="shell-map__greaseboard-row">
            <span>Objective</span>
            <strong>{data.objective}</strong>
          </div>
          <div className="shell-map__greaseboard-row">
            <span>Front</span>
            <strong>{data.front_status}</strong>
          </div>
          <div className="shell-map__greaseboard-row">
            <span>Supply</span>
            <strong>{data.supply_status}</strong>
          </div>
        </div>
      </div>

      <div className="shell-map__greaseboard-effort">
        <div className="shell-map__greaseboard-subhead">Main Effort</div>
        <strong>{data.main_effort}</strong>
      </div>

      <div className="shell-map__greaseboard-section">
        <div className="shell-map__greaseboard-subhead">Active Orders</div>
        {renderList(data.orders, "shell-map__greaseboard-item", "No active orders reported.")}
      </div>

      <div className="shell-map__greaseboard-section">
        <div className="shell-map__greaseboard-subhead">Pressure / Risk Indicators</div>
        {renderList(data.alerts, "shell-map__greaseboard-item shell-map__greaseboard-item--alert", "No immediate alerts reported.")}
      </div>

      {data.staff_notes ? (
        <div className="shell-map__greaseboard-note">
          <div className="shell-map__greaseboard-subhead">Staff Note</div>
          <p>{data.staff_notes}</p>
        </div>
      ) : null}
    </section>
  );
}
