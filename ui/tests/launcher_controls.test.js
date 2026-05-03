import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const launcherSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/LauncherScreen.tsx"),
  "utf8",
);
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("launcher controls present one obvious primary entry path", () => {
  assert.match(launcherSource, /Select a scenario, then use the primary action to enter the playable preview shell\./);
  assert.match(launcherSource, /shell-launcher__button--primary-action/);
  assert.match(launcherSource, /Primary path into the playable preview shell|Loads the selected scenario and enters the playable operational shell|Refreshes launcher readiness before shell entry/);
});

test("launcher utility actions are demoted below the primary launch control", () => {
  assert.match(launcherSource, /Resume Current Shell/);
  assert.match(launcherSource, /Refresh Picture/);
  assert.match(launcherSource, /Play Theme/);
  assert.match(launcherSource, /Stop Theme/);
  assert.match(launcherSource, /Optional opening theme remains manual and does not affect shell entry\./);
  assert.match(shellCssSource, /\.shell-launcher__button--utility\s*\{/);
  assert.match(shellCssSource, /\.shell-launcher__audio-actions\s*\{/);
});
