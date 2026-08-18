"""Production configuration loader for Vedi Pocket PC.

Three-tier resolution:

1. Defaults compiled into this module (sensible production values).
2. ``%LOCALAPPDATA%\\Vedi Pocket PC\\config.json`` — per-user overrides.
3. (Development only) ``.env`` at the repository root.

No secrets, no developer paths, no personal IPs live in the
defaults. The application discovers the LAN IP at runtime.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import user_data_dir


log = logging.getLogger(__name__)


# --- Defaults -----------------------------------------------------------
# Pinned to the same port numbers the wire-protocol already speaks.
# The mobile app (Android APK) is hard-coded to look for these; do
# not change without co-ordinating with the mobile app release.

DEFAULT_CONTROLLER_HOST = "0.0.0.0"
DEFAULT_CONTROLLER_PORT = 8090        # desktop management UI
DEFAULT_STREAM_HOST = "0.0.0.0"
DEFAULT_STREAM_PORT = 8080            # JPEG screen stream WebSocket
DEFAULT_BACKEND_HOST = "0.0.0.0"
DEFAULT_BACKEND_PORT = 8000           # FastAPI pairing / control agent
DEFAULT_EXPO_PORT = 8088              # legacy — only used if a dev-mode
                                     # Expo server is explicitly enabled

DEFAULT_FPS = 30
DEFAULT_JPEG_QUALITY = 50
DEFAULT_MAX_WIDTH = 1280
DEFAULT_MAX_HEIGHT = 720
DEFAULT_MONITOR_INDEX = 1
DEFAULT_MOUSE_SENSITIVITY = 1.5
DEFAULT_SCROLL_SENSITIVITY = 1.0


@dataclass
class AppConfig:
    """Resolved, ready-to-use configuration for every component."""

    controller_host: str = DEFAULT_CONTROLLER_HOST
    controller_port: int = DEFAULT_CONTROLLER_PORT
    stream_host: str = DEFAULT_STREAM_HOST
    stream_port: int = DEFAULT_STREAM_PORT
    backend_host: str = DEFAULT_BACKEND_HOST
    backend_port: int = DEFAULT_BACKEND_PORT
    expo_port: int = DEFAULT_EXPO_PORT

    fps: int = DEFAULT_FPS
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    max_width: int = DEFAULT_MAX_WIDTH
    max_height: int = DEFAULT_MAX_HEIGHT
    monitor_index: int = DEFAULT_MONITOR_INDEX
    mouse_sensitivity: float = DEFAULT_MOUSE_SENSITIVITY
    scroll_sensitivity: float = DEFAULT_SCROLL_SENSITIVITY

    # Mobile companion: ships a release-build APK by default and
    # leaves Expo off, but most controller builds are developer
    # builds that want the Metro dev server running so they can scan
    # the QR code from the Expo Go client on their phone. Flip this
    # to False in ``%LOCALAPPDATA%\Vedi Pocket PC\config.json`` (or
    # via the ``EXPO_ENABLED=0`` env var) to suppress auto-start.
    expo_enabled: bool = True

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_overrides_env(self) -> Dict[str, str]:
        """Turn this config into ``KEY=VALUE`` strings for child env vars.

        Used when the screen-stream server or backend is started as
        an in-process ``os.environ`` patch (we still keep the legacy
        env-var API so any future subprocess can pick them up).
        """
        return {
            "STREAM_HOST": self.stream_host,
            "STREAM_PORT": str(self.stream_port),
            "STREAM_FPS": str(self.fps),
            "STREAM_JPEG_QUALITY": str(self.jpeg_quality),
            "STREAM_MAX_WIDTH": str(self.max_width),
            "STREAM_MAX_HEIGHT": str(self.max_height),
            "STREAM_MONITOR_INDEX": str(self.monitor_index),
            "STREAM_MOUSE_SENSITIVITY": str(self.mouse_sensitivity),
            "STREAM_SCROLL_SENSITIVITY": str(self.scroll_sensitivity),
            "BACKEND_HOST": self.backend_host,
            "BACKEND_PORT": str(self.backend_port),
            "CONTROLLER_PORT": str(self.controller_port),
        }


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def load_config() -> AppConfig:
    """Build the runtime ``AppConfig`` by overlaying files on defaults."""
    cfg = AppConfig()

    # 1) Repo-local .env (developer convenience). Only consulted when
    # running from source — production users never have a .env.
    repo_env = Path(__file__).resolve().parent.parent / ".env"
    if repo_env.is_file():
        try:
            for raw_line in repo_env.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
        except OSError as exc:
            log.warning("Could not parse %s: %s", repo_env, exc)

    # 2) Per-user overrides.
    user_cfg_path = user_data_dir() / "config.json"
    user_overrides: Dict[str, Any] = {}
    if user_cfg_path.is_file():
        try:
            with user_cfg_path.open("r", encoding="utf-8") as fh:
                user_overrides = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("User config at %s is invalid; using defaults (%s)", user_cfg_path, exc)
            user_overrides = {}
    else:
        try:
            user_data_dir().mkdir(parents=True, exist_ok=True)
            with user_cfg_path.open("w", encoding="utf-8") as fh:
                json.dump(asdict(cfg), fh, indent=2)
        except OSError:
            pass

    # 3) Apply. Everything is defensive — bad values fall back to defaults.
    cfg.controller_host = user_overrides.get("controller_host", os.getenv("CONTROLLER_HOST", cfg.controller_host))
    cfg.controller_port = _coerce_int(user_overrides.get("controller_port", os.getenv("CONTROLLER_PORT")), cfg.controller_port)
    cfg.stream_host = user_overrides.get("stream_host", os.getenv("STREAM_HOST", cfg.stream_host))
    cfg.stream_port = _coerce_int(user_overrides.get("stream_port", os.getenv("STREAM_PORT")), cfg.stream_port)
    cfg.backend_host = user_overrides.get("backend_host", os.getenv("BACKEND_HOST", cfg.backend_host))
    cfg.backend_port = _coerce_int(user_overrides.get("backend_port", os.getenv("BACKEND_PORT")), cfg.backend_port)
    cfg.expo_port = _coerce_int(user_overrides.get("expo_port", os.getenv("EXPO_PORT")), cfg.expo_port)

    cfg.fps = _coerce_int(user_overrides.get("fps", os.getenv("STREAM_FPS")), cfg.fps)
    cfg.jpeg_quality = _coerce_int(user_overrides.get("jpeg_quality", os.getenv("STREAM_JPEG_QUALITY")), cfg.jpeg_quality)
    cfg.max_width = _coerce_int(user_overrides.get("max_width", os.getenv("STREAM_MAX_WIDTH")), cfg.max_width)
    cfg.max_height = _coerce_int(user_overrides.get("max_height", os.getenv("STREAM_MAX_HEIGHT")), cfg.max_height)
    cfg.monitor_index = _coerce_int(user_overrides.get("monitor_index", os.getenv("STREAM_MONITOR_INDEX")), cfg.monitor_index)
    cfg.mouse_sensitivity = _coerce_float(user_overrides.get("mouse_sensitivity", os.getenv("STREAM_MOUSE_SENSITIVITY")), cfg.mouse_sensitivity)
    cfg.scroll_sensitivity = _coerce_float(user_overrides.get("scroll_sensitivity", os.getenv("STREAM_SCROLL_SENSITIVITY")), cfg.scroll_sensitivity)

    cfg.expo_enabled = _coerce_bool(user_overrides.get("expo_enabled", os.getenv("EXPO_ENABLED")), cfg.expo_enabled)

    return cfg
