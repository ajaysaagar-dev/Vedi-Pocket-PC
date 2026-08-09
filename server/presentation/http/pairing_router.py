"""pairing_router — /pair, /status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from server.application.dto.pairing_dto import PairRequest, PairResponse
from server.application.dto.system_dto import SystemStatusResponse
from server.domain.entities.pairing import PairResult, SessionToken
from server.presentation.dependencies import verify_token


def build_router(container) -> APIRouter:
    router = APIRouter()

    @router.post("/pair", response_model=PairResponse)
    def pair_device(req: PairRequest, request: Request):
        client_ip = request.client.host if request.client else None
        result: PairResult = container.pair_device.pair(req.pin, client_ip=client_ip)
        
        if not result.accepted or result.device_token is None:
            print(f"[AUTH] Failed pairing attempt with PIN: '{req.pin}' from {client_ip} (Expected: '{container.pairing_pin.value}')")
            raise HTTPException(status_code=400, detail=result.reason or "Invalid PIN code")
            
        if client_ip:
            container.token_store.register_ip(client_ip)
            
        print(f"[AUTH] Device successfully paired from {client_ip}! Token issued.")
        return PairResponse(token=result.device_token.value, status="success")

    @router.get("/status", response_model=SystemStatusResponse)
    def get_system_status(_token: SessionToken = Depends(verify_token)):
        snap = container.control_system.snapshot()
        return SystemStatusResponse(
            os=snap.os,
            os_release=snap.os_release,
            hostname=snap.hostname,
            volume=snap.volume.percent,
            battery_percent=snap.battery.percent,
            battery_plugged=snap.battery.plugged,
        )

    return router
