"""media_router — /volume and media-key endpoints. Token-gated."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_core.entities.input_command import KeyPressCommand, TextInputCommand

from protocol.http.pairing_router import verify_token_header


class VolumeRequest(BaseModel):
    level: int


def build_router(container) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_token_header)])

    def _press(key: str):
        container.control_input.execute(KeyPressCommand(key=key))

    @router.post("/volume")
    def set_absolute_volume(req: VolumeRequest):
        if req.level < 0 or req.level > 100:
            raise HTTPException(status_code=400, detail="Volume level must be between 0 and 100")
        result = container.control_system.set_volume(req.level)
        return {"status": "success" if result is not None else "failed", "volume": req.level}

    @router.post("/volume/up")
    def volume_up():
        _press("volumeup")
        return {"status": "success", "volume": container.control_system.get_volume().percent}

    @router.post("/volume/down")
    def volume_down():
        _press("volumedown")
        return {"status": "success", "volume": container.control_system.get_volume().percent}

    @router.post("/volume/mute")
    def volume_mute():
        _press("volumemute")
        return {"status": "success"}

    @router.post("/playpause")
    def play_pause():
        _press("playpause")
        return {"status": "success"}

    @router.post("/next")
    def next_track():
        _press("nexttrack")
        return {"status": "success"}

    @router.post("/prev")
    def prev_track():
        _press("prevtrack")
        return {"status": "success"}

    # Type endpoint (used by DesktopViewport's text-input modal).
    @router.post("/type")
    def type_text(req: dict):
        text = (req or {}).get("text", "")
        container.control_input.execute(TextInputCommand(text=text))
        return {"status": "success"}

    return router
