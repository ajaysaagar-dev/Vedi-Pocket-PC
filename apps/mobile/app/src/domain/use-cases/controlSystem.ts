/**
 * controlSystem.ts — power / volume / system control use case.
 *
 * Hits the REST endpoints exposed by vedi-pocketpc-backend under
 * /system and /media. Replaces the scattered fetch() calls in the
 * mobile UI — one place to add retry logic, auth-header wiring, and
 * error handling.
 *
 * The mobile app already stores a `PairedDevice` (with `ip`, `port`,
 * `token`) in the device store; we read from there so callers don't
 * have to pass credentials every time.
 */

import { PairedDevice } from '../../store/deviceStore';

const SYSTEM_ENDPOINTS = {
  lock: '/system/lock',
  sleep: '/system/sleep',
  shutdown: '/system/shutdown',
} as const;

const MEDIA_ENDPOINTS = {
  volume: '/media/volume',
  volumeUp: '/media/volume/up',
  volumeDown: '/media/volume/down',
  volumeMute: '/media/volume/mute',
  playPause: '/media/playpause',
  next: '/media/next',
  prev: '/media/prev',
} as const;

export type ControlResult =
  | { ok: true }
  | { ok: false; reason: 'unauthorized' | 'network' | 'server'; detail?: string };

/**
 * Lazily resolve the active paired device from the store so this
 * module stays decoupled from Zustand.
 */
let _getActiveDevice: (() => PairedDevice | null) | null = null;
export function bindDeviceProvider(provider: () => PairedDevice | null): void {
  _getActiveDevice = provider;
}

async function post(
  path: string,
  body?: Record<string, unknown>,
): Promise<ControlResult> {
  if (!_getActiveDevice) return { ok: false, reason: 'network', detail: 'No paired device.' };
  const device = _getActiveDevice();
  if (!device) return { ok: false, reason: 'network', detail: 'No active device.' };

  try {
    const res = await fetch(`http://${device.ip}:${device.port}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${device.token}`,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) return { ok: false, reason: 'unauthorized' };
    if (!res.ok) return { ok: false, reason: 'server', detail: `HTTP ${res.status}` };
    return { ok: true };
  } catch (err) {
    return {
      ok: false,
      reason: 'network',
      detail: (err as Error)?.message ?? String(err),
    };
  }
}

export const controlSystem = {
  // ----- power -----
  lock: () => post(SYSTEM_ENDPOINTS.lock),
  sleep: () => post(SYSTEM_ENDPOINTS.sleep),
  shutdown: () => post(SYSTEM_ENDPOINTS.shutdown),

  // ----- volume -----
  setVolume: (level: number) =>
    post(MEDIA_ENDPOINTS.volume, { level: Math.max(0, Math.min(100, Math.round(level))) }),
  volumeUp: () => post(MEDIA_ENDPOINTS.volumeUp),
  volumeDown: () => post(MEDIA_ENDPOINTS.volumeDown),
  volumeMute: () => post(MEDIA_ENDPOINTS.volumeMute),

  // ----- media -----
  playPause: () => post(MEDIA_ENDPOINTS.playPause),
  next: () => post(MEDIA_ENDPOINTS.next),
  prev: () => post(MEDIA_ENDPOINTS.prev),
};
