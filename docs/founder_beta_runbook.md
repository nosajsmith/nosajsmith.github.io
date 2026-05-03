# Founder Beta Runbook

This runbook covers the current-branch reviewer path for Milestone 4 Phase A package handoff. It replaces the older UI High Shine-only framing with the current snapshot-backed shell, Dashboard, Operations Board V0, and Demo Controls surface.

## Prerequisites

- Repo checkout on the current handoff branch.
- Python bridge/runtime dependencies available for the bridge process.
- Node/UI dependencies installed in `ui/` so `npm run dev` works.
- Local ports `5173`, `8766`, and `8771` available.
- `pytest` and `node` available on `PATH` before running the founder gate.
- This is a source-checkout launch path. A native Windows package, installer, or service launcher is not validated by this runbook.

## Package / Windows Boundary

The validated founder-beta path is the bridge plus Vite UI startup documented below. Existing root-level Windows/service helper files such as `run_bridge.bat`, `install_service_nssm.bat`, `mwe_bridge_fix.bat`, `status.bat`, and `start_witpae.bat` are legacy/local-ops material and should not be treated as the founder-beta reviewer launcher unless they are separately updated and revalidated.

For a Windows source checkout, use the same commands in PowerShell-style form and then follow the same browser path:

```powershell
$repo = (Get-Location).Path
$env:PYTHONPATH = $repo
$env:MWE_SCENARIO_DIR = Join-Path $repo "scenarios"
python server/mwe_bridge_p8_ws15.py --host 127.0.0.1 --port 8766 --health-host 127.0.0.1 --health-port 8771
```

In a second PowerShell terminal:

```powershell
cd ui
npm run dev -- --host 127.0.0.1 --port 5173
```

These Windows-form commands are the intended equivalent of the validated source-checkout path, but they still require actual Windows execution before making a native Windows-readiness claim.

## Launch

From the repo root, start the bridge:

```bash
PYTHONPATH=$PWD MWE_SCENARIO_DIR=$PWD/scenarios python server/mwe_bridge_p8_ws15.py --host 127.0.0.1 --port 8766 --health-port 8771
```

In a second terminal, start the UI:

```bash
cd ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Open the reviewer front door:

```text
http://127.0.0.1:5173/?launcher=1
```

Direct shell entry remains available for validation and recovery:

```text
http://127.0.0.1:5173/?shell=1
```

Use `?launcher=1` as the reviewer default. The launcher is still the intended first screen for handoff review.

## Current Reviewer Path

- Default scenario path: `Inchon` / `inchon_mvp.json`.
- Primary launcher action: `Launch Inchon`, `Load Inchon`, or `Enter Command Shell`, depending on whether the bridge already has the selected scenario active.
- Shell source: `view.snapshot` from the live bridge read model.
- Reviewer path: launcher -> selected scenario -> snapshot-backed shell -> Dashboard / Operations Board V0 -> one turn resolved -> shell continuity check.

## Snapshot-Backed Surfaces

- Shell top strip, map, reports, weather, branch navigation, and current focus read from the normalized snapshot.
- Dashboard is reached from the top-strip `View` selector by choosing `Dashboard`.
- Operations Board V0 appears on the Dashboard as `Grease Board / Operations Board V0`.
- The board summarizes scenario identity, campaign/turn timing, score, objective truth, pressure/hotspots, AI/command state, and recent reports from the current snapshot.

## Demo Controls

The top strip exposes one compact Demo Controls layer:

- `Move`
- `Attack`
- `Hold / Defend`
- `Reserve / Rest`
- `End Turn`

Unit-order controls require a selected unit. `End Turn` resolves the next turn and refreshes the snapshot picture.

## Known-Good One-Turn Loop

1. Open `http://127.0.0.1:5173/?launcher=1`.
2. Confirm the launcher shows a connected bridge, populated roster, and a ready shell state.
3. Keep the scenario selector on `Inchon`.
4. Use the primary launcher action to enter the command shell.
5. Confirm the shell shows `Theater of Operations: Inchon`, the map, `Demo Controls`, and live bridge status.
6. Open `View` -> `Dashboard`.
7. Confirm `Grease Board / Operations Board V0` is visible and populated from `view.snapshot`.
8. Return to `Theatre`.
9. Click `End Turn`.
10. Confirm the turn/day/calendar advance and the shell remains coherent.
11. Check that the report/current-focus path reflects post-turn AI or player-order continuity when the bridge exposes it.

## Known Limits

- This is a founder-beta handoff package for the current branch, not a full release-readiness claim.
- Validation is centered on the Inchon preview path.
- Other scenarios may appear in the roster but are not the default reviewer path for this package.
- Unit-order buttons are affordances over existing shell/planner paths; they do not imply a finished production order UI.
- The Dashboard and Operations Board V0 are snapshot-backed V0 surfaces and should not be described as final campaign command UX.
- Packaged installer, native Windows launcher validation, broad scenario coverage, and final onboarding remain outside this package.
- Legacy shell/batch launchers in the repo are not founder-beta launch instructions unless a later validation note explicitly says so.
- Audio is optional presentation support and is not required for the walkthrough.

## Screenshot Set

The refreshed current-branch screenshots live in `docs/founder_beta_assets/`:

1. Launcher/front door with bridge, roster, and shell readiness.
2. Snapshot-backed shell with Demo Controls and top-strip operator affordances.
3. Dashboard showing Operations Board V0.
4. Post-turn shell with advanced turn/day and refreshed snapshot picture.

The asset manifest is `docs/founder_beta_assets/README.md`.

## Verification

Run the founder-beta gate before handoff:

```bash
./scripts/founder_beta_gate.sh
```

If the local shell cannot find `pytest` or `node`, activate the project Python environment and local Node environment first, then rerun the same gate script.
