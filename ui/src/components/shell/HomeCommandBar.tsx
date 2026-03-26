import type { ViewSnapshot } from "../../types/viewSnapshot";
import type { TrackedDemoOperation } from "./operations_planner_types";
import { summarizeHomeCommandBar } from "./home_command_bar_summary.js";
import { summarizeLandOperations } from "./land_operations_summary.js";

type HomeCommandBarProps = {
  snapshot: ViewSnapshot;
  operations: TrackedDemoOperation[];
  activeBranch: "Theatre" | "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements";
  onSelectBranch: (branch: "Theatre" | "Land" | "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements") => void;
};

export default function HomeCommandBar({ snapshot, operations, activeBranch, onSelectBranch }: HomeCommandBarProps) {
  const summary = summarizeHomeCommandBar(snapshot, operations);
  const land = summarizeLandOperations(snapshot, operations);
  const landStateLabel = land.available
    ? `${land.overview.metrics[0]?.value ?? "0"} formations tracked`
    : "Land picture incomplete";
  const landSupportLine = land.locAlerts.rows[0]
    ? `Current hotspot ${land.locAlerts.rows[0].name}. ${land.locAlerts.rows[0].status}.`
    : land.oob.headline;

  return (
    <section className="shell-commandbar" aria-label="Home screen command bar">
      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--theatre" + (activeBranch === "Theatre" ? " is-active" : "")}
        onClick={() => onSelectBranch("Theatre")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Operations</div>
        </div>
        <div className="shell-commandbar__state">{summary.operations.status}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{summary.operations.detail}</div>
      </button>

      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--logistics" + (activeBranch === "Logistics" ? " is-active" : "")}
        onClick={() => onSelectBranch("Logistics")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Logistics</div>
        </div>
        <div className="shell-commandbar__state">{summary.logistics.label}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{summary.logistics.detail}</div>
      </button>

      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--intelligence" + (activeBranch === "Intelligence" ? " is-active" : "")}
        onClick={() => onSelectBranch("Intelligence")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Intelligence</div>
        </div>
        <div className="shell-commandbar__state">{summary.intelligence.label}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{summary.intelligence.detail}</div>
      </button>

      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--air" + (activeBranch === "Air" ? " is-active" : "")}
        onClick={() => onSelectBranch("Air")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Air</div>
        </div>
        <div className="shell-commandbar__state">{summary.air.label}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{summary.air.detail}</div>
      </button>

      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--land" + (activeBranch === "Land" ? " is-active" : "")}
        onClick={() => onSelectBranch("Land")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Land</div>
        </div>
        <div className="shell-commandbar__state">{landStateLabel}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{landSupportLine}</div>
      </button>

      <button
        type="button"
        className={"shell-commandbar__module shell-commandbar__module--naval" + (activeBranch === "Naval" ? " is-active" : "")}
        onClick={() => onSelectBranch("Naval")}
      >
        <div className="shell-commandbar__head">
          <div className="shell-commandbar__title">Naval</div>
        </div>
        <div className="shell-commandbar__state">{summary.naval.label}</div>
        <div className="shell-commandbar__support shell-commandbar__body">{summary.naval.detail}</div>
      </button>
    </section>
  );
}
