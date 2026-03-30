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
const shellCssSource = readFileSync(
  path.resolve(__dirname, "../src/shell.css"),
  "utf8",
);

test("top strip uses compact dashboard labels and the inline status strip", () => {
  assert.match(topStripSource, /<span>BAI<\/span>/);
  assert.match(topStripSource, /<span>Bridge<\/span>/);
  assert.match(topStripSource, /<span className="shell-chip__label">Turn<\/span>/);
  assert.match(topStripSource, /<span className="shell-chip__label">Selection<\/span>/);
  assert.match(topStripSource, /label: "Replay"/);
  assert.match(topStripSource, /label: "Save"/);
  assert.match(topStripSource, /<span>Auto Save<\/span>/);
  assert.match(topStripSource, /label: "Load"/);
  assert.match(topStripSource, /inferScenarioPresentation/);
  assert.match(topStripSource, /presentation\.shellTitle/);
  assert.match(topStripSource, /presentation\.theaterLabel/);
  assert.match(topStripSource, /DEFAULT_PITCH_SCENARIO/);
  assert.match(topStripSource, /\{\[scenarioName, presentation\.frontLabel, campaignStatus\]\.filter\(Boolean\)\.join\(" • "\)\}/);
  assert.match(topStripSource, /BAI is actively evaluating or processing/);
  assert.match(topStripSource, /shell-statusstrip/);
  assert.doesNotMatch(topStripSource, /shell-livecluster/);
  assert.doesNotMatch(topStripSource, /<span>AI<\/span>/);
  assert.doesNotMatch(topStripSource, /RPY|BRG LIVE|BRG OFF/);
  assert.match(shellCssSource, /--shell-density-statusstrip-height:\s*22px;/);
  assert.match(shellCssSource, /--shell-density-statusstrip-gap:\s*4px;/);
  assert.match(shellCssSource, /--shell-density-statusstrip-pad-x:\s*8px;/);
  assert.match(shellCssSource, /--shell-density-statusstrip-font:\s*9px;/);
});
