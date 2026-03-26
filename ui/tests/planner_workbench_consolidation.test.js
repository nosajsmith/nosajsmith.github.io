import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const mapPanelShellSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MapPanelShell.tsx"),
  "utf8",
);
const operationPlannerPanelSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/OperationPlannerPanel.tsx"),
  "utf8",
);

test("planner workbench keeps plan map and qa tabs, embeds planning brief in plan tab, and avoids duplicate grease controls", () => {
  assert.match(operationPlannerPanelSource, /id: "plan", label: "Plan"/);
  assert.match(operationPlannerPanelSource, /id: "map", label: "Map"/);
  assert.match(operationPlannerPanelSource, /id: "qa", label: "QA"/);
  assert.match(operationPlannerPanelSource, /showQaTab\?: boolean/);
  assert.match(operationPlannerPanelSource, /const workbenchTabs = showQaTab \? WORKBENCH_TABS : WORKBENCH_TABS\.filter\(\(tab\) => tab\.id !== "qa"\)/);
  assert.match(mapPanelShellSource, /const qaWorkbenchVisible = import\.meta\.env\.DEV;/);
  assert.match(mapPanelShellSource, /<GreaseBoard data=\{greaseBoard\.data\} embedded \/>/);
  assert.match(mapPanelShellSource, /<GreaseMarkupPalette/);
  assert.match(mapPanelShellSource, /showQaTab=\{qaWorkbenchVisible\}/);
  assert.match(mapPanelShellSource, /const plannerQaWorkbench = qaWorkbenchVisible \?/);
  assert.doesNotMatch(mapPanelShellSource, /<GreaseBoard data=\{greaseBoard\.data\} \/>/);
  assert.doesNotMatch(mapPanelShellSource, /Grease On/);
  assert.doesNotMatch(mapPanelShellSource, /Grease Off/);
});
