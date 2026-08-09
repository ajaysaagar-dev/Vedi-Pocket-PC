/**
 * ProcessManager — owns the lifecycle of Expo, the screen-stream server,
 * and the backend agent.
 *
 * Each helper spawns its process, wires stdout / stderr to the renderer
 * via IPC events, and keeps track of running state so the UI can show
 * accurate status pills.
 */
const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const { app } = require('electron');

const network = require('./network');
const { getNodePath, getPythonPath } = require('./binaries');

function resolveSubdir(dirName) {
  // In a packaged build the child projects live under resourcesPath;
  // in dev they live next to controller/.
  const inResources = path.join(process.resourcesPath || '', dirName);
  const inApp = path.join(__dirname, '..', '..', dirName);

  if (app.isPackaged && fs.existsSync(inResources)) {
    return inResources;
  }
  return inApp;
}

class ProcessManager {
  constructor() {
    this.expoProcess = null;
    this.serverProcess = null;

    this.isExpoRunning = false;
    this.isServerRunning = false;

    this.currentExpoPort = 8081;
    this.currentExpoUrl = '';
    this.lanIp = network.getLanIp();
    this.pairingPin = '';

    this._statusListeners = new Set();
    this._logListeners = new Set();
  }

  onStatusUpdate(cb) {
    this._statusListeners.add(cb);
    return () => this._statusListeners.delete(cb);
  }

  onLog(cb) {
    this._logListeners.add(cb);
    return () => this._logListeners.delete(cb);
  }

  _emitStatus() {
    const payload = {
      lanIp: this.lanIp,
      serverPort: 8000,
      pairingPin: this.pairingPin,
      expoPort: this.currentExpoPort,
      isServerRunning: this.isServerRunning,
      isExpoRunning: this.isExpoRunning,
      expoUrl: this.currentExpoUrl || `exp://${this.lanIp}:${this.currentExpoPort}`,
    };
    for (const cb of this._statusListeners) {
      try { cb(payload); } catch (e) { /* swallow */ }
    }
  }

  _emitLog(channel, payload) {
    for (const cb of this._logListeners) {
      try { cb({ channel, payload }); } catch (e) { /* swallow */ }
    }
  }

  // ------------------------- Expo -------------------------
  startExpo() {
    if (this.expoProcess) return;

    const expoDir = resolveSubdir('mobile');
    const expoPkg = path.join(expoDir, 'node_modules', 'expo');

    if (!fs.existsSync(expoPkg)) {
      console.log(`[Desktop] Expo module not found in ${expoDir}.`);
      // Notify renderer (if a window exists yet) so it can show a tip.
      this._emitLog('expo-log', '[Desktop] Expo dev server skipped (mobile app source not installed). Stream Server active.');
      return;
    }

    const lanIp = network.getLanIp();
    this.lanIp = lanIp;
    this.currentExpoUrl = `exp://${lanIp}:${this.currentExpoPort}`;
    console.log(`[Desktop] Starting Expo Mobile Server on LAN IP (${lanIp}) in ${expoDir}...`);

    const { env } = network.getSpawnEnv();
    const nodeCmd = getNodePath();
    const isWin = process.platform === 'win32';
    const npxCmd = isWin ? 'npx.cmd' : 'npx';

    const localExpoBin = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli');
    const localExpoJs = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli.js');

    const expoArgs = ['start', '-c', '--host', 'lan'];
    const useLocal = fs.existsSync(localExpoBin) || fs.existsSync(localExpoJs);
    const cliPath = fs.existsSync(localExpoBin) ? localExpoBin : localExpoJs;

    if (useLocal) {
      console.log(`[Desktop] Spawning local Expo CLI with Node (${nodeCmd}): ${cliPath}`);
      this.expoProcess = spawn(nodeCmd, [cliPath, ...expoArgs], { cwd: expoDir, env });
    } else {
      console.log(`[Desktop] Spawning npx expo start on LAN: ${npxCmd}`);
      this.expoProcess = spawn(npxCmd, ['expo', ...expoArgs], {
        cwd: expoDir,
        shell: isWin,
        env,
      });
    }

    this.isExpoRunning = true;
    this._emitStatus();

    this.expoProcess.stdout.on('data', (data) => this._onExpoStdout(data));
    this.expoProcess.stderr.on('data', (data) => this._emitLog('expo-log', data.toString()));
    this.expoProcess.on('error', (err) => {
      console.error(`[Expo Spawn Error] ${err.message}`);
      this.isExpoRunning = false;
      this.expoProcess = null;
      this._emitStatus();
    });
    this.expoProcess.on('close', (code) => {
      console.log(`[Desktop] Expo process exited with code ${code}`);
      this.isExpoRunning = false;
      this.expoProcess = null;
      this._emitStatus();
    });
  }

