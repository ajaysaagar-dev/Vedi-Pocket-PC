"""Unified server configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass, field

@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("VEDI_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("VEDI_PORT", "8000")))
    
    # Stream capture
    stream_fps: int = field(default_factory=lambda: int(os.getenv("STREAM_FPS", "30")))
    stream_jpeg_quality: int = field(default_factory=lambda: int(os.getenv("STREAM_JPEG_QUALITY", "50")))
    stream_max_width: int = field(default_factory=lambda: int(os.getenv("STREAM_MAX_WIDTH", "640")))
    stream_max_height: int = field(default_factory=lambda: int(os.getenv("STREAM_MAX_HEIGHT", "360")))
    stream_monitor_index: int = field(default_factory=lambda: int(os.getenv("STREAM_MONITOR_INDEX", "1")))
    
    # Auth
    paired_ips_file: str = field(default_factory=lambda: os.getenv("VEDI_PAIRED_IPS", os.path.join(os.path.expanduser("~"), ".vedi_paired_ips.json")))
    
    # Metadata
    server_name: str = "Vedi Pocket PC Server"
    server_version: str = "2.0.0"
