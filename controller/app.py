"""
Vedi Pocket PC — pywebview Desktop Controller
Exact 1:1 HTML/CSS implementation of ref/dark.html and ref/other.html
with dark window background, theme switcher at top right, and zero COM exceptions.
"""

import sys
import os
import io
import re
import socket
import base64
import subprocess
import queue
import time
import json
import threading
from typing import Optional

import webview
import qrcode
from bottle import Bottle, request, response

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
        img = qr.make_image(fill_color="#000000", back_color="#ffffff").convert("RGBA")
        
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


HTML_CONTENT = """<!DOCTYPE html>
<html class="dark" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Vedi Pocket PC</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>

<script id="tailwind-config">
    const darkThemeConfig = {
        darkMode: "class",
        theme: {
            extend: {
                "colors": {
                    "background": "#131313",
                    "surface-container-lowest": "#0e0e0e",
                    "on-primary-fixed-variant": "#454747",
                    "surface-dim": "#131313",
                    "on-secondary-fixed": "#002113",
                    "surface-variant": "#353534",
                    "on-secondary-container": "#00311f",
                    "primary-fixed-dim": "#c6c6c7",
                    "on-surface": "#e5e2e1",
                    "on-primary-container": "#636565",
                    "inverse-surface": "#e5e2e1",
                    "on-error": "#690005",
                    "on-primary-fixed": "#1a1c1c",
                    "primary-container": "#e2e2e2",
                    "surface": "#131313",
                    "on-tertiary-fixed-variant": "#930013",
                    "secondary-fixed-dim": "#4edea3",
                    "surface-container-high": "#2a2a2a",
                    "tertiary-fixed-dim": "#ffb3ad",
                    "on-tertiary-container": "#c22229",
                    "secondary": "#4edea3",
                    "on-background": "#e5e2e1",
                    "secondary-container": "#00a572",
                    "surface-container-low": "#1c1b1b",
                    "error": "#ffb4ab",
                    "inverse-on-surface": "#313030",
                    "on-secondary": "#003824",
                    "tertiary-fixed": "#ffdad7",
                    "on-error-container": "#ffdad6",
                    "error-container": "#93000a",
                    "inverse-primary": "#5d5f5f",
                    "outline-variant": "#444748",
                    "on-primary": "#2f3131",
                    "outline": "#8e9192",
                    "primary-fixed": "#e2e2e2",
                    "surface-bright": "#393939",
                    "surface-tint": "#c6c6c7",
                    "tertiary": "#ffffff",
                    "tertiary-container": "#ffdad7",
                    "on-secondary-fixed-variant": "#005236",
                    "on-surface-variant": "#c4c7c8",
                    "on-tertiary-fixed": "#410004",
                    "on-tertiary": "#68000a",
                    "secondary-fixed": "#6ffbbe",
                    "primary": "#ffffff",
                    "surface-container-highest": "#353534",
                    "surface-container": "#201f1f"
                },
                "borderRadius": {
                    "DEFAULT": "0.25rem",
                    "lg": "0.5rem",
                    "xl": "0.75rem",
                    "full": "9999px"
                },
                "spacing": {
                    "container-max-width": "1440px",
                    "gutter": "16px",
                    "unit": "4px",
                    "margin": "24px"
                },
                "fontFamily": {
                    "code-log": ["JetBrains Mono"],
                    "body-md": ["Inter"],
                    "label-mono": ["JetBrains Mono"],
                    "headline-lg": ["Inter"],
                    "headline-md": ["Inter"],
                    "body-sm": ["Inter"]
                },
                "fontSize": {
                    "code-log": ["13px", { "lineHeight": "18px", "fontWeight": "400" }],
                    "body-md": ["14px", { "lineHeight": "20px", "fontWeight": "400" }],
                    "label-mono": ["12px", { "lineHeight": "16px", "letterSpacing": "0.05em", "fontWeight": "500" }],
                    "headline-lg": ["24px", { "lineHeight": "32px", "letterSpacing": "-0.02em", "fontWeight": "700" }],
                    "headline-md": ["18px", { "lineHeight": "24px", "letterSpacing": "-0.01em", "fontWeight": "600" }],
                    "body-sm": ["12px", { "lineHeight": "16px", "fontWeight": "400" }]
                }
            }
        }
    };
    tailwind.config = darkThemeConfig;
</script>
<style>
        body.theme-dark {
            background-color: #131313;
            color: #e5e2e1;
        }
        body.theme-dark .glass-panel {
            background-color: rgba(19, 19, 19, 0.6);
            backdrop-filter: blur(20px);
            border: 1px solid #2C2C2E;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }

        body.theme-cyber {
            background: linear-gradient(to bottom right, #0A0C10, #0F172A);
            color: #F3F4F6;
        }
        body.theme-cyber .glass-panel {
            background-color: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(24px);
            border: 1px solid rgba(6, 182, 212, 0.3);
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }
        body.theme-cyber .text-primary { color: #06B6D4; }
        body.theme-cyber .text-secondary { color: #A855F7; }

        .terminal-scroll::-webkit-scrollbar {
            width: 8px;
        }
        .terminal-scroll::-webkit-scrollbar-track {
            background: #000;
        }
        .terminal-scroll::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 4px;
        }
</style>
</head>
<body class="theme-dark bg-background text-on-surface font-body-md min-h-screen flex flex-col items-center pt-8 pb-12 px-margin transition-colors duration-300">

<!-- Top Navigation Container -->
<header class="glass-panel w-full max-w-container-max-width rounded-xl p-6 flex justify-between items-center mb-6">
  <div>
    <h1 class="font-headline-lg text-headline-lg text-primary">Vedi Pocket PC</h1>
    <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">pywebview Apple Glassmorphism Desktop Controller</p>
  </div>
  
  <div class="flex items-center gap-3">
    <!-- LAN IP -->
    <div class="flex items-center gap-3 bg-surface-container-high px-4 py-2 rounded-full border border-outline-variant shadow-sm">
      <span class="material-symbols-outlined text-[18px] text-secondary">language</span>
      <span class="font-label-mono text-label-mono text-on-surface" id="lanIpDisplay">127.0.0.1</span>
    </div>

    <!-- Theme Switcher Button (Top Right) -->
    <button onclick="toggleTheme()" class="flex items-center gap-2 bg-surface-container-high px-4 py-2 rounded-full border border-outline-variant hover:bg-surface-variant transition-all cursor-pointer">
      <span class="material-symbols-outlined text-[18px] text-secondary" id="themeIcon">palette</span>
      <span id="themeBtnText" class="font-label-mono text-label-mono text-on-surface">Cyber Mode</span>
    </button>
  </div>
</header>

<!-- Main Content Area Grid -->
<main class="w-full max-w-container-max-width grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
  <!-- Left Panel: System Services (Spans 4 cols) -->
  <section class="glass-panel rounded-xl p-6 lg:col-span-4 flex flex-col h-full">
    <h2 class="font-label-mono text-label-mono text-on-surface-variant mb-4 uppercase tracking-wider">System Services</h2>
    <div class="flex flex-col gap-3 flex-1">
      <!-- Service Items -->
      <div class="flex justify-between items-center py-2 border-b border-outline-variant/30">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[16px]">monitor</span>
          <span class="font-body-md text-on-surface font-medium">Screen Stream (:8080)</span>
        </div>
        <span class="bg-secondary/10 text-secondary border border-secondary/20 px-3 py-0.5 rounded-full font-label-mono text-[10px] tracking-widest" id="streamBadge">ACTIVE</span>
      </div>

      <div class="flex justify-between items-center py-2 border-b border-outline-variant/30">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[16px]">router</span>
          <span class="font-body-md text-on-surface font-medium">Remote Agent (:8000)</span>
        </div>
        <span class="bg-secondary/10 text-secondary border border-secondary/20 px-3 py-0.5 rounded-full font-label-mono text-[10px] tracking-widest" id="backendBadge">ACTIVE</span>
      </div>

      <div class="flex justify-between items-center py-2 border-b border-outline-variant/30">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[16px]">smartphone</span>
          <span class="font-body-md text-on-surface font-medium">Mobile Client (:8088)</span>
        </div>
        <span class="bg-secondary/10 text-secondary border border-secondary/20 px-3 py-0.5 rounded-full font-label-mono text-[10px] tracking-widest" id="expoBadge">ACTIVE</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex flex-col gap-3 mt-6">
      <button onclick="sendAction('start_all')" class="w-full bg-primary text-on-primary font-body-md font-semibold py-3 rounded-lg hover:bg-primary/90 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.4)] cursor-pointer">
        Start All Services
      </button>
      <button onclick="sendAction('stop_all')" class="w-full bg-error-container/30 text-error border border-error/50 font-body-md font-semibold py-3 rounded-lg hover:bg-error-container/50 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] cursor-pointer">
        Stop All Services
      </button>
      <button onclick="sendAction('restart_all')" class="w-full bg-transparent border border-outline-variant text-on-surface font-body-md font-medium py-3 rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer">
        Restart All Services
      </button>
      <button onclick="sendAction('reload_expo')" class="w-full bg-transparent border border-outline-variant text-on-surface font-body-md font-medium py-3 rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer">
        Reload Mobile App
      </button>
    </div>
  </section>

  <!-- Right Panel Container (Spans 8 cols) -->
  <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
    <!-- QR Card 1 -->
    <section class="glass-panel rounded-xl p-8 flex flex-col items-center justify-center">
      <h3 class="font-label-mono text-label-mono text-on-surface-variant mb-6 uppercase tracking-wider text-center">1. Scan PC Pairing QR</h3>
      <div class="bg-white p-4 rounded-lg mb-6 shadow-xl flex items-center justify-center">
        <img id="pcQrImg" class="w-48 h-48 rounded" src="" alt="PC Pairing QR" />
      </div>
      <p class="font-headline-md text-headline-md text-primary tracking-widest" id="pinDisplay">PIN: ----</p>
    </section>

    <!-- QR Card 2 -->
    <section class="glass-panel rounded-xl p-8 flex flex-col items-center justify-center">
      <h3 class="font-label-mono text-label-mono text-on-surface-variant mb-6 uppercase tracking-wider text-center">2. Scan Expo Go QR</h3>
      <div class="bg-white p-4 rounded-lg mb-6 shadow-xl flex items-center justify-center">
        <img id="expoQrImg" class="w-48 h-48 rounded" src="" alt="Expo Go QR" />
      </div>
      <p class="font-label-mono text-label-mono text-on-surface-variant lowercase" id="expoUrlDisplay">Initializing Expo...</p>
    </section>
  </div>

  <!-- Terminal Logs Panel (Spans 12 cols) -->
  <section class="glass-panel rounded-xl lg:col-span-12 flex flex-col mt-2 h-80 overflow-hidden">
    <div class="flex justify-between items-center bg-surface-container-lowest/80 border-b border-outline-variant px-4 py-3">
      <div class="flex gap-4">
        <button id="tab-combined" onclick="switchTab('combined')" class="bg-surface-variant/50 text-on-surface px-4 py-1.5 rounded-full font-label-mono text-label-mono border border-outline-variant shadow-sm transition-colors hover:bg-surface-variant cursor-pointer">Combined Logs</button>
        <button id="tab-python" onclick="switchTab('python')" class="text-on-surface-variant px-4 py-1.5 rounded-full font-label-mono text-label-mono transition-colors hover:text-on-surface hover:bg-surface-variant/20 cursor-pointer">Python Backend Logs</button>
        <button id="tab-expo" onclick="switchTab('expo')" class="text-on-surface-variant px-4 py-1.5 rounded-full font-label-mono text-label-mono transition-colors hover:text-on-surface hover:bg-surface-variant/20 cursor-pointer">Expo Mobile Logs</button>
      </div>
      <button onclick="clearLogs()" class="flex items-center gap-1 text-on-surface-variant hover:text-primary transition-colors text-xs font-label-mono cursor-pointer">
        <span class="material-symbols-outlined text-[14px]">cleaning_services</span>
        Clear
      </button>
    </div>
    <div class="bg-black flex-1 p-4 overflow-y-auto terminal-scroll">
      <pre class="font-code-log text-code-log text-secondary whitespace-pre-wrap break-all" id="logBox"></pre>
    </div>
  </section>
</main>

<script>
  let currentTheme = 'theme-dark';
  let activeTab = 'combined';
  const logs = {
    combined: [],
    python: [],
    expo: []
  };

  function toggleTheme() {
    const body = document.body;
    const themeBtnText = document.getElementById('themeBtnText');
    
    if (currentTheme === 'theme-dark') {
      body.classList.remove('theme-dark');
      body.classList.add('theme-cyber');
      currentTheme = 'theme-cyber';
      themeBtnText.innerText = 'Dark Mode';
    } else {
      body.classList.remove('theme-cyber');
      body.classList.add('theme-dark');
      currentTheme = 'theme-dark';
      themeBtnText.innerText = 'Cyber Mode';
    }
  }

  function sendAction(actionName) {
    fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionName })
    }).catch(err => console.error(err));
  }

  function switchTab(tab) {
    activeTab = tab;
    ['combined', 'python', 'expo'].forEach(t => {
      const el = document.getElementById(`tab-${t}`);
      if (t === tab) {
        el.className = "bg-surface-variant/50 text-on-surface px-4 py-1.5 rounded-full font-label-mono text-label-mono border border-outline-variant shadow-sm transition-colors cursor-pointer";
      } else {
        el.className = "text-on-surface-variant px-4 py-1.5 rounded-full font-label-mono text-label-mono transition-colors hover:text-on-surface hover:bg-surface-variant/20 cursor-pointer";
      }
    });
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

  // Poll status & logs
  async function pollData() {
    try {
      const statusRes = await fetch('/api/status');
      const data = await statusRes.json();

      if (data.lan_ip) {
        document.getElementById('lanIpDisplay').innerText = data.lan_ip;
      }

      const setBadge = (id, active) => {
        const el = document.getElementById(id);
        el.innerText = active ? 'ACTIVE' : 'OFFLINE';
        if (active) {
          el.className = 'bg-secondary/10 text-secondary border border-secondary/20 px-3 py-0.5 rounded-full font-label-mono text-[10px] tracking-widest';
        } else {
          el.className = 'bg-error-container/20 text-error border border-error/30 px-3 py-0.5 rounded-full font-label-mono text-[10px] tracking-widest';
        }
      };
      setBadge('streamBadge', data.stream_running);
      setBadge('backendBadge', data.backend_running);
      setBadge('expoBadge', data.expo_running);

      if (data.pairing_pin) {
        document.getElementById('pinDisplay').innerText = `PIN: ${data.pairing_pin}`;
      }
      if (data.expo_url) {
        document.getElementById('expoUrlDisplay').innerText = data.expo_url;
      }

      if (data.pc_qr) {
        document.getElementById('pcQrImg').src = data.pc_qr;
      }
      if (data.expo_qr) {
        document.getElementById('expoQrImg').src = data.expo_qr;
      }
    } catch (e) {}

    try {
      const logsRes = await fetch('/api/logs');
      const items = await logsRes.json();
      if (items && items.length) {
        items.forEach(item => {
          const line = `[${item.target.toUpperCase()}] ${item.message}`;
          logs.combined.push(line);
          if (item.target === 'python') logs.python.push(item.message);
          if (item.target === 'expo') logs.expo.push(item.message);
        });
        renderLogs();
      }
    } catch (e) {}
  }

  setInterval(pollData, 300);
  pollData();
</script>
</body>
</html>
"""


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

        self.is_running = True
        self.log_queue = queue.Queue()

    def append_log(self, target: str, text: str):
        if not text or not self.is_running:
            return
        self.log_queue.put((target, text))

    def get_pending_logs(self):
        batch = []
        while len(batch) < 40:
            try:
                target, text = self.log_queue.get_nowait()
                batch.append({"target": target, "message": text})
            except queue.Empty:
                break
        return batch

    def get_status_dict(self):
        pc_payload = f"{self.lan_ip}:{self.backend_port}:{self.pairing_pin or '0000'}"
        expo_payload = self.expo_url or f"exp://{self.lan_ip}:{self.expo_port}"

        pc_qr = generate_qr_base64(pc_payload)
        expo_qr = generate_qr_base64(expo_payload)

        return {
            "lan_ip": self.lan_ip,
            "stream_running": self.stream_proc is not None and self.stream_proc.poll() is None,
            "backend_running": self.backend_proc is not None and self.backend_proc.poll() is None,
            "expo_running": self.expo_proc is not None and self.expo_proc.poll() is None,
            "pairing_pin": self.pairing_pin,
            "expo_url": self.expo_url,
            "pc_qr": pc_qr,
            "expo_qr": expo_qr,
        }

    def start_all_services(self):
        self.start_stream_server()
        self.start_backend_server()
        self.start_expo_server()

    def stop_all_services(self):
        self.stop_stream_server()
        self.stop_backend_server()
        self.stop_expo_server()

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
        def reader():
            for line in iter(proc.stdout.readline, ''):
                if not line or not self.is_running:
                    break
                text = line.strip()
                self.append_log(target, text)

                if parse_pin:
                    match = re.search(r"Pairing PIN:\s*(\d{4})", text)
                    if match:
                        self.pairing_pin = match.group(1)

                if parse_expo:
                    clean_text = re.sub(r"\x1b\[[0-9;]*m", "", text)
                    match = re.search(r"exp://[\w.\-]+(?::\d+)?[^\s]*", clean_text)
                    if match:
                        self.expo_url = match.group(0)

        t = threading.Thread(target=reader, daemon=True)
        t.start()