  _onExpoStdout(data) {
    const text = data.toString();
    console.log(`[Expo] ${text}`);
    this._emitLog('expo-log', text);

    // Detect exp:// or http:// LAN URL and refresh the QR payload.
    const expMatch = text.match(/exp:\/\/[^\s\x1b]+/);
    if (expMatch) {
      this.currentExpoUrl = expMatch[0];
    } else {
      const httpMatch = text.match(/http:\/\/[\w.-]+:(\d+)/);
      if (httpMatch) {
        this.currentExpoPort = parseInt(httpMatch[1], 10);
        this.currentExpoUrl = `exp://${this.lanIp}:${this.currentExpoPort}`;
      }
    }
    const portMatch = (this.currentExpoUrl || '').match(/:(\d+)/);
    if (portMatch) this.currentExpoPort = parseInt(portMatch[1], 10);
    this._emitStatus();
  }

  stopExpo() {
    if (!this.expoProcess) return;
    this._kill(this.expoProcess);
    this.expoProcess = null;
    this.isExpoRunning = false;
    this.currentExpoUrl = '';
    this._emitStatus();
  }

  // ------------------------- Unified Server -------------------------
  startServer() {
    if (this.serverProcess) return;

    const rootDir = resolveSubdir('');
    console.log(`[Desktop] Starting Unified Server in ${rootDir}...`);

    const { env } = network.getSpawnEnv();
    const pythonCmd = getPythonPath();
    console.log(`[Desktop] Using Python executable: ${pythonCmd}`);

    this.serverProcess = spawn(pythonCmd, ['-m', 'server'], { cwd: rootDir, env });
    this.isServerRunning = true;
    this._emitStatus();

    this.serverProcess.stdout.on('data', (data) => {
      const text = data.toString();
      this._emitLog('python-log', `[Server] ${text}`);
      const pinMatch = text.match(/Pairing PIN:\s*(\d{4})/i);
      if (pinMatch) {
        this.pairingPin = pinMatch[1];
        this._emitStatus();
      }
    });
    this.serverProcess.stderr.on('data', (data) => this._emitLog('python-log', `[Server Err] ${data.toString()}`));
    this.serverProcess.on('error', (err) => {
      console.error(`[Server Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[SPAWN ERROR] ${err.message}`);
      this.isServerRunning = false;
      this.serverProcess = null;
      this._emitStatus();
    });
    this.serverProcess.on('close', (code) => {
      console.log(`[Desktop] Server process exited with code ${code}`);
      this.isServerRunning = false;
      this.serverProcess = null;
      this._emitStatus();
    });
  }

  stopServer() {
    if (this.serverProcess) {
      this._kill(this.serverProcess);
      this.serverProcess = null;
      this.isServerRunning = false;
    }
    this._emitStatus();
  }

  stopAll() {
    this.stopServer();
    this.stopExpo();
  }

  // ------------------------- helpers -------------------------
  _kill(child) {
    try {
      if (process.platform === 'win32') {
        exec(`taskkill /pid ${child.pid} /T /F`);
      } else {
        child.kill('SIGINT');
      }
    } catch (e) {
      /* best effort */
    }
  }
}

module.exports = { ProcessManager };
