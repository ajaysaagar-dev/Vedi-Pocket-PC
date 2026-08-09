/**
 * Window factory — creates the BrowserWindow that hosts the renderer.
 */
const { BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1080,
    height: 780,
    minWidth: 880,
    minHeight: 650,
    title: 'VediPocketPC Controller',
    backgroundColor: '#0F131A',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      // __dirname = .../controller/services → '../preload.js' = controller/preload.js
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  win.loadFile(path.join(__dirname, '..', '..', 'index.html'));
  win.on('closed', () => { /* window is closed by Electron */ });
  return win;
}

module.exports = { createWindow };
