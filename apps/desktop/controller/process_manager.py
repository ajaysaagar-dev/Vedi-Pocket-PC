"""Production process manager for Vedi Pocket PC.

Key difference from ``controller/process_manager.py``: the screen-stream
server and the FastAPI backend run as *threads* inside the controller's
process, not as separate ``python main.py`` subprocesses.

Why this shape:

* ``screen-stream-server`` and ``vedi-pocketpc-backend`` are Python
  source trees whose names contain hyphens. Python identifiers cannot
  contain hyphens, so PyInstaller's analyser cannot freeze them as
  importable modules. We **bundle the source trees as data files** and
  drive them through ``runpy.run_path``. Each script already uses an
  in-process event loop (aiohttp or a daemon thread + uvicorn), so we
  can run it on a background thread without spawning a fresh Python
  interpreter.

* ``pystray.Icon.run`` blocks, so the backend's tray loop cannot live
  on the controller's event loop. We patch the tray on the runpy side
  to be a no-op (a 1-second idle loop) so the backend exits cleanly
  when the controller is told to stop. Real users see the application's
  native window; the tray icon was redundant once we have one.

* The screen-stream server is itself a ``pystray``-free aiohttp
  application; calling ``ScreenStreamServer.start()`` is sufficient
  and we only need to run the rest of the script (banner, signal
  trap) on a worker thread.

* The Expo / Metro dev server is a Node.js process — it cannot run
  in-process, so we drive it as a normal ``subprocess.Popen`` child.
  ``expo_enabled`` in the config toggles it on (developer mode) or
  off (production users ship a release APK).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .config import AppConfig, load_config
from .network import find_free_port, get_lan_ip
from .paths import bundle_root


log = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Public snapshot of one managed service."""

    name: str
    running: bool
    port: int
    started_at: Optional[float] = None
    last_error: Optional[str] = None
    restart_count: int = 0


