"""Production logging for Vedi Pocket PC.

Sends logs to *both* the per-user logs directory under
``%LOCALAPPDATA%\\Vedi Pocket PC\\logs\\`` and (when running from
source with a console attached) stderr. The directory exists at
``vedi_app.paths.logs_dir()``.

Never writes into the Program Files install directory — that would
require admin rights and break uninstall.

The configuration uses only stdlib logging so PyInstaller can find
every class without extra hooks.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .paths import APP_NAME, logs_dir


_LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _SafeRotatingHandler(logging.handlers.RotatingFileHandler):
    """Rotating file handler that tolerates a missing / read-only dir.

    PyInstaller onefile bundles extract to a per-launch temp dir; the
    user's ``%LOCALAPPDATA%`` is the canonical log destination. If
    that ever fails (locked profile, antivirus interference, no
    permission) the handler silently no-ops rather than crashing the
    application during startup.
    """

    def __init__(self, filename: Path, **kwargs) -> None:
        super().__init__(filename, encoding="utf-8", **kwargs)
        self._disabled = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._disabled:
            return
        try:
            super().emit(record)
        except (OSError, ValueError):
            self._disabled = True


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Install the production logging configuration.

    Idempotent — safe to call from every entry point without doubling
    handlers. Returns the root logger so callers can do
    ``log = configure_logging(); log.info(...)``.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Drop existing handlers (idempotent re-init).
    for existing in list(root.handlers):
        root.removeHandler(existing)

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    logs_path = logs_dir()
    log_file = logs_path / "vedi-pocketpc.log"

    file_handler = _SafeRotatingHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console handler only when stderr is a real terminal (e.g. running
    # from source or with `--debug`). For windowed EXE launches the
    # bootloader detaches the console, so writing to stderr there is
    # a no-op anyway — but we gate on sys.stderr.isatty() to keep the
    # log file the single source of truth in production.
    if sys.stderr is not None and getattr(sys.stderr, "isatty", lambda: False)():
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    # Tame the chatty libraries we depend on.
    for noisy in ("zeroconf", "asyncio", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.info("=== %s logger initialised (file=%s) ===", APP_NAME, log_file)
    return root


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience wrapper around ``logging.getLogger``."""
    return logging.getLogger(name)
