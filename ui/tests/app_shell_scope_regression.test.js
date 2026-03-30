import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appSource = readFileSync(
  path.resolve(__dirname, "../src/App.tsx"),
  "utf8",
);

test("app shell chrome does not reference trackedOperations outside a block-scoped ready branch", () => {
  assert.match(appSource, /const trackedOperations = phase === "ready" && snapshot/);
  assert.match(appSource, /selectionSummary=\{phase === "ready" && snapshot \? buildSelectionSummary\(snapshot, selectedSelection, trackedOperations\) : null\}/);
  assert.doesNotMatch(appSource, /if \(phase === "ready" && snapshot\) \{\s+const trackedOperations = sanitizeTrackedOperations/s);
});
