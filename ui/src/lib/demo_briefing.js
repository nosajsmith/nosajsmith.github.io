export function pickDefaultScenario(scenarios = []) {
  const items = Array.isArray(scenarios) ? scenarios : [];
  const inchon = items.find((name) => String(name).trim() === "inchon_mvp.json");
  return inchon ?? items[0] ?? "";
}

export function summarizeObjectives(objectives = []) {
  const items = Array.isArray(objectives) ? objectives : [];
  return items
    .map((objective) => ({
      id: objective?.id ?? "",
      label: objective?.label ?? objective?.id ?? "Objective",
      controlled: objective?.controlled === true,
      side: objective?.side ?? null,
    }))
    .filter((objective) => objective.label)
    .slice(0, 4);
}
