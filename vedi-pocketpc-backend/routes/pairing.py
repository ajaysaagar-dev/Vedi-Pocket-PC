import platform
import os
import time
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from state import state
from input_control import get_volume

router = APIRouter()

# Track agent startup time so /health can report uptime
_AGENT_START_TIME = time.time()

class PairRequest(BaseModel):
    pin: str

class PairResponse(BaseModel):
    token: str
    status: str

# Helper to verify token from header
def verify_token_header(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header format (Bearer <token> expected)")
        token = parts[1]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    if not state.verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid session token")
    return token

@router.get("/health")
def health_check():
    """
    Public reachability probe. No auth required.
    Used by the mobile app to verify the agent is reachable before
    attempting to pair. Also useful for ad-hoc `curl` diagnostics.
    """
    return {
        "status": "ok",
        "agent_version": "1.0.0",
        "hostname": platform.node(),
        "ip": state.local_ip,
        "port": state.port,
        "uptime_seconds": int(time.time() - _AGENT_START_TIME),
    }

@router.post("/pair", response_model=PairResponse)
def pair_device(req: PairRequest):
    """
    Pairs the mobile client with the laptop by verifying the 4-digit PIN.
    Returns a signed session token.
    """
    if req.pin == state.pairing_pin:
        token = state.generate_token()
        print(f"[AUTH] Device successfully paired! Token issued.")
        return PairResponse(token=token, status="success")
    else:
        print(f"[AUTH] Failed pairing attempt with PIN: {req.pin}")
        raise HTTPException(status_code=400, detail="Invalid PIN code")

@router.get("/status")
def get_system_status(token: str = Depends(verify_token_header)):
    """
    Returns general OS status, volume, and connection status.
    """
    # Simple battery lookup using psutil if available, otherwise return None
    battery_percent = None
    power_plugged = None
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            power_plugged = battery.power_plugged
    except Exception:
        pass

    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "hostname": platform.node(),
        "volume": get_volume(),
        "battery": {
            "percent": battery_percent,
            "plugged": power_plugged
        }
    }
