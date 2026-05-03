# Founder Beta Screenshot Set

This folder contains the current-branch reviewer screenshot set for Milestone 4 Phase A. The set was refreshed from a live local bridge/UI session so it reflects the snapshot-backed shell, Demo Controls, Dashboard, and Operations Board V0.

## Asset Index

| Filename | What it shows | Why it matters |
| --- | --- | --- |
| `01_launcher_front_door.png` | Launcher/front door with connected bridge, six-scenario roster, and shell readiness | Establishes the intended reviewer entry path |
| `02_snapshot_shell_demo_controls.png` | Snapshot-backed Inchon shell with map, bridge status, and Demo Controls/five-command layer | Shows the current operator surface rather than the older UI High Shine-only shell |
| `03_dashboard_operations_board_v0.png` | Dashboard view with `Grease Board / Operations Board V0` populated from `view.snapshot` | Captures the current reviewer-facing board/summary truth |
| `04_post_turn_snapshot_loop.png` | Shell after `End Turn`, with Turn 2 / Day 2 / 16 Sept 1950 visible | Confirms the current one-turn loop preserves shell coherence |

## Capture Notes

- Source path: live bridge -> launcher -> shell -> Dashboard -> Theatre -> `End Turn`.
- Capture size: 1600 x 1000.
- Local capture method used Electron offscreen rendering against the running Vite/bridge session after Firefox headless screenshotting was not reliable in this environment.
- These images are for reviewer understanding, not final marketing polish.
