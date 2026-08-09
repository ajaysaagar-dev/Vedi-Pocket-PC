const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getServerInfo: () => ipcRenderer.invoke('get-server-info'),
  startServers: () => ipcRenderer.invoke('start-servers'),
  stopServers: () => ipcRenderer.invoke('stop-servers'),
  restartServers: () => ipcRenderer.invoke('restart-servers'),
  generateQR: (text) => ipcRenderer.invoke('generate-qr', text),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  onPythonLog: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('python-log', subscription);
    return () => ipcRenderer.removeListener('python-log', subscription);
  },
  onExpoLog: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('expo-log', subscription);
    return () => ipcRenderer.removeListener('expo-log', subscription);
  },
  onStatusUpdate: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('status-update', subscription);
    return () => ipcRenderer.removeListener('status-update', subscription);
  },
});
