# Architecture And Support Note

## MWE Core

MWE core is the playable engine/server/UI stack: scenario content, engine rules, bridge transport, and the browser-facing client. This is the layer that has to behave coherently for a demo or product review to make sense.

## ORL

ORL is the operational readiness layer around the core build. It exists to answer practical support questions:

- does the bridge come up
- does the selected scenario load
- does the UI build
- do replay/snapshot/reporting paths still work
- are the current scenario/support expectations still true

ORL is deliberately support-focused. It is not a feature surface.

## War Lab

War Lab is the exploratory/analysis surface. It is where experimental AI and analysis workflows can be exercised without pretending that every experimental path is part of the main operator runbook. It is useful for depth and investigation, but it is not the front door for demo support.

## Operations Console

The Operations Console is the daily operator shell around those support surfaces. It is responsible for:

- launching the bridge and UI through supported local paths
- exposing scenario-sensitive ORL actions without retyping exact names
- exporting reports
- surfacing known issues and incident bundles
- handing off into terminal-first workflows when needed

## Maintenance Philosophy

The maintenance posture is narrow and factual:

- prefer additive support seams over broad engine churn
- keep support gates close to the real operator path
- make current artifacts reproducible from source-of-truth files and validated runs
- treat missing reports, missing artifacts, and unclear ownership as support debt

## Support Gates

Current practical gates are:

- `ORL / Demo Readiness` for the demo slice
- `ORL / Core Validation Suite` for broader operator confidence
- `ORL / Pitch Support Bundle` for packaging the latest validated state into a reviewer-facing support packet

These gates are meant to reduce folklore, not to replace engineering judgment. If a gate fails, the failure artifact should travel with the discussion.
