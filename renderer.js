document.addEventListener('DOMContentLoaded', async () => {
  // Setup Controller Bridge API (Python REST & WebSocket Backend)
  const api = window.electronAPI || (() => {
    const listeners = {
      'python-log': new Set(),
      'expo-log': new Set(),
      'status-update': new Set(),
    };

    let ws = null;
    let reconnectTimeout = null;

    function connectWs() {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }

      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${location.host}/ws/events`;

      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        scheduleReconnect();
        return;
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'log') {
            const set = listeners[msg.channel];
            if (set) {
              set.forEach((cb) => {
                try { cb(msg.payload); } catch (_) {}
              });
            }
          } else if (msg.type === 'status-update') {
            listeners['status-update'].forEach((cb) => {
              try { cb(msg.data); } catch (_) {}
            });
          }
        } catch (err) {
          console.warn('[WS] Parse error:', err);
        }
      };

      ws.onclose = () => {
        ws = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        if (ws) {
          try { ws.close(); } catch (_) {}
        }
      };
    }

    function scheduleReconnect() {
      if (!reconnectTimeout) {
        reconnectTimeout = setTimeout(connectWs, 1500);
      }
    }

    connectWs();

    return {
      getServerInfo: async () => {
        const res = await fetch('/api/server-info');
        return await res.json();
      },
      startServers: async () => {
        const res = await fetch('/api/start-servers', { method: 'POST' });
        return await res.json();
      },
      stopServers: async () => {
        const res = await fetch('/api/stop-servers', { method: 'POST' });
        return await res.json();
      },
      restartServers: async () => {
        const res = await fetch('/api/restart-servers', { method: 'POST' });
        return await res.json();
      },
      reloadExpo: async () => {
        const res = await fetch('/api/reload-expo', { method: 'POST' });
        return await res.json();
      },
      probeHealth: async () => {
        try {
          const res = await fetch('/api/probe-health');
          return await res.json();
        } catch (_) {
          return { streamReachable: false, backendReachable: false };
        }
      },
      generateQR: async (text) => {
        const res = await fetch('/api/generate-qr', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });
        const data = await res.json();
        return data.qr || '';
      },
      openExternal: (url) => {
        window.open(url, '_blank');
      },
      onPythonLog: (cb) => {
        listeners['python-log'].add(cb);
        return () => listeners['python-log'].delete(cb);
      },
      onExpoLog: (cb) => {
        listeners['expo-log'].add(cb);
        return () => listeners['expo-log'].delete(cb);
      },
      onStatusUpdate: (cb) => {
        listeners['status-update'].add(cb);
        return () => listeners['status-update'].delete(cb);
      },
    };
  })();

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
  const pillBackendStatus = document.getElementById('pillBackendStatus');

  const btnCopyServerUrl = document.getElementById('btnCopyServerUrl');
  const btnCopyExpoUrl = document.getElementById('btnCopyExpoUrl');
  const btnCopyIp = document.getElementById('btnCopyIp');
  const btnRefreshInfo = document.getElementById('btnRefreshInfo');
  const btnReloadMetro = document.getElementById('btnReloadMetro');

  const tabPython = document.getElementById('tabPython');
  const tabExpo = document.getElementById('tabExpo');
  const logPython = document.getElementById('logPython');
  const logExpo = document.getElementById('logExpo');

  const btnCopyLogs = document.getElementById('btnCopyLogs');
  const btnClearLogs = document.getElementById('btnClearLogs');
  const toast = document.getElementById('toast');

  let activeTab = 'python';

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  function copyToClipboard(text) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      showToast(`Copied "${text}" to clipboard!`);
    }).catch(() => {
      showToast('Copied to clipboard!');
    });
  }

  // Load and refresh server information
  async function refreshServerInfo() {
    try {
      const info = await api.getServerInfo();

      if (txtLanIp) txtLanIp.textContent = info.lanIp;
      if (txtWsUrl) txtWsUrl.textContent = info.wsUrl;
      if (txtExpoUrl) txtExpoUrl.textContent = info.expoUrl;
      if (txtPairingUrl) {
        txtPairingUrl.textContent = info.pairingUrl || info.wsUrl;
      }
      if (txtPairingPin) {
        txtPairingPin.textContent = info.pairingPin || '----';
      }

      // Render Server Connect QR
      const hasQrPayload = !!(info.pairingUrl || info.serverQr);
      if (hasQrPayload && info.serverQr) {
        if (imgServerQr) {
          imgServerQr.src = info.serverQr;
          imgServerQr.style.display = 'block';
        }
        if (serverQrLoader) serverQrLoader.style.display = 'none';
      } else {
        if (imgServerQr) imgServerQr.style.display = 'none';
        if (serverQrLoader) {
          serverQrLoader.style.display = 'flex';
          serverQrLoader.classList.add('loading');
        }
      }

      // Render Expo Mobile App QR
      if (info.isExpoRunning && info.expoQr) {
        if (imgExpoQr) {
          imgExpoQr.src = info.expoQr;
          imgExpoQr.style.display = 'block';
        }
        if (expoQrLoader) expoQrLoader.style.display = 'none';
      } else {
        if (imgExpoQr) imgExpoQr.style.display = 'none';
        if (expoQrLoader) {
          expoQrLoader.style.display = 'flex';
          expoQrLoader.classList.add('loading');
        }
      }

      // Update status badges
      const probeStream = pillPythonStatus ? pillPythonStatus.dataset.probeStream : undefined;
      const probeBackend = pillBackendStatus ? pillBackendStatus.dataset.probeBackend : undefined;
      const streamReachable = probeStream === 'true';
      const backendReachable = probeBackend === 'true';

      if (pillPythonStatus) {
        if (info.isPythonRunning && !streamReachable) {
          pillPythonStatus.textContent = 'Running';
          pillPythonStatus.className = 'status-pill online';
        } else if (streamReachable || info.isPythonRunning) {
          pillPythonStatus.textContent = 'Running';
          pillPythonStatus.className = 'status-pill online';
        } else {
          pillPythonStatus.textContent = 'Stopped';
          pillPythonStatus.className = 'status-pill';
        }
      }

      if (pillBackendStatus) {
        if (info.isBackendRunning || backendReachable) {
          pillBackendStatus.textContent = 'Running';
          pillBackendStatus.className = 'status-pill online';
        } else {
          pillBackendStatus.textContent = 'Stopped';
          pillBackendStatus.className = 'status-pill';
        }
      }

      if (pillExpoStatus) {
        if (info.isExpoRunning) {
          pillExpoStatus.textContent = 'Running';
          pillExpoStatus.className = 'status-pill online';
        } else {
          pillExpoStatus.textContent = 'Stopped';
          pillExpoStatus.className = 'status-pill';
        }
      }

      if (globalStatusDot && globalStatusText) {
        if (hasQrPayload && info.isExpoRunning) {
          globalStatusDot.className = 'status-dot active';
          globalStatusText.textContent = `All Servers Active (${info.lanIp})`;
        } else if (hasQrPayload || info.isExpoRunning) {
          globalStatusDot.className = 'status-dot active';
          globalStatusText.textContent = `Active (${info.lanIp})`;
        } else {
          globalStatusDot.className = 'status-dot off';
          globalStatusText.textContent = 'Servers Offline';
        }
      }
    } catch (err) {
      console.error('Error fetching server info:', err);
    }
  }

  // Button Listeners
  if (btnStartServers) {
    btnStartServers.addEventListener('click', async () => {
      if (globalStatusText) globalStatusText.textContent = 'Starting servers...';
      if (serverQrLoader) serverQrLoader.classList.add('loading');
      if (expoQrLoader) expoQrLoader.classList.add('loading');
      await api.startServers();
      setTimeout(refreshServerInfo, 1000);
    });
  }

  if (btnRestartServers) {
    btnRestartServers.addEventListener('click', async () => {
      if (globalStatusText) globalStatusText.textContent = 'Restarting...';
      if (serverQrLoader) serverQrLoader.classList.add('loading');
      if (expoQrLoader) expoQrLoader.classList.add('loading');
      await api.restartServers();
      setTimeout(refreshServerInfo, 2000);
    });
  }

  if (btnStopServers) {
    btnStopServers.addEventListener('click', async () => {
      if (globalStatusText) globalStatusText.textContent = 'Stopping...';
      await api.stopServers();
      setTimeout(refreshServerInfo, 500);
    });
  }

  if (btnRefreshInfo) {
    btnRefreshInfo.addEventListener('click', refreshServerInfo);
  }

  // Reload Metro
  if (btnReloadMetro) {
    btnReloadMetro.addEventListener('click', async () => {
      btnReloadMetro.disabled = true;
      btnReloadMetro.textContent = 'Reloading…';
      try {
        await api.reloadExpo();
        showToast('Sent Reload command to Expo CLI.');
      } catch (err) {
        console.error('Reload failed:', err);
      } finally {
        setTimeout(() => {
          btnReloadMetro.disabled = false;
          btnReloadMetro.textContent = 'Reload Metro';
        }, 2000);
      }
    });
  }

  if (btnCopyServerUrl) {
    btnCopyServerUrl.addEventListener('click', () => {
      const textToCopy = txtPairingUrl ? txtPairingUrl.textContent : (txtWsUrl ? txtWsUrl.textContent : '');
      copyToClipboard(textToCopy);
    });
  }

  if (btnCopyExpoUrl) {
    btnCopyExpoUrl.addEventListener('click', () => copyToClipboard(txtExpoUrl ? txtExpoUrl.textContent : ''));
  }

  if (btnCopyIp) {
    btnCopyIp.addEventListener('click', () => copyToClipboard(txtLanIp ? txtLanIp.textContent : ''));
  }

  // Tab switching
  if (tabPython && tabExpo && logPython && logExpo) {
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
  }

  // Log Actions
  if (btnClearLogs) {
    btnClearLogs.addEventListener('click', () => {
      if (activeTab === 'python' && logPython) {
        logPython.textContent = '';
      } else if (logExpo) {
        logExpo.textContent = '';
      }
    });
  }

  if (btnCopyLogs) {
    btnCopyLogs.addEventListener('click', () => {
      const text = activeTab === 'python' ? (logPython ? logPython.textContent : '') : (logExpo ? logExpo.textContent : '');
      copyToClipboard(text);
    });
  }

  // Log Streams
  api.onPythonLog((text) => {
    if (logPython) {
      logPython.textContent += text;
      if (logPython.textContent.length > 150000) {
        logPython.textContent = logPython.textContent.slice(-100000);
      }
      logPython.scrollTop = logPython.scrollHeight;
    }
  });

  api.onExpoLog((text) => {
    if (logExpo) {
      logExpo.textContent += text;
      if (logExpo.textContent.length > 150000) {
        logExpo.textContent = logExpo.textContent.slice(-100000);
      }
      logExpo.scrollTop = logExpo.scrollHeight;
    }
  });

  api.onStatusUpdate(() => {
    refreshServerInfo();
  });

  // Reachability probe
  let probeInFlight = false;
  setInterval(async () => {
    if (probeInFlight) return;
    probeInFlight = true;
    try {
      const reach = await api.probeHealth();
      if (pillPythonStatus) pillPythonStatus.dataset.probeStream = String(reach.streamReachable);
      if (pillBackendStatus) pillBackendStatus.dataset.probeBackend = String(reach.backendReachable);
      refreshServerInfo();
    } catch (_) {
    } finally {
      probeInFlight = false;
    }
  }, 2500);

  // Initial load
  refreshServerInfo();
});
