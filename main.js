const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { spawn, exec } = require('child_process');
const QRCode = require('qrcode');

let mainWindow = null;
let pythonProcess = null;
let backendProcess = null;
let expoProcess = null;

let isPythonRunning = false;
let isBackendRunning = false;
let isExpoRunning = false;

let currentExpoPort = 8081;
let currentExpoUrl = '';

function getLanIp() {
  const interfaces = os.networkInterfaces();
  const virtualKeywords = [
    'vethernet', 'vbox', 'vmware', 'docker', 'wsl', 'virtual', 'zerotier',
    'tailscale', 'vpn', 'tap', 'tun', 'pseudo', 'bluetooth', 'hyper-v',
    'npcap', 'default switch', 'host-only'
  ];

  let candidatePhysicalIp = null;
  let fallbackIp = null;

  for (const name of Object.keys(interfaces)) {
    const lowerName = name.toLowerCase();
    const isVirtual = virtualKeywords.some(keyword => lowerName.includes(keyword));

    for (const net of interfaces[name]) {
      if (net.family === 'IPv4' && !net.internal) {
        if (!isVirtual) {
          if (lowerName.includes('wi-fi') || lowerName.includes('wifi') || lowerName.includes('ethernet') || lowerName.includes('wlan') || lowerName.includes('lan') || lowerName.startsWith('eth') || lowerName.startsWith('en')) {
            return net.address;
          }
          if (!candidatePhysicalIp) candidatePhysicalIp = net.address;
        } else if (!fallbackIp) {
          fallbackIp = net.address;
        }
      }
    }
  }

  return candidatePhysicalIp || fallbackIp || '127.0.0.1';
}

function getSpawnEnv() {
  const sysRoot = process.env.SystemRoot || process.env.SYSTEMROOT || 'C:\\Windows';
  const comSpec = process.env.ComSpec || process.env.COMSPEC || path.join(sysRoot, 'System32', 'cmd.exe');
  const system32 = path.join(sysRoot, 'System32');

  const currentPath = process.env.PATH || process.env.Path || '';
  const extendedPath = `${system32};${sysRoot};${currentPath}`;
  lanIp = getLanIp();

  return {
    env: {
      ...process.env,
      SystemRoot: sysRoot,
      ComSpec: comSpec,
      PATH: extendedPath,
      Path: extendedPath,
      PYTHONUNBUFFERED: '1',
      REACT_NATIVE_PACKAGER_HOSTNAME: lanIp,
    },
    comSpec,
  };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 780,
    minWidth: 880,
    minHeight: 650,
    title: 'VediPocketPC Controller',
    backgroundColor: '#0F131A',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadFile('index.html');

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

const serverPort = 8080;
const backendPort = 8000;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 780,
    minWidth: 880,
    minHeight: 650,
    title: 'VediPocketPC Controller',
    backgroundColor: '#0F131A',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadFile('index.html');

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function sendStatus() {
  if (mainWindow) {
    lanIp = getLanIp();
    const effectiveExpoUrl = currentExpoUrl || `exp://${lanIp}:${currentExpoPort}`;
    let expoQrData = '';
    if (isExpoRunning && effectiveExpoUrl) {
      try {
        expoQrData = await QRCode.toDataURL(effectiveExpoUrl);
      } catch (e) {
        console.error('Error generating expo QR in sendStatus:', e);
      }
    }

    mainWindow.webContents.send('status-update', {
      lanIp,
      serverPort,
      backendPort,
      expoPort: currentExpoPort,
      isPythonRunning,
      isBackendRunning,
      isExpoRunning,
      serverUrl: `http://${lanIp}:${serverPort}`,
      wsUrl: `ws://${lanIp}:${serverPort}/ws`,
      expoUrl: effectiveExpoUrl,
      expoQr: expoQrData,
    });
  }
}

function getNodePath() {
  const isWin = process.platform === 'win32';
  try {
    const cmd = isWin ? 'where node' : 'which node';
    const output = require('child_process').execSync(cmd, { encoding: 'utf8' }).trim();
    const firstLine = output.split(/[\r\n]+/)[0];
    if (firstLine && fs.existsSync(firstLine)) {
      return firstLine;
    }
  } catch (e) {}

  if (isWin) {
    const pfNode = path.join(process.env['ProgramFiles'] || 'C:\\Program Files', 'nodejs', 'node.exe');
    if (fs.existsSync(pfNode)) return pfNode;
    const pf86Node = path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'nodejs', 'node.exe');
    if (fs.existsSync(pf86Node)) return pf86Node;
  }
  return 'node';
}

