"""pairing_router — /health, /pair, /status.

Login flow is preserved exactly: same paths, same request bodies,
same response shape. The mobile app's pairing.tsx already speaks
this wire format and we deliberately don't change it.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from agent_core.entities.pairing import PairResult, SessionToken


class PairRequest(BaseModel):
    pin: str


class PairResponse(BaseModel):
    token: str
    status: str


def _container(request: Request):
    return request.app.state.container


def verify_token_header(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> SessionToken:
    """FastAPI dependency: rejects requests without a valid bearer token.

    The mobile app's WebSocket client already sends `Authorization:
    Bearer <token>` on every REST call after pairing; we just verify it
    against the shared `TokenStore`.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format (Bearer <token> expected)",
        )

    client_ip = request.client.host if request.client else None
    container = request.app.state.container
    token = SessionToken(value=parts[1])
    if not container.token_store.verify(token, client_ip=client_ip):
        raise HTTPException(status_code=401, detail="Invalid session token")
    return token


def build_router(container) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health_check():
        """Public reachability probe. No auth required."""
        return {
            "status": "ok",
            "agent_version": "1.0.0",
            "hostname": __import__("platform").node(),
            "ip": container.local_ip,
            "port": container.port,
            "uptime_seconds": int(time.time() - container.started_at),
        }

    @router.post("/pair", response_model=PairResponse)
    def pair_device(req: PairRequest, request: Request):
        client_ip = request.client.host if request.client else None
        result: PairResult = container.pair_device.pair(req.pin)
        if not result.accepted or result.device_token is None:
            print(f"[AUTH] Failed pairing attempt with PIN: {req.pin} from {client_ip}")
            raise HTTPException(status_code=400, detail=result.reason or "Invalid PIN code")
        if client_ip:
            container.token_store.register_ip(client_ip)
        print(f"[AUTH] Device successfully paired from {client_ip}! Token issued.")
        return PairResponse(token=result.device_token.value, status="success")

    @router.get("/status")
    def get_system_status(_token: SessionToken = Depends(verify_token_header)):
        snap = container.control_system.snapshot()
        return {
            "os": snap.os,
            "os_release": snap.os_release,
            "hostname": snap.hostname,
            "volume": snap.volume.percent,
            "battery": {
                "percent": snap.battery.percent,
                "plugged": snap.battery.plugged,
            },
        }

    return router
