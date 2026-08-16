from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routes.pairing import verify_token_header
import input_control

router = APIRouter(dependencies=[Depends(verify_token_header)])

class VolumeRequest(BaseModel):
    level: int

@router.post("/volume")
def set_absolute_volume(req: VolumeRequest):
    """
    Sets the master volume to an absolute percentage level (0 to 100).
    """
    if req.level < 0 or req.level > 100:
        raise HTTPException(status_code=400, detail="Volume level must be between 0 and 100")
    success = input_control.set_volume(req.level)
    return {"status": "success" if success else "failed", "volume": req.level}

@router.post("/volume/up")
def volume_up():
    """
    Presses the hardware volume up key.
    """
    input_control.press_key("volumeup")
    return {"status": "success", "volume": input_control.get_volume()}

@router.post("/volume/down")
def volume_down():
    """
    Presses the hardware volume down key.
    """
    input_control.press_key("volumedown")
    return {"status": "success", "volume": input_control.get_volume()}

@router.post("/volume/mute")
def volume_mute():
    """
    Toggles mute by pressing the hardware volume mute key.
    """
    input_control.press_key("volumemute")
    return {"status": "success"}

@router.post("/playpause")
def play_pause():
    """
    Sends the media play/pause key stroke.
    """
    input_control.press_key("playpause")
    return {"status": "success"}

@router.post("/next")
def next_track():
    """
    Sends the media next track key stroke.
    """
    input_control.press_key("nexttrack")
    return {"status": "success"}

@router.post("/prev")
def prev_track():
    """
    Sends the media previous track key stroke.
    """
    input_control.press_key("prevtrack")
    return {"status": "success"}
