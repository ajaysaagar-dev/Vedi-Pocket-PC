"""
Vedi Pocket PC — pywebview Desktop Controller
Native Python GUI control panel built with pywebview & HTML/CSS Apple Glassmorphism UI.
Manages Screen Stream Server, FastAPI Backend Agent, and Mobile Expo Dev Server.
"""

import sys
import os
import io
import re
import socket
import base64
import subprocess
from typing import Optional

import webview
import qrcode
from PIL import Image as PILImage


def get_lan_ip() -> str:
    """Find local Wi-Fi / Ethernet LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_free_port(preferred: int) -> int:
    port = preferred
    while is_port_in_use(port):
        port += 1
    return port


def generate_qr_base64(data: str) -> str:
    """Generate a crisp base64 PNG data URL for a QR code."""
    if not data:
        data = "VediPocketPC"
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#ffffff", back_color="#0a0a0f").convert("RGBA")
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[QR Error] {e}")
        return ""


def kill_process_tree(pid: int):
    """Safely terminate a process and all its child trees on Windows."""
    if not pid:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass


# --- Apple Glassmorphism Dark UI (HTML / CSS / JS) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Vedi Pocket PC</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
    }
    
    body {
      background-color: #000000;
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
      padding: 20px;
      overflow-x: hidden;
      min-height: 100vh;
    }

    /* Apple Glass Card */
    .glass-card {
      background: rgba(22, 22, 26, 0.75);
      backdrop-filter: blur(25px);
      -webkit-backdrop-filter: blur(25px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      transition: border-color 0.3s ease;
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }

    .brand-title {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }

    .brand-sub {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
      margin-top: 2px;
    }

    .lan-pill {
      font-size: 13px;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 6px 16px;
      border-radius: 14px;
    }

    /* Grid System */
    .dashboard-grid {
      display: grid;
      grid-template-columns: 1.3fr 1fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }

    .section-title {
      font-size: 12px;
      font-weight: 700;
      color: rgba(255, 255, 255, 0.45);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 14px;
    }

    /* Services List */
    .service-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .service-row:last-child {
      border-bottom: none;
    }
    .service-name {
      font-size: 13px;
      font-weight: 600;
    }

    .badge {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 12px;
      letter-spacing: 0.5px;
    }
    .badge-active {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .badge-offline {
      background: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Controls */
    .btn-group {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 14px;
    }

    .btn {
      font-size: 13px;
      font-weight: 600;
      border-radius: 20px;
      padding: 10px 16px;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: rgba(255, 255, 255, 0.08);
      color: #ffffff;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .btn:hover {
      background: rgba(255, 255, 255, 0.18);
      border-color: rgba(255, 255, 255, 0.3);
      transform: translateY(-1px);
    }
    .btn:active {
      transform: translateY(0);
    }

    .btn-primary {
      background: #ffffff;
      color: #000000;
      border: 1px solid #ffffff;
      font-weight: 700;
    }
    .btn-primary:hover {
      background: rgba(255, 255, 255, 0.88);
    }

    .btn-danger {
      background: rgba(239, 68, 68, 0.16);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .btn-danger:hover {
      background: rgba(239, 68, 68, 0.28);
    }

    /* QR Code Card Alignment */
    .qr-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }

    .qr-img-box {
      width: 155px;
      height: 155px;
      background: #0a0a0f;
      border-radius: 14px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 10px 0;
    }

    .qr-img-box img {
      width: 145px;
      height: 145px;
      border-radius: 6px;
    }

    .pin-label {
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 2px;
      color: #ffffff;
    }

    .url-label {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.45);
      word-break: break-all;
    }

    /* Terminal Console Logs */
    .tabs-bar {
      display: flex;
      gap: 6px;
      margin-bottom: 10px;
    }

    .tab {
      font-size: 12px;
      font-weight: 600;
      padding: 6px 16px;
      border-radius: 12px;
      cursor: pointer;
      color: rgba(255, 255, 255, 0.45);
      background: transparent;
      border: none;
    }
    .tab.active {
      background: rgba(255, 255, 255, 0.12);
      color: #ffffff;
    }

    .log-box {
      background: #050508;
      border-radius: 12px;
      padding: 12px;
      height: 180px;
      overflow-y: auto;
      font-family: 'SF Mono', Consolas, monospace;
      font-size: 11px;
      line-height: 1.6;
      color: #34d399;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .log-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .clear-btn {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      background: transparent;
      border: none;
      cursor: pointer;
    }
    .clear-btn:hover {
      color: #ffffff;
    }
  </style>
</head>
<body>

  <!-- Header -->
  <div class="glass-card header">
    <div>
      <div class="brand-title">Vedi Pocket PC</div>
      <div class="brand-sub">pywebview Apple Glassmorphism Desktop Controller</div>
    </div>
    <div class="lan-pill" id="lanIpDisplay">🌐 127.0.0.1</div>
  </div>

  <!-- Dashboard Grid -->
  <div class="dashboard-grid">

    <!-- Column 1: Services & Controls -->
    <div class="glass-card">
      <div class="section-title">System Services</div>
      
      <div class="service-row">
        <span class="service-name">📡 Screen Stream (:8080)</span>
        <span class="badge badge-offline" id="streamBadge">OFFLINE</span>
      </div>
      <div class="service-row">
        <span class="service-name">🔧 Remote Agent (:8000)</span>
        <span class="badge badge-offline" id="backendBadge">OFFLINE</span>
      </div>
      <div class="service-row">
        <span class="service-name">📱 Mobile Client (:8088)</span>
        <span class="badge badge-offline" id="expoBadge">OFFLINE</span>
      </div>

      <div class="btn-group">
        <button class="btn btn-primary" onclick="pywebview.api.start_all_services()">Start All Services</button>
        <button class="btn btn-danger" onclick="pywebview.api.stop_all_services()">Stop All Services</button>
        <button class="btn" onclick="pywebview.api.restart_all_services()">Restart All Services</button>
        <button class="btn" onclick="pywebview.api.reload_expo()">Reload Mobile App</button>
      </div>
    </div>

    <!-- Column 2: PC Pairing QR -->
    <div class="glass-card qr-card">
      <div class="section-title">1. Scan PC Pairing QR</div>
      <div class="qr-img-box">
        <img id="pcQrImg" src="" alt="PC Pairing QR" />
      </div>
      <div class="pin-label" id="pinDisplay">PIN: ----</div>
    </div>

    <!-- Column 3: Expo Go QR -->
    <div class="glass-card qr-card">
      <div class="section-title">2. Scan Expo Go QR</div>
      <div class="qr-img-box">
        <img id="expoQrImg" src="" alt="Expo Go QR" />
      </div>
      <div class="url-label" id="expoUrlDisplay">Initializing Expo...</div>
    </div>

  </div>

  <!-- Terminal Logs -->
  <div class="glass-card">
    <div class="log-header">
      <div class="tabs-bar">
        <button class="tab active" onclick="switchTab('combined')">Combined Logs</button>
        <button class="tab" onclick="switchTab('python')">Python Backend Logs</button>
        <button class="tab" onclick="switchTab('expo')">Expo Mobile Logs</button>
      </div>
      <button class="clear-btn" onclick="clearLogs()">🧹 Clear</button>
    </div>

    <div class="log-box" id="logBox"></div>
  </div>

  <script>
    let activeTab = 'combined';
    const logs = {
      combined: [],
      python: [],
      expo: []
    };

    function appendLog(target, message) {
      if (!message) return;
      const line = `[${target.toUpperCase()}] ${message}`;
      
      logs.combined.push(line);
      if (target === 'python') logs.python.push(message);
      if (target === 'expo') logs.expo.push(message);

      renderLogs();
    }

    function switchTab(tab) {
      activeTab = tab;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      event.target.classList.add('active');
      renderLogs();
    }

    function renderLogs() {
      const logBox = document.getElementById('logBox');
      const lines = logs[activeTab] || [];
      logBox.innerText = lines.join('\\n');
      logBox.scrollTop = logBox.scrollHeight;
    }

    function clearLogs() {
      logs.combined = [];
      logs.python = [];
      logs.expo = [];
      renderLogs();
    }

    function updateState(data) {
      if (data.lan_ip) {
        document.getElementById('lanIpDisplay').innerText = `🌐 ${data.lan_ip}`;
      }

      // Badges
      const setBadge = (id, active) => {
        const el = document.getElementById(id);
        el.innerText = active ? 'ACTIVE' : 'OFFLINE';
        el.className = `badge ${active ? 'badge-active' : 'badge-offline'}`;
      };
      setBadge('streamBadge', data.stream_running);
      setBadge('backendBadge', data.backend_running);
      setBadge('expoBadge', data.expo_running);

      // PIN & URL
      if (data.pairing_pin) {
        document.getElementById('pinDisplay').innerText = `PIN: ${data.pairing_pin}`;
      }
      if (data.expo_url) {
        document.getElementById('expoUrlDisplay').innerText = data.expo_url;
      }

      // QR Images
      if (data.pc_qr) {
        document.getElementById('pcQrImg').src = data.pc_qr;
      }
      if (data.expo_qr) {
        document.getElementById('expoQrImg').src = data.expo_qr;
      }
    }
  </script>
</body>
</html>
"""


