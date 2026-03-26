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
const mapPanelShellSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MapPanelShell.tsx"),
  "utf8",
);
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("layers header stays a planner entry while map shell avoids duplicate floating overlay controls", () => {
  assert.match(topStripSource, /onOpenPlannerWorkbench\("map"\)/);
  assert.match(topStripSource, /Planner > Map/);
  assert.match(mapPanelShellSource, /Detailed map and overlay controls live here\./);
  assert.match(mapPanelShellSource, /Quick Controls/);
  assert.match(mapPanelShellSource, /\{basemapRuntimeState\.invalid \|\| scene\.emptyState \? \(/);
  assert.match(mapPanelShellSource, /shell-map__overlay--top/);
  assert.doesNotMatch(mapPanelShellSource, /Map navigation controls/);
  assert.doesNotMatch(mapPanelShellSource, /Detailed map controls live in Planner &gt; Map\./);
  assert.doesNotMatch(mapPanelShellSource, /shell-map__overlay-stack/);
  assert.doesNotMatch(shellCssSource, /\.shell-map__overlay-stack/);
  assert.doesNotMatch(shellCssSource, /\.shell-map__overlay-card/);
  assert.doesNotMatch(shellCssSource, /\.shell-map__viewbuttons/);
  assert.doesNotMatch(shellCssSource, /\.shell-map__viewtools/);
  assert.doesNotMatch(shellCssSource, /\.shell-map__viewstate/);
});
