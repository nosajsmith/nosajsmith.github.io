# Founder Beta Validation Note

This note records what has actually been verified for the current-branch Milestone 4 Phase A handoff/package refresh.

## Branch And Scope

- Branch observed during refresh: `feat/ui-high-shine`.
- Scope verified in this pass: founder gate, launcher/front door, snapshot-backed Inchon shell, Demo Controls/five-command layer, Dashboard, Operations Board V0, one-turn continuity, handoff docs, and refreshed screenshot assets.
- Scope not changed: gameplay semantics, backend protocol, AI logic, bridge code, map model code, smoke tooling, and shell feature work.

This is not a claim that the full product, all scenarios, packaged installer, Windows launcher, final campaign experience, or production onboarding are release-complete.

## What Is Ready

- Reviewer-facing launcher path exists at `?launcher=1`.
- Direct shell validation path exists at `?shell=1`.
- Default reviewer path remains `Inchon` / `inchon_mvp.json`.
- Shell and Dashboard consume the current `view.snapshot` bridge read model.
- Demo Controls expose `Move`, `Attack`, `Hold / Defend`, `Reserve / Rest`, and `End Turn`.
- Operations Board V0 is visible from `View` -> `Dashboard`.
- One turn can be resolved from the shell and the snapshot picture remains coherent.
- Handoff runbook, walkthrough, checklist, validation note, and asset manifest exist.
- Screenshot set has been refreshed from a live local bridge/UI session for the current shell/dashboard/control layer.

## What Was Verified In This Pass

- Founder gate passed before package edits when run with the project Python and Node environments on `PATH`.
- Launcher opened with bridge connected, six scenarios ready, and shell readiness visible.
- Current shell opened with `Theater of Operations: Inchon`, map, top-strip controls, bridge status, and Demo Controls visible.
- Dashboard opened through the `View` selector.
- `Grease Board / Operations Board V0` rendered with scenario identity, objective truth, pressure/hotspots, AI/command picture, and recent operational picture.
- `End Turn` advanced the shell from Turn 1 / Day 1 / 15 Sept 1950 to Turn 2 / Day 2 / 16 Sept 1950 in the captured session.
- Screenshot assets were captured from the live local path and placed under `docs/founder_beta_assets/`.

## Package / Windows Validation Lane - 2026-05-03

This lane was limited to package and launch confidence. No gameplay semantics, AI logic, bridge protocol, map model files, backend feature code, or UI polish were changed.

Validation targets reviewed:

- Founder handoff docs: `docs/founder_beta_runbook.md`, `docs/founder_beta_release_checklist.md`, `docs/founder_beta_walkthrough.md`, `docs/founder_beta_validation_note.md`, and `docs/founder_beta_assets/README.md`
- Gate and startup helpers: `scripts/founder_beta_gate.sh`, `scripts/start_mwe.sh`, and `scripts/stop_mwe.sh`
- Windows/local helper files: `run_bridge.bat`, `install_service_nssm.bat`, `mwe_bridge_fix.bat`, `status.bat`, and `start_witpae.bat`
- UI package metadata: `ui/package.json`

Environment used:

- Linux source checkout
- Python 3.12.3 from the project virtual environment
- Node v24.15.0
- npm 11.12.1
- No Windows runner was available: `cmd.exe`, `powershell.exe`, `pwsh`, and `wine` were not found

Commands/results:

- Bare `./scripts/founder_beta_gate.sh` failed in the default shell with `pytest: command not found`; this confirms the gate still depends on an activated Python/Node environment.
- `./scripts/founder_beta_gate.sh` passed after putting the project Python virtual environment and Node toolchain on `PATH`; visible Python result was `269 passed`.
- Documented bridge startup succeeded on `127.0.0.1:8766` with health at `127.0.0.1:8771/healthz`.
- Documented UI startup succeeded with `npm run dev -- --host 127.0.0.1 --port 5173`.
- `http://127.0.0.1:5173/?launcher=1` and `http://127.0.0.1:5173/?shell=1` returned HTTP 200.
- A live WebSocket probe listed scenarios, found Inchon, loaded `inchon_mvp.json`, fetched `view.snapshot`, ran `end_turn`, and fetched the post-turn snapshot; observed turn advanced from 1 to 2 with post-turn reports present.
- `npm run build` passed; Vite emitted only the large chunk-size warning.

Packaging findings:

- The current honest reviewer launch path is a source checkout with Python dependencies, UI dependencies, the bridge command, the Vite command, and the browser URL.
- The existing root `.bat` files and `scripts/start_mwe.sh` / `scripts/stop_mwe.sh` reference older bridge/service/local-game paths and are not founder-beta reviewer launchers unless separately updated and revalidated.
- Native Windows execution, packaged installer behavior, Windows service setup, and a one-click launcher remain untested.

## Gate Status

Current validation command:

```bash
./scripts/founder_beta_gate.sh
```

Expected visible Python-suite result in this environment:

```text
269 passed
```

The script also runs collection, engine smoke, and targeted Node UI tests. The Node test output is redirected by the script; successful gate status is exit code `0`.

If `pytest` or `node` is missing, the correct action is to activate the project Python environment and Node environment, then rerun the same script. Do not treat a bare-shell PATH failure as proof that the handoff path itself failed.

## Screenshot Status

Captured assets live in `docs/founder_beta_assets/`.

The refreshed set includes:

- launcher/front door
- snapshot-backed shell with Demo Controls
- Dashboard with Operations Board V0
- post-turn shell continuity

These are truthful reviewer screenshots from a local current-branch session, not final marketing composites.

## Known Limits And Out-Of-Scope Areas

- Validation is centered on the Inchon preview path.
- Other roster scenarios are not the primary handoff path and were not revalidated as full reviewer walkthroughs in this pass.
- Windows validation is pending / outside this package refresh.
- Packaged launcher/installer validation is pending / outside this package refresh.
- Legacy root `.bat` files and old shell helpers are not validated founder-beta launchers.
- Backend protocol, map model semantics, AI internals, scenario/OOB logic, and gameplay systems were intentionally not changed.
- Unit-order Demo Controls are current operator affordances over existing shell/planner paths and should not be described as a finished production order system.
- Audio is optional presentation support and is not required for successful walkthrough.

## Handoff Position

Milestone 4 Phase A is supportable for external source-checkout handoff if the founder gate remains green and the documented Inchon launcher -> shell -> Dashboard / Operations Board V0 -> End Turn path remains reproducible from `docs/founder_beta_runbook.md`.

Do not claim native Windows package or installer readiness from this lane. That claim should remain on hold until the PowerShell/source-checkout path or a real packaged launcher is executed on Windows and recorded in this note.
