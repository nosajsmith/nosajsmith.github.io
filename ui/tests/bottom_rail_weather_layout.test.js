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
const homeCommandBarSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/HomeCommandBar.tsx"),
  "utf8",
);
const weatherBriefSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MapWeatherBrief.tsx"),
  "utf8",
);
const reportsFeedSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/ReportsFeed.tsx"),
  "utf8",
);
const mapPanelShellSource = readFileSync(
  path.resolve(__dirname, "../src/components/shell/MapPanelShell.tsx"),
  "utf8",
);

test("bottom rail uses the anchored 3-zone layout with a 2-row center band, keeps the shared lift offset, and weather follows the same summary/detail card grammar", () => {
  assert.match(shellCssSource, /--shell-frame-pad: clamp\(6px, 0\.75vw, 10px\);/);
  assert.match(shellCssSource, /--shell-bottom-band-anchor-height: clamp\(135px, 13\.55dvh, 147px\);/);
  assert.match(shellCssSource, /--shell-bottom-band-offset: var\(--shell-frame-pad\);/);
  assert.match(shellCssSource, /--shell-bottom-band-anchor-width: clamp\(228px, 15vw, 252px\);/);
  assert.match(shellCssSource, /--shell-bottom-band-card-radius: 10px;/);
  assert.match(shellCssSource, /--shell-bottom-band-card-border-width: 1\.5px;/);
  assert.match(shellCssSource, /--shell-bottom-band-card-pad-x: calc\(var\(--shell-bottom-band-pad-x\) \+ 1px\);/);
  assert.match(shellCssSource, /--shell-bottom-band-card-pad-y: calc\(var\(--shell-bottom-band-pad-y\) \+ 1px\);/);
  assert.match(shellCssSource, /--shell-bottom-band-inner-radius: calc\(var\(--shell-bottom-band-card-radius\) - 2px\);/);
  assert.match(shellCssSource, /\.shell-root \{[\s\S]*padding: var\(--shell-frame-pad\);/);
  assert.match(shellCssSource, /\.shell-home__lower \{[\s\S]*display: grid;[\s\S]*grid-template-columns: var\(--shell-bottom-band-anchor-width\) minmax\(0, 1fr\) var\(--shell-bottom-band-anchor-width\);[\s\S]*padding-bottom: var\(--shell-bottom-band-offset\);/);
  assert.match(shellCssSource, /\.shell-home__lower \{[\s\S]*--shell-bottom-band-type-body: 10px;[\s\S]*--shell-bottom-band-type-title-strong: 12px;/);
  assert.match(shellCssSource, /\.shell-home__commandstack \{[\s\S]*display: grid;/);
  assert.match(shellCssSource, /\.shell-weather-dock \{[\s\S]*display: block;/);
  assert.match(shellCssSource, /\.shell-commandbar \{[\s\S]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\);[\s\S]*grid-template-rows: repeat\(2, minmax\(0, 1fr\)\);[\s\S]*height: 100%;/);
  assert.match(homeCommandBarSource, /shell-commandbar__title">Operations[\s\S]*shell-commandbar__title">Logistics[\s\S]*shell-commandbar__title">Intelligence[\s\S]*shell-commandbar__title">Air[\s\S]*shell-commandbar__title">Land[\s\S]*shell-commandbar__title">Naval/);
  assert.match(weatherBriefSource, /className="shell-weather__summary"/);
  assert.match(weatherBriefSource, /className="shell-weather__summary-title">Weather</);
  assert.match(weatherBriefSource, /className="shell-weather__summary-state"/);
  assert.match(weatherBriefSource, /className="shell-weather__summary-support"/);
  assert.match(weatherBriefSource, /className="shell-weather__detail-grid"/);
  assert.match(weatherBriefSource, /label: "Temp"/);
  assert.match(weatherBriefSource, /label: "Wind"/);
  assert.match(weatherBriefSource, /label: "Time"/);
  assert.match(weatherBriefSource, /label: "Sight"/);
  assert.match(weatherBriefSource, /<strong>\{row\.label\}<\/strong>[\s\S]*<span>\{row\.value\}<\/span>/);
  assert.match(shellCssSource, /\.shell-weather \{[\s\S]*border: var\(--shell-bottom-band-card-border-width\) solid var\(--shell-weather-border\);[\s\S]*border-radius: var\(--shell-bottom-band-card-radius\);/);
  assert.match(shellCssSource, /\.shell-weather-dock \.shell-weather::before \{[\s\S]*height: 2px;[\s\S]*border-radius: var\(--shell-bottom-band-card-radius\) var\(--shell-bottom-band-card-radius\) 0 0;/);
  assert.match(shellCssSource, /\.shell-weather__summary \{[\s\S]*gap: var\(--shell-bottom-band-gap\);[\s\S]*padding: var\(--shell-bottom-band-card-pad-y\) var\(--shell-bottom-band-card-pad-x\) var\(--shell-bottom-band-card-pad-bottom\);/);
  assert.match(shellCssSource, /\.shell-weather__summary-state \{[\s\S]*font-size: var\(--shell-bottom-band-type-title-strong\);/);
  assert.match(shellCssSource, /\.shell-weather__summary-support \{[\s\S]*font-size: var\(--shell-bottom-band-type-body\);[\s\S]*-webkit-line-clamp: 2;/);
  assert.match(shellCssSource, /\.shell-weather__detail \{[\s\S]*padding: var\(--shell-bottom-band-card-pad-y\) var\(--shell-bottom-band-card-pad-x\) var\(--shell-bottom-band-card-pad-bottom\);/);
  assert.match(shellCssSource, /\.shell-weather__detail-grid \{[\s\S]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);/);
  assert.match(shellCssSource, /\.shell-weather__detail-row span \{[\s\S]*font-size: var\(--shell-bottom-band-type-body\);/);
  assert.match(shellCssSource, /\.shell-weather__detail-row strong \{[\s\S]*font-size: var\(--shell-bottom-band-type-title-compact\);/);
  assert.match(shellCssSource, /\.shell-commandbar__state \{[\s\S]*font-size: var\(--shell-bottom-band-type-title-compact\);/);
  assert.match(shellCssSource, /\.shell-commandbar__module \{[\s\S]*gap: var\(--shell-bottom-band-gap\);[\s\S]*padding: var\(--shell-bottom-band-card-pad-y\) var\(--shell-bottom-band-card-pad-x\) var\(--shell-bottom-band-card-pad-bottom\);[\s\S]*border: var\(--shell-bottom-band-card-border-width\) solid var\(--shell-bottom-band-card-border-color\);[\s\S]*border-radius: var\(--shell-bottom-band-card-radius\);/);
  assert.match(shellCssSource, /\.shell-commandbar__support,[\s\S]*\.shell-commandbar__body \{/);
  assert.match(shellCssSource, /\.shell-report__kicker \{[\s\S]*text-transform: uppercase;/);
  assert.match(shellCssSource, /\.shell-report__context \{[\s\S]*font-size: var\(--shell-bottom-band-type-body\);/);
  assert.match(shellCssSource, /\.shell-reports \{[\s\S]*padding: var\(--shell-bottom-band-card-pad-y\) var\(--shell-bottom-band-card-pad-x\) var\(--shell-bottom-band-card-pad-bottom\);[\s\S]*border: var\(--shell-bottom-band-card-border-width\) solid var\(--shell-comm-border\);[\s\S]*border-radius: var\(--shell-bottom-band-card-radius\);/);
  assert.match(shellCssSource, /\.shell-reports::before \{[\s\S]*height: 2px;[\s\S]*border-radius: var\(--shell-bottom-band-card-radius\) var\(--shell-bottom-band-card-radius\) 0 0;/);
  assert.match(shellCssSource, /\.shell-reports \.shell-report \{[\s\S]*border-radius: var\(--shell-bottom-band-inner-radius\);/);
  assert.match(shellCssSource, /\.shell-report \{[\s\S]*padding: var\(--shell-bottom-band-card-pad-y\) var\(--shell-bottom-band-card-pad-x\) var\(--shell-bottom-band-card-pad-bottom\);/);
  assert.match(shellCssSource, /\.shell-report--latest \{[\s\S]*margin-bottom: var\(--shell-bottom-band-gap\);[\s\S]*border: var\(--shell-bottom-band-card-border-width\) solid rgba\(76, 79, 71, 0\.58\);[\s\S]*border-radius: var\(--shell-bottom-band-inner-radius\);/);
  assert.match(shellCssSource, /--shell-card-comm: linear-gradient\(180deg, rgba\(88, 98, 75, 0\.24\), rgba\(84, 96, 93, 0\.2\) 52%, rgba\(58, 58, 46, 0\.94\)\);/);
  assert.match(shellCssSource, /--shell-card-weather: linear-gradient\(180deg, rgba\(80, 102, 104, 0\.22\), rgba\(58, 58, 46, 0\.94\)\);/);
  assert.doesNotMatch(homeCommandBarSource, /shell-commandbar__launcher/);
  assert.match(reportsFeedSource, /shell-report__kicker/);
  assert.match(reportsFeedSource, /shell-report__context/);
  assert.match(mapPanelShellSource, /className=\{"shell-map__stage" \+ \(effectiveUnderlayLayerVisible \? " shell-map__stage--underlay" : ""\)\}/);
  assert.match(mapPanelShellSource, /className=\{"shell-map__field" \+ \(effectiveUnderlayLayerVisible \? " has-underlay" : ""\)\}/);
});
