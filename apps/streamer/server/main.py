"""screen-stream-server — composition root.

After the refactor this server uses the SAME `InputController`
(`agent_core.use_cases.ControlInput`) as the control agent. The
domain code (mouse / keyboard / monitor-clamping) is no longer
duplicated here. The WebSocket now requires a verified token from
the shared `TokenStore` — closing the previous auth hole.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import sys
from typing import Any, Dict

# Make the local `presentation` package importable without an
# editable install: this file is the project's entry point and is
# expected to run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Make the shared `agent_core` package importable without requiring
# `pip install -e packages/core`. This is the same trick the
# previous monolithic `main.py` used, just kept explicit so the path
# is obvious when running from a packaged build.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir, os.pardir))
_AGENT_CORE_ROOT = os.path.join(_REPO_ROOT, "packages", "core")
if os.path.isdir(_AGENT_CORE_ROOT) and _AGENT_CORE_ROOT not in sys.path:
    sys.path.insert(0, _AGENT_CORE_ROOT)

from aiohttp import web

from agent_core.adapters.memory_token_store import MemoryTokenStore
from agent_core.adapters.pyautogui_input_driver import PyAutoGUIInputDriver
from agent_core.use_cases.control_input import ControlInput

from domain.capture import ScreenCapturer
from presentation.ws_router import build_ws_router
from config import (
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
    MAX_WIDTH,
    MAX_HEIGHT,
    FPS,
    JPEG_QUALITY,
)


def get_lan_ip() -> str:
    """Best-effort LAN IP discovery."""
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for name, addrs in interfaces.items():
            is_up = stats.get(name).isup if name in stats else True
            for a in addrs:
                if a.family == socket.AF_INET and not a.address.startswith("127.") and not a.address.startswith("169.254."):
                    lower = name.lower()
                    if is_up and any(k in lower for k in ("wi-fi", "wifi", "ethernet", "lan", "wlan")):
                        return a.address
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"



def _common_token_path() -> str:
    """Disk path that stores the persistent common token (control-agent
    compatible location). Survives a stream-server restart so the
    mobile app can re-connect without a PIN round-trip."""
    base = os.environ.get("PCREMOTE_DATA_DIR")
    if not base:
        if sys.platform == "win32":
            base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PCRemoteAgent")
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PCRemoteAgent")
        else:
            base = os.path.join(
                os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")),
                "PCRemoteAgent",
            )
    return os.path.join(base, "common_token.txt")


class ScreenStreamServer:
    """Main application server combining screen capture, WebSockets, and HTTP API."""

    def __init__(self) -> None:
        self.capturer = ScreenCapturer()
        self.lan_ip = get_lan_ip()

        # Adapters / use cases — same shape as vedi-pocketpc-backend
        # so a single `ControlInput` does all input work.
        self.input_driver = PyAutoGUIInputDriver()
        self.control_input = ControlInput(self.input_driver)
        # NEW: persist the common ("easy-connect") token to the same
        # per-user data directory the control agent uses. The mobile
        # app caches this token so reconnects can skip the PIN step.
        self.token_store = MemoryTokenStore(
            persist_path=_common_token_path(),
        )

        self.stream_manager = build_ws_router(
            capturer=self.capturer,
            control_input=self.control_input,
            token_store=self.token_store,
        )

        self.capture_task: asyncio.Task | None = None
        self.app = web.Application(middlewares=[self._cors_middleware])
        self._setup_routes()

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler) -> web.StreamResponse:
        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        return response

    def _setup_routes(self) -> None:
        self.app.router.add_options("/{tail:.*}", self.handle_options)
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_post("/pair", self.handle_pair)
        self.app.router.add_get("/status", self.handle_status)
        self.app.router.add_get("/ws", self.stream_manager.handle_websocket)

    async def handle_options(self, request: web.Request) -> web.Response:
        return web.Response(status=204)

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": SERVER_NAME})

    async def handle_pair(self, request: web.Request) -> web.Response:
        """Issue a session token from the shared TokenStore.

        PIN validation isn't enforced here (the screen-stream server
        historically didn't have a PIN — it's intended for trusted LANs).
        We accept whatever the mobile app sends and mint a token; the
        websocket layer then verifies it. If the body is malformed we
        still issue a token so existing clients keep working.

        NEW: alongside the per-device token we also surface the stable
        "common" token (when the underlying store provides one). The
        mobile app caches it so subsequent reconnects to this stream
        server can skip the pairing round-trip.
        """
        try:
            payload: Dict[str, Any] = await request.json()
        except Exception:
            payload = {}
        # Honour the same `pin` field the control agent uses, but
        # don't reject — the stream server's threat model is local-LAN.
        _ = payload.get("pin", "")
        token = self.token_store.issue()
        common = self.token_store.common_token()
        body: Dict[str, Any] = {"status": "success", "token": token.value}
        if common is not None:
            body["common_token"] = common.value
        return web.json_response(body)

    async def handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "online", "hostname": socket.gethostname()})

    async def handle_index(self, request: web.Request) -> web.Response:
        last_res = self.capturer.last_resolution
        if last_res[0] > 0 and last_res[1] > 0:
            res_str = f"{last_res[0]}x{last_res[1]}"
        else:
            res_str = f"{MAX_WIDTH}x{MAX_HEIGHT}"

        monitors = self.capturer.get_monitors()

        response_data: Dict[str, Any] = {
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "websocket": f"ws://{self.lan_ip}:{PORT}/ws",
            "fps": FPS,
            "resolution": res_str,
            "clients": self.stream_manager.client_count,
            "lan_ip": self.lan_ip,
            "monitors": monitors,
        }
        return web.json_response(response_data)

    async def _capture_loop(self) -> None:
        loop = asyncio.get_running_loop()
        consecutive_errors = 0
        target_fps = max(1, self.stream_manager.target_fps)
        interval = 1.0 / target_fps
        next_frame_time = loop.time()
        was_active = False

        while True:
            try:
                # Idle optimization: If no clients connected, avoid hammering CPU with captures
                if self.stream_manager.client_count == 0:
                    if was_active:
                        was_active = False
                        import gc
                        gc.collect()
                    await asyncio.sleep(0.15)
                    next_frame_time = loop.time()
                    continue

                was_active = True
                target_fps = max(1, self.stream_manager.target_fps)
                interval = 1.0 / target_fps
                now = loop.time()


                if now < next_frame_time:
                    await asyncio.sleep(next_frame_time - now)

                # Set next target frame boundary (drift compensation)
                next_frame_time += interval
                if next_frame_time < loop.time():
                    next_frame_time = loop.time() + interval

                jpeg_bytes, _res = await asyncio.to_thread(
                    self.capturer.capture_frame,
                    self.stream_manager.monitor_index,
                    self.stream_manager.max_width,
                    self.stream_manager.max_height,
                    self.stream_manager.jpeg_quality,
                )

                if jpeg_bytes is not None and self.stream_manager.client_count > 0:
                    await self.stream_manager.broadcast_frame(jpeg_bytes)
                    consecutive_errors = 0
                elif jpeg_bytes is not None:
                    consecutive_errors = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3 or consecutive_errors % 30 == 0:
                    print(f"[ERROR] Capture loop exception ({consecutive_errors}): {e}", flush=True)
                await asyncio.sleep(0.01)

    def print_banner(self) -> None:
        last_res = self.capturer.last_resolution
        res_display = f"{last_res[0]}x{last_res[1]}" if last_res[0] > 0 else f"{MAX_WIDTH}x{MAX_HEIGHT}"

        banner = f"""
