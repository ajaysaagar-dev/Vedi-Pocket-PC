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
const { spawn, exec, execSync } = require('child_process');
const { app } = require('electron');

const network = require('./network');
const { getNodePath, getPythonPath } = require('./binaries');

function resolveSubdir(dirName) {
  // In a packaged build the child projects live under resourcesPath;
  // in dev they live next to controller/.
  const inResources = path.join(process.resourcesPath || '', dirName);
  const inApp = path.join(__dirname, '..', '..', dirName);

  if (app && app.isPackaged && fs.existsSync(inResources)) {
    return inResources;
  }
  return inApp;
}

function isPortInUse(port) {
  if (process.platform !== 'win32') return false;
  try {
    const stdout = execSync(`netstat -ano | findstr LISTENING | findstr ":${port} "`, { encoding: 'utf8', timeout: 3000 });
    return !!(stdout && stdout.trim().length > 0);
  } catch (e) {
    return false;
  }
}

function findFreePort(preferredPort) {
  let p = preferredPort;
  while (isPortInUse(p)) {
    p++;
  }
  return p;
}

class ProcessManager {
  constructor() {
    this.expoProcess = null;
    this.pythonProcess = null;
    this.backendProcess = null;

    this.isExpoRunning = false;
    this.isPythonRunning = false;
    this.isBackendRunning = false;

    this.streamPort = 8080;
    this.backendPort = 8000;
    this.currentExpoPort = 8088;
    this.currentExpoUrl = '';
    this.lanIp = network.getLanIp();

    // Backend pairing credentials parsed from its stdout.
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
      serverPort: this.streamPort,
      backendPort: this.backendPort,
      expoPort: this.currentExpoPort,
      isPythonRunning: this.isPythonRunning,
      isBackendRunning: this.isBackendRunning,
      isExpoRunning: this.isExpoRunning,
      expoUrl: this.currentExpoUrl || `exp://${this.lanIp}:${this.currentExpoPort}`,
      pairingPin: this.pairingPin,
      pairingUrl:
        this.pairingPin && this.lanIp
          ? `${this.lanIp}:${this.backendPort}:${this.pairingPin}`
          : '',
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

    this.currentExpoPort = findFreePort(8088);

    const expoDir = resolveSubdir('veddi-pocketpc');
    const expoPkg = path.join(expoDir, 'node_modules', 'expo');

    if (!fs.existsSync(expoPkg)) {
      console.log(`[Desktop] Expo module not found in ${expoDir}.`);
      this._emitLog('expo-log', '[Desktop] Expo dev server skipped (mobile app source not installed). Stream Server active.');
      return;
    }

    const lanIp = network.getLanIp();
    this.lanIp = lanIp;
    this.currentExpoUrl = `exp://${lanIp}:${this.currentExpoPort}`;
    console.log(`[Desktop] Starting Expo Mobile Server on LAN IP (${lanIp}:${this.currentExpoPort}) in ${expoDir}...`);

    const { env } = network.getSpawnEnv();
    const nodeCmd = getNodePath();
    const isWin = process.platform === 'win32';
    const npxCmd = isWin ? 'npx.cmd' : 'npx';

    const localExpoBin = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli');
    const localExpoJs = path.join(expoDir, 'node_modules', 'expo', 'bin', 'cli.js');

    const expoArgs = ['start', '-c', '--non-interactive', '--host', 'lan', '--port', String(this.currentExpoPort)];
    const useLocalJs = fs.existsSync(localExpoJs);
    const cliPath = useLocalJs ? localExpoJs : localExpoBin;

    const spawnOptions = {
      cwd: expoDir,
      env: {
        ...env,
        CI: '1',
        EXPO_NO_INTERACTIVE: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    };

    if (useLocalJs) {
      console.log(`[Desktop] Spawning local Expo CLI with Node (${nodeCmd}): ${cliPath}`);
      this.expoProcess = spawn(nodeCmd, [cliPath, ...expoArgs], spawnOptions);
    } else {
      console.log(`[Desktop] Spawning npx expo start on LAN: ${npxCmd}`);
      this.expoProcess = spawn(npxCmd, ['expo', ...expoArgs], {
        ...spawnOptions,
        shell: isWin,
      });
    }

    // If spawn itself fails (e.g. ENOENT on a packaged build missing
    // the node binary), the error event fires asynchronously and the
    // rest of the code path already handles it. Guard here too so a
    // partially-initialized `expoProcess` doesn't leak into the next
    // start attempt.
    if (!this.expoProcess) {
      this.isExpoRunning = false;
      this._emitStatus();
      return;
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
    // Strip ANSI escape codes (Expo wraps URLs in colour codes) so
    // the regex below can match the bare URL.
    const clean = text.replace(/\x1b\[[0-9;]*m/g, '');
    const expMatch = clean.match(/exp:\/\/[\w.\-]+(?::\d+)?[^\s\x1b]*/);
    if (expMatch) {
      this.currentExpoUrl = expMatch[0];
    } else {
      const httpMatch = clean.match(/https?:\/\/[\w.\-]+:(\d+)/);
      if (httpMatch) {
        this.currentExpoPort = parseInt(httpMatch[1], 10);
        this.currentExpoUrl = `exp://${this.lanIp}:${this.currentExpoPort}`;
      }
    }
    const portMatch = (this.currentExpoUrl || '').match(/:(\d+)(?:\/|$)/);
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

  reloadExpo() {
    if (this.expoProcess && this.expoProcess.stdin && !this.expoProcess.stdin.destroyed) {
      console.log('[Desktop] Sending "r" command to Expo CLI stdin...');
      this._emitLog('expo-log', '[Desktop] > Executed "r" key (Reloading connected Expo devices)...');
      try {
        this.expoProcess.stdin.write('r\n');
        return true;
      } catch (e) {
        console.error('[Desktop] Error sending "r" to stdin:', e);
      }
    }
    console.log('[Desktop] Expo stdin unavailable, restarting Expo server process...');
    this.stopExpo();
    setTimeout(() => this.startExpo(), 500);
    return false;
  }

  // ------------------------- Stream server -------------------------
  startStreamServer() {
    if (this.pythonProcess) return;

    this.streamPort = findFreePort(8080);

    const serverDir = resolveSubdir('screen-stream-server');
    const { env: spawnEnv } = network.getSpawnEnv();
    const env = { ...spawnEnv, STREAM_PORT: String(this.streamPort) };
    const pythonCmd = getPythonPath();

    console.log(`[Desktop] Starting Python Stream Server`);
    console.log(`[Desktop]   cwd     = ${serverDir}`);
    console.log(`[Desktop]   python  = ${pythonCmd}`);
    console.log(`[Desktop]   port    = ${this.streamPort}`);
    this._emitLog(
      'python-log',
      `[Desktop] Starting screen-stream-server on port ${this.streamPort}\n  cwd:    ${serverDir}\n  python: ${pythonCmd}\n`
    );

    let child;
    try {
      child = spawn(pythonCmd, ['main.py'], {
        cwd: serverDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err) {
      console.error(`[Python Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[SPAWN ERROR] ${err.message}`);
      this.pythonProcess = null;
      this.isPythonRunning = false;
      this._emitStatus();
      return;
    }

    this.pythonProcess = child;
    child.stdout.on('data', (data) => this._emitLog('python-log', data.toString()));
    child.stderr.on('data', (data) => this._emitLog('python-log', `[ERROR] ${data.toString()}`));

    this._markStartedWhenReady(this, child, 'isPythonRunning');

    child.on('error', (err) => {
      console.error(`[Python Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[SPAWN ERROR] ${err.message}`);
      this.isPythonRunning = false;
      this.pythonProcess = null;
      this._emitStatus();
    });
    child.on('close', (code) => {
      console.log(`[Desktop] Python stream process exited with code ${code}`);
      this.isPythonRunning = false;
      this.pythonProcess = null;
      this._emitStatus();
    });
  }

  // ------------------------- Backend agent -------------------------
  startBackend() {
    if (this.backendProcess) return;

    this.backendPort = findFreePort(8000);

    const backendDir = resolveSubdir('vedi-pocketpc-backend');
    const { env: spawnEnv } = network.getSpawnEnv();
    const env = { ...spawnEnv, BACKEND_PORT: String(this.backendPort) };
    const pythonCmd = getPythonPath();

    console.log(`[Desktop] Starting FastAPI Backend`);
    console.log(`[Desktop]   cwd     = ${backendDir}`);
    console.log(`[Desktop]   python  = ${pythonCmd}`);
    console.log(`[Desktop]   port    = ${this.backendPort}`);
    this._emitLog(
      'python-log',
      `[Desktop] Starting vedi-pocketpc-backend on port ${this.backendPort}\n  cwd:    ${backendDir}\n  python: ${pythonCmd}\n`
    );

    let child;
    try {
      child = spawn(pythonCmd, ['main.py'], {
        cwd: backendDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err) {
      console.error(`[Backend Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[BACKEND SPAWN ERROR] ${err.message}`);
      this.backendProcess = null;
      this.isBackendRunning = false;
      this._emitStatus();
      return;
    }

    this.backendProcess = child;

    child.stdout.on('data', (data) => {
      const text = data.toString();
      this._emitLog('python-log', `[Backend] ${text}`);
      const match = text.match(/Pairing PIN:\s*(\d{4})/);
      if (match) {
        const pin = match[1];
        if (pin !== this.pairingPin) {
          this.pairingPin = pin;
          console.log(`[Desktop] Captured backend pairing PIN: ${pin}`);
          this._emitStatus();
        }
      }
    });
    child.stderr.on('data', (data) =>
      this._emitLog('python-log', `[Backend Err] ${data.toString()}`)
    );

    this._markStartedWhenReady(this, child, 'isBackendRunning');

    child.on('error', (err) => {
      console.error(`[Backend Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[BACKEND SPAWN ERROR] ${err.message}`);
      this.isBackendRunning = false;
      this.backendProcess = null;
      this._emitStatus();
    });
    child.on('close', (code) => {
      console.log(`[Desktop] Backend process exited with code ${code}`);
      this.isBackendRunning = false;
      this.backendProcess = null;
      // Don't clear the PIN here — the user may still need to scan
      // it from the most recent QR. We only forget it on restart.
      this._emitStatus();
    });
  }

  /**
   * Helper — flips `manager[flag] = true` only once either:
   *   (a) the child process emits data (real sign it's alive), OR
   *   (b) a 1-second grace timer expires.
   * If the child closes/errors before either, the flag stays false
   * and the UI correctly reports "Stopped".
   */
  _markStartedWhenReady(manager, child, flag) {
    let confirmed = false;
    const confirm = () => {
      if (confirmed) return;
      confirmed = true;
      if (manager[flag] === false) {
        manager[flag] = true;
        manager._emitStatus();
      }
    };
    // The stdout 'data' event fires for any emitted line, so
    // attach to the stdout stream (not the child) — same stream
    // the existing logger is reading from.
    if (child.stdout) child.stdout.once('data', confirm);
    // Wait briefly so a process that prints its banner immediately
    // (normal case) still flips to "Running" within ~1s.
    setTimeout(confirm, 1000);
    // If the child dies before confirming, leave the flag false and
    // suppress the timeout's late flip.
    child.once('close', () => {
      if (!confirmed) confirmed = true;
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
    // PIN is no longer valid once the backend is stopped — invalidate
    // it so the QR can't accidentally grant a token against a stale
    // PIN if the user scans an old QR.
    this.pairingPin = '';
    this._emitStatus();
  }

  stopAll() {
    this.stopStreamAndBackend();
    this.stopExpo();
  }

  // ------------------------- helpers -------------------------
  _kill(child) {
    if (!child || child.pid === undefined || child.pid === null) return;
    try {
      if (process.platform === 'win32') {
        // taskkill used to be fire-and-forget `exec(...)` here, but
        // that races with the next spawn: by the time `_freePort`
        // ran a millisecond later, the OS hadn't actually released
        // 8080/8000 and the new bind failed with [Errno 10048].
        // Switched to `execSync` with a 4-second budget so the port
        // is guaranteed free before the caller continues. The /T flag
        // tears down child trees (mss / opencv / etc.) so we don't
        // leak grandchildren holding subresources.
        try {
          execSync(`taskkill /pid ${child.pid} /T /F`, {
            stdio: 'ignore',
            timeout: 4000,
          });
        } catch (_) {
          // Exit code 128 / non-zero means the process was already
          // gone — that's fine, the port is already free.
        }
      } else {
        try {
          child.kill('SIGINT');
        } catch (_) {
          /* best effort */
        }
      }
    } catch (e) {
      /* best effort */
    }
  }
}

module.exports = { ProcessManager };
