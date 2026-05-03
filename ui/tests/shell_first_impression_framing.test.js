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
const reportsFeedSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/ReportsFeed.tsx"),
  "utf8",
);
const drawerSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MainMapDrawer.tsx"),
  "utf8",
);
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("top strip frames the current shell workflow and current focus", () => {
  assert.match(topStripSource, /Theatre view\. Work from the map, then open Current Focus or review the operational feed\./);
  assert.match(topStripSource, /Map selection pending/);
  assert.match(topStripSource, /Select a visible unit, objective, airfield, or port to open Current Focus\./);
  assert.match(shellCssSource, /\.shell-topstrip__contextline,/);
  assert.match(shellCssSource, /\.shell-topstrip__focusline \{/);
});

test("reports feed adds a clearer read path for the latest dispatch", () => {
  assert.match(reportsFeedSource, /Read the latest dispatch first, then open Communications Center for the wider traffic picture\./);
  assert.match(reportsFeedSource, /Earlier Traffic/);
  assert.match(reportsFeedSource, /Feed Status/);
  assert.match(reportsFeedSource, /Open Communications Center to review dispatch history and recent traffic\./);
  assert.match(shellCssSource, /\.shell-reports__summaryline,/);
  assert.match(shellCssSource, /-webkit-line-clamp:\s*3;/);
});

test("current focus drawer uses product-facing focus language", () => {
  assert.match(drawerSource, /aria-label="Current focus drawer"/);
  assert.match(drawerSource, />Current Focus</);
  assert.match(drawerSource, /Read readiness, posture, and local reporting before committing the next order\./);
  assert.match(drawerSource, /No Current Focus/);
  assert.match(drawerSource, /Select a visible unit, objective, airfield, or port on the map to review state, readiness, and local reporting\./);
  assert.match(shellCssSource, /\.shell-drawer__lead \{/);
});
