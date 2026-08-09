import { useDeviceStore, PairedDevice } from '../store/deviceStore';
import { cleanIp } from './pairing';

class PCRemoteWSClient {
  private ws: WebSocket | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private currentDevice: PairedDevice | null = null;
  private isManuallyClosed = false;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;

  /**
   * Open a WebSocket to the given paired device.
   *
   * Idempotent: if we're already connected (or connecting) to the same
   * device, this is a no-op. Otherwise it closes any prior connection,
   * marks us as "intentional close" so the old socket's onclose doesn't
   * trigger a reconnect race, and opens a fresh socket.
   */
  connect(device: PairedDevice) {
    const safeIp = cleanIp(device.ip);
    const safeDevice = { ...device, ip: safeIp };

    // Already connected (or mid-handshake) to this exact device? Nothing to do.
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) &&
      this.currentDevice &&
      this.currentDevice.ip === safeDevice.ip &&
      this.currentDevice.port === safeDevice.port &&
      this.currentDevice.token === safeDevice.token
    ) {
      return;
    }

    // Close any existing socket. Crucially, we set this.ws = null inside
    // disconnect() so the old socket's onclose sees "I'm not the current
    // socket anymore" and skips reconnect.
    this.disconnect();

    this.currentDevice = safeDevice;
    // Note: do NOT reset isManuallyClosed to false here. The old socket's
    // onclose is still pending and must see isManuallyClosed = true so it
    // doesn't kick off a reconnect. We reset to false only in onopen of
    // the new socket below.

    const url = `ws://${safeDevice.ip}:${safeDevice.port}/ws?token=${safeDevice.token}`;
    console.log(`[WS] Connecting to ${url}`);
    useDeviceStore.getState().setConnectionStatus('connecting');

    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch (e) {
      console.warn('[WS] Failed to instantiate WebSocket:', e);
      useDeviceStore.getState().setConnectionStatus('disconnected');
      this.scheduleReconnect();
      return;
    }

    this.ws = socket;

    socket.onopen = () => {
      // If a newer connect() has already replaced this socket, ignore.
      if (this.ws !== socket) return;

      console.log('[WS] Connected successfully');
      this.isManuallyClosed = false; // safe to auto-reconnect from now on
      this.reconnectAttempts = 0;
      useDeviceStore.getState().setConnectionStatus('connected');

      // Send explicit auth message as a backup to the query-param token.
      this.send({ type: 'auth', token: safeDevice.token });
      this.startHeartbeat();
    };

    socket.onmessage = event => {
      if (this.ws !== socket) return;
      if (typeof event.data !== 'string') return;
      const raw = event.data.trim();
      if (!raw || raw === '[]') return;

      try {
        const msg = JSON.parse(raw);
        if (msg.type === 'pong') {
          // heartbeat alive
        } else if (msg.type === 'auth_result' && msg.status === 'failed') {
          console.warn('[WS] Auth failed:', msg.message);
          this.disconnect();
        }
      } catch (e) {
        // Silently ignore non-JSON socket payloads
      }
    };

    socket.onerror = error => {
      if (this.ws !== socket) return;
      console.warn('[WS] Connection pending or offline.');
    };

    socket.onclose = event => {
      // The key fix: if this socket has been replaced by a newer connect()
      // call, the close was intentional and we must NOT reconnect.
      if (this.ws !== socket) {
        console.log('[WS] Old socket closed (replaced).');
        return;
      }

      console.log('[WS] Connection closed:', event.code, event.reason);
      this.stopHeartbeat();
      this.ws = null;
      useDeviceStore.getState().setConnectionStatus('disconnected');

      // Code 1008 = policy violation / unauthorized. Token invalidated by
      // the server (e.g. agent restart wiped the token set). Stop here —
      // the user must re-pair.
      if (event.code === 1008) {
        console.warn('[WS] Token invalidated by server.');
        this.isManuallyClosed = true;
        return;
      }

      if (!this.isManuallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  send(data: object): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  disconnect() {
    this.isManuallyClosed = true;
    this.stopHeartbeat();
    this.clearReconnect();

    const socket = this.ws;
    this.ws = null; // mark stale BEFORE close() so onclose skips reconnect

    if (socket) {
      try {
        socket.close();
      } catch {
        // ignore
      }
    }

    useDeviceStore.getState().setConnectionStatus('disconnected');
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 8000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private clearReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private scheduleReconnect() {
    this.clearReconnect();
    if (!this.currentDevice || this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WS] Reconnect skipped: no device or max attempts reached.');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 8000);
    console.log(
      `[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );
    useDeviceStore.getState().setConnectionStatus('connecting');

    this.reconnectTimeout = setTimeout(() => {
      if (this.currentDevice) {
        this.connect(this.currentDevice);
      }
    }, delay);
  }
}

export const wsClient = new PCRemoteWSClient();
export default wsClient;
