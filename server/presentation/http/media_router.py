"""media_router — /volume and media-key endpoints. Token-gated."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.application.dto.system_dto import VolumeRequest
from server.domain.entities.input_command import KeyPressCommand, TextInputCommand
from server.presentation.dependencies import verify_token


def build_router(container) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_token)])

    def _press(key: str):
        container.control_input.execute(KeyPressCommand(key=key))

    @router.post("/volume")
    def set_absolute_volume(req: VolumeRequest):
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
