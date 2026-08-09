/**
 * Vedi Pocket PC — Electron entry point.
 *
 * Thin wiring layer: every line of business logic lives in
 * `services/*` or `ipc/handlers.js`. This file should stay close to
 * 90 lines — if it grows, pull another concern into its own module.
 */
const { app, BrowserWindow } = require('electron');

const network = require('./services/network');
const { createWindow } = require('./services/window');
const { ProcessManager } = require('./services/process-manager');
const { findBinaries } = require('./services/binaries');
const registerIpcHandlers = require('./ipc/handlers');

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------
let mainWindow = null;
const processes = new ProcessManager();
const binaries = findBinaries(); // resolved once, used by service modules via require

// ---------------------------------------------------------------------------
// IPC
// ---------------------------------------------------------------------------
function bindIpc() {
  registerIpcHandlers({
    getWindow: () => mainWindow,
    processes,
  });
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
async function boot() {
  bindIpc();
  mainWindow = createWindow();

  // Kick off Expo first (mobile dev server), then stream + backend.
  processes.startExpo();
  setTimeout(() => {
    processes.startStreamServer();
    processes.startBackend();
  }, 1200);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
    }
  });
}

app.whenReady().then(boot);

app.on('window-all-closed', () => {
  processes.stopAll();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  processes.stopAll();
});
