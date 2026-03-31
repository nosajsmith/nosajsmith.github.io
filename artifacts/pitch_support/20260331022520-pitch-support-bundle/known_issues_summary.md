# Known Issues Summary

Source: `/home/jason/dev/mwe/tools/operations_console/known_issues.yaml`
Issue Count: 2

## KI-001 — UI build occasionally fails when local Node dependencies are stale

- Severity: medium
- Status: known
- Category: ORL
- Affects: ORL / UI Build Check
- Scenarios: <all>
- Notes: Refresh dependencies in ui/ and rerun when this reproduces on a clean branch.

## KI-002 — Snapshot smoke may fail on inchon_mvp while persistence contract is in flux

- Severity: high
- Status: waived
- Category: ORL
- Affects: ORL / Snapshot Smoke, ORL / Core Validation Suite
- Scenarios: inchon_mvp, inchon_mvp.json
- Notes: Temporary waiver for operator visibility while the snapshot format stabilizes.
