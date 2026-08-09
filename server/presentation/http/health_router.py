"""health_router — unified health/status/index endpoints."""

from __future__ import annotations

import time
from fastapi import APIRouter, Request

def build_router(container) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def get_index():
        # Stream info
        last_res = container.screen_capture.last_resolution
        max_w = container.settings.stream_max_width
        max_h = container.settings.stream_max_height
        
        if last_res[0] > 0 and last_res[1] > 0:
            res_str = f"{last_res[0]}x{last_res[1]}"
        else:
            res_str = f"{max_w}x{max_h}"

        monitors = container.screen_capture.get_monitors()

        return {
            "server": container.settings.server_name,
            "version": container.settings.server_version,
            "websocket": f"ws://{container.local_ip}:{container.port}/stream",
            "control_websocket": f"ws://{container.local_ip}:{container.port}/ws",
            "fps": container.settings.stream_fps,
            "resolution": res_str,
            "clients": container.screen_capture.client_count,
            "lan_ip": container.local_ip,
            "monitors": monitors,
        }

    @router.get("/health")
    def health_check():
        """Public reachability probe. No auth required."""
        return {
            "status": "ok",
            "service": container.settings.server_name,
            "agent_version": container.settings.server_version,
            "hostname": __import__("platform").node(),
            "ip": container.local_ip,
            "port": container.port,
            "uptime_seconds": int(time.time() - container.started_at),
        }

    return router
