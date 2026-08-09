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

  const pillServerStatus = document.getElementById('pillServerStatus');
  const pillExpoStatus = document.getElementById('pillExpoStatus');

  const btnCopyServerUrl = document.getElementById('btnCopyServerUrl');
  const btnCopyExpoUrl = document.getElementById('btnCopyExpoUrl');
  const btnCopyIp = document.getElementById('btnCopyIp');
  const btnRefreshInfo = document.getElementById('btnRefreshInfo');

  const tabServer = document.getElementById('tabServer');
  const tabExpo = document.getElementById('tabExpo');
  const logServer = document.getElementById('logServer');
  const logExpo = document.getElementById('logExpo');

  const btnCopyLogs = document.getElementById('btnCopyLogs');
  const btnClearLogs = document.getElementById('btnClearLogs');
  const toast = document.getElementById('toast');

  let activeTab = 'server';

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

      // Render Server Connect QR
      const serverRunning = info.isServerRunning;
      if (serverRunning && info.serverQr) {
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

      // Update status badges
      if (info.isServerRunning) {
        pillServerStatus.textContent = 'Running';
        pillServerStatus.className = 'status-pill online';
      } else {
        pillServerStatus.textContent = 'Stopped';
        pillServerStatus.className = 'status-pill';
      }

      if (info.isExpoRunning) {
        pillExpoStatus.textContent = 'Running';
        pillExpoStatus.className = 'status-pill online';
      } else {
        pillExpoStatus.textContent = 'Stopped';
        pillExpoStatus.className = 'status-pill';
      }

      if (serverRunning && info.isExpoRunning) {
        globalStatusDot.className = 'status-dot active';
        globalStatusText.textContent = `All Servers Active (${info.lanIp})`;
      } else if (serverRunning || info.isExpoRunning) {
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
  tabServer.addEventListener('click', () => {
    activeTab = 'server';
    tabServer.classList.add('active');
    tabExpo.classList.remove('active');
    logServer.classList.remove('hidden');
    logExpo.classList.add('hidden');
  });

  tabExpo.addEventListener('click', () => {
    activeTab = 'expo';
    tabExpo.classList.add('active');
    tabServer.classList.remove('active');
    logExpo.classList.remove('hidden');
    logServer.classList.add('hidden');
  });

  // Log Actions
  btnClearLogs.addEventListener('click', () => {
    if (activeTab === 'server') {
      logServer.textContent = '';
    } else {
      logExpo.textContent = '';
    }
  });

  btnCopyLogs.addEventListener('click', () => {
    const text = activeTab === 'server' ? logServer.textContent : logExpo.textContent;
    copyToClipboard(text);
  });

  // Log Streams
  window.electronAPI.onPythonLog((text) => {
    logServer.textContent += text;
    logServer.scrollTop = logServer.scrollHeight;
  });

  window.electronAPI.onExpoLog((text) => {
    logExpo.textContent += text;
    logExpo.scrollTop = logExpo.scrollHeight;
  });

  window.electronAPI.onStatusUpdate((data) => {
    refreshServerInfo();
  });

  // Initial load
  refreshServerInfo();
});
