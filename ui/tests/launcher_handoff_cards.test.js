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

test("launcher handoff cards describe the founder-beta flow from bridge to shell", () => {
  assert.match(launcherSource, /aria-label="Launcher handoff flow"/);
  assert.match(launcherSource, />Bridge</);
  assert.match(launcherSource, />Roster</);
  assert.match(launcherSource, />Command Shell</);
  assert.match(launcherSource, /operational picture before roster review and command-shell entry/i);
  assert.match(launcherSource, /playable scenarios prepared for this preview and sets the shell entry point/i);
  assert.match(launcherSource, /Primary playable surface for founder beta/i);
});

test("launcher handoff styling keeps Command Shell visually primary", () => {
  assert.match(shellCssSource, /\.shell-launcher__signal--primary\s*\{/);
  assert.match(shellCssSource, /grid-template-columns:\s*minmax\(0,\s*0\.92fr\)\s+minmax\(0,\s*0\.92fr\)\s+minmax\(0,\s*1\.16fr\)/);
});
