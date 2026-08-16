import os
import sys
import socket
import asyncio
import signal
from typing import Dict, Any
from aiohttp import web

import config
from capture import ScreenCapturer
from streaming import StreamManager


def get_lan_ip() -> str:
    """Automatically determines the PC's primary LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to non-routable address to discover outbound interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ScreenStreamServer:
    """Main application server combining screen capture, WebSockets, and HTTP API."""

    def __init__(self) -> None:
        self.capturer = ScreenCapturer()
        self.stream_manager = StreamManager()
        self.lan_ip = get_lan_ip()
        self.capture_task: asyncio.Task | None = None
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_post("/pair", self.handle_pair)
        self.app.router.add_get("/status", self.handle_status)
        self.app.router.add_get("/ws", self.stream_manager.handle_websocket)

    async def handle_health(self, request: web.Request) -> web.Response:
        """GET /health endpoint for reachability probes."""
        return web.json_response({"status": "ok", "service": config.SERVER_NAME})

    async def handle_pair(self, request: web.Request) -> web.Response:
        """POST /pair endpoint returning a valid session token."""
        return web.json_response({"status": "success", "token": "stream_paired_token"})

    async def handle_status(self, request: web.Request) -> web.Response:
        """GET /status endpoint returning host info."""
        return web.json_response({"status": "online", "hostname": socket.gethostname()})

    async def handle_index(self, request: web.Request) -> web.Response:
        """GET / endpoint returning server metadata, WS URL, resolution, and monitor list."""
        last_res = self.capturer.last_resolution
        if last_res[0] > 0 and last_res[1] > 0:
            res_str = f"{last_res[0]}x{last_res[1]}"
        else:
            res_str = f"{config.MAX_WIDTH}x{config.MAX_HEIGHT}"

        monitors = self.capturer.get_monitors()

        response_data: Dict[str, Any] = {
            "server": config.SERVER_NAME,
            "version": config.SERVER_VERSION,
            "websocket": f"ws://{self.lan_ip}:{config.PORT}/ws",
            "fps": config.FPS,
            "resolution": res_str,
            "clients": self.stream_manager.client_count,
            "lan_ip": self.lan_ip,
            "monitors": monitors
        }
        return web.json_response(response_data)

    async def _capture_loop(self) -> None:
        """Continuous background task capturing screen frames with dynamic resolution and FPS settings."""
        loop = asyncio.get_running_loop()

        while True:
            t0 = loop.time()
            # Calculate dynamic interval from current stream_manager target_fps
            interval = 1.0 / max(1, self.stream_manager.target_fps)

            try:
                # Capture and encode frame using realtime requested resolution & quality
                jpeg_bytes, _res = await asyncio.to_thread(
                    self.capturer.capture_frame,
                    config.MONITOR_INDEX,
                    self.stream_manager.max_width,
                    self.stream_manager.max_height,
                    self.stream_manager.jpeg_quality
                )

                # Broadcast frame only if there are connected clients
                if self.stream_manager.client_count > 0:
                    await self.stream_manager.broadcast_frame(jpeg_bytes)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Capture loop exception: {e}")

            # Precise FPS timing calculation
            elapsed = loop.time() - t0
            sleep_time = max(0.001, interval - elapsed)
            await asyncio.sleep(sleep_time)

    def print_banner(self) -> None:
        """Displays startup configuration and connection URLs."""
        last_res = self.capturer.last_resolution
        res_display = f"{last_res[0]}x{last_res[1]}" if last_res[0] > 0 else f"{config.MAX_WIDTH}x{config.MAX_HEIGHT}"

        banner = f"""
========================================
 {config.SERVER_NAME}
========================================
 Local:
   http://127.0.0.1:{config.PORT}

 LAN:
   http://{self.lan_ip}:{config.PORT}

 WebSocket:
   ws://{self.lan_ip}:{config.PORT}/ws

 Resolution: {res_display}
 FPS:        {config.FPS}
 JPEG:       {config.JPEG_QUALITY}
========================================

Waiting for mobile connection...
"""
        print(banner, flush=True)

    async def start(self) -> None:
        """Starts HTTP/WS server and background screen capture loop."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, config.HOST, config.PORT)
        await site.start()

        # Start capture loop
        self.capture_task = asyncio.create_task(self._capture_loop())

        self.print_banner()

        # Shutdown signal handler event
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
                # On Windows, keep waiting while listening for KeyboardInterrupt
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
            print("Server stopped cleanly.", flush=True)


def main() -> None:
    server = ScreenStreamServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
