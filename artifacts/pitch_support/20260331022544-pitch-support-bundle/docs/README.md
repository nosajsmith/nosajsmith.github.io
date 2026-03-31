# Pitch Support Runbook

This directory is the factual support/runbook layer for internal review, demo support, and publisher diligence.

## Export The Current Package

- Primary path: `python -m tools.orl.pitch_support export`
- Scenario override: `python -m tools.orl.pitch_support export inchon_mvp`
- Console path: run `ORL / Pitch Support Bundle` after `ORL / Demo Readiness` and `ORL / Core Validation Suite`

The bundle is written under `artifacts/pitch_support/<timestamp>-pitch-support-bundle/`.

## Launch The Build

- Open the Operations Console: `python -m tools.operations_console.app`
- In the console, use `Run Bridge` and `Run MWE` for the supported local launcher path
- Terminal-first fallback:
  - bridge: `python server/mwe_bridge_p8_ws15.py --host 127.0.0.1 --port 8766 --health-port 8771`
  - UI: `cd ui && npm run dev -- --host 127.0.0.1 --port 4175`

## Run The Demo

- Refresh scenarios from the current bridge URI
- Select `inchon_mvp` unless a different demo slice has been explicitly prepared
- Run `ORL / Demo Readiness`
- Review the generated `*-orl-demo-readiness.json` and `*.txt` report under `artifacts/operations_console/`
- Use `ORL / Latest Artifacts` if you need the current replay, snapshot, and compare paths quickly

## Validate The Build

- Fast operator path: run `ORL / Core Validation Suite`
- Headless ORL path:
  - `python -m tools.orl.round1_gate gate`
  - `python -m tools.orl.demo_readiness deterministic-demo inchon_mvp`
  - `python -m tools.orl.demo_readiness latest-artifacts`
- Test path: `pytest -q tests/engine tests/orl tests/operations_console`

## Expected Outputs

- `artifacts/operations_console/*-orl-demo-readiness.json` and `.txt`
- `artifacts/operations_console/*-orl-core-validation-suite.json` and `.txt`
- `artifacts/operations_console/engine_adapter/replays/*.json`
- `artifacts/operations_console/engine_adapter/snapshots/*.json`
- `artifacts/operations_console/engine_adapter/compares/*.json`
- `artifacts/pitch_support/<timestamp>-pitch-support-bundle/`

If the report or engine-adapter artifacts are missing, rerun the corresponding validation flow before packaging anything for review.

## Current Known Issues

Authoritative source: `tools/operations_console/known_issues.yaml`

- `KI-001`: UI build can fail when local Node dependencies are stale. Expected operator response is to refresh `ui/` dependencies and rerun the build check.
- `KI-002`: `inchon_mvp` snapshot smoke can still be waived to `WARN` while the persistence contract settles. The waiver is for visibility, not for ignoring the report.

The pitch-support bundle also regenerates `known_issues_summary.json` and `known_issues_summary.md` from the source file above.

## Expected Demo Slice Outcomes

- `inchon_mvp` loads from the live roster without requiring an exact filename every run
- the UI build succeeds
- replay compare stays deterministic
- snapshot smoke remains stable enough for demo support

## Support Discipline

- Use generated reports, not copied snippets, when summarizing readiness
- Keep support artifacts traceable back to the current build and current source files
- Treat missing reports as support blockers, even if the demo still happens to work locally