function getPythonPath() {
  const isWin = process.platform === 'win32';
  try {
    const cmd = isWin ? 'where python' : 'which python3';
    const output = require('child_process').execSync(cmd, { encoding: 'utf8' }).trim();
    const firstLine = output.split(/[\r\n]+/)[0];
    if (firstLine && fs.existsSync(firstLine) && !firstLine.includes('WindowsApps')) {
      return firstLine;
    }
  } catch (e) {}

  if (isWin) {
    const localAppData = process.env.LOCALAPPDATA || '';
    if (localAppData) {
      const pyDir = path.join(localAppData, 'Programs', 'Python');
      if (fs.existsSync(pyDir)) {
        const subdirs = fs.readdirSync(pyDir);
        for (const dir of subdirs) {
          const exe = path.join(pyDir, dir, 'python.exe');
          if (fs.existsSync(exe)) return exe;
        }
      }
    }
    return 'python';
  }
  return 'python3';
}

function getBaseDir() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return __dirname;
}

function resolveSubdir(dirName) {
  const inResources = path.join(process.resourcesPath, dirName);
  const inApp = path.join(__dirname, dirName);

  if (app.isPackaged && fs.existsSync(inResources)) {
    return inResources;
  }
  return inApp;
}

// Sequence step 1: Start Expo Server
function startExpoServer() {
  if (expoProcess) return;

  const expoDir = resolveSubdir('veddi-pocketpc');
  const expoPkg = path.join(expoDir, 'node_modules', 'expo');

  if (!fs.existsSync(expoPkg)) {
    console.log(`[Desktop] Expo module not found in ${expoDir}.`);
    if (mainWindow) {
      mainWindow.webContents.send('expo-log', '[Desktop] Expo dev server skipped (mobile app source not installed). Stream Server active.');
    }
    return;
  }

  lanIp = getLanIp();
  currentExpoUrl = `exp://${lanIp}:${currentExpoPort}`;
  console.log(`[Desktop] 1/2: Starting Expo Mobile Server on LAN IP (${lanIp}) in ${expoDir}...`);

  try {
    const { env } = getSpawnEnv();
    const nodeCmd = getNodePath();
    const isWin = process.platform === 'win32';
    const npxCmd = isWin ? 'npx.cmd' : 'npx';

    const localExpoBin = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli');
    const localExpoJs = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli.js');

    const expoArgs = ['start', '-c', '--host', 'lan'];

    if (fs.existsSync(localExpoBin) || fs.existsSync(localExpoJs)) {
      const cliPath = fs.existsSync(localExpoBin) ? localExpoBin : localExpoJs;
      console.log(`[Desktop] Spawning local Expo CLI with Node (${nodeCmd}): ${cliPath}`);
      expoProcess = spawn(nodeCmd, [cliPath, ...expoArgs], {
        cwd: expoDir,
        env: env,
      });
    } else {
      console.log(`[Desktop] Spawning npx expo start on LAN: ${npxCmd}`);
      expoProcess = spawn(npxCmd, ['expo', ...expoArgs], {
        cwd: expoDir,
        shell: isWin ? true : false,
        env: env,
      });
    }

    isExpoRunning = true;
    sendStatus();

    expoProcess.stdout.on('data', async (data) => {
      const text = data.toString();
      console.log(`[Expo] ${text}`);
      if (mainWindow) {
        mainWindow.webContents.send('expo-log', text);
      }

      // Automatically extract exp:// or http:// URL from Expo output and update QR
      let detectedUrl = null;
      const expMatch = text.match(/exp:\/\/[^\s\x1b]+/);
      if (expMatch) {
        detectedUrl = expMatch[0];
      } else {
        const httpMatch = text.match(/http:\/\/[\w.-]+:(\d+)/);
        if (httpMatch) {
          const port = httpMatch[1];
          currentExpoPort = parseInt(port, 10);
          detectedUrl = `exp://${lanIp}:${currentExpoPort}`;
        }
      }

      if (detectedUrl) {
        currentExpoUrl = detectedUrl;
        const portMatch = currentExpoUrl.match(/:(\d+)/);
        if (portMatch) {
          currentExpoPort = parseInt(portMatch[1], 10);
        }
        console.log(`[Desktop] Detected Expo URL: ${currentExpoUrl}`);
        sendStatus();
      }
    });

    expoProcess.stderr.on('data', (data) => {
      const text = data.toString();
      console.error(`[Expo Err] ${text}`);
      if (mainWindow) {
        mainWindow.webContents.send('expo-log', text);
      }
    });

    expoProcess.on('error', (err) => {
      console.error(`[Expo Spawn Error] ${err.message}`);
      isExpoRunning = false;
      expoProcess = null;
      sendStatus();
    });

    expoProcess.on('close', (code) => {
      console.log(`[Desktop] Expo process exited with code ${code}`);
      isExpoRunning = false;
      expoProcess = null;
      sendStatus();
    });
  } catch (err) {
    console.error(`[Expo Start Exception] ${err.message}`);
    isExpoRunning = false;
    expoProcess = null;
    sendStatus();
  }
}

