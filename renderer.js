document.addEventListener('DOMContentLoaded', async () => {
  // DOM Elements
  const globalStatusDot = document.getElementById('globalStatusDot');
  const globalStatusText = document.getElementById('globalStatusText');

  const btnStartServers = document.getElementById('btnStartServers');
  const btnRestartServers = document.getElementById('btnRestartServers');
  const btnStopServers = document.getElementById('btnStopServers');

  const imgServerQr = document.getElementById('imgServerQr');
  const imgExpoQr = document.getElementById('imgExpoQr');
  const serverQrLoader = document.getElementById('serverQrLoader');
  const expoQrLoader = document.getElementById('expoQrLoader');

  const txtWsUrl = document.getElementById('txtWsUrl');
  const txtExpoUrl = document.getElementById('txtExpoUrl');
  const txtLanIp = document.getElementById('txtLanIp');
  const txtPairingUrl = document.getElementById('txtPairingUrl');
  const txtPairingPin = document.getElementById('txtPairingPin');

  const pillPythonStatus = document.getElementById('pillPythonStatus');
  const pillExpoStatus = document.getElementById('pillExpoStatus');

  const btnCopyServerUrl = document.getElementById('btnCopyServerUrl');
  const btnCopyExpoUrl = document.getElementById('btnCopyExpoUrl');
  const btnCopyIp = document.getElementById('btnCopyIp');
  const btnRefreshInfo = document.getElementById('btnRefreshInfo');

  const tabPython = document.getElementById('tabPython');
  const tabExpo = document.getElementById('tabExpo');
  const logPython = document.getElementById('logPython');
  const logExpo = document.getElementById('logExpo');

  const btnCopyLogs = document.getElementById('btnCopyLogs');
  const btnClearLogs = document.getElementById('btnClearLogs');
  const toast = document.getElementById('toast');

  let activeTab = 'python';

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    showToast(`Copied "${text}" to clipboard!`);
  }

  // Load and refresh server information
  async function refreshServerInfo() {
    try {
      const info = await window.electronAPI.getServerInfo();

      txtLanIp.textContent = info.lanIp;
      txtWsUrl.textContent = info.wsUrl;
      txtExpoUrl.textContent = info.expoUrl;
      if (txtPairingUrl) {
        // Show the encoded QR payload, not the URL the WebSocket uses.
        // That's what the mobile scanner parses.
        txtPairingUrl.textContent = info.pairingUrl || info.wsUrl;
      }
      if (txtPairingPin) {
        txtPairingPin.textContent = info.pairingPin || '----';
      }

      // Render Server Connect QR — show as soon as we have a pairing
      // payload (either the real `ip:port:pin` from the backend, or
      // the http://ip:8080 fallback from the stream server). We no
      // longer require both Python servers running — the stream server
      // alone is enough to grant a session token via its /pair endpoint.
      const hasQrPayload = !!(info.pairingUrl || info.serverQr);
      if (hasQrPayload && info.serverQr) {
        imgServerQr.src = info.serverQr;
        imgServerQr.style.display = 'block';
        serverQrLoader.style.display = 'none';
      } else {
        imgServerQr.style.display = 'none';
        serverQrLoader.style.display = 'flex';
        serverQrLoader.classList.add('loading');
      }

      // Render Expo Mobile App QR (Requires Expo Server running)
      if (info.isExpoRunning && info.expoQr) {
        imgExpoQr.src = info.expoQr;
        imgExpoQr.style.display = 'block';
        expoQrLoader.style.display = 'none';
      } else {
        imgExpoQr.style.display = 'none';
        expoQrLoader.style.display = 'flex';
        expoQrLoader.classList.add('loading');
      }

      // Update status badges. The spawn flags are the optimistic view;
// the reachability probe (data-probe-stream / data-probe-backend
// on the pill) is the truth — it actually fetched /health. When
// they disagree we mark the pill as "stalled" so the user knows
// the Node process says "running" but the network disagrees.
      const probeStream = pillPythonStatus.dataset.probeStream;
      const probeBackend = pillPythonStatus.dataset.probeBackend;
      const streamReachable = probeStream === 'true';
      const backendReachable = probeBackend === 'true';

      if (info.isPythonRunning && !streamReachable) {
        pillPythonStatus.textContent = 'Stalled';
        pillPythonStatus.className = 'status-pill stalled';
      } else if (streamReachable) {
        pillPythonStatus.textContent = 'Running';
        pillPythonStatus.className = 'status-pill online';
      } else {
        pillPythonStatus.textContent = 'Stopped';
        pillPythonStatus.className = 'status-pill';
      }

      if (info.isExpoRunning) {
        pillExpoStatus.textContent = 'Running';
        pillExpoStatus.className = 'status-pill online';
      } else {
        pillExpoStatus.textContent = 'Stopped';
        pillExpoStatus.className = 'status-pill';
      }

      // We also surface backend reachability — if the backend says
      // "Running" but /health on port 8000 is unreachable, that's a
      // strong indicator the listening port never bound (port
      // collision, missing dep, etc.).
      const backendPill = document.getElementById('pillBackendStatus');
      if (backendPill) {
        if (info.isBackendRunning && !backendReachable) {
          backendPill.textContent = 'Stalled';
          backendPill.className = 'status-pill stalled';
        } else if (backendReachable || info.isBackendRunning) {
          backendPill.textContent = 'Running';
          backendPill.className = 'status-pill online';
        } else {
          backendPill.textContent = 'Stopped';
          backendPill.className = 'status-pill';
        }
      }

      if (hasQrPayload && info.isExpoRunning) {
        globalStatusDot.className = 'status-dot active';
        globalStatusText.textContent = `All Servers Active (${info.lanIp})`;
      } else if (hasQrPayload || info.isExpoRunning) {
        globalStatusDot.className = 'status-dot active';
        globalStatusText.textContent = `Partial Active (${info.lanIp})`;
      } else {
        globalStatusDot.className = 'status-dot off';
        globalStatusText.textContent = 'Servers Offline';
      }
    } catch (err) {
      console.error('Error fetching server info:', err);
    }
  }

  // Button Listeners
  btnStartServers.addEventListener('click', async () => {
    globalStatusText.textContent = 'Starting servers...';
    serverQrLoader.classList.add('loading');
    expoQrLoader.classList.add('loading');
    await window.electronAPI.startServers();
    setTimeout(refreshServerInfo, 1000);
  });

  btnRestartServers.addEventListener('click', async () => {
    globalStatusText.textContent = 'Restarting...';
    serverQrLoader.classList.add('loading');
    expoQrLoader.classList.add('loading');
    await window.electronAPI.restartServers();
    setTimeout(refreshServerInfo, 2000);
  });

  btnStopServers.addEventListener('click', async () => {
    globalStatusText.textContent = 'Stopping...';
    await window.electronAPI.stopServers();
    setTimeout(refreshServerInfo, 500);
  });

  btnRefreshInfo.addEventListener('click', refreshServerInfo);

  btnCopyServerUrl.addEventListener('click', () => copyToClipboard(txtWsUrl.textContent));
  btnCopyExpoUrl.addEventListener('click', () => copyToClipboard(txtExpoUrl.textContent));
  btnCopyIp.addEventListener('click', () => copyToClipboard(txtLanIp.textContent));

  // Tab switching
  tabPython.addEventListener('click', () => {
    activeTab = 'python';
    tabPython.classList.add('active');
    tabExpo.classList.remove('active');
    logPython.classList.remove('hidden');
    logExpo.classList.add('hidden');
  });

  tabExpo.addEventListener('click', () => {
    activeTab = 'expo';
    tabExpo.classList.add('active');
    tabPython.classList.remove('active');
    logExpo.classList.remove('hidden');
    logPython.classList.add('hidden');
  });

  // Log Actions
  btnClearLogs.addEventListener('click', () => {
    if (activeTab === 'python') {
      logPython.textContent = '';
    } else {
      logExpo.textContent = '';
    }
  });

  btnCopyLogs.addEventListener('click', () => {
    const text = activeTab === 'python' ? logPython.textContent : logExpo.textContent;
    copyToClipboard(text);
  });

  // Log Streams
  window.electronAPI.onPythonLog((text) => {
    logPython.textContent += text;
    logPython.scrollTop = logPython.scrollHeight;
  });

  window.electronAPI.onExpoLog((text) => {
    logExpo.textContent += text;
    logExpo.scrollTop = logExpo.scrollHeight;
  });

  window.electronAPI.onStatusUpdate((data) => {
    refreshServerInfo();
  });

  // Reachability probe — every 2 seconds, ask the Electron main
  // process to fetch /health on the actual LAN IP:port. If the probe
  // disagrees with the controller's spawn-tracked flags, we treat
  // the probe as authoritative (the renderer can see what the mobile
  // phone sees on the network). We surface the disagreement with a
  // subtle dot color so the user notices a process that's "Running"
  // according to Node but unreachable in practice.
  let probeInFlight = false;
  setInterval(async () => {
    if (probeInFlight) return;
    probeInFlight = true;
    try {
      const reach = await window.electronAPI.probeHealth();
      // Update pill colors based on *real* reachability.
      pillPythonStatus.dataset.probeStream = String(reach.streamReachable);
      pillPythonStatus.dataset.probeBackend = String(reach.backendReachable);
      // Re-run the status render so the badges use the probe.
      refreshServerInfo();
    } catch (e) {
      // Silent — the next tick will retry.
    } finally {
      probeInFlight = false;
    }
  }, 2000);

  // Initial load
  refreshServerInfo();
});
