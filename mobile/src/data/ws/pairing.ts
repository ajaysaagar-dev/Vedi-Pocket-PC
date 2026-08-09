/**
 * Pairing helpers — separates "can we reach the host?" from "is the PIN right?".
 *
 * The mobile app used to show the same generic "ensure both devices are on the
 * same network" message for every failure mode. With these helpers we probe
 * /health first (no auth) so we can tell the user exactly what failed.
 */

import { PairedDevice } from '../../store/deviceStore';

export type PairResult =
  | { kind: 'ok'; device: PairedDevice; hostname: string }
  | { kind: 'unreachable'; reason: string }
  | { kind: 'bad-pin'; reason: string }
  | { kind: 'server-error'; status: number; reason: string };

/** Clean and sanitize IP/Host string from raw QR codes or text inputs. */
export function cleanIp(input: string): string {
  if (!input) return '127.0.0.1';
  let cleaned = input.trim();
  // Strip protocol headers
  cleaned = cleaned.replace(/^(https?:\/\/|wss?:\/\/)/i, '');
  // Strip paths
  cleaned = cleaned.split('/')[0];
  // Extract IPv4 if port is attached
  const match = cleaned.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
  if (match) {
    return match[0];
  }
  // Strip port if hostname:port
  if (cleaned.includes(':')) {
    cleaned = cleaned.split(':')[0];
  }
  return cleaned || '127.0.0.1';
}

/** Build the base URL for the agent. */
function serverUrl(ip: string, port: number | string) {
  const safeIp = cleanIp(ip);
  return `http://${safeIp}:${port}`;
}

/**
 * Quick reachability probe. Hits public endpoints.
 * Returns null on success, or a human-readable reason on failure.
 */
export async function probeReachable(ip: string, port: number | string): Promise<string | null> {
  const safeIp = cleanIp(ip);
  const targetPort = port || 8000;
  const url = `http://${safeIp}:${targetPort}/health`;

  try {
    const fetchPromise = fetch(url);
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Timed out')), 5000)
    );

    const res = (await Promise.race([fetchPromise, timeoutPromise])) as Response;
    if (res && res.ok) {
      return null;
    }
    return `Server replied with HTTP status ${res ? res.status : 'offline'}.`;
  } catch (err: any) {
    const msg = err?.message || String(err);
    return `Could not reach server (${safeIp}:${targetPort}): ${msg}`;
  }
}

/**
 * Full pairing flow:
 *  1. Probe /health (reachability)
 *  2. POST /pair with the PIN (auth)
 *  3. Fetch /status to grab the hostname (so we can label the device)
 *
 * Returns a tagged union so the caller can render a precise error.
 */
export async function pairWithHost(
  ip: string,
  port: number | string,
  pin: string
): Promise<PairResult> {
  const safeIp = cleanIp(ip);
  const targetPort = typeof port === 'string' ? parseInt(port, 10) || 8000 : port || 8000;
  const url = `http://${safeIp}:${targetPort}`;

  // 1. Direct POST /pair authentication
  let pairJson: any;
  try {
    const fetchPromise = fetch(`${url}/pair`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin }),
    });

    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Connection timed out after 6 seconds')), 6000)
    );

    const res = (await Promise.race([fetchPromise, timeoutPromise])) as Response;

    pairJson = await res.json().catch(() => ({}));
    if (!res.ok || pairJson.status !== 'success' || !pairJson.token) {
      if (res.status === 400) {
        return { kind: 'bad-pin', reason: pairJson.detail || 'Invalid PIN code.' };
      }
      return {
        kind: 'server-error',
        status: res.status,
        reason: pairJson.detail || `Pairing failed (HTTP ${res.status}).`,
      };
    }
  } catch (err: any) {
    const msg = err?.message || String(err);
    return {
      kind: 'unreachable',
      reason: `Could not connect to server at ${safeIp}:${targetPort}: ${msg}`,
    };
  }

  const token: string = pairJson.token;

  // 2. Fetch /status for hostname (best-effort)
  let hostname = `PC (${safeIp})`;
  try {
    const statusRes = await fetch(`${url}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (statusRes.ok) {
      const statusJson: any = await statusRes.json();
      hostname = statusJson.hostname || hostname;
    }
  } catch {
    // Non-fatal
  }

  const device: PairedDevice = {
    ip: safeIp,
    port: targetPort,
    token,
    hostname,
  };
  return { kind: 'ok', device, hostname };
}

/** Map a PairResult to the user-facing alert title + body. */
export function describePairError(result: Exclude<PairResult, { kind: 'ok' }>): {
  title: string;
  body: string;
} {
  if (result.kind === 'bad-pin') {
    return { title: 'Wrong PIN', body: result.reason };
  }
  if (result.kind === 'server-error') {
    return { title: `Server error (HTTP ${result.status})`, body: result.reason };
  }
  return { title: 'PC not reachable', body: result.reason };
}
