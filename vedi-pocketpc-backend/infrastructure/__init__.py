"""Infrastructure — process-level concerns (logging, mDNS). No use
cases or adapters here."""

from infrastructure import discovery, logging_config

__all__ = ["discovery", "logging_config"]
