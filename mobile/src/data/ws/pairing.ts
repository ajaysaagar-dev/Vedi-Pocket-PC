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
  const rootUrl = `http://${safeIp}:${targetPort}/`;

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 5000);
    
    // Try /health first, fallback to /
    let res = await fetch(url, { signal: ctrl.signal }).catch(() => null);
    if (!res || !res.ok) {
      res = await fetch(rootUrl, { signal: ctrl.signal }).catch(() => null);
    }
    
    clearTimeout(timer);
    if (res && res.ok) {
      return null;
    }
    return `Server replied with HTTP status ${res ? res.status : 'offline'}.`;
  } catch (err: any) {
    const msg = err?.message || String(err);
    if (msg.includes('Aborted')) {
      return `Server ${safeIp}:${targetPort} did not respond within 5 seconds. Make sure the server is running and Windows Firewall allows inbound connections.`;
    }
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
  // 1. Reachability probe
  const reachErr = await probeReachable(ip, port);
  if (reachErr) return { kind: 'unreachable', reason: reachErr };

  const url = serverUrl(ip, port);

  // 2. Pair
  let pairJson: any;
  try {
    const res = await fetch(`${url}/pair`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin }),
    });
    pairJson = await res.json().catch(() => ({}));
    if (!res.ok || pairJson.status !== 'success' || !pairJson.token) {
      if (res.status === 400) {
        return { kind: 'bad-pin', reason: pairJson.detail || 'Invalid PIN code.' };
      }
      // If server doesn't require PIN authentication (e.g. 404 / 405 on stream server), pair directly
      if (res.status === 404 || res.status === 405) {
        const safeIp = cleanIp(ip);
        const device: PairedDevice = {
          ip: safeIp,
          port: typeof port === 'string' ? parseInt(port, 10) : port,
          token: pin || 'stream_paired_token',
          hostname: `PC Stream (${safeIp})`,
        };
        return { kind: 'ok', device, hostname: device.hostname };
      }
      return {
        kind: 'server-error',
        status: res.status,
        reason: pairJson.detail || `Pairing failed (HTTP ${res.status}).`,
      };
    }
  } catch (err: any) {
    return {
      kind: 'unreachable',
      reason: `Lost connection during pairing: ${err?.message || String(err)}`,
    };
  }

  const token: string = pairJson.token;

  // 3. Status (best-effort — fall back to a default hostname)
  let hostname = 'Unknown PC';
  try {
    const statusRes = await fetch(`${url}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (statusRes.ok) {
      const statusJson: any = await statusRes.json();
      hostname = statusJson.hostname || hostname;
    }
  } catch {
    // Non-fatal — pairing still succeeded.
  }

  const device: PairedDevice = {
    ip,
    port: typeof port === 'string' ? parseInt(port, 10) : port,
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
