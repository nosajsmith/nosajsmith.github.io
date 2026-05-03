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
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("map presentation styles objective labels by current control state and keeps counters readable without extra shell chrome", () => {
  assert.match(mapPanelShellSource, /shell-map__objective-label is-\$\{objective\.settlement\?\.controlState \?\? "unknown"\}/);
  assert.match(mapPanelShellSource, /shell-map__objective-state is-\$\{objective\.settlement\?\.controlState \?\? "unknown"\}/);
  assert.match(shellCssSource, /\.shell-map__objective-badge \{/);
  assert.match(shellCssSource, /\.shell-map__objective-label\.is-contested \{/);
  assert.match(shellCssSource, /\.shell-map__objective-label\.is-neutral,/);
  assert.match(shellCssSource, /\.shell-map__objective-state\.is-contested \{/);
  assert.match(shellCssSource, /\.shell-map__objective-state\.is-neutral,/);
  assert.match(shellCssSource, /\.shell-map__unit\.is-faction-enemy \.shell-map__unit-name \{/);
  assert.match(shellCssSource, /\.shell-map__unit\.is-faction-friendly \.shell-map__unit-name \{/);
});
