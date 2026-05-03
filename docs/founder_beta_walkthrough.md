# Founder Beta Walkthrough Note

Use this as the compact reviewer-facing preview flow for the current branch.

## Launcher

- Open `http://127.0.0.1:5173/?launcher=1`.
- Confirm the bridge is connected and the scenario roster is populated.
- Keep the selector on `Inchon`.
- Use the primary launcher action to enter the command shell.

## Shell Entry

- Confirm `Theater of Operations: Inchon` appears cleanly.
- Confirm the map, reports/current-focus path, bridge status, and `Demo Controls` are visible.
- Treat the shell as the current snapshot-backed operator surface.

## Dashboard / Operations Board

- Use the top-strip `View` selector and choose `Dashboard`.
- Confirm `Grease Board / Operations Board V0` appears.
- Review objective truth, pressure/hotspots, AI/command picture, and recent operational picture.
- Return to `Theatre` when ready to continue the live loop.

## Demo Controls

- The five visible commands are `Move`, `Attack`, `Hold / Defend`, `Reserve / Rest`, and `End Turn`.
- Unit-order commands arm after a unit is selected.
- `End Turn` is the current known-good turn-resolution control for the reviewer loop.

## One-Turn Continuity

- Click `End Turn`.
- Confirm turn/day/calendar values advance.
- Confirm the shell remains stable after turn resolution.
- Review the report/current-focus path for post-turn AI or player-order continuity when exposed by the bridge.

The expected outcome is current-branch coherence across launcher, snapshot-backed shell, Dashboard / Operations Board V0, Demo Controls, and one-turn continuity. Do not present this as final release scope.
