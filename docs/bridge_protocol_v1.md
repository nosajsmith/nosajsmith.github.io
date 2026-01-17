# MWE Bridge Protocol (WebSocket) — v1.0

## Transport
- WebSocket: `ws://127.0.0.1:8766`
- Health check: `http://127.0.0.1:8770/healthz`

## Request Envelope
Every request MUST be a JSON object:

```json
{
  "id": "string",
  "proto": "1.0",
  "cmd": "string",
  "args": {}
}

