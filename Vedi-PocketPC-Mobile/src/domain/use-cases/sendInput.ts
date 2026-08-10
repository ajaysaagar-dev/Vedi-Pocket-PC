/**
 * sendInput.ts — single use case for sending every kind of input to
 * the paired PC.
 *
 * Replaces the ad-hoc WebSocket.send() calls scattered through the
 * UI. Components only need to call `sendInput.execute(...)` and the
 * use case handles serialization, throttling, and graceful no-op when
 * the socket isn't connected yet.
 *
 * The existing `src/ws/client.ts` already exposes a `send(data)`
 * method on the WebSocket client; we wrap it here so callers don't
 * have to know about wire-format details.
 */

import { DeviceInput, deviceInputToWire } from '../entities/deviceInput';

// We import the WebSocket client lazily so this module is usable in
// SSR / Storybook / test contexts where the full store isn't loaded.
let _wsClient: { send(data: object): boolean } | null = null;

export function bindWebSocketClient(client: { send(data: object): boolean }): void {
  _wsClient = client;
}

/**
 * Optional dependency-injection hook for tests. Allows the use case
 * to be unit-tested without spinning up the full Zustand store.
 */
export function _setClientForTest(client: { send(data: object): boolean } | null): void {
  _wsClient = client;
}

export type SendInputResult =
  | { ok: true }
  | { ok: false; reason: 'disconnected' | 'throttled' | 'unsupported' };

/**
 * Send a single input command to the paired PC.
 *
 * `execute` is fire-and-forget — it never throws and never blocks the
 * UI. The caller can subscribe to connection status via the device
 * store and disable controls accordingly.
 */
export function execute(input: DeviceInput): SendInputResult {
  if (!_wsClient) {
    return { ok: false, reason: 'disconnected' };
  }
  const wire = deviceInputToWire(input);
  const sent = _wsClient.send(wire);
  return sent ? { ok: true } : { ok: false, reason: 'disconnected' };
}

/**
 * Convenience helpers — keeps the call sites short.
 */
export const sendInput = {
  moveRelative: (dx: number, dy: number) => execute({ kind: 'relativeMove', dx, dy }),
  moveTo: (x: number, y: number) => execute({ kind: 'absoluteMove', x, y }),
  click: (button: 'left' | 'right' | 'middle' = 'left', x?: number, y?: number) =>
    execute({ kind: 'click', button, x, y }),
  scroll: (dy: number) => execute({ kind: 'scroll', dy }),
  type: (text: string) => execute({ kind: 'text', text }),
  pressKey: (key: string) => execute({ kind: 'keyPress', key }),
  hotkey: (keys: string[]) => execute({ kind: 'hotkey', keys }),
};