// Sequence step 2: Start Stream Server & Backend Server
function startPythonServer() {
  if (pythonProcess) return;

  const serverDir = resolveSubdir('screen-stream-server');
  console.log(`[Desktop] 2/2: Starting Python Stream Server in ${serverDir}...`);

  try {
    const { env } = getSpawnEnv();
    const pythonCmd = getPythonPath();
    console.log(`[Desktop] Using Python executable: ${pythonCmd}`);

    pythonProcess = spawn(pythonCmd, ['server.py'], {
      cwd: serverDir,
      env: env,
    });

    isPythonRunning = true;
    sendStatus();

    pythonProcess.stdout.on('data', (data) => {
      const text = data.toString();
      console.log(`[Python Stream] ${text}`);
      if (mainWindow) {
        mainWindow.webContents.send('python-log', text);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const text = data.toString();
      console.error(`[Python Stream Err] ${text}`);
      if (mainWindow) {
        mainWindow.webContents.send('python-log', `[ERROR] ${text}`);
      }
    });

    pythonProcess.on('error', (err) => {
      console.error(`[Python Stream Spawn Error] ${err.message}`);
      if (mainWindow) {
        mainWindow.webContents.send('python-log', `[SPAWN ERROR] ${err.message}`);
      }
      isPythonRunning = false;
      pythonProcess = null;
      sendStatus();
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Desktop] Python stream process exited with code ${code}`);
      isPythonRunning = false;
      pythonProcess = null;
      sendStatus();
    });
  } catch (err) {
    console.error(`[Python Stream Exception] ${err.message}`);
    isPythonRunning = false;
    pythonProcess = null;
    sendStatus();
  }
}

function startBackendServer() {
  if (backendProcess) return;

  const backendDir = resolveSubdir('vedi-pocketpc-backend');
  console.log(`[Desktop] Starting FastAPI Backend in ${backendDir}...`);

  try {
    const { env } = getSpawnEnv();
    const pythonCmd = getPythonPath();

    backendProcess = spawn(pythonCmd, ['main.py'], {
      cwd: backendDir,
      env: env,
    });

    isBackendRunning = true;
    sendStatus();

    backendProcess.stdout.on('data', (data) => {
      const text = data.toString();
      console.log(`[Backend] ${text}`);
      if (mainWindow) {
        mainWindow.webContents.send('python-log', `[Backend] ${text}`);
      }
    });

    backendProcess.stderr.on('data', (data) => {
      const text = data.toString();
      if (mainWindow) {
        mainWindow.webContents.send('python-log', `[Backend Err] ${text}`);
      }
    });

    backendProcess.on('error', () => {
      isBackendRunning = false;
      backendProcess = null;
      sendStatus();
    });

    backendProcess.on('close', () => {
      isBackendRunning = false;
      backendProcess = null;
      sendStatus();
    });
  } catch (err) {
    isBackendRunning = false;
    backendProcess = null;
    sendStatus();
  }
}

function stopPythonServer() {
  if (pythonProcess) {
    try {
      if (process.platform === 'win32') {
        exec(`taskkill /pid ${pythonProcess.pid} /T /F`);
      } else {
        pythonProcess.kill('SIGINT');
      }
    } catch (e) {}
    pythonProcess = null;
    isPythonRunning = false;
  }

  if (backendProcess) {
    try {
      if (process.platform === 'win32') {
        exec(`taskkill /pid ${backendProcess.pid} /T /F`);
      } else {
        backendProcess.kill('SIGINT');
      }
    } catch (e) {}
    backendProcess = null;
    isBackendRunning = false;
  }
  sendStatus();
}

function stopExpoServer() {
  if (expoProcess) {
    console.log('[Desktop] Stopping Expo server...');
    try {
      if (process.platform === 'win32') {
        exec(`taskkill /pid ${expoProcess.pid} /T /F`);
      } else {
        expoProcess.kill('SIGINT');
      }
    } catch (e) {}
    expoProcess = null;
    isExpoRunning = false;
    currentExpoUrl = '';
    sendStatus();
  }
}

// IPC Handlers
ipcMain.handle('get-server-info', async () => {
  lanIp = getLanIp();
  const serverUrl = `http://${lanIp}:${serverPort}`;
  const wsUrl = `ws://${lanIp}:${serverPort}/ws`;
  const effectiveExpoUrl = currentExpoUrl || `exp://${lanIp}:${currentExpoPort}`;

  let serverQr = '';
  let expoQr = '';

  try {
    serverQr = await QRCode.toDataURL(serverUrl);
  } catch (e) {
    console.error('Failed generating server QR:', e);
  }

  if (isExpoRunning && effectiveExpoUrl) {
    try {
      expoQr = await QRCode.toDataURL(effectiveExpoUrl);
    } catch (e) {
      console.error('Failed generating expo QR:', e);
    }
  }

  return {
    lanIp,
    serverPort,
    backendPort,
    expoPort: currentExpoPort,
    isPythonRunning,
    isBackendRunning,
    isExpoRunning,
    serverUrl,
    wsUrl,
    expoUrl: effectiveExpoUrl,
    serverQr,
    expoQr,
  };
});

ipcMain.handle('start-servers', () => {
  startExpoServer();
  setTimeout(() => {
    startPythonServer();
    startBackendServer();
  }, 1000);
  return { success: true };
});

ipcMain.handle('stop-servers', () => {
  stopPythonServer();
  stopExpoServer();
  return { success: true };
});

ipcMain.handle('restart-servers', () => {
  stopPythonServer();
  stopExpoServer();
  setTimeout(() => {
    startExpoServer();
    setTimeout(() => {
      startPythonServer();
      startBackendServer();
    }, 1000);
  }, 1000);
  return { success: true };
});

ipcMain.handle('generate-qr', async (event, text) => {
  try {
    return await QRCode.toDataURL(text);
  } catch (e) {
    console.error('Error generating QR code:', e);
    return '';
  }
});

ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url);
});

// App Lifecycle
app.whenReady().then(() => {
  createWindow();

  // Sequence: Expo Server first -> Stream Server next
  startExpoServer();
  setTimeout(() => {
    startPythonServer();
    startBackendServer();
  }, 1200);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopPythonServer();
  stopExpoServer();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopPythonServer();
  stopExpoServer();
});