manager = ControllerManager()
bottle_app = Bottle()

@bottle_app.route('/')
def route_index():
    return HTML_CONTENT

@bottle_app.route('/api/status')
def route_status():
    response.content_type = 'application/json'
    return json.dumps(manager.get_status_dict())

@bottle_app.route('/api/logs')
def route_logs():
    response.content_type = 'application/json'
    return json.dumps(manager.get_pending_logs())

@bottle_app.route('/api/action', method='POST')
def route_action():
    data = request.json or {}
    act = data.get('action')
    if act == 'start_all':
        manager.start_all_services()
    elif act == 'stop_all':
        manager.stop_all_services()
    elif act == 'restart_all':
        manager.restart_all_services()
    elif act == 'reload_expo':
        manager.reload_expo()
    return json.dumps({'status': 'ok'})


def start_server_and_gui():
    server_port = find_free_port(18090)
    server_thread = threading.Thread(
        target=lambda: bottle_app.run(host='127.0.0.1', port=server_port, quiet=True),
        daemon=True
    )
    server_thread.start()
    time.sleep(0.3)

    manager.start_all_services()

    window = webview.create_window(
        title="Vedi Pocket PC",
        url=f"http://127.0.0.1:{server_port}",
        width=1240,
        height=840,
        resizable=True,
        background_color="#131313"
    )

    def on_closing():
        manager.is_running = False
        manager.stop_all_services()

    window.events.closing += on_closing
    webview.start(debug=False)


if __name__ == "__main__":
    start_server_and_gui()
