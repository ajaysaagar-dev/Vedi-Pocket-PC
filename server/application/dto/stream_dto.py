"""Stream DTOs."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class StreamSettingsUpdate(BaseModel):
    max_width: Optional[int] = Field(None, ge=320, le=3840)
    max_height: Optional[int] = Field(None, ge=240, le=2160)
    fps: Optional[int] = Field(None, ge=1, le=60)
    jpeg_quality: Optional[int] = Field(None, ge=10, le=100)
