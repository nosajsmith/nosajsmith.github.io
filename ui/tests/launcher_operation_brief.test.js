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

test("launcher operation brief explains the founder beta operation model", () => {
  assert.match(launcherSource, /Founder Beta Preview/);
  assert.match(launcherSource, /Playable publisher preview focused on the opening operational turn\./);
  assert.match(launcherSource, /const commandSet = \["Move", "Attack", "Hold \/ Defend", "Reserve \/ Rest", "End Turn"\];/);
  assert.match(launcherSource, /Keep the main effort coherent, take or hold decisive ground, preserve readiness, and end the turn with the operational picture improved\./);
});

test("launcher operation brief remains subordinate to launch control", () => {
  assert.ok(launcherSource.indexOf("Launch Control") < launcherSource.indexOf("Operation Brief"));
  assert.match(shellCssSource, /\.shell-launcher__card--brief\s*\{/);
  assert.match(shellCssSource, /\.shell-launcher__brief-commands\s*\{/);
});