class Api:
    def __init__(self, controller):
        self.c = controller

    def start_all_services(self):
        self.c.start_all_services()

    def stop_all_services(self):
        self.c.stop_all_services()

    def restart_all_services(self):
        self.c.restart_all_services()

    def reload_expo(self):
        self.c.reload_expo()


class ControllerManager:
    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.server_dir = os.path.join(self.root_dir, "Screen-Stream-Server")
        self.backend_dir = os.path.join(self.root_dir, "Vedi-PocketPC-Backend")
        self.mobile_dir = os.path.join(self.root_dir, "Vedi-PocketPC-Mobile")

        self.lan_ip = get_lan_ip()
        self.stream_port = 8080
        self.backend_port = 8000
        self.expo_port = 8088

        self.pairing_pin = ""
        self.expo_url = ""

        self.stream_proc: Optional[subprocess.Popen] = None
        self.backend_proc: Optional[subprocess.Popen] = None
        self.expo_proc: Optional[subprocess.Popen] = None

        self.window = None

    def set_window(self, window):
        self.window = window

    def push_js(self, js_code: str):
        if self.window:
            try:
                self.window.evaluate_js(js_code)
            except Exception:
                pass

    def append_log(self, target: str, text: str):
        if not text:
            return
        clean_text = text.replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
        self.push_js(f"appendLog('{target}', '{clean_text}')")

    def update_ui_state(self):
        pc_payload = f"{self.lan_ip}:{self.backend_port}:{self.pairing_pin or '0000'}"
        expo_payload = self.expo_url or f"exp://{self.lan_ip}:{self.expo_port}"

        pc_qr = generate_qr_base64(pc_payload)
        expo_qr = generate_qr_base64(expo_payload)

        state = {
            "lan_ip": self.lan_ip,
            "stream_running": self.stream_proc is not None and self.stream_proc.poll() is None,
            "backend_running": self.backend_proc is not None and self.backend_proc.poll() is None,
            "expo_running": self.expo_proc is not None and self.expo_proc.poll() is None,
            "pairing_pin": self.pairing_pin,
            "expo_url": self.expo_url,
            "pc_qr": pc_qr,
            "expo_qr": expo_qr,
        }
        
        import json
        js = f"updateState({json.dumps(state)})"
        self.push_js(js)

    def start_all_services(self):
        self.start_stream_server()
        self.start_backend_server()
        self.start_expo_server()
        self.update_ui_state()

    def stop_all_services(self):
        self.stop_stream_server()
        self.stop_backend_server()
        self.stop_expo_server()
        self.update_ui_state()

    def restart_all_services(self):
        self.append_log("python", "Restarting all system services...")
        self.stop_all_services()
        self.start_all_services()

    # 1. Screen Stream Server
    def start_stream_server(self):
        if self.stream_proc and self.stream_proc.poll() is None:
            return

        self.stream_port = find_free_port(8080)
        self.append_log("python", f"Starting Screen Stream Server on port {self.stream_port}...")

        env = os.environ.copy()
        env["STREAM_PORT"] = str(self.stream_port)
        env["STREAM_HOST"] = "0.0.0.0"

        self.stream_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=self.server_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self._start_log_thread(self.stream_proc, "python")

    # 2. Remote Agent Backend
    def start_backend_server(self):
        if self.backend_proc and self.backend_proc.poll() is None:
            return

        self.backend_port = find_free_port(8000)
        self.append_log("python", f"Starting Remote Agent Backend on port {self.backend_port}...")

        env = os.environ.copy()
        env["BACKEND_PORT"] = str(self.backend_port)
        env["BACKEND_HOST"] = "0.0.0.0"

        self.backend_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=self.backend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self._start_log_thread(self.backend_proc, "python", parse_pin=True)

    # 3. Mobile Expo Server
    def start_expo_server(self):
        if self.expo_proc and self.expo_proc.poll() is None:
            return

        self.expo_port = find_free_port(8088)
        self.expo_url = f"exp://{self.lan_ip}:{self.expo_port}"
        self.append_log("expo", f"Starting Expo Server on {self.expo_url}...")

        npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
        expo_args = [npx_cmd, "expo", "start", "-c", "--host", "lan", "--port", str(self.expo_port)]

        self.expo_proc = subprocess.Popen(
            expo_args,
            cwd=self.mobile_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self._start_log_thread(self.expo_proc, "expo", parse_expo=True)

    def reload_expo(self):
        if self.expo_proc and self.expo_proc.poll() is None and self.expo_proc.stdin:
            self.append_log("expo", "Sending 'r' key signal to reload connected Expo devices...")
            try:
                self.expo_proc.stdin.write("r\n")
                self.expo_proc.stdin.flush()
            except Exception:
                pass
        else:
            self.stop_expo_server()
            self.start_expo_server()

    def stop_stream_server(self):
        if self.stream_proc:
            kill_process_tree(self.stream_proc.pid)
            self.stream_proc = None

    def stop_backend_server(self):
        if self.backend_proc:
            kill_process_tree(self.backend_proc.pid)
            self.backend_proc = None

    def stop_expo_server(self):
        if self.expo_proc:
            kill_process_tree(self.expo_proc.pid)
            self.expo_proc = None

    def _start_log_thread(self, proc, target: str, parse_pin=False, parse_expo=False):
        import threading
        def reader():
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                text = line.strip()
                self.append_log(target, text)

                if parse_pin:
                    match = re.search(r"Pairing PIN:\s*(\d{4})", text)
                    if match:
                        self.pairing_pin = match.group(1)
                        self.update_ui_state()

                if parse_expo:
                    clean_text = re.sub(r"\x1b\[[0-9;]*m", "", text)
                    match = re.search(r"exp://[\w.\-]+(?::\d+)?[^\s]*", clean_text)
                    if match:
                        self.expo_url = match.group(0)
                        self.update_ui_state()

            self.update_ui_state()

        t = threading.Thread(target=reader, daemon=True)
        t.start()


def main():
    manager = ControllerManager()
    api = Api(manager)

    window = webview.create_window(
        title="Vedi Pocket PC",
        html=HTML_CONTENT,
        js_api=api,
        width=980,
        height=720,
        resizable=True,
        background_color="#000000"
    )
    
    manager.set_window(window)

    def on_loaded():
        manager.start_all_services()

    window.events.loaded += on_loaded

    def on_closing():
        manager.stop_all_services()

    window.events.closing += on_closing

    webview.start(debug=False)


if __name__ == "__main__":
    main()
