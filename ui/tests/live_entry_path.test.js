import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const mainSource = readFileSync(
  path.resolve(__dirname, "../src/main.jsx"),
  "utf8",
);
const appSource = readFileSync(
  path.resolve(__dirname, "../src/App.jsx"),
  "utf8",
);
const shellSource = readFileSync(
  path.resolve(__dirname, "../src/App.tsx"),
  "utf8",
);

test("main entry mounts the canonical App.tsx shell", () => {
  assert.match(mainSource, /import App from "\.\/App\.tsx";/);
});

test("App.jsx is only a compatibility export to the canonical shell", () => {
  assert.match(appSource, /Compatibility export only/);
  assert.match(appSource, /export \{ default \} from "\.\/App\.tsx";/);
});

test("live shell does not depend on the legacy useGameStore hook", () => {
  assert.doesNotMatch(shellSource, /useGameStore/);
});
