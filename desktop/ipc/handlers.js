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
  const serverUrl = `http://${lanIp}:8000`;
  const wsUrl = `ws://${lanIp}:8000/ws`;
  const expoUrl = processes.currentExpoUrl || `exp://${lanIp}:${processes.currentExpoPort}`;

  return {
    lanIp,
    serverPort: 8000,
    expoPort: processes.currentExpoPort,
    isServerRunning: processes.isServerRunning,
    isExpoRunning: processes.isExpoRunning,
    serverUrl,
    wsUrl,
    expoUrl,
  };
}

function registerIpcHandlers({ getWindow, processes }) {
  // Push status updates to the renderer whenever the process manager
  // emits one.
  processes.onStatusUpdate(async () => {
    const win = getWindow();
    if (!win) return;
    const base = statusPayload(processes);
    win.webContents.send('status-update', {
      ...base,
      serverQr: await qr.toDataUrl(base.serverUrl),
      expoQr: processes.isExpoRunning ? await qr.toDataUrl(base.expoUrl) : '',
    });
  });

  // Forward child-process logs to the renderer over the matching channel.
  processes.onLog(({ channel, payload }) => {
    const win = getWindow();
    if (!win) return;
    win.webContents.send(channel, payload);
  });

  // Kick off an initial status push so the renderer has something to
  // render before the first status update.
  const win = getWindow();
  if (win) {
    const base = statusPayload(processes);
    Promise.all([qr.toDataUrl(base.serverUrl), qr.toDataUrl(base.expoUrl)])
      .then(([serverQr, expoQr]) => {
        win.webContents.send('status-update', { ...base, serverQr, expoQr });
      });
  }

  ipcMain.handle('get-server-info', async () => {
    const base = statusPayload(processes);
    return {
      ...base,
      serverQr: await qr.toDataUrl(base.serverUrl),
      expoQr: processes.isExpoRunning ? await qr.toDataUrl(base.expoUrl) : '',
    };
  });

  ipcMain.handle('start-servers', () => {
    processes.startExpo();
    setTimeout(() => {
      processes.startServer();
    }, 1000);
    return { success: true };
  });

  ipcMain.handle('stop-servers', () => {
    processes.stopServer();
    processes.stopExpo();
    return { success: true };
  });

  ipcMain.handle('restart-servers', () => {
    processes.stopServer();
    processes.stopExpo();
    setTimeout(() => {
      processes.startExpo();
      setTimeout(() => {
        processes.startServer();
      }, 1000);
    }, 1000);
    return { success: true };
  });

  ipcMain.handle('generate-qr', async (_event, text) => qr.toDataUrl(text));

  ipcMain.handle('open-external', (_event, url) => shell.openExternal(url));
}

module.exports = registerIpcHandlers;
