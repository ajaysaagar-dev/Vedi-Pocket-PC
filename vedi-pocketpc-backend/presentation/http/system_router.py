"""system_router — POST /lock, /sleep, /shutdown. All require a valid
session token (enforced via the same dependency the pairing router
exposes)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_core.entities.pairing import SessionToken

from presentation.http.pairing_router import verify_token_header


def build_router(container) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_token_header)])

    @router.post("/lock")
    def lock_pc():
        ok = container.control_system.lock()
        return {"status": "success" if ok else "failed"}

    @router.post("/sleep")
    def sleep_pc():
        ok = container.control_system.sleep()
        return {"status": "success" if ok else "failed"}

    @router.post("/shutdown")
    def shutdown_pc():
        ok = container.control_system.shutdown()
        return {"status": "success" if ok else "failed"}

    return router
