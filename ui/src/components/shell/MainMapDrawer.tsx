import { useEffect, useState } from "react";
import type { ViewSnapshot } from "../../types/viewSnapshot";
import type { SnapshotUnit } from "../../types/viewSnapshot";
import { summarizeInspector } from "./inspector_summary.js";
import type { InspectorSelection } from "./inspector_types";
import CommanderScreen from "./CommanderScreen";

type MainMapDrawerProps = {
  snapshot: ViewSnapshot;
  selection: InspectorSelection | null;
  previousSelectedUnit: SnapshotUnit | null;
  previousSnapshotLabel: string | null;
  open: boolean;
  pinned: boolean;
  onOpen: () => void;
  onClose: () => void;
  onTogglePin: () => void;
  onClearSelection: () => void;
};

export default function MainMapDrawer({
  snapshot,
  selection,
  previousSelectedUnit,
  previousSnapshotLabel,
  open,
  pinned,
  onOpen,
  onClose,
  onTogglePin,
  onClearSelection,
}: MainMapDrawerProps) {
  const inspector = summarizeInspector(snapshot, selection, {
    previousUnit: previousSelectedUnit,
    previousSnapshotLabel,
  });
  const [screen, setScreen] = useState<"inspector" | "commander">("inspector");
  const locStateClass = inspector.header.loc?.state ? String(inspector.header.loc.state).trim().toLowerCase() : "";
  const sectionNodes = [];
  let previousGroup: string | null = null;

  if (screen === "inspector") {
    for (const section of inspector.sections) {
      const groupLabel = "group" in section && typeof section.group === "string" && section.group.trim() ? section.group.trim() : null;
      if (groupLabel && groupLabel !== previousGroup) {
        sectionNodes.push(
          <div className="shell-drawer__group-label" key={`group-${section.id}`}>
            {groupLabel}
          </div>,
        );
        previousGroup = groupLabel;
      }

      sectionNodes.push(
        <section className="shell-drawer__section" key={section.id}>
          <div className="shell-drawer__title">{section.title}</div>
          {section.variant === "metric-grid" ? (
            <div className="shell-unitinspector__grid">
              {section.metrics.map((metric) => (
                <div className="shell-unitinspector__metric" key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                </div>
              ))}
            </div>
          ) : section.variant === "count-table" ? (
            <div className="shell-unitinspector__table">
              <div className="shell-unitinspector__table-head">
                <span>Category</span>
                <span>On Hand</span>
                <span>Authorized</span>
              </div>
              {section.rows.map((row) => (
                <div className="shell-unitinspector__table-row" key={row.label}>
                  <span>{row.label}</span>
                  <strong>{row.onHand ?? row.status ?? "Unavailable"}</strong>
                  <strong>{row.authorized ?? row.status ?? "Unavailable"}</strong>
                </div>
              ))}
            </div>
          ) : section.variant === "key-list" ? (
            <div className="shell-unitinspector__list">
              {section.rows.map((row) => (
                <div className="shell-unitinspector__list-row" key={row.label}>
                  <span>{row.label}</span>
                  <strong>{row.value}</strong>
                </div>
              ))}
            </div>
          ) : section.variant === "commander-link" ? (
            <div className="shell-unitinspector__commander-link">
              <div className="shell-unitinspector__commander-link-head">
                <div className="shell-unitinspector__portrait" aria-label={section.commander.portraitLabel}>
                  <span>{section.commander.portraitMonogram}</span>
                </div>
                <div className="shell-unitinspector__dossier-copy">
                  <div className="shell-unitinspector__dossier-rank">{section.commander.rank}</div>
                  <div className="shell-unitinspector__dossier-name">{section.commander.name}</div>
                  <div className="shell-unitinspector__dossier-service">{section.commander.service}</div>
                  <div className="shell-unitinspector__dossier-position">{section.commander.assignment}</div>
                </div>
              </div>
              <div className="shell-unitinspector__note">{section.commander.notes}</div>
              <button type="button" className="shell-button" onClick={() => setScreen("commander")}>
                Open Commander Screen
              </button>
            </div>
          ) : (
            <div className="shell-unitinspector__placeholder">{section.body}</div>
          )}
          {"note" in section && section.note ? <div className="shell-unitinspector__note">{section.note}</div> : null}
        </section>,
      );
    }
  }

  useEffect(() => {
    setScreen("inspector");
  }, [selection?.kind, selection?.id, open]);

  return (
    <aside className={"shell-drawer" + (open ? " is-open" : "") + (pinned ? " is-pinned" : "")} aria-label="Inspector drawer">
      <button
        type="button"
        className="shell-drawer__handle"
        onClick={open ? onClose : onOpen}
        aria-expanded={open}
        aria-controls="shell-detail-drawer-panel"
      >
        <span>Inspector</span>
        <span>{open ? "Hide" : "Open"}</span>
      </button>

      {open ? (
        <div className="shell-drawer__panel" id="shell-detail-drawer-panel">
          <div className="shell-drawer__head">
            <div>
              <div className="shell-eyebrow">{inspector.header.eyebrow}</div>
              <h2 className="shell-panel__title">{inspector.header.title}</h2>
              <div className="shell-drawer__subtitle">{inspector.header.subtitle}</div>
            </div>
            <div className="shell-drawer__actions">
              {selection ? (
                <button type="button" className="shell-button shell-button--secondary" onClick={onClearSelection}>
                  Clear Selection
                </button>
              ) : null}
              <button type="button" className="shell-button shell-button--secondary" onClick={onTogglePin}>
                {pinned ? "Unpin Panel" : "Pin Panel"}
              </button>
              <button type="button" className="shell-button shell-button--secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </div>

          <div className="shell-drawer__body">
            {inspector.selected ? (
              <>
                {screen === "commander" && inspector.commanderScreen ? (
                  <CommanderScreen commander={inspector.commanderScreen} onBack={() => setScreen("inspector")} />
                ) : (
                  <>
                    {inspector.header.loc ? (
                      <div className={"shell-unitinspector__loc" + (locStateClass ? ` shell-unitinspector__loc--${locStateClass}` : "")}>
                        <div className="shell-unitinspector__loc-bar" aria-hidden="true" />
                        <div className="shell-unitinspector__loc-copy">
                          <strong>{inspector.header.loc.label}</strong>
                          <span>{inspector.header.loc.detail}</span>
                        </div>
                      </div>
                    ) : null}
                    {inspector.summary ? (
                      <section className="shell-drawer__summary">
                        <div className="shell-drawer__title">{inspector.summary.title}</div>
                        <div className="shell-unitinspector__summary-grid">
                          {inspector.summary.rows.map((row) => (
                            <div className="shell-unitinspector__summary-item" key={row.label}>
                              <span>{row.label}</span>
                              <strong>{row.value}</strong>
                            </div>
                          ))}
                        </div>
                        {inspector.summary.note ? <div className="shell-drawer__summary-note">{inspector.summary.note}</div> : null}
                      </section>
                    ) : null}
                    {sectionNodes}
                  </>
                )}
              </>
            ) : (
              <section className="shell-drawer__section shell-unitinspector__empty">
                <div className="shell-drawer__title">Inspection State</div>
                <div className="shell-unitinspector__placeholder">
                  No active selection is open. Select a visible unit, objective, airfield, or port marker to review its current state.
                </div>
              </section>
            )}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
