export function nextActionCue(game = {}, objectives = [], selectedUnit = null) {
  if (!game?.started) {
    return "Start the scenario to begin the landing.";
  }

  const detail = selectedUnit?.raw?.player_detail ?? {};
  if (selectedUnit && ((detail.readiness_band === "Fatigued" || detail.readiness_band === "Exhausted") || Number(detail.supply_days_current ?? 99) < 1.5)) {
    return `Rest ${selectedUnit.name || selectedUnit.id} before pushing inland again.`;
  }

  const alliedOpen = (Array.isArray(objectives) ? objectives : []).find(
    (objective) => objective?.side === "ALLIED" && objective?.controlled !== true,
  );
  if (alliedOpen?.label) {
    return `Next: push toward ${alliedOpen.label}.`;
  }

  if (Number(game?.time_remaining ?? 999) <= 24) {
    return "Final window: seize points quickly and avoid unnecessary delay.";
  }

  return "Maintain tempo, watch the AI response, and preserve your best units.";
}

export function selectedUnitCue(selectedUnit = null) {
  if (!selectedUnit) {
    return "Select a unit to inspect readiness, supply, and order posture.";
  }

  const detail = selectedUnit?.raw?.player_detail ?? {};
  const lifecycle = detail.order_lifecycle ?? {};
  const readiness = detail.readiness_band ?? "Unknown";
  const morale = detail.morale_band ?? "Unknown";
  const supply = Number(detail.supply_days_current ?? 0);
  const state = lifecycle.state ? String(lifecycle.state) : "";

  if (state === "Delayed" && lifecycle.delay_reason) {
    return `${selectedUnit.name || selectedUnit.id} is delayed: ${lifecycle.delay_reason}`;
  }
  if (readiness === "Exhausted" || readiness === "Fatigued" || supply < 1.5) {
    return `${selectedUnit.name || selectedUnit.id} needs recovery before another hard push.`;
  }
  if (state === "Executing" || state === "Preparing") {
    return `${selectedUnit.name || selectedUnit.id} is ${state.toLowerCase()} an order; watch turn results and support effects.`;
  }
  if (morale === "Shaken" || morale === "Unmotivated") {
    return `${selectedUnit.name || selectedUnit.id} is fragile; use support or rest before risking contact.`;
  }
  return `${selectedUnit.name || selectedUnit.id} is ready for action.`;
}

export function displayLogKind(kind) {
  const raw = String(kind || "").toLowerCase();
  const labels = {
    ai: "AI Pressure",
    support: "Support",
    player_order: "Player Order",
    scenario: "Scenario",
    objective: "Objective",
    combat: "Combat",
    recovery: "Recovery",
    operations: "Operations",
    report: "Report",
    tick: "Status",
    status: "Status",
    flavor: "Scenario",
  };
  return labels[raw] ?? "Log";
}

export function recentLogsFirst(logs = []) {
  const items = Array.isArray(logs) ? logs : [];
  return [...items].reverse();
}
