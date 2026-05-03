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
const appSource = readFileSync(
  path.resolve(__dirname, "../src/App.tsx"),
  "utf8",
);

test("map shell routes right-click quick commands through the planner-owned command path", () => {
  assert.match(mapPanelShellSource, /buildMapCommandPreview/);
  assert.match(mapPanelShellSource, /onContextMenu=\{handleMapContextMenu\}/);
  assert.match(mapPanelShellSource, /onCommitFastCommand\(preview\)/);
  assert.match(mapPanelShellSource, /setCommandHoverHex\(null\)/);
  assert.match(mapPanelShellSource, /shell-map__quickcommand-path/);
  assert.match(appSource, /seedPlannerStateFromMapCommand/);
  assert.match(appSource, /function commitFastCommand/);
  assert.match(appSource, /createApprovedOperation\(snapshot, seededPlannerState\)/);
});

test("objective fast commands preserve the clicked objective identity before preview seeding", () => {
  assert.match(mapPanelShellSource, /data-objective-id=\{objective.id\}/);
  assert.match(mapPanelShellSource, /closest\("\.shell-map__objective"\)/);
  assert.match(mapPanelShellSource, /scene\.objectives\.find\(\(row\) => row\.id === objectiveId\)/);
});
