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
  const koreaHeroSrc = `${import.meta.env.BASE_URL}branding/theater-of-operations-korea-hero.svg`;
  const rosterStatus = scenariosLoading
    ? "Refreshing roster"
    : scenarios.length
      ? `${scenarios.length} slice${scenarios.length === 1 ? "" : "s"} ready`
      : "No scenarios listed";
  const shellStatus = primaryActionDisabled
    ? "Preparing handoff"
    : enterActionDisabled
      ? "Shell handoff busy"
      : "Direct shell handoff ready";
  const musicVolumePercent = `${Math.round(Math.min(1, Math.max(0, musicVolume)) * 100)}%`;

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
          <div className="shell-eyebrow">Publisher Demo Vertical Slice</div>
          <h1 className="shell-launcher__title">
            <span className="shell-launcher__title-main">{title}</span>
            <span className="shell-launcher__title-sub">{subtitle}</span>
          </h1>
          <div className="shell-launcher__theater">{theaterLabel}</div>
          <div className="shell-launcher__hero-meta">
            <span className="shell-launcher__pill shell-launcher__pill--active">Current Vertical Slice: Inchon</span>
            <span className="shell-launcher__pill">Operation Chromite</span>
            <span className="shell-launcher__pill">Publisher Demo Vertical Slice</span>
          </div>
          <p className="shell-launcher__lede">
            Live command-shell presentation for the Inchon landing and Seoul axis. The current bridge can stay headless and fast while this front door carries the demo framing.
          </p>
          <div className="shell-launcher__signal-band" aria-label="Launcher readiness summary">
            <article className="shell-launcher__signal">
              <span className="shell-launcher__signal-label">Bridge</span>
              <strong className="shell-launcher__signal-value">{bridgeStatus}</strong>
              <span className="shell-launcher__signal-note">{scenarioStatus}</span>
            </article>
            <article className="shell-launcher__signal">
              <span className="shell-launcher__signal-label">Scenario Roster</span>
              <strong className="shell-launcher__signal-value">{rosterStatus}</strong>
              <span className="shell-launcher__signal-note">{selectedScenario ? humanizeScenarioLabel(selectedScenario) : "Awaiting selection"}</span>
            </article>
            <article className="shell-launcher__signal">
              <span className="shell-launcher__signal-label">Shell Handoff</span>
              <strong className="shell-launcher__signal-value">{shellStatus}</strong>
              <span className="shell-launcher__signal-note">Direct to Command Shell remains the fast path into the live demo.</span>
            </article>
          </div>
        </header>

        <div className="shell-launcher__grid">
          <div className="shell-launcher__rail">
            <section className="shell-launcher__card shell-launcher__card--brief">
              <div className="shell-card__title">Operation Brief</div>
              <div className="shell-launcher__brief-name">{scenarioName}</div>
              <div className="shell-launcher__brief-status">{scenarioStatus}</div>
              <div className="shell-launcher__brief-grid">
                <div className="shell-launcher__brief-row">
                  <span>Bridge</span>
                  <strong>{bridgeStatus}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Turn</span>
                  <strong>{currentTurn}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Phase</span>
                  <strong>{currentPhase}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Main Objective</span>
                  <strong>{objective}</strong>
                </div>
                <div className="shell-launcher__brief-row">
                  <span>Main Effort</span>
                  <strong>{mainEffort}</strong>
                </div>
              </div>
            </section>

            <section className="shell-launcher__card shell-launcher__card--actions">
              <div className="shell-card__title">Launch Control</div>
              <label className="shell-launcher__field">
                <span className="shell-launcher__field-label">Scenario Slice</span>
                <select
                  className="shell-select"
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
                    <option value="">Awaiting scenario list</option>
                  )}
                </select>
              </label>

              <div className="shell-launcher__actions">
                <button
                  type="button"
                  className="shell-button shell-button--primary shell-launcher__button"
                  onClick={onPrimaryAction}
                  disabled={primaryActionDisabled}
                >
                  {primaryActionLabel}
                </button>
                <button
                  type="button"
                  className="shell-button shell-button--secondary shell-launcher__button"
                  onClick={onEnterShell}
                  disabled={enterActionDisabled}
                >
                  Direct To Command Shell
                </button>
                <button
                  type="button"
                  className="shell-button shell-button--secondary shell-launcher__button"
                  onClick={onRefresh}
                  disabled={refreshDisabled}
                >
                  Refresh Bridge State
                </button>
                <button
                  type="button"
                  className={"shell-button shell-launcher__button" + (musicEnabled ? " shell-button--primary" : " shell-button--secondary")}
                  onClick={onToggleMusic}
                  disabled={musicDisabled}
                >
                  {musicEnabled ? "Music On" : "Music Off"}
                </button>
              </div>

              <div className="shell-launcher__statusline">
                <span className="shell-launcher__statusline-label">Launcher Audio</span>
                <strong>{musicLabel}</strong>
              </div>
              <div className="shell-launcher__audio-bank" aria-label="Launcher music controls">
                <div className="shell-launcher__audio-meta">
                  <span className="shell-launcher__audio-title">Optional Menu Theme</span>
                  <strong className="shell-launcher__audio-value">{musicEnabled ? musicVolumePercent : "Muted"}</strong>
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
                  aria-label="Launcher music volume"
                />
                <div className="shell-launcher__audio-note">
                  Manual opt-in keeps playback browser-safe while preserving a premium menu theme for the pitch build.
                </div>
              </div>
              <div className="shell-launcher__statusnote">
                {controlStatus || "Use the live bridge path when available, or move directly into the restored shell for instant demo flow."}
              </div>
            </section>
          </div>

          <aside className="shell-launcher__card shell-launcher__card--art" aria-label="Franchise title art preview">
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
                  <span className="shell-launcher__art-kicker">Franchise Key Art</span>
                  <strong className="shell-launcher__art-title">Theater Of Operations: Korea</strong>
                  <span className="shell-launcher__art-copy">Branding artwork unavailable in this browser session. The active pitch slice remains Inchon / Operation Chromite.</span>
                </div>
              )}
              <div className="shell-launcher__art-vignette" aria-hidden="true" />
              <div className="shell-launcher__art-badges">
                <span className="shell-launcher__pill">Franchise Key Art</span>
                <span className="shell-launcher__pill shell-launcher__pill--active">Current Vertical Slice: Inchon</span>
              </div>
              <figcaption className="shell-launcher__art-caption">
                <span className="shell-launcher__art-kicker">Theater Of Operations: Korea</span>
                <strong className="shell-launcher__art-title">Franchise Preview Panel</strong>
                <span className="shell-launcher__art-copy">Current playable slice remains Inchon / Operation Chromite.</span>
              </figcaption>
            </figure>
          </aside>
        </div>
      </div>
    </section>
  );
}
