# Founder Beta Release Checklist

This checklist is for Milestone 4 Phase A handoff/package prep on the current branch.

## Required Local Prerequisites

- Repo is on the intended handoff branch.
- Python bridge/runtime dependencies are available in the local environment, including `requirements.txt`.
- `ui/` dependencies are installed and `npm run dev` works.
- `pytest` and `node` are available on `PATH` for the founder gate.
- Local ports `5173`, `8766`, and `8771` are free.
- Reviewer has access to the docs in `docs/` and the screenshot set in `docs/founder_beta_assets/`.
- Reviewer understands this checklist covers the source-checkout founder-beta path, not a native packaged installer.

## Startup Path

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

## Gate And Smoke Checks

Run the founder-beta gate before handoff:

```bash
./scripts/founder_beta_gate.sh
```

The gate currently covers:

- `pytest -q --ignore=server/test_drive_engine.py`
- `pytest --collect-only -q`
- `python server/tools/smoke_test_engine_api.py`
- targeted `view.snapshot`, launcher, and live-entry UI tests

If a narrower smoke is needed while diagnosing, the engine smoke command is:

```bash
python server/tools/smoke_test_engine_api.py
```

## Package / Windows Validation Notes

Validation lane reviewed these launch/package materials:

- `docs/founder_beta_runbook.md`
- `docs/founder_beta_walkthrough.md`
- `docs/founder_beta_validation_note.md`
- `docs/founder_beta_assets/README.md`
- `scripts/founder_beta_gate.sh`
- `scripts/start_mwe.sh`
- `scripts/stop_mwe.sh`
- `run_bridge.bat`
- `install_service_nssm.bat`
- `mwe_bridge_fix.bat`
- `status.bat`
- `start_witpae.bat`
- `ui/package.json`

Current truth:

- The documented source-checkout bridge/UI path was validated on Linux with Python 3.12.3, Node v24.15.0, and npm 11.12.1.
- `?launcher=1` and `?shell=1` returned HTTP 200 from the running Vite server.
- A live WebSocket probe listed scenarios, loaded `inchon_mvp.json`, fetched `view.snapshot`, ended one turn, and fetched the post-turn snapshot.
- `npm run build` completed successfully.
- A native Windows command runner (`cmd.exe`, `powershell.exe`, `pwsh`, or `wine`) was not available in this environment, so Windows execution remains untested.
- Existing root `.bat` and `scripts/start_mwe.sh` / `scripts/stop_mwe.sh` materials reference older local/service paths and should not be used as founder-beta reviewer launchers without separate update and validation.

## Known-Good Current-Branch Flow

Use the reviewer path documented in `docs/founder_beta_runbook.md` and `docs/founder_beta_walkthrough.md`.

1. Open the launcher/front door.
2. Confirm bridge, roster, and shell readiness.
3. Keep the scenario selector on `Inchon`.
4. Enter the command shell from the primary launcher action.
5. Confirm `Demo Controls` and the five-command layer are visible.
6. Open `View` -> `Dashboard`.
7. Confirm `Grease Board / Operations Board V0` is visible and populated.
8. Return to `Theatre`.
9. Click `End Turn`.
10. Confirm the turn/day/calendar advance and the shell remains coherent.

## Screenshot Asset Set

Screenshot assets are under `docs/founder_beta_assets/`.

- `01_launcher_front_door.png`
- `02_snapshot_shell_demo_controls.png`
- `03_dashboard_operations_board_v0.png`
- `04_post_turn_snapshot_loop.png`

The asset manifest is `docs/founder_beta_assets/README.md`.

## Must Be True Before Handoff

- Founder-beta gate passes on the handoff branch.
- Launcher opens from `?launcher=1`.
- Bridge status is connected and the roster is populated.
- `Inchon` enters the playable shell from the launcher primary action.
- Shell reads from the current snapshot-backed bridge path.
- Demo Controls show the five-command layer.
- Dashboard exposes Operations Board V0.
- At least one turn can be ended and the shell remains coherent.
- Handoff docs and refreshed screenshot assets are present in `docs/`.
- The handoff claim is limited to the documented source-checkout path unless a later Windows/package validation record proves more.

## Stop Conditions

Hold handoff if any of these occur:

- The founder-beta gate fails.
- The bridge or launcher cannot start from the documented commands.
- The launcher primary action does not reach the playable shell.
- The shell does not show the current Demo Controls layer.
- Dashboard does not show Operations Board V0.
- Turn resolution crashes or loses shell continuity.
- The screenshot set or validation note is missing.
- The handoff depends on the legacy root `.bat` files or old `scripts/start_mwe.sh` / `scripts/stop_mwe.sh` helpers as reviewer launchers.
- A native Windows/package-readiness claim is required before actual Windows execution has passed.
