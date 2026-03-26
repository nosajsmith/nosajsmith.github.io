import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("non-header shell typography tokens are larger while top strip tokens remain unchanged", () => {
  assert.match(shellCssSource, /--shell-type-eyebrow:\s*8px;/);
  assert.match(shellCssSource, /--shell-type-body:\s*10px;/);
  assert.match(shellCssSource, /--shell-type-title-compact:\s*11px;/);
  assert.match(shellCssSource, /--shell-type-title-strong:\s*12px;/);
  assert.match(shellCssSource, /--shell-density-gap:\s*7px;/);
  assert.match(shellCssSource, /--shell-density-panel-pad:\s*13px;/);
  assert.match(shellCssSource, /--shell-density-button-height:\s*23px;/);

  assert.match(shellCssSource, /\.shell-home\s*\{[\s\S]*--shell-type-eyebrow:\s*9px;[\s\S]*--shell-type-body:\s*11px;[\s\S]*--shell-type-title-compact:\s*12px;[\s\S]*--shell-type-title-strong:\s*13px;/);
  assert.match(shellCssSource, /\.shell-home\s*\{[\s\S]*--shell-density-gap:\s*6px;[\s\S]*--shell-density-panel-pad:\s*11px;[\s\S]*--shell-density-button-height:\s*22px;/);

  assert.match(shellCssSource, /\.shell-topstrip\s*\{[\s\S]*--shell-type-eyebrow:\s*7px;[\s\S]*--shell-type-body:\s*10px;[\s\S]*--shell-type-title-compact:\s*10px;[\s\S]*--shell-type-title-strong:\s*11px;/);
});
