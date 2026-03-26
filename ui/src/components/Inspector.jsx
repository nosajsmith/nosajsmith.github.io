import React from "react";
import { selectedUnitCue } from "../lib/demo_polish.js";

function kv(label, value) {
  return (
    <div className="kv" key={label}>
      <div className="kv-k">{label}</div>
      <div className="kv-v">{String(value ?? "")}</div>
    </div>
  );
}

function formatPair(pair) {
  if (!pair || (pair.on_hand == null && pair.authorized == null)) {
    return "Not reported";
  }
  const onHand = pair.on_hand == null ? "?" : pair.on_hand;
  const authorized = pair.authorized == null ? "?" : pair.authorized;
  return `${onHand} / ${authorized}`;
}

function formatAmmoRounds(ammoRounds) {
  if (!ammoRounds || !Object.keys(ammoRounds).length) {
    return "Not reported";
  }
  return Object.entries(ammoRounds)
    .map(([kind, rounds]) => `${kind} ${rounds}`)
    .join(" • ");
}

function formatLossSummary(losses) {
  if (!losses?.categories) {
    return "No categorized losses reported";
  }
  return Object.entries(losses.categories)
    .filter(([, value]) => Number(value) > 0)
    .map(([kind, value]) => `${kind.replaceAll("_", " ")} ${value}`)
    .join(" • ") || "No categorized losses reported";
}

export default function Inspector({ unit, onIssueOrder = null, orderBusy = false }) {
  if (!unit) {
    return (
      <div className="inspector">
        <div className="inspector-title">Inspector</div>
        <div className="inspector-muted">No unit selected.</div>
      </div>
    );
  }

  const id = unit.id ?? unit.uid ?? unit.name;
  const x = unit.x ?? unit.pos_x ?? unit.pos?.x;
  const y = unit.y ?? unit.pos_y ?? unit.pos?.y;
  const detail = unit.raw?.player_detail ?? {};
  const showAltSupply = detail.supply_days_defensive != null || detail.supply_days_resting != null;
  const artillery = detail.artillery;
  const orderLifecycle = detail.order_lifecycle;
  const g7Losses = detail.g7_losses;
  const recentLogs = detail.recent_logs || [];
  const unitCue = selectedUnitCue(unit);

  return (
    <div className="inspector">
      <div className="inspector-title">Inspector</div>

      <div className="inspector-block">
        {kv("Name", unit.name ?? "")}
        {kv("ID", id)}
        {kv("X", x)}
        {kv("Y", y)}
      </div>

      <div className="inspector-block">
        <div className="inspector-subtitle">Assessment</div>
        <div className="inspector-callout">{unitCue}</div>
      </div>

      {onIssueOrder ? (
        <div className="inspector-block">
          <div className="inspector-subtitle">Orders</div>
          <div className="row">
            <button className="btn" onClick={() => onIssueOrder("attack")} disabled={orderBusy}>Probe</button>
            <button className="btn" onClick={() => onIssueOrder("reposition")} disabled={orderBusy}>Advance</button>
            <button className="btn" onClick={() => onIssueOrder("rest")} disabled={orderBusy}>Rest</button>
          </div>
        </div>
      ) : null}

      <div className="inspector-block">
        <div className="inspector-subtitle">Combat Power</div>
        {kv("Men", formatPair(detail.men))}
        {kv("Tanks", formatPair(detail.tanks))}
        {kv("Guns", formatPair(detail.guns))}
        {kv("Vehicles", formatPair(detail.vehicles))}
        {kv("TOE", detail.toe_pct != null ? `${detail.toe_pct}%` : "Not reported")}
        {kv("Shortfalls", detail.missing_summary ?? "Not reported")}
      </div>

      <div className="inspector-block">
        <div className="inspector-subtitle">Readiness</div>
        {kv("Supply", detail.supply_days_current != null ? `${detail.supply_days_current.toFixed(1)} days` : "Not reported")}
        {showAltSupply ? kv("If defending/resting", `${(detail.supply_days_defensive ?? 0).toFixed(1)} / ${(detail.supply_days_resting ?? 0).toFixed(1)} days`) : null}
        {kv("LOC", detail.loc_status ?? "Unknown")}
        {kv("Morale", detail.morale_band ?? "Not reported")}
        {kv("Readiness", detail.readiness_band ?? "Not reported")}
        {kv("Fatigue trend", detail.fatigue_trend ?? "Not reported")}
      </div>

      {artillery ? (
        <div className="inspector-block">
          <div className="inspector-subtitle">Artillery</div>
          {kv("Ammo", formatAmmoRounds(artillery.ammo_rounds))}
          {kv("Fire policy", artillery.fire_policy ?? "Not reported")}
          {kv("Estimated endurance", artillery.endurance_days != null ? `${artillery.endurance_days.toFixed(1)} days` : "Not reported")}
        </div>
      ) : null}

      {g7Losses ? (
        <div className="inspector-block">
          <div className="inspector-subtitle">G-7 Losses</div>
          {kv("Summary", g7Losses.summary ?? formatLossSummary(g7Losses))}
          {kv("Destroyed", g7Losses.categories?.destroyed ?? 0)}
          {kv("Damaged", g7Losses.categories?.damaged ?? 0)}
          {kv("Abandoned", g7Losses.categories?.abandoned ?? 0)}
          {kv("Operational attrition", g7Losses.categories?.operational_attrition ?? 0)}
          {kv("Retreat losses", g7Losses.categories?.retreat_losses ?? 0)}
        </div>
      ) : null}

      {orderLifecycle ? (
        <div className="inspector-block">
          <div className="inspector-subtitle">Command Log</div>
          {kv("Order state", orderLifecycle.state ?? "Unknown")}
          {kv("Tracked orders", (orderLifecycle.orders || []).length || 1)}
          {orderLifecycle.delay_reason ? kv("Delay reason", orderLifecycle.delay_reason) : null}
          {(orderLifecycle.log || []).length ? (
            <div className="inspector-log">
              {orderLifecycle.log.map((entry, idx) => (
                <div className="inspector-log-entry" key={`${entry.state}-${idx}`}>
                  <div className="inspector-log-state">{entry.state}</div>
                  <div className="inspector-log-msg">{entry.message}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {recentLogs.length ? (
        <div className="inspector-block">
          <div className="inspector-subtitle">Loss Summary</div>
          <div className="inspector-log">
            {recentLogs.map((entry, idx) => (
              <div className="inspector-log-entry" key={`${entry.type || "log"}-${idx}`}>
                <div className="inspector-log-state">{entry.type || "Log"}</div>
                <div className="inspector-log-msg">{entry.message}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
