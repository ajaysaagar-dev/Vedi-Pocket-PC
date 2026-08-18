"""ProcessManager — manages the lifecycle of Expo, screen-stream server,
and FastAPI backend agent in Python.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Callable, Dict, List, Optional, Set

from .network import find_free_port, get_lan_ip


def resolve_project_dir(subdir_name: str) -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(root, subdir_name)


def get_python_exe() -> str:
    """Returns the best python executable to spawn child servers."""
    return sys.executable or "python"


def get_node_cmd() -> str:
    """Finds node binary."""
    node = shutil.which("node")
    if node:
        return node
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        candidate = os.path.join(pf, "nodejs", "node.exe")
        if os.path.exists(candidate):
            return candidate
    return "node"


def get_npx_cmd() -> str:
    """Finds npx command."""
    npx = shutil.which("npx.cmd" if sys.platform == "win32" else "npx")
    if npx:
        return npx
    return "npx.cmd" if sys.platform == "win32" else "npx"


class ProcessManager:
    """Manages child processes for Expo, Screen Stream, and FastAPI Backend."""

    def __init__(self) -> None:
        self.expo_process: Optional[subprocess.Popen] = None
        self.stream_process: Optional[subprocess.Popen] = None
        self.backend_process: Optional[subprocess.Popen] = None

        self.is_expo_running = False
        self.is_python_running = False
        self.is_backend_running = False

        self.stream_port = 8080
        self.backend_port = 8000
        self.expo_port = 8088

        self.expo_url = ""
        self.lan_ip = get_lan_ip()
        self.pairing_pin = ""

        self._status_listeners: Set[Callable[[dict], None]] = set()
        self._log_listeners: Set[Callable[[str, str], None]] = set()

        self._lock = threading.Lock()

    def add_status_listener(self, cb: Callable[[dict], None]) -> Callable[[], None]:
        self._status_listeners.add(cb)
        return lambda: self._status_listeners.discard(cb)

    def add_log_listener(self, cb: Callable[[str, str], None]) -> Callable[[], None]:
        self._log_listeners.add(cb)
        return lambda: self._log_listeners.discard(cb)

    def get_status_payload(self) -> dict:
        self.lan_ip = get_lan_ip()
        server_url = f"http://{self.lan_ip}:{self.stream_port}"
        ws_url = f"ws://{self.lan_ip}:{self.stream_port}/ws"
        current_expo_url = self.expo_url or f"exp://{self.lan_ip}:{self.expo_port}"

        pairing_url = (
            f"{self.lan_ip}:{self.backend_port}:{self.pairing_pin}"
            if self.pairing_pin and self.lan_ip
            else server_url
        )

        return {
            "lanIp": self.lan_ip,
            "serverPort": self.stream_port,
            "backendPort": self.backend_port,
            "expoPort": self.expo_port,
            "isPythonRunning": self.is_python_running,
            "isBackendRunning": self.is_backend_running,
            "isExpoRunning": self.is_expo_running,
            "pairingPin": self.pairing_pin,
            "pairingUrl": pairing_url,
            "serverUrl": server_url,
            "wsUrl": ws_url,
            "expoUrl": current_expo_url,
        }

    def emit_status(self) -> None:
        payload = self.get_status_payload()
        for cb in list(self._status_listeners):
            try:
                cb(payload)
            except Exception:
                pass

    def emit_log(self, channel: str, message: str) -> None:
        for cb in list(self._log_listeners):
            try:
                cb(channel, message)
            except Exception:
                pass

    # ------------------------- Expo -------------------------
    def start_expo(self) -> None:
        with self._lock:
            if self.expo_process is not None and self.expo_process.poll() is None:
                return

            self.expo_port = find_free_port(8088)
            expo_dir = resolve_project_dir("veddi-pocketpc")

            if not os.path.isdir(expo_dir):
                self.emit_log("expo-log", f"[Controller] Mobile directory not found: {expo_dir}\n")
                return

            self.lan_ip = get_lan_ip()
            self.expo_url = f"exp://{self.lan_ip}:{self.expo_port}"
            self.emit_log(
                "expo-log",
                f"[Controller] Starting Expo Mobile Server on LAN ({self.lan_ip}:{self.expo_port})...\n",
            )

            env = os.environ.copy()
            env["REACT_NATIVE_PACKAGER_HOSTNAME"] = self.lan_ip
            env["FORCE_COLOR"] = "1"
            env["PYTHONUNBUFFERED"] = "1"
            env.pop("CI", None)
            env.pop("EXPO_NO_INTERACTIVE", None)

            expo_cli_candidates = [
                os.path.join(expo_dir, "node_modules", "expo", "bin", "cli"),
                os.path.join(expo_dir, "node_modules", "expo", "bin", "cli.js"),
                os.path.join(expo_dir, "node_modules", ".bin", "expo.cmd"),
                os.path.join(expo_dir, "node_modules", ".bin", "expo"),
            ]
            expo_cli = next((p for p in expo_cli_candidates if os.path.exists(p)), None)
            node_cmd = get_node_cmd()
            npx_cmd = get_npx_cmd()

            args = ["start", "-c", "--host", "lan", "--port", str(self.expo_port)]
            if expo_cli:
                if expo_cli.endswith(".cmd"):
                    cmd = [expo_cli] + args
                    use_shell = True
                else:
                    cmd = [node_cmd, expo_cli] + args
                    use_shell = False
            else:
                cmd = [npx_cmd, "expo"] + args
                use_shell = sys.platform == "win32"

            try:
                self.expo_process = subprocess.Popen(
                    cmd,
                    cwd=expo_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    shell=use_shell,
                )
                self.is_expo_running = True
                self.emit_status()

                threading.Thread(
                    target=self._reader_thread,
                    args=(self.expo_process.stdout, "expo-log", self._on_expo_stdout),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._reader_thread,
                    args=(self.expo_process.stderr, "expo-log", None),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._listen_expo_events,
                    args=(self.expo_port,),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._wait_process,
                    args=(self.expo_process, "expo"),
                    daemon=True,
                ).start()

            except Exception as e:
                self.emit_log("expo-log", f"[SPAWN ERROR] Failed to start Expo: {e}\n")
                self.is_expo_running = False
                self.expo_process = None
                self.emit_status()

    def _on_expo_stdout(self, line: str) -> None:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        exp_match = re.search(r"exp://[\w.\-]+(?::\d+)?[^\s\x1b]*", clean)
        if exp_match:
            self.expo_url = exp_match.group(0)
            self.emit_status()
        else:
            http_match = re.search(r"https?://[\w.\-]+:(\d+)", clean)
            if http_match:
                self.expo_port = int(http_match.group(1))
                self.expo_url = f"exp://{self.lan_ip}:{self.expo_port}"
                self.emit_status()

    def _listen_expo_events(self, port: int) -> None:
        """Subscribes to Metro's /events WebSocket to stream real-time JS device logs from mobile app."""
        import json
        try:
            import websockets.sync.client as ws_client
        except ImportError:
            return

        ws_url = f"ws://127.0.0.1:{port}/events"
        for _ in range(30):
            if not self.is_expo_running:
                return
            try:
                with ws_client.connect(ws_url, open_timeout=2) as ws:
                    self.emit_log("expo-log", f"[Controller] Connected to Metro live event stream on port {port}.\n")
                    for message in ws:
                        if not self.is_expo_running:
                            break
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            if msg_type == "client_log":
                                level = str(data.get("level", "info")).upper()
                                raw_items = data.get("data", [])
                                formatted_items = []
                                for item in raw_items:
                                    if isinstance(item, str):
                                        formatted_items.append(item)
                                    else:
                                        formatted_items.append(json.dumps(item))
                                payload = " ".join(formatted_items)
                                self.emit_log("expo-log", f"[Mobile Log] [{level}] {payload}\n")
                            elif msg_type == "error":
                                err = data.get("error", "Unknown Expo Error")
                                self.emit_log("expo-log", f"[Expo Error] {err}\n")
                            elif msg_type == "bundle_build_done":
                                self.emit_log("expo-log", "[Controller] Mobile bundle build complete.\n")
                        except Exception:
                            pass
                    break
            except Exception:
                time.sleep(1)

    def reload_expo(self) -> bool:
        reloaded = False
        self.emit_log("expo-log", '[Controller] > Triggering Expo Mobile App reload...\n')

        # 1. Broadcast reload via Metro WebSocket /message
        try:
            import json
            import websockets.sync.client as ws_client
            ws_url = f"ws://127.0.0.1:{self.expo_port}/message"
            with ws_client.connect(ws_url, open_timeout=2) as ws:
                ws.send(json.dumps({"method": "reload", "params": {}}))
                self.emit_log("expo-log", '[Controller] > Broadcasted reload command to connected Expo devices via WebSocket.\n')
                reloaded = True
        except Exception:
            pass

        # 2. Trigger HTTP reload endpoints
        try:
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{self.expo_port}/reload", method="POST")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    self.emit_log("expo-log", '[Controller] > Triggered HTTP /reload endpoint.\n')
                    reloaded = True
        except Exception:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.expo_port}/_expo/reload", method="POST")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        reloaded = True
            except Exception:
                pass

        # 3. Send "r\n" to stdin if process stdin is available
        if self.expo_process and self.expo_process.poll() is None and self.expo_process.stdin:
            try:
                self.expo_process.stdin.write("r\n")
                self.expo_process.stdin.flush()
                self.emit_log("expo-log", '[Controller] > Sent "r" keystroke signal to Expo process.\n')
                reloaded = True
            except Exception:
                pass

        if not reloaded:
            self.emit_log("expo-log", "[Controller] Restarting Expo dev server...\n")
            self.stop_expo()
            time.sleep(0.5)
            self.start_expo()
            return False

        return True

    def stop_expo(self) -> None:
        with self._lock:
            if self.expo_process:
                self._kill_process(self.expo_process)
                self.expo_process = None
            self.is_expo_running = False
            self.expo_url = ""
            self.emit_status()

    # ------------------------- Stream Server -------------------------
    def start_stream_server(self) -> None:
        with self._lock:
            if self.stream_process is not None and self.stream_process.poll() is None:
                return

            self.stream_port = find_free_port(8080)
            server_dir = resolve_project_dir("screen-stream-server")
            py_exe = get_python_exe()

            env = os.environ.copy()
            env["STREAM_PORT"] = str(self.stream_port)
            env["PYTHONUNBUFFERED"] = "1"

            self.emit_log(
                "python-log",
                f"[Controller] Starting screen-stream-server on port {self.stream_port}\n",
            )

            try:
                self.stream_process = subprocess.Popen(
                    [py_exe, "main.py"],
                    cwd=server_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                self.is_python_running = True
                self.emit_status()

                threading.Thread(
                    target=self._reader_thread,
                    args=(self.stream_process.stdout, "python-log", None),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._reader_thread,
                    args=(self.stream_process.stderr, "python-log", None),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._wait_process,
                    args=(self.stream_process, "stream"),
                    daemon=True,
                ).start()

            except Exception as e:
                self.emit_log("python-log", f"[SPAWN ERROR] Screen stream server failed: {e}\n")
                self.is_python_running = False
                self.stream_process = None
                self.emit_status()

    # ------------------------- Backend Agent -------------------------
    def start_backend(self) -> None:
        with self._lock:
            if self.backend_process is not None and self.backend_process.poll() is None:
                return

            self.backend_port = find_free_port(8000)
            backend_dir = resolve_project_dir("vedi-pocketpc-backend")
            py_exe = get_python_exe()

            env = os.environ.copy()
            env["BACKEND_PORT"] = str(self.backend_port)
            env["PYTHONUNBUFFERED"] = "1"
            env["HIDE_DIALOG"] = "1"

            self.emit_log(
                "python-log",
                f"[Controller] Starting vedi-pocketpc-backend on port {self.backend_port}\n",
            )

            try:
                self.backend_process = subprocess.Popen(
                    [py_exe, "main.py"],
                    cwd=backend_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                self.is_backend_running = True
                self.emit_status()

                threading.Thread(
                    target=self._reader_thread,
                    args=(self.backend_process.stdout, "python-log", self._on_backend_stdout),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._reader_thread,
                    args=(self.backend_process.stderr, "python-log", None),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=self._wait_process,
                    args=(self.backend_process, "backend"),
                    daemon=True,
                ).start()

            except Exception as e:
                self.emit_log("python-log", f"[SPAWN ERROR] FastAPI backend failed: {e}\n")
                self.is_backend_running = False
                self.backend_process = None
                self.emit_status()

    def _on_backend_stdout(self, line: str) -> None:
        match = re.search(r"Pairing PIN:\s*(\d{4})", line)
        if match:
            pin = match.group(1)
            if pin != self.pairing_pin:
                self.pairing_pin = pin
                self.emit_log("python-log", f"[Controller] Captured Pairing PIN: {pin}\n")
                self.emit_status()

    # ------------------------- Aggregates -------------------------
    def start_all(self) -> None:
        self.start_expo()
        time.sleep(0.5)
        self.start_stream_server()
        self.start_backend()

    def stop_stream_and_backend(self) -> None:
        with self._lock:
            if self.stream_process:
                self._kill_process(self.stream_process)
                self.stream_process = None
            if self.backend_process:
                self._kill_process(self.backend_process)
                self.backend_process = None
            self.is_python_running = False
            self.is_backend_running = False
            self.pairing_pin = ""
            self.emit_status()

    def stop_all(self) -> None:
        self.stop_stream_and_backend()
        self.stop_expo()

    def restart_all(self) -> None:
        self.stop_all()
        time.sleep(0.8)
        self.start_all()

    # ------------------------- Helpers -------------------------
    def _reader_thread(
        self,
        pipe,
        channel: str,
        line_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not pipe:
            return
        try:
            for line in iter(pipe.readline, ""):
                if not line:
                    break
                self.emit_log(channel, line)
                if line_cb:
                    try:
                        line_cb(line)
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def _wait_process(self, proc: subprocess.Popen, name: str) -> None:
        code = proc.wait()
        self.emit_log(
            "python-log" if name in ("stream", "backend") else "expo-log",
            f"[Controller] {name} process exited with code {code}\n",
        )
        if name == "expo":
            self.is_expo_running = False
            self.expo_process = None
        elif name == "stream":
            self.is_python_running = False
            self.stream_process = None
        elif name == "backend":
            self.is_backend_running = False
            self.backend_process = None
        self.emit_status()

    def _kill_process(self, proc: subprocess.Popen) -> None:
        if not proc or proc.poll() is not None:
            return
        pid = proc.pid
        if sys.platform == "win32":
            try:
                subprocess.run(
                    f"taskkill /pid {pid} /T /F",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except Exception:
                pass
        else:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