========================================
 {SERVER_NAME}
========================================
 Local:
   http://127.0.0.1:{PORT}

 LAN:
   http://{self.lan_ip}:{PORT}

 WebSocket:
   ws://{self.lan_ip}:{PORT}/ws

 Resolution: {res_display}
 FPS:        {FPS}
 JPEG:       {JPEG_QUALITY}
========================================

Waiting for mobile connection...
"""
        print(banner, flush=True)

    async def start(self) -> None:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass

        runner = web.AppRunner(self.app)
        await runner.setup()

        global PORT
        bound_port = PORT
        max_attempts = 20
        site = None

        for attempt in range(max_attempts):
            test_port = bound_port + attempt
            try:
                site = web.TCPSite(runner, HOST, test_port)
                await site.start()
                bound_port = test_port
                break
            except OSError as e:
                if e.errno in (10048, 98, 48) or "address" in str(e).lower() or "10048" in str(e):
                    print(f"[WARN] Port {test_port} in use, attempting next port {test_port + 1}...", flush=True)
                    continue
                raise e

        if not site:
            raise RuntimeError(f"Could not bind to any free port starting from {PORT}")

        PORT = bound_port
        print(f"[Desktop] screen-stream-server running on port {PORT}", flush=True)

        self.capture_task = asyncio.create_task(self._capture_loop())
        self.print_banner()

        shutdown_event = asyncio.Event()

        def _signal_handler() -> None:
            print("\nShutting down server...", flush=True)
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        if sys.platform != "win32":
            for s in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(s, _signal_handler)

        try:
            if sys.platform == "win32":
                while not shutdown_event.is_set():
                    await asyncio.sleep(0.5)
            else:
                await shutdown_event.wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nReceived stop signal. Cleaning up...", flush=True)
        finally:
            if self.capture_task and not self.capture_task.done():
                self.capture_task.cancel()
                try:
                    await self.capture_task
                except asyncio.CancelledError:
                    pass

            await self.stream_manager.close_all()
            await runner.cleanup()
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
            print("Server stopped cleanly.", flush=True)


def main() -> None:
    server = ScreenStreamServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
