import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const topStripSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/TopStrip.tsx"),
  "utf8",
);
const appSource = readFileSync(
  path.resolve(__dirname, "../src/App.tsx"),
  "utf8",
);
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("top strip presents the demo command set as one operator affordance layer", () => {
  assert.match(topStripSource, /const DEMO_COMMANDS = \[/);
  assert.match(topStripSource, /label: "Move"/);
  assert.match(topStripSource, /label: "Attack"/);
  assert.match(topStripSource, /label: "Hold \/ Defend"/);
  assert.match(topStripSource, /label: "Reserve \/ Rest"/);
  assert.match(topStripSource, /label: "End Turn"/);
  assert.match(topStripSource, /Resolve the next turn and refresh the snapshot picture\./);
  assert.doesNotMatch(topStripSource, /Resolve six hours/);
  assert.match(topStripSource, /aria-label="Demo controls \/ operator affordances"/);
  assert.match(topStripSource, />Demo Controls</);
  assert.doesNotMatch(topStripSource, /<span className="shell-control-group__label">Operations<\/span>/);
});

test("operator affordances stay on existing shell command paths", () => {
  assert.match(topStripSource, /selectionKind: InspectorSelectionKind \| null;/);
  assert.match(appSource, /selectionKind=\{phase === "ready" && snapshot \? selectedSelection\?\.kind \?\? null : null\}/);
  assert.match(topStripSource, /const hasUnitFocus = selectionKind === "unit";/);
  assert.match(topStripSource, /onClick=\{command\.action === "step" \? onStepSixHours : \(\) => onOpenPlannerWorkbench\("plan"\)\}/);
  assert.match(topStripSource, /Select a unit on the map to arm Move, Attack, Hold, and Reserve\./);
});

test("operator affordance styling is compact and highlights a primary command", () => {
  assert.match(shellCssSource, /\.shell-operator-controls \{/);
  assert.match(shellCssSource, /\.shell-operator-controls__grid \{[\s\S]*grid-template-columns:\s*repeat\(5, minmax\(48px, 1fr\)\);/);
  assert.match(shellCssSource, /\.shell-operator-controls__command\.is-primary \{/);
  assert.match(shellCssSource, /\.shell-operator-controls__flow \{/);
});
