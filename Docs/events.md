# MWE Bridge Events (Phase 6)

## Inbound (client -> server)
- `auth` `{ token }`  (optional; required if `security.token` is set)
- `ping` `{}`
- `next_turn` `{}`
- `auto_execute` `{}`
- `execute_orders` `{ orders: [{ unit_id, order_type, target_hex?: [q,r], priority?: number }] }`

## Outbound (server -> client)
- `snapshot` `{ engine, blue, red }`
- `pong` `{ ts }`
- `turn_advanced` `{ turn }`
- `movement_report` `{ movements: [...] }`
- `combat_report` `{ combats: [...] }`
- `error` `{ code, message, details? }`

## JSONL Archive
`logs/events.jsonl`: one JSON object per line, with fields:
`{ ts, type, data }`