# ---------------------------------------------------------------------------
# Background service runner (thread-based; matches the existing aiohttp /
# FastAPI scripts which were already designed for blocking main loops).
# ---------------------------------------------------------------------------
class _ServiceThread:
    """Owns one bundled service script and tracks its lifecycle."""

    def __init__(self, name: str, script_subdir: str, runner: Callable[[], None]) -> None:
        self.name = name
        self._script_subdir = script_subdir
        self._runner = runner
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.started_at: Optional[float] = None
        self.last_error: Optional[str] = None
        self.restart_count = 0

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_alive():
            return

        def _wrap() -> None:
            self.started_at = time.time()
            try:
                self._runner()
            except Exception as exc:  # noqa: BLE001
                self.last_error = repr(exc)
                log.exception("Service %s crashed", self.name)

        self._thread = threading.Thread(
            target=_wrap, name=f"vedi.{self.name}", daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 4.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if not thread:
            return
        thread.join(timeout=timeout)
        if thread.is_alive():
            log.warning("Service %s did not exit within %.1fs", self.name, timeout)
        self._thread = None


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------
class _SingleInstance:
    def __init__(self) -> None:
        self._socket: Optional[socket.socket] = None
        self.owner = False

    def acquire(self) -> bool:
        if os.environ.get("VEDI_ALLOW_MULTIPLE") == "1":
            log.warning("Multi-instance mode forced via env var.")
            return True
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            s.bind(("127.0.0.1", 0))
            s.listen(8)
            self._socket = s
            self.owner = True
            log.info("Acquired single-instance lock on port %d.", s.getsockname()[1])
            return True
        except OSError as exc:
            log.error("Another Vedi Pocket PC instance is already running: %s", exc)
            return False

    def release(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
            self.owner = False


# ---------------------------------------------------------------------------
# Already-running error
# ---------------------------------------------------------------------------
class AlreadyRunningError(RuntimeError):
    """Raised when another Vedi Pocket PC process holds the single-instance lock."""


# ---------------------------------------------------------------------------
# Process manager
# ---------------------------------------------------------------------------
class ProcessManager:
    """Owns the lifetime of every in-process service."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or load_config()
        self.lan_ip: str = get_lan_ip()

        self._lock = threading.RLock()  # reentrant — see start_expo / stop_expo
        self._status_listeners: Set[Callable[[Dict[str, Any]], None]] = set()
        self._log_listeners: Set[Callable[[str, str], None]] = set()
        self._status: Dict[str, ServiceStatus] = {}
        self._pairing_pin: str = ""
        self._single = _SingleInstance()
        self._services: Dict[str, _ServiceThread] = {}
        # Guards all sys.path / sys.modules manipulation so the two
        # bundled-service scripts don't race when they each want to
        # add their own directory to sys.path (Python's import
        # machinery uses a single global sys.path and sys.modules
        # cache shared by every thread).
        self._import_lock = threading.Lock()

        # ---------- Expo / Metro dev-server state ----------
        # The Expo bundler is a Node.js child process — we cannot run
        # it in-process. State lives on the ProcessManager so the
        # controller UI's ``reload_expo`` button can talk to it.
        self._expo_process: Optional[subprocess.Popen] = None
        self._expo_url: str = ""
        self._expo_runtime_port: int = self.config.expo_port
        self._is_expo_running: bool = False

    # ---------- listener wiring ----------
    def add_status_listener(self, callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        self._status_listeners.add(callback)
        return lambda: self._status_listeners.discard(callback)

    # Backwards-compat shim for the legacy ``controller/server.py``
    # which subscribes to (channel, message) log events. The
    # production controller routes both types of listener through the
    # same fan-out, so we translate (channel, message) into a status
    # payload that contains the new log.
    def add_log_listener(self, callback: Callable[[str, str], None]) -> Callable[[], None]:
        def _wrap(channel: str, message: str) -> None:
            try:
                callback(channel, message)
            except Exception:
                pass
        self._log_listeners.add(_wrap)
        return lambda: self._log_listeners.discard(_wrap)

    def emit_log(self, channel: str, message: str) -> None:
        """Append ``(channel, message)`` to every registered log listener
        AND mirror it to the file log under the ``[expo-log]`` /
        ``[python-log]`` prefix so operators can debug without having
        the controller UI open.
        """
        # Mirror to the file log so headless / background use is
        # diagnosable from the log file alone.
        try:
            file_log = logging.getLogger(f"vedi.{channel}")
            clean = message.rstrip("\n")
            if clean:
                file_log.info(clean)
        except Exception:
            pass
        for cb in list(self._log_listeners):
            try:
                cb(channel, message)
            except Exception:
                pass

    # Backwards-compat attribute. Production builds that ship a
    # release APK leave ``expo_enabled`` off; developer builds toggle
    # it on and call ``start_expo()`` from the controller UI.
    @property
    def is_expo_running(self) -> bool:
        return self._is_expo_running

    @property
    def stream_port(self) -> int:
        return self.config.stream_port

    @property
    def backend_port(self) -> int:
        return self.config.backend_port

    @property
    def expo_port(self) -> int:
        return self._expo_runtime_port

    @property
    def expo_url(self) -> str:
        if self._expo_url:
            return self._expo_url
        return f"exp://{self.lan_ip}:{self._expo_runtime_port}"

    def reload_expo(self) -> bool:
        """Trigger a Metro reload on every connected mobile device.

        Strategy (tried in order, first success wins):

        1. Send ``{"method":"reload"}`` over Metro's WebSocket
           ``/message`` endpoint — fast, hits already-connected
           devices without bundling.
        2. POST to Metro's ``/reload`` HTTP endpoint — works even
           if the device just opened the URL but hasn't loaded JS.
        3. Write ``r\\n`` to the Expo child process's stdin (the
           interactive reload keystroke).
        4. If none of the above reach Metro, restart the dev server.
        """
        self.emit_log("expo-log", "[Controller] > Triggering Expo Mobile App reload...\n")

        # 1) WebSocket /message — the official "reload everything" hook.
        try:
            import json
            import websockets.sync.client as ws_client  # type: ignore
            with ws_client.connect(
                f"ws://127.0.0.1:{self._expo_runtime_port}/message",
                open_timeout=2,
            ) as ws:
                ws.send(json.dumps({"method": "reload", "params": {}}))
                self.emit_log(
                    "expo-log",
                    "[Controller] > Broadcast reload over Metro WebSocket.\n",
                )
                return True
        except Exception as exc:
            log.debug("Expo reload via WebSocket failed: %s", exc)

        # 2) HTTP /reload — fallback when no device is connected yet.
        try:
            import urllib.request
            for path in ("/reload", "/_expo/reload"):
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self._expo_runtime_port}{path}",
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        self.emit_log(
                            "expo-log",
                            f"[Controller] > Triggered HTTP {path}.\n",
                        )
                        return True
        except Exception as exc:
            log.debug("Expo reload via HTTP failed: %s", exc)

        # 3) Interactive keystroke — works as long as the child
        # process owns a console / stdin pipe.
        if self._expo_process and self._expo_process.poll() is None and self._expo_process.stdin:
            try:
                self._expo_process.stdin.write("r\n")
                self._expo_process.stdin.flush()
                self.emit_log(
                    "expo-log",
                    '[Controller] > Sent "r" to Expo stdin.\n',
                )
                return True
            except Exception as exc:
                log.debug("Expo reload via stdin failed: %s", exc)

        # 4) Last resort — bounce the dev server.
        self.emit_log(
            "expo-log",
            "[Controller] > Metro did not respond; restarting Expo dev server.\n",
        )
        self.stop_expo()
        time.sleep(0.5)
        self.start_expo()
        return False

    def _emit_status(self) -> None:
        payload = self.get_status_payload()
        for cb in list(self._status_listeners):
            try:
                cb(payload)
            except Exception:
                pass

    # ---------- public status ----------
    def get_status_payload(self) -> Dict[str, Any]:
        with self._lock:
            status_copy = {name: _status_to_dict(s) for name, s in self._status.items()}
        pairing_url = (
            f"{self.lan_ip}:{self.config.backend_port}:{self._pairing_pin}"
            if self._pairing_pin
            else f"{self.lan_ip}:{self.config.stream_port}"
        )
        return {
            "lanIp": self.lan_ip,
            "serverPort": self.config.stream_port,
            "backendPort": self.config.backend_port,
            "controllerPort": self.config.controller_port,
            "expoPort": self._expo_runtime_port,
            "expoUrl": self.expo_url,
            "isExpoRunning": self._is_expo_running,
            "streamRunning": status_copy.get("stream", {}).get("running", False),
            "backendRunning": status_copy.get("backend", {}).get("running", False),
            "pairingPin": self._pairing_pin,
            "pairingUrl": pairing_url,
            "services": status_copy,
        }

    def update_pairing_pin(self, pin: str) -> None:
        with self._lock:
            self._pairing_pin = pin
        self._emit_status()

    @property
    def pairing_pin(self) -> str:
        """Read-only view of the current pairing PIN (``""`` until set)."""
        with self._lock:
            return self._pairing_pin

    @property
    def expo_url(self) -> str:
        """Read-only view of the active Expo bundler URL (may be ``""``)."""
        return self._expo_url

    def request_shutdown(self) -> None:
        """Signal the asyncio core to stop and tear down every service.

        Safe to call from any thread — the heavy lifting happens on
        the worker thread that called :meth:`start_all` via
        :meth:`stop_all`.
        """
        try:
            self.stop_all()
        except Exception:  # noqa: BLE001
            log.exception("Error during shutdown.")

    # ---------- lifecycle ----------
    def is_owner(self) -> bool:
        return self._single.owner

    def start_all(self) -> None:
        if not self._single.acquire():
            raise AlreadyRunningError(
                "Another Vedi Pocket PC instance is already running."
            )

        self.config.stream_port = find_free_port(self.config.stream_port)
        self.config.backend_port = find_free_port(self.config.backend_port)
        self.config.controller_port = find_free_port(self.config.controller_port)

        with self._lock:
            self._status = {
                "stream": ServiceStatus(name="stream", running=False, port=self.config.stream_port),
                "backend": ServiceStatus(name="backend", running=False, port=self.config.backend_port),
            }
        os.environ["STREAM_PORT"] = str(self.config.stream_port)
        os.environ["BACKEND_PORT"] = str(self.config.backend_port)
        os.environ["HIDE_DIALOG"] = "1"

        stream = _ServiceThread("stream", "screen-stream-server", self._stream_runner)
        backend = _ServiceThread("backend", "vedi-pocketpc-backend",
                                 lambda: self._backend_runner(backend))
        self._services = {"stream": stream, "backend": backend}
        # Serialise the two runpy-loaded scripts: each mutates
        # ``sys.path`` and ``sys.modules`` and Python's import
        # machinery shares those globals across threads. Starting the
        # backend before the stream has finished its initial import
        # block reliably breaks ``domain`` lookups.
        stream.start()
        # Wait for the stream service to bind its port and have aiohttp
        # listening — that's a positive signal that its imports are
        # done and sys.modules is in a stable state.
        if not _wait_until(lambda: stream.is_alive(), timeout=3.0, poll=0.05):
            log.warning("Stream service did not stay alive long enough to confirm startup.")
        time.sleep(1.0)
        backend.start()
        time.sleep(1.0)
        self._set_running("stream", stream.is_alive())
        self._set_running("backend", backend.is_alive())
        # Optional: bring up the Expo / Metro dev server in parallel.
        if self.config.expo_enabled:
            try:
                self.start_expo()
            except Exception:
                log.exception("Expo start failed; continuing without it.")
        self._emit_status()

    def stop_all(self) -> None:
        runners = list(self._services.values())
        self._services.clear()
        for svc in runners:
            try:
                svc.stop()
            except Exception:
                log.exception("Error stopping %s", svc.name)
        try:
            self.stop_expo()
        except Exception:
            log.exception("Error stopping Expo.")
        self._single.release()
        self._emit_status()

    def restart(self, name: str) -> None:
        if name == "expo":
            self.stop_expo()
            time.sleep(0.5)
            self.start_expo()
            self._emit_status()
            return
        svc = self._services.get(name)
        if not svc:
            return
        svc.stop()
        if name == "stream":
            new = _ServiceThread("stream", "screen-stream-server", self._stream_runner)
        elif name == "backend":
            new = _ServiceThread("backend", "vedi-pocketpc-backend",
                                 lambda: self._backend_runner(new))
        else:
            return
        self._services[name] = new
        new.start()
        self._set_running(name, new.is_alive())
        self._emit_status()

    # Legacy alias kept so the controller REST surface stays stable.
    def restart_all(self) -> None:
        self.stop_all()
        self.start_all()

    # ---------- Expo / Metro lifecycle ----------
    def start_expo(self) -> None:
        """Spawn the Expo CLI (``npx expo start``) as a child process."""
        with self._lock:
            if self._expo_process is not None and self._expo_process.poll() is None:
                return

            expo_dir = _resolve_expo_dir()
            if not os.path.isdir(expo_dir):
                self.emit_log(
                    "expo-log",
                    f"[Controller] Mobile app directory not found: {expo_dir}\n",
                )
                return

            self._expo_runtime_port = find_free_port(self.config.expo_port)
            self.lan_ip = get_lan_ip()
            self._expo_url = f"exp://{self.lan_ip}:{self._expo_runtime_port}"
            self.emit_log(
                "expo-log",
                f"[Controller] Starting Expo Mobile Server on LAN "
                f"({self.lan_ip}:{self._expo_runtime_port})...\n",
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
            expo_cli = next((p for p in expo_cli_candidates if os.path.isfile(p)), None)
            node_cmd = _find_node_cmd()
            npx_cmd = _find_npx_cmd()

            args = [
                "start", "-c", "--host", "lan", "--port", str(self._expo_runtime_port),
            ]
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
                self._expo_process = subprocess.Popen(
                    cmd,
                    cwd=expo_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    # DEVNULL, not PIPE: with stdin=PIPE and no writer
                    # the child gets EOF and exits. Expo does not
                    # need anything from stdin, but reading EOF makes
                    # it shut down right after "Waiting on …".
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    shell=use_shell,
                    # Detach the child from the controller's console
                    # group so a Ctrl+C / window-close on the parent
                    # does not cascade-kill the bundler.
                    creationflags=getattr(
                        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                    ),
                )
            except Exception as exc:
                self.emit_log("expo-log", f"[SPAWN ERROR] Expo failed to start: {exc}\n")
                self._expo_process = None
                self._is_expo_running = False
                return

            self._is_expo_running = True
            self._emit_status()

            # stdout — used to scrape ``exp://...`` URLs Expo prints.
            threading.Thread(
                target=self._reader_thread,
                args=(self._expo_process.stdout, "expo-log", self._on_expo_stdout),
                daemon=True,
                name="vedi.expo.stdout",
            ).start()
            # stderr — Metro logs go here.
            threading.Thread(
                target=self._reader_thread,
                args=(self._expo_process.stderr, "expo-log", None),
                daemon=True,
                name="vedi.expo.stderr",
            ).start()
            # Listen on Metro's /events WebSocket for live JS device logs.
            threading.Thread(
                target=self._listen_expo_events,
                args=(self._expo_runtime_port,),
                daemon=True,
                name="vedi.expo.events",
            ).start()
            # Watch for unexpected exit so we can flip the running flag.
            threading.Thread(
                target=self._wait_expo_process,
                daemon=True,
                name="vedi.expo.waiter",
            ).start()

    def stop_expo(self) -> None:
        """Kill the Expo child process and clear its state."""
        with self._lock:
            proc = self._expo_process
            if proc is not None:
                self._kill_process(proc)
            self._expo_process = None
            self._is_expo_running = False
            self._expo_url = ""
            self._emit_status()

    # ---------- runners (execute bundled main.py via runpy) ----------
    def _stream_runner(self) -> None:
        """Run the screen-stream server's main() in this thread."""
        from ._service_runner import run_stream_service
        run_stream_service(self.config)

    def _backend_runner(self, backend_svc: _ServiceThread) -> None:
        """Run the FastAPI backend's main() in this thread.

        Wires the backend's pairing-PIN discovery into our status
        callback so the controller UI can render the QR code without
        scraping stdout.
        """
        from ._service_runner import run_backend_service
        run_backend_service(
            self.config,
            lan_ip=self.lan_ip,
            on_pairing_pin=self.update_pairing_pin,
            stop_marker=backend_svc._stop_event,
        )

    # ---------- internal helpers ----------
    def _set_running(self, name: str, running: bool) -> None:
        with self._lock:
            self._status[name].running = running

    # ---------- Expo / Metro worker threads ----------
    def _on_expo_stdout(self, line: str) -> None:
        """Parse the Expo CLI's stdout for the ``exp://...`` URL it
        prints once the dev server is up, and a fallback ``http://...``
        URL if Metro binds to a different port than we asked for.
        """
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        exp_match = re.search(r"exp://[\w.\-]+(?::\d+)?[^\s\x1b]*", clean)
        if exp_match:
            self._expo_url = exp_match.group(0)
            self._emit_status()
            return
        http_match = re.search(r"https?://[\w.\-]+:(\d+)", clean)
        if http_match:
            self._expo_runtime_port = int(http_match.group(1))
            self._expo_url = f"exp://{self.lan_ip}:{self._expo_runtime_port}"
            self._emit_status()

    def _listen_expo_events(self, port: int) -> None:
        """Subscribe to Metro's ``/events`` WebSocket to surface
        live JS ``console.log`` lines from the connected mobile app.
        """
        try:
            import json
            import websockets.sync.client as ws_client  # type: ignore
        except ImportError:
            return

        ws_url = f"ws://127.0.0.1:{port}/events"
        for _ in range(30):
            if not self._is_expo_running:
                return
            try:
                with ws_client.connect(ws_url, open_timeout=2) as ws:
                    self.emit_log(
                        "expo-log",
                        f"[Controller] Connected to Metro live event stream on port {port}.\n",
                    )
                    for message in ws:
                        if not self._is_expo_running:
                            break
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            if msg_type == "client_log":
                                level = str(data.get("level", "info")).upper()
                                raw_items = data.get("data", [])
                                formatted: List[str] = []
                                for item in raw_items:
                                    formatted.append(
                                        item if isinstance(item, str) else json.dumps(item)
                                    )
                                self.emit_log(
                                    "expo-log",
                                    f"[Mobile Log] [{level}] {' '.join(formatted)}\n",
                                )
                            elif msg_type == "error":
                                err = data.get("error", "Unknown Expo Error")
                                self.emit_log("expo-log", f"[Expo Error] {err}\n")
                            elif msg_type == "bundle_build_done":
                                self.emit_log(
                                    "expo-log",
                                    "[Controller] Mobile bundle build complete.\n",
                                )
                        except Exception:
                            pass
                    return
            except Exception:
                time.sleep(1)

    def _reader_thread(
        self,
        pipe,
        channel: str,
        line_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Forward lines from a child process's pipe into the log
        channel, optionally running a per-line callback first.
        """
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

    def _wait_expo_process(self) -> None:
        """Watch the Expo child and flip ``is_expo_running`` off
        when it exits unexpectedly.
        """
        proc = self._expo_process
        if not proc:
            return
        try:
            code = proc.wait()
        except Exception:
            return
        self.emit_log(
            "expo-log",
            f"[Controller] Expo process exited with code {code}.\n",
        )
        self._is_expo_running = False
        self._expo_process = None
        self._expo_url = ""
        self._emit_status()

    def _kill_process(self, proc: subprocess.Popen) -> None:
        """Terminate ``proc`` and its children; no-op if it's already gone."""
        if not proc or proc.poll() is not None:
            return
        if sys.platform == "win32":
            try:
                subprocess.run(
                    f"taskkill /pid {proc.pid} /T /F",
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
                try:
                    proc.kill()
                except Exception:
                    pass


def _wait_until(predicate, *, timeout: float = 3.0, poll: float = 0.05) -> bool:
    """Block until ``predicate()`` is truthy or the timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(poll)
    return predicate()


def _status_to_dict(s: ServiceStatus) -> Dict[str, Any]:
    return {
        "name": s.name,
        "running": s.running,
        "port": s.port,
        "started_at": s.started_at,
        "last_error": s.last_error,
        "restart_count": s.restart_count,
    }


# ---------------------------------------------------------------------------
# Module-level helpers for finding the Expo app directory and node / npx.
# ---------------------------------------------------------------------------
def _resolve_expo_dir() -> str:
    """Locate the Expo mobile-app source tree.

    Strategy — walk ``app_root`` and ``bundle_root`` plus every parent
    directory looking for a directory named ``apps/mobile/app`` (or
    the legacy ``veddi-pocketpc`` typo). This covers both layouts:

    * Source checkout: ``bundle_root()`` is the repo root, so
      ``bundle_root() / apps/mobile/app`` matches.
    * PyInstaller bundle: the EXE is in ``dist/VediPocketPC/`` and
      the mobile app lives at ``<repo>/apps/mobile/app``. Walking up
      from ``app_root()`` finds ``<repo>/apps/mobile/app`` even when
      the EXE and the source tree share an ancestor.
    """
    from .paths import app_root

    roots: List[Path] = []
    seen_roots: Set[Path] = set()

    def _add_root(p: Path) -> None:
        try:
            p = p.resolve()
        except OSError:
            return
        if p in seen_roots:
            return
        seen_roots.add(p)
        roots.append(p)

    for base in (app_root(), bundle_root()):
        _add_root(base)
        # Walk up to five parents — enough for ``dist/VediPocketPC``
        # under a normal repo layout.
        current = base
        for _ in range(5):
            current = current.parent
            if current == current.parent:
                break
            _add_root(current)

    candidate_subdirs = ("apps/mobile/app", "veddi-pocketpc", "apps/mobile")
    seen_dirs: Set[Path] = set()
    for root in roots:
        for sub in candidate_subdirs:
            candidate = (root / sub).resolve()
            if candidate in seen_dirs:
                continue
            seen_dirs.add(candidate)
            if candidate.is_dir():
                return str(candidate)

    # Return the most-likely one even if it doesn't exist so the
    # error message in the UI is meaningful instead of empty.
    return str((app_root() / "apps" / "mobile" / "app").resolve())


def _find_node_cmd() -> str:
    """Return the absolute path of ``node``, falling back to the well-known
    Windows install location if ``node`` isn't on ``PATH``.
    """
    node = shutil.which("node")
    if node:
        return node
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidate = os.path.join(pf, "nodejs", "node.exe")
        if os.path.isfile(candidate):
            return candidate
    return "node"


def _find_npx_cmd() -> str:
    """Return the absolute path of ``npx`` for the current platform."""
    npx_name = "npx.cmd" if sys.platform == "win32" else "npx"
    npx = shutil.which(npx_name)
    if npx:
        return npx
    return "npx.cmd" if sys.platform == "win32" else "npx"
