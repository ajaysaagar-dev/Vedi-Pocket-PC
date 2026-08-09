"""System DTOs."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class VolumeRequest(BaseModel):
    level: int = Field(ge=0, le=100)

class PowerResponse(BaseModel):
    status: str

class SystemStatusResponse(BaseModel):
    hostname: str
    os: str
    os_release: str
    volume: int
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None
