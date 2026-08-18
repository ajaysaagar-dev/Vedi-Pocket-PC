"""Infrastructure — process-level concerns (logging, mDNS). No use
cases or adapters here."""

from . import networking, logging

__all__ = ["networking", "logging"]
