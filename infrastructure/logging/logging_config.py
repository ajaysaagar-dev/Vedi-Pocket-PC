"""logging_config — single source of truth for log formatting."""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Set up a consistent log format for stdout.

    Called once from the composition root. Idempotent so test code
    that imports the package can call it freely.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
