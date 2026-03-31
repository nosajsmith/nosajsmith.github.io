# ORL Round 1 Support

## How To Run Tests

- `pytest -q tests/engine/test_testing_api.py tests/engine/test_round1_support.py tests/orl tests/operations_console`
- `python -m tools.orl.round1_gate gate`
- `python -m tools.orl.round1_gate validate-scenarios`
- `python -m tools.orl.round1_gate scenario-matrix`
- `python -m tools.orl.demo_readiness checklist`
- `python -m tools.orl.demo_readiness deterministic-demo inchon_mvp`
- `python -m tools.orl.demo_readiness validate-artifacts`
- `python -m tools.orl.pitch_support export`

## Artifacts

- `artifacts/orl/*` contains Round 1 validator, matrix, and gate JSON artifacts.
- `artifacts/operations_console/*` contains exported console reports and incident bundles.
- `artifacts/pitch_support/*` contains regenerated pitch-support bundles assembled from the current validated reports and source files.
- `artifacts/operations_console/*-orl-demo-readiness.json` is the current one-button demo report artifact from the console.
- `artifacts/operations_console/engine_adapter/replays/*.json`, `snapshots/*.json`, and `compares/*.json` are the deterministic demo runner artifacts.
- Inspect replay/snapshot artifacts first when `persistence.snapshot_replay_compare` fails.
- Inspect matrix artifacts first when `scenario.matrix` or `ai.objective_reasoning` fails.

## Bug Reports

- File blocker reports with the artifact path, failing blocker class, scenario id, variant id if applicable, and the exact command that reproduced the failure.
- Use incident bundles under `artifacts/operations_console/incidents` when the Operations Console captured the failure.
- Use `tools/orl/round1_manifest.yaml` as the source of expected scenario outcomes and operator guidance.
- Use `tools/orl/demo_checklist.yaml` as the source of the current demo/release checklist and artifact expectations.

## Expected Outcomes

- `inchon_mvp`: engine-loadable, explainability-ready, primary objective focus on Seoul axis, useful for replay/snapshot/explainability support.
- `mini_gc_1942`: engine-loadable, BAI-playable, useful for objective reasoning and first-playable AI sanity.
- `gc_1942_historical`: engine-loadable from `server/scenarios`, useful as a broader historical skeleton readiness check.
- Variants `base`, `aggressive`, and `cautious` should all produce legal AI orders and a non-empty chosen operation for matrix-enabled scenarios.
- Demo path: smoke suite, UI build, deterministic demo runner, and artifact validation should all pass before internal or external review.
