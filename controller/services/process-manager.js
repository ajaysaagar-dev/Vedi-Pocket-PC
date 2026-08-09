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
    this.pythonProcess = null;
    this.backendProcess = null;

    this.isExpoRunning = false;
    this.isPythonRunning = false;
    this.isBackendRunning = false;

    this.currentExpoPort = 8081;
    this.currentExpoUrl = '';
    this.lanIp = network.getLanIp();

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
      serverPort: 8080,
      backendPort: 8000,
      expoPort: this.currentExpoPort,
      isPythonRunning: this.isPythonRunning,
      isBackendRunning: this.isBackendRunning,
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

    const expoDir = resolveSubdir('veddi-pocketpc');
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

  // ------------------------- Stream server -------------------------
  startStreamServer() {
    if (this.pythonProcess) return;

    const serverDir = resolveSubdir('screen-stream-server');
    console.log(`[Desktop] Starting Python Stream Server in ${serverDir}...`);

    const { env } = network.getSpawnEnv();
    const pythonCmd = getPythonPath();
    console.log(`[Desktop] Using Python executable: ${pythonCmd}`);

    this.pythonProcess = spawn(pythonCmd, ['main.py'], { cwd: serverDir, env });
    this.isPythonRunning = true;
    this._emitStatus();

    this.pythonProcess.stdout.on('data', (data) => this._emitLog('python-log', data.toString()));
    this.pythonProcess.stderr.on('data', (data) => this._emitLog('python-log', `[ERROR] ${data.toString()}`));
    this.pythonProcess.on('error', (err) => {
      console.error(`[Python Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[SPAWN ERROR] ${err.message}`);
      this.isPythonRunning = false;
      this.pythonProcess = null;
      this._emitStatus();
    });
    this.pythonProcess.on('close', (code) => {
      console.log(`[Desktop] Python stream process exited with code ${code}`);
      this.isPythonRunning = false;
      this.pythonProcess = null;
      this._emitStatus();
    });
  }

  // ------------------------- Backend agent -------------------------
  startBackend() {
    if (this.backendProcess) return;

    const backendDir = resolveSubdir('vedi-pocketpc-backend');
    console.log(`[Desktop] Starting FastAPI Backend in ${backendDir}...`);

    const { env } = network.getSpawnEnv();
    const pythonCmd = getPythonPath();

    this.backendProcess = spawn(pythonCmd, ['main.py'], { cwd: backendDir, env });
    this.isBackendRunning = true;
    this._emitStatus();

    this.backendProcess.stdout.on('data', (data) => this._emitLog('python-log', `[Backend] ${data.toString()}`));
    this.backendProcess.stderr.on('data', (data) => this._emitLog('python-log', `[Backend Err] ${data.toString()}`));
    this.backendProcess.on('error', () => {
      this.isBackendRunning = false;
      this.backendProcess = null;
      this._emitStatus();
    });
    this.backendProcess.on('close', () => {
      this.isBackendRunning = false;
      this.backendProcess = null;
      this._emitStatus();
    });
  }

  stopStreamAndBackend() {
    if (this.pythonProcess) {
      this._kill(this.pythonProcess);
      this.pythonProcess = null;
      this.isPythonRunning = false;
    }
    if (this.backendProcess) {
      this._kill(this.backendProcess);
      this.backendProcess = null;
      this.isBackendRunning = false;
    }
    this._emitStatus();
  }

  stopAll() {
    this.stopStreamAndBackend();
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
