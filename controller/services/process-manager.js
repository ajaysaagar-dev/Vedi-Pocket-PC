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

    // Backend pairing credentials parsed from its stdout. The
    // backend prints `Pairing PIN: NNNN` on startup — we capture it
    // here so the controller can render a proper `ip:port:pin`
    // QR that the mobile app's QR scanner already understands.
    this.pairingPin = '';
    this.backendPort = 8000;

    this._statusListeners = new Set();
    this._logListeners = new Set();
  }

  _freePort(port) {
    if (process.platform !== 'win32') return;
    try {
      // `findstr ":PORT>"` is anchored to a non-digit so we don't
      // accidentally match `:80801` or `:8080X` — the trailing `>`
      // (or end-of-line, if findstr supports it) ensures we only get
      // exact-port matches. `findstr LISTENING` filters out
      // ESTABLISHED / TIME_WAIT lines that also bind a port locally.
      const stdout = execSync(
        `netstat -ano | findstr LISTENING | findstr ":${port} "`,
        { encoding: 'utf8', timeout: 4000 }
      );
      if (!stdout) return;
      const lines = stdout.trim().split(/[\r\n]+/);
      const myPid = String(process.pid);
      const killed = new Set();
      for (const line of lines) {
        // netstat row: "<Proto> <Local> <Remote> <State> <PID>"
        // matches both IPv4 ("0.0.0.0:8080") and IPv6 ("[::]:8080").
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (!pid || !/^\d+$/.test(pid) || pid === '0' || pid === myPid) continue;
        if (killed.has(pid)) continue;
        killed.add(pid);
        console.log(`[Desktop] Auto-clearing port ${port} occupied by PID ${pid}`);
        try {
          // Synchronous kill + timeout so the OS actually releases
          // the socket before we return. Asynchronous `exec` would
          // race with the subsequent `spawn()`.
          execSync(`taskkill /pid ${pid} /F /T`, {
            stdio: 'ignore',
            timeout: 4000,
          });
        } catch (_) {
          // Non-zero exit usually means the process is already gone
          // by the time we got here — that's still success for our
          // purposes, the port is free.
        }
      }
    } catch (_) {
      // netstat / findstr returning nothing is the happy path —
      // port is already free, nothing to do.
    }
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
      backendPort: this.backendPort,
      expoPort: this.currentExpoPort,
      isPythonRunning: this.isPythonRunning,
      isBackendRunning: this.isBackendRunning,
      isExpoRunning: this.isExpoRunning,
      expoUrl: this.currentExpoUrl || `exp://${this.lanIp}:${this.currentExpoPort}`,
      pairingPin: this.pairingPin,
      // `pairingUrl` is the canonical `ip:port:pin` payload the mobile
      // app's QR scanner parses. Built from whatever credentials we
      // have so far; the renderer fills in blanks with the LAN IP
      // default if the backend isn't up yet.
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

    this._freePort(8081);

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

    const expoArgs = ['start', '-c', '--host', 'lan', '--port', '8081'];
    const useLocalJs = fs.existsSync(localExpoJs);
    const cliPath = useLocalJs ? localExpoJs : localExpoBin;

    if (useLocalJs) {
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

  // ------------------------- Stream server -------------------------
  startStreamServer() {
    if (this.pythonProcess) return;

    this._freePort(8080);

    const serverDir = resolveSubdir('screen-stream-server');
    const { env } = network.getSpawnEnv();
    const pythonCmd = getPythonPath();

    // Log the resolved binary up-front so a wrong / missing Python
    // interpreter is immediately visible in the log panel — without
    // this, "Python Stream Server: Stopped" was the only symptom.
    console.log(`[Desktop] Starting Python Stream Server`);
    console.log(`[Desktop]   cwd     = ${serverDir}`);
    console.log(`[Desktop]   python  = ${pythonCmd}`);
    console.log(`[Desktop]   port    = 8080`);
    this._emitLog(
      'python-log',
      `[Desktop] Starting screen-stream-server\n  cwd:    ${serverDir}\n  python: ${pythonCmd}\n`
    );

    let child;
    try {
      child = spawn(pythonCmd, ['main.py'], {
        cwd: serverDir,
        env,
        // Explicit stdio — guarantees `pipe` so we never miss a
        // first-chunk stderr (the original code relied on defaults
        // which on some Node builds silently inherit `inherit` for
        // stderr in console-mode Electron, hiding tracebacks).
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err) {
      // Synchronous spawn failure (rare, but happens when the path
      // resolves to something Node refuses to exec).
      console.error(`[Python Spawn Error] ${err.message}`);
      this._emitLog('python-log', `[SPAWN ERROR] ${err.message}`);
      this.pythonProcess = null;
      this.isPythonRunning = false;
      this._emitStatus();
      return;
    }

    this.pythonProcess = child;
    // Attach listeners IMMEDIATELY (in the same tick as spawn) so we
    // never lose the first chunk — the previous code's
    // `isPythonRunning = true` line raced with the early-exit case
    // and could miss a 10-line traceback that fired before listeners
    // were wired.
    child.stdout.on('data', (data) => this._emitLog('python-log', data.toString()));
    child.stderr.on('data', (data) => this._emitLog('python-log', `[ERROR] ${data.toString()}`));

    // Don't flip `isPythonRunning = true` until we've actually seen
    // output OR a 1-second grace timer expires. This eliminates the
    // "Running but actually dead" UI flicker when the child crashes
    // inside the import phase (e.g. missing `mss`).
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

    this._freePort(8000);

    const backendDir = resolveSubdir('vedi-pocketpc-backend');
    const { env } = network.getSpawnEnv();
    const pythonCmd = getPythonPath();

    // Same up-front diagnostic logging as the stream server so an
    // obvious misconfiguration isn't a mystery.
    console.log(`[Desktop] Starting FastAPI Backend`);
    console.log(`[Desktop]   cwd     = ${backendDir}`);
    console.log(`[Desktop]   python  = ${pythonCmd}`);
    console.log(`[Desktop]   port    = 8000`);
    this._emitLog(
      'python-log',
      `[Desktop] Starting vedi-pocketpc-backend\n  cwd:    ${backendDir}\n  python: ${pythonCmd}\n`
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
