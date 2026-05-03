import type { ViewSnapshot } from "../../types/viewSnapshot";
import type { TrackedDemoOperation } from "./operations_planner_types";
import { summarizeOperationsBoard } from "./operations_board.js";

type OperationsBoardProps = {
  snapshot: ViewSnapshot;
  operations: TrackedDemoOperation[];
};

function renderRows(rows: Array<{ label?: string; title?: string; value?: string | number | null; detail?: string | null }>, emptyLabel: string) {
  if (!rows.length) {
    return <div className="shell-empty">{emptyLabel}</div>;
  }

  return (
    <div className="shell-opsboard__list">
      {rows.map((row, index) => (
        <div className="shell-opsboard__row" key={`${row.label ?? row.title ?? "row"}-${index}`}>
          <span>{row.label ?? row.title}</span>
          <strong>{row.value}</strong>
          {row.detail ? <small>{row.detail}</small> : null}
        </div>
      ))}
    </div>
  );
}

export default function OperationsBoard({ snapshot, operations }: OperationsBoardProps) {
  const board = summarizeOperationsBoard(snapshot, operations);
  const latestReports = board.recent.slice(0, 3).map((report) => ({
    title: report.title,
    value: report.severity,
    detail: report.summary,
  }));
  const objectiveRows = board.objectiveTruth.key.slice(0, 4).map((objective) => ({
    label: objective.name,
    value: objective.state,
    detail: objective.side ? `Side ${objective.side}` : null,
  }));
  const hotspotRows = board.hotspots.slice(0, 4).map((hotspot) => ({
    label: hotspot.label,
    value: hotspot.state,
    detail: hotspot.detail,
  }));

  return (
    <section className="shell-opsboard shell-card" aria-label="Grease Board / Operations Board">
      <header className="shell-opsboard__head">
        <div>
          <div className="shell-eyebrow">Grease Board / Operations Board V0</div>
          <h3 className="shell-opsboard__title">{board.identity.scenarioName}</h3>
          <p className="shell-card__body">{board.identity.operationName}</p>
        </div>
        <div className="shell-opsboard__source">{board.identity.source}</div>
      </header>

      <div className="shell-opsboard__metrics">
        <div className="shell-stat">
          <span>Campaign</span>
          <strong>{board.score.status}</strong>
        </div>
        <div className="shell-stat">
          <span>Turn / Day / Time</span>
          <strong>{board.timing.turnLabel} • {board.timing.dayLabel} • {board.timing.hourLabel}</strong>
        </div>
        <div className="shell-stat">
          <span>Score</span>
          <strong>{board.score.leader}</strong>
        </div>
        <div className="shell-stat">
          <span>AI / Command</span>
          <strong>{board.command.aiEnabled ? "AI Enabled" : "AI Disabled"}</strong>
        </div>
      </div>

      <div className="shell-opsboard__body">
        <section className="shell-opsboard__panel">
          <div className="shell-opsboard__subhead">Objective Truth</div>
          {renderRows(objectiveRows, "No objectives exposed on the current snapshot.")}
        </section>

        <section className="shell-opsboard__panel">
          <div className="shell-opsboard__subhead">Pressure / Hotspots</div>
          <div className="shell-opsboard__summary">{board.pressure.summary ?? "Pressure summary unavailable"}</div>
          {renderRows(hotspotRows, "No objective pressure rows exposed.")}
        </section>

        <section className="shell-opsboard__panel">
          <div className="shell-opsboard__subhead">AI / Command Picture</div>
          <div className="shell-opsboard__signal">
            <strong>{board.command.headline}</strong>
            <span>{board.command.detail}</span>
            <small>{board.command.aiIntent}</small>
          </div>
        </section>

        <section className="shell-opsboard__panel">
          <div className="shell-opsboard__subhead">Recent Operational Picture</div>
          {renderRows(latestReports, "No recent reports exposed.")}
        </section>
      </div>
    </section>
  );
}
