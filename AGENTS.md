# AGENTS.md — MWE (MacArthur War Engine) contributor rules for Codex

## Project overview (repo map)
- `server/` — networking/bridge layer + command dispatch (Phase 8 focus)
  - `server/engine_core.py` — primary command router/dispatcher (if/elif chain today)
  - `server/bridge_protocol.py` — command name constants (prefer using these)
  - `server/tools/` — smoke/utility scripts
- `engine/` — simulation core (change cautiously; performance sensitive)
- `ui/` — client/UI layer
- `scenarios/` — scenario content (treat as data; don’t modify unless ticket says so)
- `docs/` and `Docs/` — documentation (prefer `docs/` going forward; don’t reorganize unless requested)

## Operating principles (MWE doctrine)
- Make changes **minimal and mechanical** unless explicitly asked to redesign.
- Prefer **small, shippable steps** with regression coverage.
- Don’t silently change JSON contracts: preserve response shapes and keys.
- Avoid touching `engine/` unless required; Phase 8 work is primarily in `server/`.

## Command & protocol rules
- Command string constants live in `server/bridge_protocol.py`.
  - Prefer referencing constants (or centralizing strings) rather than scattering new literals.
- All command handlers must:
  - validate inputs (required keys and types)
  - return a consistent error object on failure
  - never crash the server on malformed input

### Recommended error shape
Use a predictable structure for errors, e.g.:
```json
{"ok": false, "error": {"code": "bad_request", "message": "Missing cmd"}}


