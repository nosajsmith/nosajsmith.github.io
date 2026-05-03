import { useState } from "react";

import { humanizeScenarioLabel } from "../../lib/view_snapshot.js";

type LauncherScreenProps = {
  title: string;
  subtitle: string;
  theaterLabel: string;
  scenarioName: string;
  scenarioStatus: string;
  bridgeStatus: string;
  currentTurn: string;
  currentPhase: string;
  objective: string;
  mainEffort: string;
  selectedScenario: string;
  scenarios: string[];
  scenariosLoading: boolean;
  controlStatus: string;
  primaryActionLabel: string;
  primaryActionDisabled: boolean;
  enterActionDisabled: boolean;
  refreshDisabled: boolean;
  musicLabel: string;
  musicVolume: number;
  musicDisabled: boolean;
  musicEnabled: boolean;
  onSelectScenario: (value: string) => void;
  onPrimaryAction: () => void;
  onEnterShell: () => void;
  onRefresh: () => void;
  onToggleMusic: () => void;
  onSetMusicVolume: (value: number) => void;
};

export default function LauncherScreen({
  title,
  subtitle,
  theaterLabel,
  scenarioName,
  scenarioStatus,
  bridgeStatus,
  currentTurn,
  currentPhase,
  objective,
  mainEffort,
  selectedScenario,
  scenarios,
  scenariosLoading,
  controlStatus,
  primaryActionLabel,
  primaryActionDisabled,
  enterActionDisabled,
  refreshDisabled,
  musicLabel,
  musicVolume,
  musicDisabled,
  musicEnabled,
  onSelectScenario,
  onPrimaryAction,
  onEnterShell,
  onRefresh,
  onToggleMusic,
  onSetMusicVolume,
}: LauncherScreenProps) {
  const [heroArtAvailable, setHeroArtAvailable] = useState(true);
  const commandSet = ["Move", "Attack", "Hold / Defend", "Reserve / Rest", "End Turn"];
  const koreaHeroSrc = `${import.meta.env.BASE_URL}branding/theater-of-operations-korea-hero.svg`;
  const rosterStatus = scenariosLoading
    ? "Refreshing roster"
    : scenarios.length
      ? `${scenarios.length} scenario${scenarios.length === 1 ? "" : "s"} ready`
      : "Roster pending";
  const shellStatus = primaryActionDisabled
    ? "Standing by"
    : enterActionDisabled
      ? "Updating shell"
      : "Ready to enter";
  const selectedScenarioLabel = selectedScenario
    ? humanizeScenarioLabel(selectedScenario)
    : "Select a scenario to frame the opening command shell";
  const shellContext = [scenarioName, currentTurn, currentPhase].filter(Boolean).join(" • ");
  const primaryActionCopy = (() => {
    const normalized = primaryActionLabel.toLowerCase();
    if (normalized.startsWith("launch") || normalized.startsWith("load")) {
      return "Loads the selected scenario and enters the playable operational shell with the preview context set.";
    }
    if (normalized.includes("refresh") || normalized.includes("bridge") || normalized.includes("connecting")) {
      return "Refreshes launcher readiness before shell entry and keeps the current selection intact.";
    }
    return "Primary path into the playable preview shell.";
  })();
  const operationFrame = [currentTurn, currentPhase].filter(Boolean).join(" • ");
  const musicVolumePercent = `${Math.round(Math.min(1, Math.max(0, musicVolume)) * 100)}%`;
  const readinessItems = [
    { label: "Bridge", value: bridgeStatus },
    { label: "Roster", value: rosterStatus },
    { label: "Shell", value: shellStatus },
  ];

  return (
    <section className="shell-launcher" aria-label="Theater of Operations launcher">
      <div
        className={"shell-launcher__cinematic-bg" + (heroArtAvailable ? "" : " is-fallback")}
        aria-hidden="true"
        style={heroArtAvailable ? { backgroundImage: `url(${koreaHeroSrc})` } : undefined}
      />
      <div className="shell-launcher__backdrop" aria-hidden="true" />
      <div className="shell-launcher__inner">
        <header className="shell-launcher__hero">
          <div className="shell-eyebrow">Publisher Preview Build</div>
          <h1 className="shell-launcher__title">
            <span className="shell-launcher__title-main">{title}</span>
            <span className="shell-launcher__title-sub">{subtitle}</span>
          </h1>
          <div className="shell-launcher__theater">{theaterLabel}</div>
          <div className="shell-launcher__hero-meta">
            <span className="shell-launcher__pill shell-launcher__pill--active">Playable Publisher Preview</span>
            <span className="shell-launcher__pill">Live Bridge Handoff</span>
            <span className="shell-launcher__pill">One-Turn Playable Loop</span>
          </div>
          <p className="shell-launcher__lede">
            Enter the Inchon preview through a deliberate front door: confirm the live bridge, choose the scenario, then open the command shell with the operational picture already in place.
          </p>
          <div className="shell-launcher__mission-strip" aria-label="Founder beta readiness">
            <div className="shell-launcher__mission-item">
              <span>Build</span>
              <strong>Founder Beta</strong>
            </div>
            <div className="shell-launcher__mission-item">
              <span>Scenario</span>
              <strong>{scenarioName}</strong>
            </div>
            <div className="shell-launcher__mission-item">
              <span>Objective</span>
              <strong>{objective}</strong>
            </div>
            <div className="shell-launcher__mission-item">
              <span>Main Effort</span>
              <strong>{mainEffort}</strong>
            </div>
          </div>
          <div className="shell-launcher__signal-band" aria-label="Launcher handoff flow">
            <article className="shell-launcher__signal">
              <div className="shell-launcher__signal-head">
                <span className="shell-launcher__signal-step">01</span>
                <span className="shell-launcher__signal-label">Bridge</span>
              </div>
              <strong className="shell-launcher__signal-value">{bridgeStatus}</strong>
              <span className="shell-launcher__signal-note">
                Verifies the live operational picture before roster review and command-shell entry.
              </span>
              <span className="shell-launcher__signal-detail">{scenarioStatus}</span>
            </article>
            <article className="shell-launcher__signal">
              <div className="shell-launcher__signal-head">
                <span className="shell-launcher__signal-step">02</span>
                <span className="shell-launcher__signal-label">Roster</span>
              </div>
              <strong className="shell-launcher__signal-value">{rosterStatus}</strong>
              <span className="shell-launcher__signal-note">
                Shows the playable scenarios prepared for this preview and sets the shell entry point.
              </span>
              <span className="shell-launcher__signal-detail">{selectedScenarioLabel}</span>
            </article>
            <article className="shell-launcher__signal shell-launcher__signal--primary">
              <div className="shell-launcher__signal-head">
                <span className="shell-launcher__signal-step">03</span>
                <span className="shell-launcher__signal-label">Command Shell</span>
              </div>
              <strong className="shell-launcher__signal-value">{shellStatus}</strong>
              <span className="shell-launcher__signal-note">
                Primary playable surface for founder beta, opened with the selected scenario context already in place.
              </span>
              <span className="shell-launcher__signal-detail">{shellContext || "Command shell context pending"}</span>
            </article>
          </div>
        </header>

        <div className="shell-launcher__grid">
          <div className="shell-launcher__rail">
            <section className="shell-launcher__card shell-launcher__card--actions">
              <div className="shell-card__title">Launch Control</div>
              <p className="shell-launcher__control-copy">
                Select a scenario, then use the primary action to enter the playable preview shell.
              </p>
              <div className="shell-launcher__control-stack">
                <label className="shell-launcher__field">
                  <span className="shell-launcher__field-label">Scenario</span>
                  <select
                    className="shell-select shell-launcher__select"
                    value={selectedScenario}
                    onChange={(event) => onSelectScenario(event.target.value)}
                    disabled={scenariosLoading || !scenarios.length}
                  >
                    {scenarios.length ? (
                      scenarios.map((scenario) => (
                        <option key={scenario} value={scenario}>
                          {humanizeScenarioLabel(scenario)}
                        </option>
                      ))
                    ) : (
                      <option value="">Roster pending</option>
                    )}
                  </select>
                </label>

                <div className="shell-launcher__primary-panel">
                  <button
                    type="button"
                    className="shell-button shell-button--primary shell-launcher__button shell-launcher__button--primary-action"
                    onClick={onPrimaryAction}
                    disabled={primaryActionDisabled}
                  >
                    {primaryActionLabel}
                  </button>
                  <div className="shell-launcher__primary-note">{primaryActionCopy}</div>
                </div>
              </div>
              <div className="shell-launcher__readiness" aria-label="Launcher readiness summary">
                {readinessItems.map((item) => (
                  <div key={item.label} className="shell-launcher__readiness-item">
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>

              <div className="shell-launcher__actions shell-launcher__actions--utility">
                <button
                  type="button"
                  className="shell-button shell-button--secondary shell-launcher__button shell-launcher__button--utility"
                  onClick={onEnterShell}
                  disabled={enterActionDisabled}
                >
                  Resume Current Shell
                </button>
                <button
                  type="button"
                  className="shell-button shell-button--secondary shell-launcher__button shell-launcher__button--utility"
                  onClick={onRefresh}
                  disabled={refreshDisabled}
                >
                  Refresh Picture
                </button>
              </div>
              <div className="shell-launcher__utility-note">
                Secondary controls are for returning to the current shell or refreshing bridge readiness.
              </div>

              <div className="shell-launcher__statusline">
                <span className="shell-launcher__statusline-label">Preview Audio</span>
                <strong>{musicLabel}</strong>
              </div>
              <div className="shell-launcher__audio-bank" aria-label="Preview audio controls">
                <div className="shell-launcher__audio-meta">
                  <span className="shell-launcher__audio-title">Opening Theme</span>
                  <strong className="shell-launcher__audio-value">{musicEnabled ? musicVolumePercent : "Off"}</strong>
                </div>
                <input
                  className="shell-launcher__audio-slider"
                  type="range"
                  min="0"
                  max="0.7"
                  step="0.01"
                  value={musicVolume}
                  onChange={(event) => onSetMusicVolume(Number(event.target.value))}
                  disabled={musicDisabled}
                  aria-label="Opening theme level"
                />
                <div className="shell-launcher__audio-actions">
                  <button
                    type="button"
                    className="shell-button shell-button--secondary shell-launcher__button shell-launcher__button--utility"
                    onClick={onToggleMusic}
                    disabled={musicDisabled}
                  >
                    {musicEnabled ? "Stop Theme" : "Play Theme"}
                  </button>
                </div>
                <div className="shell-launcher__audio-note">
                  Optional opening theme remains manual and does not affect shell entry.
                </div>
              </div>
              <div className="shell-launcher__statusnote">
                {controlStatus || "Primary launch uses the selected scenario and enters the operational command shell."}
              </div>
            </section>

            <section className="shell-launcher__card shell-launcher__card--brief">
              <div className="shell-card__title">Operation Brief</div>
              <div className="shell-launcher__brief-kicker">Founder Beta Preview</div>
              <div className="shell-launcher__brief-name">{scenarioName}</div>
              <div className="shell-launcher__brief-status">
                Playable publisher preview focused on the opening operational turn.
              </div>
              <div className="shell-launcher__brief-route" aria-label="Reviewer path">
                <span>Reviewer Path</span>
                <strong>Launcher &gt; Scenario &gt; Command Shell &gt; End Turn</strong>
              </div>
              <div className="shell-launcher__brief-grid">
                <div className="shell-launcher__brief-row">
                  <span>Build</span>
                  <strong>Founder beta operational preview</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Entry State</span>
                  <strong>{scenarioStatus}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Main Objective</span>
                  <strong>{objective}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Main Effort</span>
                  <strong>{mainEffort}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Turn Frame</span>
                  <strong>{operationFrame}</strong>
                </div>
              </div>
              <div className="shell-launcher__brief-section">
                <div className="shell-launcher__brief-section-label">Command Set</div>
                <div className="shell-launcher__brief-commands" aria-label="Founder beta command set">
                  {commandSet.map((command) => (
                    <span key={command} className="shell-launcher__brief-command">
                      {command}
                    </span>
                  ))}
                </div>
              </div>
              <div className="shell-launcher__brief-section">
                <div className="shell-launcher__brief-section-label">What Good Looks Like</div>
                <p className="shell-launcher__brief-copy">
                  Keep the main effort coherent, take or hold decisive ground, preserve readiness, and end the turn with the operational picture improved.
                </p>
              </div>
            </section>
          </div>

          <aside className="shell-launcher__card shell-launcher__card--art" aria-label="Theater of Operations title art preview">
            <figure className="shell-launcher__art-frame">
              {heroArtAvailable ? (
                <img
                  className="shell-launcher__art-image"
                  src={koreaHeroSrc}
                  alt="Theater of Operations Korea title art preview"
                  loading="eager"
                  decoding="async"
                  onError={() => setHeroArtAvailable(false)}
                />
              ) : (
                <div className="shell-launcher__art-fallback">
                  <span className="shell-launcher__art-kicker">Theater of Operations: Korea</span>
                  <strong className="shell-launcher__art-title">Theater of Operations: Korea</strong>
                  <span className="shell-launcher__art-copy">Key art is unavailable in this session. The current playable preview remains Inchon / Operation Chromite.</span>
                </div>
              )}
              <div className="shell-launcher__art-vignette" aria-hidden="true" />
              <div className="shell-launcher__art-badges">
                <span className="shell-launcher__pill">Korea Theater Key Art</span>
                <span className="shell-launcher__pill shell-launcher__pill--active">Current Preview: Inchon</span>
              </div>
              <figcaption className="shell-launcher__art-caption">
                <span className="shell-launcher__art-kicker">Theater of Operations: Korea</span>
                <strong className="shell-launcher__art-title">Publisher Preview Key Art</strong>
                <span className="shell-launcher__art-copy">Current playable preview remains Inchon / Operation Chromite.</span>
              </figcaption>
            </figure>
          </aside>
        </div>
      </div>
    </section>
  );
}
