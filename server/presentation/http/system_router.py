"""system_router — POST /lock, /sleep, /shutdown. All require a valid
session token (enforced via the same dependency the pairing router
exposes)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from server.application.dto.system_dto import PowerResponse
from server.presentation.dependencies import verify_token


def build_router(container) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_token)])

    @router.post("/lock", response_model=PowerResponse)
    def lock_pc():
        ok = container.control_system.lock()
        return PowerResponse(status="success" if ok else "failed")

    @router.post("/sleep", response_model=PowerResponse)
    def sleep_pc():
        ok = container.control_system.sleep()
        return PowerResponse(status="success" if ok else "failed")

    @router.post("/shutdown", response_model=PowerResponse)
    def shutdown_pc():
        ok = container.control_system.shutdown()
        return PowerResponse(status="success" if ok else "failed")

    return router
