/**
 * IPC handlers — bridge between the renderer (sandboxed) and the
 * services in `../services/*`. Each handler is small and delegates to
 * the right service.
 */
const { ipcMain, shell } = require('electron');
const network = require('../services/network');
const qr = require('../services/qr');

function statusPayload(processes) {
  const lanIp = network.getLanIp();
  const streamPort = processes.streamPort || 8080;
  const backendPort = processes.backendPort || 8000;
  const serverUrl = `http://${lanIp}:${streamPort}`;
  const wsUrl = `ws://${lanIp}:${streamPort}/ws`;
  const expoUrl = processes.currentExpoUrl || `exp://${lanIp}:${processes.currentExpoPort}`;

  // The mobile app's QR scanner parses two formats:
  //   A) "ip:port:pin"        — backend pairing (preferred)
  //   B) "http(s)://ip:port"  — direct WS (stream server)
  // We prefer format A whenever the backend is running and we know
  // the PIN, because it carries auth credentials end-to-end. Format B
  // is shown as a fallback when the backend is offline.
  const pairingPin = processes.pairingPin || '';
  const pairingUrl = pairingPin && lanIp
    ? `${lanIp}:${backendPort}:${pairingPin}`
    : serverUrl;

  return {
    lanIp,
    serverPort: streamPort,
    backendPort: backendPort,
    expoPort: processes.currentExpoPort,
    isPythonRunning: processes.isPythonRunning,
    isBackendRunning: processes.isBackendRunning,
    isExpoRunning: processes.isExpoRunning,
    pairingPin,
    pairingUrl,
    serverUrl,
    wsUrl,
    expoUrl,
  };
}

function registerIpcHandlers({ getWindow, processes }) {
  // Helper — defers to the *current* mainWindow, not a captured one.
  // This matters at boot: getWindow() returns null until mainWindow
  // is created inside boot(), and again later if the window is
  // recreated via 'activate'.
  const sendStatus = async () => {
    const win = getWindow();
    if (!win) return;
    const base = statusPayload(processes);
    try {
      // The "PC Stream Connection" QR is the one users actually scan
      // to pair. Encode the pairing URL (`ip:port:pin` when we have a
      // PIN, else `http://ip:8080` as a fallback) so the mobile app's
      // scanner always has the credentials it needs.
      const serverQr = await qr.toDataUrl(base.pairingUrl);
      const expoQr = processes.isExpoRunning ? await qr.toDataUrl(base.expoUrl) : '';
      win.webContents.send('status-update', { ...base, serverQr, expoQr });
    } catch (e) {
      // Never let a QR generation error kill the status pipeline.
      console.error('[IPC] failed to push status-update:', e);
    }
  };

  // Probe the real servers from the renderer process (Chromium) so
  // the UI can show "actually up" even when the Node-side spawn
  // race leaves isRunning flags stale. The Electron renderer's
  // fetch() goes straight to the LAN IP — same network path the
  // mobile app uses — so a port collision / process death
  // surfaces immediately.
  ipcMain.handle('probe-health', async (_event) => {
    const lanIp = network.getLanIp();
    const streamPort = processes.streamPort || 8080;
    const backendPort = processes.backendPort || 8000;
    const targets = {
      streamReachable: `http://${lanIp}:${streamPort}/health`,
      backendReachable: `http://${lanIp}:${backendPort}/health`,
    };
    const out = { streamReachable: false, backendReachable: false };
    await Promise.all(
      Object.entries(targets).map(async ([key, url]) => {
        try {
          const ctrl = new AbortController();
          const timer = setTimeout(() => ctrl.abort(), 1500);
          const res = await fetch(url, { signal: ctrl.signal });
          clearTimeout(timer);
          out[key] = res.ok;
        } catch {
          out[key] = false;
        }
      })
    );
    return out;
  });

  // Push status updates to the renderer whenever the process manager
  // emits one.
  processes.onStatusUpdate(() => {
    sendStatus();
  });

  // Forward child-process logs to the renderer over the matching channel.
  processes.onLog(({ channel, payload }) => {
    const win = getWindow();
    if (!win) return;
    win.webContents.send(channel, payload);
  });

  // Kick off an initial status push — but only once the window's
  // renderer has finished loading, otherwise the message is dropped
  // before preload/contextBridge is wired up.
  const initialWin = getWindow();
  if (initialWin) {
    if (initialWin.webContents.isLoading()) {
      initialWin.webContents.once('did-finish-load', () => sendStatus());
    } else {
      sendStatus();
    }
  }

  ipcMain.handle('get-server-info', async () => {
    const base = statusPayload(processes);
    try {
      const serverQr = await qr.toDataUrl(base.pairingUrl);
      const expoQr = processes.isExpoRunning ? await qr.toDataUrl(base.expoUrl) : '';
      return { ...base, serverQr, expoQr };
    } catch (e) {
      console.error('[IPC] get-server-info QR generation failed:', e);
      return { ...base, serverQr: '', expoQr: '' };
    }
  });

  ipcMain.handle('start-servers', () => {
    processes.startExpo();
    setTimeout(() => {
      processes.startStreamServer();
      processes.startBackend();
    }, 1000);
    return { success: true };
  });

  ipcMain.handle('stop-servers', () => {
    processes.stopStreamAndBackend();
    processes.stopExpo();
    return { success: true };
  });

  ipcMain.handle('restart-servers', () => {
    processes.stopStreamAndBackend();
    processes.stopExpo();
    setTimeout(() => {
      processes.startExpo();
      setTimeout(() => {
        processes.startStreamServer();
        processes.startBackend();
      }, 1000);
    }, 1000);
    return { success: true };
  });

  ipcMain.handle('reload-expo', () => {
    const success = processes.reloadExpo();
    return { success };
  });

  ipcMain.handle('generate-qr', async (_event, text) => qr.toDataUrl(text));

  ipcMain.handle('open-external', (_event, url) => shell.openExternal(url));
}

module.exports = registerIpcHandlers;
