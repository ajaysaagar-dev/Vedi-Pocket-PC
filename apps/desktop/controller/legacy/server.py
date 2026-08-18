"""Aiohttp HTTP & WebSocket Controller Server for Vedi Pocket PC.

Serves the frontend UI assets and handles REST / WebSocket controller API calls.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Dict, Set

from aiohttp import web

from .network import get_lan_ip
from .process_manager import ProcessManager
from .qr import to_data_url

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# When the application is packaged with PyInstaller, the static assets
# (index.html, styles.css, …) sit at the bundle root (``_internal/``),
# not alongside this file (``_internal/apps/desktop/controller/``).
# Probe both locations so the controller UI can be served from
# either layout — source checkout or frozen EXE — without code
# changes at the call site.
_BUNDLE_ROOTS = [
    ROOT_DIR,
    os.path.abspath(os.path.join(ROOT_DIR, "..", "..", "..")),
]


def _resolve_static(filename: str) -> str:
    """Return the first existing path for ``filename`` across the
    candidate roots, falling back to ``ROOT_DIR`` if none match.
    """
    for base in _BUNDLE_ROOTS:
        candidate = os.path.join(base, filename)
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(ROOT_DIR, filename)


class ControllerServer:
    def __init__(self, process_manager: ProcessManager, host: str = "0.0.0.0", port: int = 8090) -> None:
        self.pm = process_manager
        self.host = host
        self.port = port
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        self.app = web.Application(middlewares=[self._cors_middleware])
        self.ws_clients: Set[web.WebSocketResponse] = set()

        self._setup_routes()
        self.pm.add_log_listener(self._on_process_log)
        self.pm.add_status_listener(self._on_process_status)

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

        # API
        self.app.router.add_get("/api/server-info", self.handle_get_server_info)
        self.app.router.add_post("/api/start-servers", self.handle_start_servers)
        self.app.router.add_post("/api/stop-servers", self.handle_stop_servers)
        self.app.router.add_post("/api/restart-servers", self.handle_restart_servers)
        self.app.router.add_post("/api/reload-expo", self.handle_reload_expo)
        self.app.router.add_get("/api/probe-health", self.handle_probe_health)
        self.app.router.add_post("/api/generate-qr", self.handle_generate_qr)

        # WebSocket events for logs and live status updates
        self.app.router.add_get("/ws/events", self.handle_ws_events)

        # Static files
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/styles.css", self.handle_static_css)
        self.app.router.add_get("/renderer.js", self.handle_static_js)
        self.app.router.add_get("/logo.jpeg", self.handle_static_logo)
        self.app.router.add_get("/logo.ico", self.handle_static_ico)

    async def handle_options(self, request: web.Request) -> web.Response:
        return web.Response(status=204)

    async def handle_index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(_resolve_static("index.html"))

    async def handle_static_css(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(_resolve_static("styles.css"))

    async def handle_static_js(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(_resolve_static("renderer.js"))

    async def handle_static_logo(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(_resolve_static("logo.jpeg"))

    async def handle_static_ico(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(_resolve_static("logo.ico"))


    async def _build_full_info(self) -> dict:
        base = self.pm.get_status_payload()
        loop = asyncio.get_running_loop()
        server_qr = await loop.run_in_executor(None, to_data_url, base["pairingUrl"])
        expo_qr = (
            await loop.run_in_executor(None, to_data_url, base["expoUrl"])
            if self.pm.is_expo_running
            else ""
        )
        return {**base, "serverQr": server_qr, "expoQr": expo_qr}

    async def handle_get_server_info(self, request: web.Request) -> web.Response:
        info = await self._build_full_info()
        return web.json_response(info)

    async def handle_start_servers(self, request: web.Request) -> web.Response:
        self.pm.start_all()
        return web.json_response({"success": True})

    async def handle_stop_servers(self, request: web.Request) -> web.Response:
        self.pm.stop_all()
        return web.json_response({"success": True})

    async def handle_restart_servers(self, request: web.Request) -> web.Response:
        self.pm.restart_all()
        return web.json_response({"success": True})

    async def handle_reload_expo(self, request: web.Request) -> web.Response:
        success = self.pm.reload_expo()
        return web.json_response({"success": success})

    async def handle_probe_health(self, request: web.Request) -> web.Response:
        lan_ip = self.pm.lan_ip or get_lan_ip()
        stream_port = self.pm.stream_port
        backend_port = self.pm.backend_port

        stream_url = f"http://{lan_ip}:{stream_port}/health"
        backend_url = f"http://{lan_ip}:{backend_port}/health"

        out = {"streamReachable": False, "backendReachable": False}

        import aiohttp

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1.2)) as session:
            try:
                async with session.get(stream_url) as res:
                    out["streamReachable"] = res.status == 200
            except Exception:
                out["streamReachable"] = False

            try:
                async with session.get(backend_url) as res:
                    out["backendReachable"] = res.status == 200
            except Exception:
                out["backendReachable"] = False

        return web.json_response(out)

    async def handle_generate_qr(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
            text = body.get("text", "")
        except Exception:
            text = request.query.get("text", "")
        loop = asyncio.get_running_loop()
        qr_data = await loop.run_in_executor(None, to_data_url, text)
        return web.json_response({"qr": qr_data})

    async def handle_ws_events(self, request: web.Request) -> web.WebSocketResponse:
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)

        # Send initial status snapshot
        try:
            info = await self._build_full_info()
            await ws.send_json({"type": "status-update", "data": info})
        except Exception:
            pass

        try:
            async for msg in ws:
                pass
        finally:
            self.ws_clients.discard(ws)
        return ws

    async def _send_to_all_ws(self, payload: str) -> None:
        for ws in list(self.ws_clients):
            if not ws.closed:
                try:
                    await ws.send_str(payload)
                except Exception:
                    pass

    def _on_process_log(self, channel: str, message: str) -> None:
        if not self.ws_clients:
            return
        payload = json.dumps({"type": "log", "channel": channel, "payload": message})
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send_to_all_ws(payload), self.loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._send_to_all_ws(payload))
            except Exception:
                pass

    def _on_process_status(self, data: dict) -> None:
        if not self.ws_clients:
            return

        async def _push():
            info = await self._build_full_info()
            payload = json.dumps({"type": "status-update", "data": info})
            await self._send_to_all_ws(payload)

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_push(), self.loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(_push())
            except Exception:
                pass
