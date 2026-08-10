/**
 * preload.js — exposes a narrow, typed API to the renderer.
 *
 * The renderer never touches ipcRenderer / Node directly; it only
 * sees `window.electronAPI`. This boundary is what lets us refactor
 * the backend freely without breaking the UI.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getServerInfo: () => ipcRenderer.invoke('get-server-info'),
  startServers: () => ipcRenderer.invoke('start-servers'),
  stopServers: () => ipcRenderer.invoke('stop-servers'),
  restartServers: () => ipcRenderer.invoke('restart-servers'),
  generateQR: (text) => ipcRenderer.invoke('generate-qr', text),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  probeHealth: () => ipcRenderer.invoke('probe-health'),

  onPythonLog: (callback) => {
    const sub = (_event, data) => callback(data);
    ipcRenderer.on('python-log', sub);
    return () => ipcRenderer.removeListener('python-log', sub);
  },
  onExpoLog: (callback) => {
    const sub = (_event, data) => callback(data);
    ipcRenderer.on('expo-log', sub);
    return () => ipcRenderer.removeListener('expo-log', sub);
  },
  onStatusUpdate: (callback) => {
    const sub = (_event, data) => callback(data);
    ipcRenderer.on('status-update', sub);
    return () => ipcRenderer.removeListener('status-update', sub);
  },
});
