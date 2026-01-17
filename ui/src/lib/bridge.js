export const WS_URL_DEFAULT = "ws://127.0.0.1:8766";
export const PROTO = "1.0";

/**
 * Create a protocol v1 request envelope.
 */
export function makeReq(cmd, args = {}, id = crypto.randomUUID()) {
  return { id, proto: PROTO, cmd, args };
}

/**
 * Safe JSON parse for WS messages.
 */
export function safeJsonParse(raw) {
  try {
    return { ok: true, value: JSON.parse(raw) };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}
